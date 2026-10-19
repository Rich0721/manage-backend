from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal

import pytest

from src.constants.user import UserRole
from src.models.po.label import Label
from src.models.po.order import OrderItemPO
from src.models.po.order import OrderPO
from src.models.po.order import OrderItemResult
from src.models.po.order import OrderResult
from src.models.po.product import Product
from src.models.po.user import UserPO
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.order import SellOrderInfo
from src.repositories.order_repository import OrderRepositoryError
from src.repositories.product_cache_repository import ProductCacheRepositoryError
from src.repositories.product_repository import ProductRepositoryError
from src.services.authorization_service import AuthorizationContext
from src.services.order_errors import SoldProductNotFoundError
from src.services.order_errors import OrderBadRequestError
from src.services.order_errors import OrderServiceUnavailableError
from src.services.sell_service import SellService


NOW = datetime(2026, 10, 19, 12, 0, 0)


class FakeAuthorization:
    async def validate_session(
        self,
        auth: AuthorizationObject,
    ) -> AuthorizationContext:
        return AuthorizationContext(auth.uid or "", auth.authorization, False)

    async def refresh_session(self, context: AuthorizationContext) -> None:
        return None


class FakeUserRepository:
    async def get_by_uid(self, uid: str) -> UserPO:
        return UserPO(
            uid=uid,
            email="seller@example.com",
            user_name="Seller",
            password="unused",
            permission=UserRole.USER,
            created_at=NOW,
            updated_at=NOW,
        )


class FakeLease:
    def __init__(self) -> None:
        self.invalidated = False

    async def ensure_held(self) -> None:
        return None


class FakeProductCache:
    def __init__(self, products: list[Product]) -> None:
        self.products = products
        self.lease = FakeLease()
        self.replacements = 0
        self.invalidations = 0

    @asynccontextmanager
    async def products_lock(self):
        yield self.lease

    async def invalidate_products(self, lease: FakeLease) -> None:
        self.invalidations += 1
        self.products = None

    async def replace_products(
        self,
        products: list[Product],
        label_names_by_id: dict[int, str],
        lease: FakeLease,
    ) -> None:
        self.replacements += 1
        self.products = products

    async def invalidate_after_commit(self) -> None:
        self.products = None


class FailingProductCache(FakeProductCache):
    async def replace_products(
        self,
        products: list[Product],
        label_names_by_id: dict[int, str],
        lease: FakeLease,
    ) -> None:
        raise ProductCacheRepositoryError


class FakeProductRepository:
    def __init__(self, products: list[Product]) -> None:
        self.by_id = {product.id: product for product in products}
        self.transaction_calls = 0
        self.updated: list[tuple[str, int, str, datetime]] = []

    @asynccontextmanager
    async def transaction(self):
        snapshot = self.by_id.copy()
        updated_snapshot = list(self.updated)
        self.transaction_calls += 1
        try:
            yield object()
        except Exception:
            self.by_id = snapshot
            self.updated = updated_snapshot
            raise

    async def get_by_id_for_update_in_transaction(
        self,
        product_id: str,
        connection: object,
    ) -> Product | None:
        return self.by_id.get(product_id)

    async def update_stock_in_transaction(
        self,
        product_id: str,
        stock: int,
        updated_uid: str,
        updated_at: datetime,
        connection: object,
    ) -> bool:
        product = self.by_id.get(product_id)
        if product is None:
            return False
        self.by_id[product_id] = Product(
            id=product.id,
            name=product.name,
            label_ids=product.label_ids,
            cost=product.cost,
            price=product.price,
            stock=stock,
            delete_flag=product.delete_flag,
            created_uid=product.created_uid,
            created_at=product.created_at,
            updated_uid=updated_uid,
            updated_at=updated_at,
            label_names=product.label_names,
        )
        self.updated.append((product_id, stock, updated_uid, updated_at))
        return True

    async def list_all(self) -> list[Product]:
        return list(self.by_id.values())


class FakeOrderRepository:
    def __init__(self) -> None:
        self.orders: list[OrderPO] = []
        self.items: list[OrderItemPO] = []
        self.query_results: list[OrderResult] = []

    async def next_order_id(self, connection: object) -> str:
        return "0000000001"

    async def insert_order(self, order: OrderPO, connection: object) -> None:
        self.orders.append(order)

    async def insert_items(
        self,
        items: list[OrderItemPO],
        connection: object,
    ) -> None:
        self.items.extend(items)

    async def get_orders(self, **kwargs: object) -> list[OrderResult]:
        return self.query_results


class FakeLabelRepository:
    async def list_all(self) -> list[Label]:
        return []


class FakeLabelCache:
    @staticmethod
    async def get() -> dict[str, tuple[int, str]]:
        return {}


def make_product(
    product_id: str = "1790705105001",
    *,
    stock: int = 5,
    deleted: bool = False,
) -> Product:
    return Product(
        id=product_id,
        name="Product",
        label_ids="",
        cost=Decimal("10"),
        price=Decimal("20"),
        stock=stock,
        delete_flag=deleted,
        created_uid="creator",
        created_at=NOW,
        updated_uid="old-user",
        updated_at=NOW,
    )


def make_service(products: list[Product]):
    product_repository = FakeProductRepository(products)
    product_cache = FakeProductCache(products)
    order_repository = FakeOrderRepository()
    service = SellService(
        order_repository,  # type: ignore[arg-type]
        product_repository,  # type: ignore[arg-type]
        product_cache,  # type: ignore[arg-type]
        FakeLabelRepository(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUserRepository(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )
    return service, product_repository, product_cache, order_repository


def make_info(product_id: str = "1790705105001") -> SellOrderInfo:
    return SellOrderInfo.model_validate(
        {
            "totalAmount": 20,
            "totalDiscount": 15,
            "orderItems": [
                {
                    "productId": product_id,
                    "quantity": 2,
                    "price": 20,
                    "discount": 15,
                },
            ],
        }
    )


@pytest.mark.asyncio
async def test_sell_creates_order_updates_stock_audit_and_cache() -> None:
    service, products, product_cache, orders = make_service(
        [make_product(stock=1)]
    )

    result = await service.sell(
        AuthorizationObject(uid="seller", authorization="token"),
        make_info(),
    )

    updated = products.by_id["1790705105001"]
    assert result.info.order_id == "0000000001"
    assert len(orders.orders) == 1
    assert updated.stock == 0
    assert updated.updated_uid == "seller"
    assert updated.updated_at != NOW
    assert product_cache.replacements == 1
    assert product_cache.products[0].stock == 0


@pytest.mark.asyncio
async def test_sell_missing_product_rolls_back_before_cache_or_order_write() -> None:
    service, products, product_cache, orders = make_service(
        [make_product()]
    )

    with pytest.raises(SoldProductNotFoundError):
        await service.sell(
            AuthorizationObject(uid="seller", authorization="token"),
            make_info("1790705105999"),
        )

    assert product_cache.invalidations == 0
    assert product_cache.replacements == 0
    assert len(orders.orders) == 0
    assert products.by_id["1790705105001"].stock == 5


@pytest.mark.asyncio
async def test_sell_rejects_soft_deleted_product_without_writes() -> None:
    service, products, product_cache, orders = make_service(
        [make_product(deleted=True)]
    )

    with pytest.raises(SoldProductNotFoundError):
        await service.sell(
            AuthorizationObject(uid="seller", authorization="token"),
            make_info(),
        )

    assert product_cache.invalidations == 0
    assert orders.orders == []
    assert products.by_id["1790705105001"].updated_uid == "old-user"


@pytest.mark.asyncio
async def test_cache_failure_after_commit_keeps_sale_and_invalidates_snapshot() -> None:
    product = make_product(stock=3)
    product_repository = FakeProductRepository([product])
    product_cache = FailingProductCache([product])
    order_repository = FakeOrderRepository()
    service = SellService(
        order_repository,  # type: ignore[arg-type]
        product_repository,  # type: ignore[arg-type]
        product_cache,  # type: ignore[arg-type]
        FakeLabelRepository(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUserRepository(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    with pytest.raises(OrderServiceUnavailableError):
        await service.sell(
            AuthorizationObject(uid="seller", authorization="token"),
            make_info(),
        )

    assert len(order_repository.orders) == 1
    assert product_repository.by_id["1790705105001"].stock == 1
    assert product_cache.products is None


@pytest.mark.asyncio
async def test_get_all_orders_maps_joined_data_and_accepts_30_day_range() -> None:
    service, _, _, orders = make_service([])
    orders.query_results = [
        OrderResult(
            id="0000000001",
            total_amount=Decimal("20"),
            total_discount=Decimal("15"),
            created_at=NOW,
            created_by="Seller",
            items=(
                OrderItemResult(
                    product_id="1790705105001",
                    product_name="Product",
                    quantity=2,
                    price=Decimal("20"),
                    discount=Decimal("15"),
                ),
            ),
        ),
    ]

    result = await service.get_order(
        AuthorizationObject(uid="seller", authorization="token"),
        "ALL",
        "2026-10-01",
        "2026-10-31",
    )

    assert len(result.info.root) == 1
    assert result.info.root[0].created_by == "Seller"
    assert result.info.root[0].order_items[0].product_name == "Product"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("start_date", "end_date", "message"),
    [
        (None, "2026-10-31", "請輸入查詢起始日期"),
        ("2026-10-01", None, "請輸入查詢結束日期"),
        ("2026-10-01", "2026-11-01", "查詢日期區間不得超過30天"),
    ],
)
async def test_get_all_orders_rejects_invalid_date_ranges(
    start_date: str | None,
    end_date: str | None,
    message: str,
) -> None:
    service, _, _, _ = make_service([])

    with pytest.raises(OrderBadRequestError) as error:
        await service.get_order(
            AuthorizationObject(uid="seller", authorization="token"),
            "all",
            start_date,
            end_date,
        )

    assert error.value.public_message == message
