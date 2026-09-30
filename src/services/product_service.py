import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from src.config.settings import Settings
from src.constants.user import UserRole
from src.models.po.product import Product
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.product import ProductCreateInfo
from src.models.schemas.product import ProductCreateResponseInfo
from src.models.schemas.product import ProductDeleteInfo
from src.models.schemas.product import ProductListResponseInfo
from src.models.schemas.product import ProductResponseInfo
from src.models.schemas.product import ProductUpdateInfo
from src.repositories.product_cache_repository import ProductCacheRepository
from src.repositories.product_cache_repository import ProductCacheRepositoryError
from src.repositories.product_repository import DuplicateProductRecordError
from src.repositories.product_repository import ProductRepository
from src.repositories.product_repository import ProductRepositoryError
from src.repositories.user_repository import UserRepository
from src.repositories.user_repository import UserRepositoryError
from src.services.authorization_service import AuthorizationContext
from src.services.authorization_service import AuthorizationService
from src.services.errors import ServiceUnavailableError
from src.services.product_errors import ProductCacheUnavailableError
from src.services.product_errors import ProductConflictError
from src.services.product_errors import ProductLabelNotFoundError
from src.services.product_errors import ProductNotFoundError
from src.services.product_errors import ProductPermissionError


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProtectedProductResult:
    context: AuthorizationContext
    info: ProductCreateResponseInfo | ProductListResponseInfo


class ProductService(object):
    def __init__(
        self,
        settings: Settings,
        products: ProductRepository,
        cache: ProductCacheRepository,
        users: UserRepository,
        authorization: AuthorizationService,
    ) -> None:
        self.__settings = settings
        self.__products = products
        self.__cache = cache
        self.__users = users
        self.__authorization = authorization

    async def add(
        self,
        auth: AuthorizationObject,
        info: ProductCreateInfo,
    ) -> ProtectedProductResult:
        context = await self.__authorize(auth)
        label_ids = await self.__resolve_label_ids(info.label_names)
        now = self.__utc_now()
        product = Product(
            id=str(time.time_ns() // 1_000_000),
            name=info.name,
            label_ids=",".join(str(label_id) for label_id in label_ids),
            cost=info.cost,
            price=info.price,
            delete_flag=False,
            created_uid=context.uid,
            created_at=now,
            updated_uid=context.uid,
            updated_at=now,
        )
        await self.__write_product(product, operation="add")
        await self.__refresh_session(context)
        return ProtectedProductResult(
            context=context,
            info=self.__to_create_response(await self.__to_response(product)),
        )

    async def get(
        self,
        auth: AuthorizationObject,
        product_id: str,
    ) -> ProtectedProductResult:
        context = await self.__authorize(auth)
        products = await self.__get_all_products()
        visible_products = [product for product in products if not product.delete_flag]
        if product_id.upper() != "ALL":
            visible_products = [
                product for product in visible_products if product.id == product_id
            ]
            if not visible_products:
                raise ProductNotFoundError
        await self.__refresh_session(context)
        return ProtectedProductResult(
            context=context,
            info=ProductListResponseInfo(
                [await self.__to_response(product) for product in visible_products]
            ),
        )

    async def update(
        self,
        auth: AuthorizationObject,
        info: ProductUpdateInfo,
    ) -> ProtectedProductResult:
        context = await self.__authorize(auth)
        label_ids = await self.__resolve_label_ids(info.label_names)
        current = await self.__find_visible_product(info.id)
        product = Product(
            id=current.id,
            name=info.name,
            label_ids=",".join(str(label_id) for label_id in label_ids),
            cost=info.cost,
            price=info.price,
            delete_flag=False,
            created_uid=current.created_uid,
            created_at=current.created_at,
            updated_uid=context.uid,
            updated_at=self.__utc_now(),
        )
        await self.__write_product(product, operation="update")
        await self.__refresh_session(context)
        return ProtectedProductResult(
            context=context,
            info=ProductListResponseInfo([await self.__to_response(product)]),
        )

    async def delete(
        self,
        auth: AuthorizationObject,
        info: ProductDeleteInfo,
    ) -> ProtectedProductResult:
        context = await self.__authorize(auth)
        current = await self.__find_visible_product(info.id)
        now = self.__utc_now()
        product = Product(
            id=current.id,
            name=current.name,
            label_ids=current.label_ids,
            cost=current.cost,
            price=current.price,
            delete_flag=True,
            created_uid=current.created_uid,
            created_at=current.created_at,
            updated_uid=context.uid,
            updated_at=now,
        )
        await self.__delete_product(product)
        await self.__refresh_session(context)
        return ProtectedProductResult(
            context=context,
            info=ProductListResponseInfo([await self.__to_response(product)]),
        )

    async def __authorize(self, auth: AuthorizationObject) -> AuthorizationContext:
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

    async def __write_product(self, product: Product, operation: str) -> None:
        try:
            async with self.__cache.products_lock():
                await self.__cache.invalidate_products()
                try:
                    async with self.__products.transaction() as connection:
                        if operation == "add":
                            await self.__products.create(product, connection)
                        else:
                            updated = await self.__products.update(product, connection)
                            if not updated:
                                raise ProductNotFoundError
                except DuplicateProductRecordError as error:
                    raise ProductConflictError from error
                await self.__replace_product_cache(product.id, operation)
        except (ProductConflictError, ProductNotFoundError):
            raise
        except ProductRepositoryError as error:
            raise ServiceUnavailableError from error
        except ProductCacheRepositoryError as error:
            raise ProductCacheUnavailableError from error

    async def __delete_product(self, product: Product) -> None:
        try:
            async with self.__cache.products_lock():
                await self.__cache.invalidate_products()
                async with self.__products.transaction() as connection:
                    deleted = await self.__products.soft_delete(
                        product.id,
                        product.updated_uid,
                        product.updated_at,
                        connection,
                    )
                    if not deleted:
                        raise ProductNotFoundError
                await self.__replace_product_cache(product.id, "delete")
        except ProductNotFoundError:
            raise
        except ProductRepositoryError as error:
            raise ServiceUnavailableError from error
        except ProductCacheRepositoryError as error:
            raise ProductCacheUnavailableError from error

    async def __replace_product_cache(self, product_id: str, operation: str) -> None:
        try:
            products = await self.__products.list_products()
            await self.__cache.replace_products(products)
        except (ProductRepositoryError, ProductCacheRepositoryError):
            LOGGER.exception(
                "Product cache replacement failed operation=%s product_id=%s",
                operation,
                product_id,
            )
            raise

    async def __get_all_products(self) -> list[Product]:
        try:
            products = await self.__cache.get_products()
            if products is not None:
                return products
            async with self.__cache.products_lock():
                products = await self.__cache.get_products()
                if products is None:
                    products = await self.__products.list_products()
                    await self.__cache.replace_products(products)
                return products
        except ProductRepositoryError as error:
            raise ServiceUnavailableError from error
        except ProductCacheRepositoryError as error:
            raise ProductCacheUnavailableError from error

    async def __find_visible_product(self, product_id: str) -> Product:
        products = await self.__get_all_products()
        for product in products:
            if product.id == product_id and not product.delete_flag:
                return product
        raise ProductNotFoundError

    async def __resolve_label_ids(self, label_names: str) -> list[int]:
        requested_names = [name.strip() for name in label_names.split(",")]
        labels = await self.__get_labels()
        label_ids = self.__lookup_label_ids(requested_names, labels)
        if label_ids is not None:
            return label_ids

        try:
            async with self.__cache.labels_lock():
                await self.__cache.invalidate_labels()
                labels = await self.__reload_labels()
        except ProductRepositoryError as error:
            raise ServiceUnavailableError from error
        except ProductCacheRepositoryError as error:
            raise ProductCacheUnavailableError from error
        label_ids = self.__lookup_label_ids(requested_names, labels)
        if label_ids is None:
            raise ProductLabelNotFoundError
        return label_ids

    async def __get_labels(self) -> dict[str, tuple[int, str]]:
        try:
            labels = await self.__cache.get_labels()
            if labels is not None:
                return labels
            async with self.__cache.labels_lock():
                labels = await self.__cache.get_labels()
                if labels is None:
                    labels = await self.__reload_labels()
                return labels
        except ProductRepositoryError as error:
            raise ServiceUnavailableError from error
        except ProductCacheRepositoryError as error:
            raise ProductCacheUnavailableError from error

    async def __reload_labels(self) -> dict[str, tuple[int, str]]:
        labels = await self.__products.list_labels()
        await self.__cache.replace_labels(labels)
        return {
            self.__cache.normalize_label_name(label.name): (label.id, label.name)
            for label in labels
        }

    @staticmethod
    def __lookup_label_ids(
        requested_names: list[str],
        labels: dict[str, tuple[int, str]],
    ) -> list[int] | None:
        label_ids: list[int] = []
        for name in requested_names:
            label = labels.get(name.casefold())
            if label is None:
                return None
            label_ids.append(label[0])
        return label_ids

    async def __to_response(self, product: Product) -> ProductResponseInfo:
        labels = await self.__get_labels()
        label_names: list[str] = []
        try:
            label_ids = [int(label_id) for label_id in product.label_ids.split(",")]
            for label_id in label_ids:
                label = next(
                    (
                        value
                        for value in labels.values()
                        if value[0] == label_id
                    ),
                    None,
                )
                if label is None:
                    raise ValueError
                label_names.append(label[1])
        except ValueError as error:
            raise ProductCacheUnavailableError from error
        return ProductResponseInfo(
            id=product.id,
            name=product.name,
            label_names=",".join(label_names),
            cost=product.cost,
            price=product.price,
            delete_flag=product.delete_flag,
            updated_user=product.updated_uid,
            updated_at=product.updated_at,
        )

    @staticmethod
    def __to_create_response(
        product: ProductResponseInfo,
    ) -> ProductCreateResponseInfo:
        return ProductCreateResponseInfo(
            id=product.id,
            name=product.name,
            label_names=product.label_names,
            cost=product.cost,
            price=product.price,
        )

    async def __refresh_session(self, context: AuthorizationContext) -> None:
        await self.__authorization.refresh_session(context)

    @staticmethod
    def __utc_now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
