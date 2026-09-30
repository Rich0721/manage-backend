from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal

import pytest

from src.constants.user import UserRole
from src.models.po.product import Product
from src.models.po.user import UserPO
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.product import ProductCreateInfo
from src.repositories.product_cache_repository import ProductCacheRepository
from src.services.authorization_service import AuthorizationContext
from src.services.product_errors import ProductNotFoundError
from src.services.product_service import ProductService


class FakeAuthorization(object):
    async def validate_session(self, auth: AuthorizationObject) -> AuthorizationContext:
        return AuthorizationContext(auth.uid or "", auth.authorization, False)

    async def refresh_session(self, context: AuthorizationContext) -> None:
        return None


class FakeUsers(object):
    async def get_by_uid(self, uid: str) -> UserPO:
        return UserPO(
            uid=uid,
            email="user@example.com",
            user_name="User",
            password="x",
            permission=UserRole.USER,
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )


class FakeCache(object):
    def __init__(self, products: list[Product] | None = None) -> None:
        self.products = products
        self.labels = {"label1": (1, "Label1"), "label2": (2, "Label2")}

    @asynccontextmanager
    async def products_lock(self):
        yield

    @asynccontextmanager
    async def labels_lock(self):
        yield

    async def get_products(self) -> list[Product] | None:
        return self.products

    async def replace_products(self, products: list[Product]) -> None:
        self.products = products

    async def invalidate_products(self) -> None:
        self.products = None

    async def get_labels(self) -> dict[str, tuple[int, str]]:
        return self.labels

    async def replace_labels(self, labels: object) -> None:
        return None

    async def invalidate_labels(self) -> None:
        return None

    @staticmethod
    def normalize_label_name(name: str) -> str:
        return name.strip().casefold()


class FakeProducts(object):
    def __init__(self) -> None:
        self.values: list[Product] = []

    @asynccontextmanager
    async def transaction(self):
        yield object()

    async def create(self, product: Product, connection: object) -> Product:
        self.values.append(product)
        return product

    async def list_products(self) -> list[Product]:
        return self.values

    async def list_labels(self) -> list[object]:
        return []


@pytest.mark.asyncio
async def test_add_resolves_trimmed_case_insensitive_labels_and_warms_cache() -> None:
    products = FakeProducts()
    cache = FakeCache()
    service = ProductService(
        object(),  # type: ignore[arg-type]
        products,  # type: ignore[arg-type]
        cache,  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    result = await service.add(
        AuthorizationObject(uid="operator"),
        ProductCreateInfo(
            name="Product",
            label_names=" label1 , LABEL2 ",
            cost=Decimal("100.00"),
            price=Decimal("150.00"),
        ),
    )

    assert products.values[0].label_ids == "1,2"
    assert cache.products == products.values
    assert result.info.label_names == "Label1,Label2"


@pytest.mark.asyncio
async def test_get_soft_deleted_product_as_single_item_is_not_found() -> None:
    product = Product(
        id="1790705105001",
        name="Deleted",
        label_ids="1",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        delete_flag=True,
        created_uid="creator",
        created_at=datetime(2026, 1, 1),
        updated_uid="updater",
        updated_at=datetime(2026, 1, 2),
    )
    service = ProductService(
        object(),  # type: ignore[arg-type]
        FakeProducts(),  # type: ignore[arg-type]
        FakeCache([product]),  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    with pytest.raises(ProductNotFoundError):
        await service.get(AuthorizationObject(uid="operator"), product.id)
