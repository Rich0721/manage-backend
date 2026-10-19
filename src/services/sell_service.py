import logging
import re
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from src.constants.order import OrderMessage
from src.constants.user import UserRole
from src.models.po.order import OrderItemPO
from src.models.po.order import OrderPO
from src.models.po.order import OrderResult
from src.models.po.product import Product
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.order import GetOrderInfo
from src.models.schemas.order import GetOrderItemInfo
from src.models.schemas.order import GetOrdersResponseInfo
from src.models.schemas.order import SellOrderInfo
from src.models.schemas.order import SellOrderResponseInfo
from src.models.schemas.order import SellOrderResponseItem
from src.repositories.label_cache_repository import LabelCacheRepository
from src.repositories.label_cache_repository import LabelCacheRepositoryError
from src.repositories.label_repository import LabelRepository
from src.repositories.label_repository import LabelRepositoryError
from src.repositories.order_repository import OrderRepository
from src.repositories.order_repository import OrderRepositoryError
from src.repositories.product_cache_repository import ProductCacheRepository
from src.repositories.product_cache_repository import ProductCacheRepositoryError
from src.repositories.product_repository import ProductRepository
from src.repositories.product_repository import ProductRepositoryError
from src.repositories.user_repository import UserRepository
from src.repositories.user_repository import UserRepositoryError
from src.services.authorization_service import AuthorizationContext
from src.services.authorization_service import AuthorizationService
from src.services.errors import ServiceUnavailableError
from src.services.product_errors import ProductPermissionError
from src.services.order_errors import OrderBadRequestError
from src.services.order_errors import OrderNotFoundError
from src.services.order_errors import OrderServiceUnavailableError
from src.services.order_errors import SoldProductNotFoundError


LOGGER = logging.getLogger(__name__)
ORDER_ID_PATTERN = re.compile(r"^\d{10}$")


@dataclass(frozen=True, slots=True)
class ProtectedOrderResult:
    context: AuthorizationContext
    info: SellOrderResponseInfo | GetOrdersResponseInfo


class SellService(object):
    def __init__(
        self,
        orders: OrderRepository,
        products: ProductRepository,
        product_cache: ProductCacheRepository,
        labels: LabelRepository,
        label_cache: LabelCacheRepository,
        users: UserRepository,
        authorization: AuthorizationService,
    ) -> None:
        self.__orders = orders
        self.__products = products
        self.__product_cache = product_cache
        self.__labels = labels
        self.__label_cache = label_cache
        self.__users = users
        self.__authorization = authorization

    async def sell(
        self,
        auth: AuthorizationObject,
        info: SellOrderInfo,
    ) -> ProtectedOrderResult:
        context = await self.__authorize(auth)
        created_at = self.__utc_now()
        committed = False
        published = False
        products_by_id: dict[str, Product] = {}
        try:
            async with self.__product_cache.products_lock() as lease:
                await lease.ensure_held()
                async with self.__products.transaction() as connection:
                    for product_id in sorted(
                        item.product_id for item in info.order_items
                    ):
                        product = (
                            await self.__products.get_by_id_for_update_in_transaction(
                                product_id,
                                connection,
                            )
                        )
                        if product is None or product.delete_flag:
                            raise SoldProductNotFoundError
                        products_by_id[product_id] = product

                    # A missing/deleted product returns before changing the cache.
                    await lease.ensure_held()
                    await self.__product_cache.invalidate_products(lease)
                    order_id = await self.__orders.next_order_id(connection)
                    await self.__orders.insert_order(
                        OrderPO(
                            id=order_id,
                            total_amount=info.total_amount,
                            total_discount=info.total_discount,
                            created_uid=context.uid,
                            created_at=created_at,
                        ),
                        connection,
                    )
                    await self.__orders.insert_items(
                        [
                            OrderItemPO(
                                order_id=order_id,
                                product_id=item.product_id,
                                quantity=item.quantity,
                                price=item.price,
                                discount=item.discount,
                                created_at=created_at,
                                created_by=context.uid,
                            )
                            for item in info.order_items
                        ],
                        connection,
                    )
                    for item in info.order_items:
                        product = products_by_id[item.product_id]
                        stock = max(0, product.stock - item.quantity)
                        updated = await self.__products.update_stock_in_transaction(
                            item.product_id,
                            stock,
                            context.uid,
                            created_at,
                            connection,
                        )
                        if not updated:
                            raise SoldProductNotFoundError
                committed = True
                await lease.ensure_held()
                await self.__replace_product_cache(order_id, lease)
                published = True
        except (SoldProductNotFoundError, OrderBadRequestError):
            raise
        except (
            OrderRepositoryError,
            ProductRepositoryError,
            UserRepositoryError,
        ) as error:
            raise OrderServiceUnavailableError from error
        except (
            ProductCacheRepositoryError,
            LabelCacheRepositoryError,
            LabelRepositoryError,
        ) as error:
            raise OrderServiceUnavailableError from error
        finally:
            if committed and not published:
                await self.__invalidate_failed_publication()

        await self.__refresh_session(context)
        return ProtectedOrderResult(
            context=context,
            info=SellOrderResponseInfo(
                order_id=order_id,
                total_amount=info.total_amount,
                total_discount=info.total_discount,
                order_items=[
                    SellOrderResponseItem(
                        product_id=item.product_id,
                        quantity=item.quantity,
                        price=item.price,
                        discount=item.discount,
                    )
                    for item in info.order_items
                ],
            ),
        )

    async def get_order(
        self,
        auth: AuthorizationObject,
        order_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> ProtectedOrderResult:
        context = await self.__authorize(auth)
        if order_id.casefold() == "all":
            start = self.__parse_date(start_date, OrderMessage.START_DATE_REQUIRED)
            end = self.__parse_date(end_date, OrderMessage.END_DATE_REQUIRED)
            if start > end:
                raise OrderBadRequestError("查詢起始日期不得晚於結束日期")
            if (end - start).days > 30:
                raise OrderBadRequestError(OrderMessage.DATE_RANGE_TOO_LONG)
            try:
                results = await self.__orders.get_orders(
                    start_date=start,
                    end_date_exclusive=end + timedelta(days=1),
                )
            except OrderRepositoryError as error:
                raise OrderServiceUnavailableError from error
        else:
            if not ORDER_ID_PATTERN.fullmatch(order_id):
                raise OrderBadRequestError
            try:
                results = await self.__orders.get_orders(order_id=order_id)
            except OrderRepositoryError as error:
                raise OrderServiceUnavailableError from error
            if not results:
                raise OrderNotFoundError

        await self.__refresh_session(context)
        return ProtectedOrderResult(
            context=context,
            info=GetOrdersResponseInfo(
                [self.__to_response(result) for result in results]
            ),
        )

    async def __authorize(
        self,
        auth: AuthorizationObject,
    ) -> AuthorizationContext:
        context = await self.__authorization.validate_session(auth)
        try:
            operator = await self.__users.get_by_uid(context.uid)
        except UserRepositoryError as error:
            raise ServiceUnavailableError from error
        if operator is None or operator.permission not in (
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.USER,
        ):
            raise ProductPermissionError
        return context

    async def __replace_product_cache(self, order_id: str, lease: object) -> None:
        try:
            products = await self.__products.list_all()
            labels = await self.__get_labels()
            label_names_by_id = {
                label_id: label_name for label_id, label_name in labels.values()
            }
            await self.__product_cache.replace_products(
                products,
                label_names_by_id,
                lease,  # type: ignore[arg-type]
            )
        except (
            ProductRepositoryError,
            ProductCacheRepositoryError,
            LabelRepositoryError,
            LabelCacheRepositoryError,
        ):
            LOGGER.exception(
                "Product cache replacement failed after sale order_id=%s",
                order_id,
            )
            raise

    async def __get_labels(self) -> dict[str, tuple[int, str]]:
        labels = await self.__label_cache.get()
        if labels is not None:
            return labels
        async with self.__label_cache.lock() as lease:
            await lease.ensure_held()
            labels = await self.__label_cache.get()
            if labels is None:
                source_labels = await self.__labels.list_all()
                await self.__label_cache.replace(source_labels, lease)
                labels = await self.__label_cache.get()
                if labels is None:
                    raise LabelCacheRepositoryError
            return labels

    async def __invalidate_failed_publication(self) -> None:
        try:
            await self.__product_cache.invalidate_after_commit()
        except ProductCacheRepositoryError:
            LOGGER.exception(
                "Product cache invalidation failed after committed sale"
            )

    @staticmethod
    def __parse_date(value: str | None, missing_message: str) -> date:
        if value is None or not value.strip():
            raise OrderBadRequestError(missing_message)
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as error:
            raise OrderBadRequestError from error
        if parsed.isoformat() != value:
            raise OrderBadRequestError
        return parsed

    @staticmethod
    def __to_response(result: OrderResult) -> GetOrderInfo:
        return GetOrderInfo(
            order_id=result.id,
            total_amount=result.total_amount,
            total_discount=result.total_discount,
            created_at=result.created_at,
            created_by=result.created_by,
            order_items=[
                GetOrderItemInfo(
                    product_id=item.product_id,
                    product_name=item.product_name,
                    quantity=item.quantity,
                    price=item.price,
                    discount=item.discount,
                )
                for item in result.items
            ],
        )

    async def __refresh_session(self, context: AuthorizationContext) -> None:
        try:
            await self.__authorization.refresh_session(context)
        except ServiceUnavailableError as error:
            raise OrderServiceUnavailableError from error

    @staticmethod
    def __utc_now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
