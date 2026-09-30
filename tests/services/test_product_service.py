from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal

import pytest

from src.constants.user import UserRole
from src.models.po.product import Product
from src.models.po.user import UserPO
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.product import ProductCreateInfo
from src.models.schemas.product import ProductDeleteInfo
from src.models.schemas.product import ProductUpdateInfo
from src.repositories.product_cache_repository import ProductCacheRepositoryError
from src.services.authorization_service import AuthorizationContext
from src.services.product_errors import ProductLabelNotFoundError
from src.services.product_errors import ProductCacheUnavailableError
from src.services.product_errors import ProductNotFoundError
from src.services.product_service import ProductService


class FakeAuthorization(object):
    async def validate_session(self, auth: AuthorizationObject) -> AuthorizationContext:
        return AuthorizationContext(auth.uid or "", auth.authorization, False)

    async def refresh_session(self, context: AuthorizationContext) -> None:
        return None


class FakeLease(object):
    async def ensure_held(self) -> None:
        return None


class FakeUsers(object):
    def __init__(self, role: UserRole = UserRole.USER) -> None:
        self.role = role

    async def get_by_uid(self, uid: str) -> UserPO:
        return UserPO(
            uid=uid,
            email="user@example.com",
            user_name="User",
            password="x",
            permission=self.role,
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )


class FakeProductCache(object):
    def __init__(self, products: list[Product] | None = None) -> None:
        self.products = products

    @asynccontextmanager
    async def products_lock(self):
        yield FakeLease()

    async def get_products(self) -> list[Product] | None:
        return self.products

    async def replace_products(
        self,
        products: list[Product],
        label_names_by_id: dict[int, str] | None = None,
        lease: object | None = None,
    ) -> None:
        self.products = products

    async def invalidate_products(self) -> None:
        self.products = None


class FailingProductCache(FakeProductCache):
    async def replace_products(
        self,
        products: list[Product],
        label_names_by_id: dict[int, str] | None = None,
        lease: object | None = None,
    ) -> None:
        raise ProductCacheRepositoryError


class FakeLabelCache(object):
    def __init__(self) -> None:
        self.labels = {"label1": (1, "Label1"), "label2": (2, "Label2")}

    @asynccontextmanager
    async def lock(self):
        yield FakeLease()

    async def get(self) -> dict[str, tuple[int, str]]:
        return self.labels

    async def replace(self, labels: object, lease: object | None = None) -> None:
        return None

    async def invalidate(self) -> None:
        return None

    @staticmethod
    def normalize_name(name: str) -> str:
        return name.strip().casefold()


class FakeProducts(object):
    def __init__(self) -> None:
        self.values: list[Product] = []

    @asynccontextmanager
    async def transaction(self):
        yield object()

    async def insert(self, product: Product, connection: object) -> Product:
        self.values.append(product)
        return product

    async def list_all(self) -> list[Product]:
        return self.values


    async def update(self, product: Product, connection: object) -> bool:
        for index, current in enumerate(self.values):
            if current.id == product.id and not current.delete_flag:
                self.values[index] = product
                return True
        return False

    async def soft_delete(
        self,
        product_id: str,
        updated_uid: str,
        updated_at: datetime,
        connection: object,
    ) -> bool:
        for index, current in enumerate(self.values):
            if current.id == product_id and not current.delete_flag:
                self.values[index] = Product(
                    id=current.id,
                    name=current.name,
                    label_ids=current.label_ids,
                    cost=current.cost,
                    price=current.price,
                    delete_flag=True,
                    created_uid=current.created_uid,
                    created_at=current.created_at,
                    updated_uid=updated_uid,
                    updated_at=updated_at,
                )
                return True
        return False

class FakeLabels(object):
    async def list_all(self) -> list[object]:
        return []


@pytest.mark.asyncio
async def test_add_resolves_trimmed_case_insensitive_labels_and_warms_cache() -> None:
    products = FakeProducts()
    product_cache = FakeProductCache()
    service = ProductService(
        object(),  # type: ignore[arg-type]
        products,  # type: ignore[arg-type]
        product_cache,  # type: ignore[arg-type]
        FakeLabels(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
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
    assert product_cache.products == products.values
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
        FakeProductCache([product]),  # type: ignore[arg-type]
        FakeLabels(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    with pytest.raises(ProductNotFoundError):
        await service.get(AuthorizationObject(uid="operator"), product.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.MANAGER, UserRole.USER])
async def test_all_roles_can_read_visible_products(role: UserRole) -> None:
    product = Product(
        id="1790705105001",
        name="Visible",
        label_ids="1",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        delete_flag=False,
        created_uid="creator",
        created_at=datetime(2026, 1, 1),
        updated_uid="updater",
        updated_at=datetime(2026, 1, 2),
        label_names=("Snapshot label",),
    )
    service = ProductService(
        object(),  # type: ignore[arg-type]
        FakeProducts(),  # type: ignore[arg-type]
        FakeProductCache([product]),  # type: ignore[arg-type]
        FakeLabels(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUsers(role),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    result = await service.get(AuthorizationObject(uid="operator"), "ALL")

    assert result.info.root[0].label_names == "Snapshot label"


@pytest.mark.asyncio
async def test_update_and_delete_rebuild_the_full_product_cache() -> None:
    product = Product(
        id="1790705105001",
        name="Original",
        label_ids="1",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        delete_flag=False,
        created_uid="creator",
        created_at=datetime(2026, 1, 1),
        updated_uid="creator",
        updated_at=datetime(2026, 1, 1),
    )
    products = FakeProducts()
    products.values = [product]
    cache = FakeProductCache([product])
    service = ProductService(
        object(),  # type: ignore[arg-type]
        products,  # type: ignore[arg-type]
        cache,  # type: ignore[arg-type]
        FakeLabels(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    updated = await service.update(
        AuthorizationObject(uid="operator"),
        ProductUpdateInfo(
            id=product.id,
            name="Updated",
            label_names="label2",
            cost=Decimal("120.00"),
            price=Decimal("150.00"),
        ),
    )
    deleted = await service.delete(
        AuthorizationObject(uid="operator"),
        ProductDeleteInfo(id=product.id),
    )

    assert updated.info.root[0].name == "Updated"
    assert deleted.info.root[0].delete_flag
    assert cache.products is not None and cache.products[0].delete_flag


@pytest.mark.asyncio
async def test_unknown_label_reloads_once_then_returns_expected_error() -> None:
    service = ProductService(
        object(),  # type: ignore[arg-type]
        FakeProducts(),  # type: ignore[arg-type]
        FakeProductCache(),  # type: ignore[arg-type]
        FakeLabels(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    with pytest.raises(ProductLabelNotFoundError):
        await service.add(
            AuthorizationObject(uid="operator"),
            ProductCreateInfo(
                name="Product",
                label_names="missing",
                cost=Decimal("100.00"),
                price=Decimal("150.00"),
            ),
        )


@pytest.mark.asyncio
async def test_cache_rebuild_failure_after_insert_returns_503() -> None:
    products = FakeProducts()
    service = ProductService(
        object(),  # type: ignore[arg-type]
        products,  # type: ignore[arg-type]
        FailingProductCache(),  # type: ignore[arg-type]
        FakeLabels(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    with pytest.raises(ProductCacheUnavailableError):
        await service.add(
            AuthorizationObject(uid="operator"),
            ProductCreateInfo(
                name="Product",
                label_names="label1",
                cost=Decimal("100.00"),
                price=Decimal("150.00"),
            ),
        )

    assert len(products.values) == 1
