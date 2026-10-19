from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
import pytest

from src.constants.user import UserRole
from src.models.po.product import Product
from src.models.po.label import Label
from src.models.po.user import UserPO
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.product import ProductCreateInfo
from src.models.schemas.product import ProductDeleteInfo
from src.models.schemas.product import ProductUpdateInfo
from src.models.schemas.product import ProductDownloadInfo
from src.repositories.product_cache_repository import ProductCacheRepositoryError
from src.repositories.product_repository import DuplicateProductRecordError
from src.repositories.product_repository import ProductRepositoryError
from src.services.authorization_service import AuthorizationContext
from src.services.product_errors import ProductLabelNotFoundError
from src.services.product_errors import ProductCacheUnavailableError
from src.services.product_errors import ProductNotFoundError
from src.services.product_service import ProductService
from src.services.product_errors import ProductBatchError


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
        self.post_commit_invalidations = 0

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

    async def invalidate_products(self, lease: object) -> None:
        self.products = None

    async def invalidate_after_commit(self) -> None:
        self.post_commit_invalidations += 1
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

    async def get(self) -> dict[str, tuple[int, str]] | None:
        return self.labels

    async def replace(self, labels: list[Label], lease: object) -> None:
        self.labels = {
            label.name.strip().casefold(): (label.id, label.name)
            for label in labels
        }

    async def invalidate(self, lease: object) -> None:
        self.labels = {}

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

    async def get_by_id_in_transaction(
        self,
        product_id: str,
        connection: object,
    ) -> Product | None:
        return next(
            (product for product in self.values if product.id == product_id),
            None,
        )

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
    def __init__(self) -> None:
        self.values: list[Label] = []

    async def list_all(self) -> list[Label]:
        return self.values

    async def list_all_in_transaction(self, connection: object) -> list[Label]:
        return self.values.copy()

    async def insert(self, label: Label, connection: object) -> Label:
        created = Label(
            id=len(self.values) + 1,
            name=label.name,
            created_uid=label.created_uid,
            created_at=label.created_at,
            updated_uid=label.updated_uid,
            updated_at=label.updated_at,
        )
        self.values.append(created)
        return created


def make_batch_file() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Add Product"
    sheet.append(["商品名稱", "商品分類", "成本", "價格", "庫存"])
    sheet.append(["Batch product", "New label", 10, 20, 3])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


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
async def test_cold_load_caches_deleted_but_filters_response() -> None:
    visible = Product(
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
    )
    deleted = Product(
        id="1790705105002",
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
    products = FakeProducts()
    products.values = [visible, deleted]
    cache = FakeProductCache()
    service = ProductService(
        object(),  # type: ignore[arg-type]
        products,  # type: ignore[arg-type]
        cache,  # type: ignore[arg-type]
        FakeLabels(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    result = await service.get(AuthorizationObject(uid="operator"), "ALL")

    assert [item.id for item in result.info.root] == [visible.id]
    assert cache.products == [visible, deleted]


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
@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.MANAGER, UserRole.USER])
async def test_all_roles_can_add_update_and_delete(role: UserRole) -> None:
    products = FakeProducts()
    cache = FakeProductCache()
    service = ProductService(
        object(),  # type: ignore[arg-type]
        products,  # type: ignore[arg-type]
        cache,  # type: ignore[arg-type]
        FakeLabels(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUsers(role),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )
    auth = AuthorizationObject(uid="operator")

    added = await service.add(
        auth,
        ProductCreateInfo(
            name="Created",
            label_names="label1",
            cost=Decimal("100.00"),
            price=Decimal("150.00"),
        ),
    )
    updated = await service.update(
        auth,
        ProductUpdateInfo(
            id=added.info.id,
            name="Updated",
            label_names="label2",
            cost=Decimal("120.00"),
            price=Decimal("150.00"),
        ),
    )
    deleted = await service.delete(
        auth,
        ProductDeleteInfo(id=added.info.id),
    )

    assert updated.info.root[0].name == "Updated"
    assert updated.info.root[0].label_names == "Label2"
    assert deleted.info.root[0].delete_flag
    assert products.values[0].delete_flag
    assert products.values[0].updated_uid == "operator"


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
async def test_add_creates_unknown_label_and_resolves_it_from_cache() -> None:
    products = FakeProducts()
    cache = FakeProductCache()
    labels = FakeLabels()
    label_cache = FakeLabelCache()
    service = ProductService(
        object(),  # type: ignore[arg-type]
        products,  # type: ignore[arg-type]
        cache,  # type: ignore[arg-type]
        labels,  # type: ignore[arg-type]
        label_cache,  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    result = await service.add(
        AuthorizationObject(uid="operator"),
        ProductCreateInfo(
            name="Product",
            label_names=" New label ",
            cost=Decimal("100.00"),
            price=Decimal("150.00"),
        ),
    )

    assert len(labels.values) == 1
    assert labels.values[0].name == "New label"
    assert labels.values[0].created_uid == "operator"
    assert labels.values[0].updated_uid == "operator"
    assert products.values[0].label_ids == str(labels.values[0].id)
    assert label_cache.labels["new label"] == (
        labels.values[0].id,
        "New label",
    )
    assert cache.products == products.values
    assert result.info.label_names == "New label"


@pytest.mark.asyncio
async def test_add_creates_only_missing_labels_and_preserves_input_order() -> None:
    products = FakeProducts()
    cache = FakeProductCache()
    labels = FakeLabels()
    seed_time = datetime(2026, 1, 1)
    labels.values = [
        Label(1, "Label1", "seed", seed_time, "seed", seed_time),
        Label(2, "Label2", "seed", seed_time, "seed", seed_time),
    ]
    label_cache = FakeLabelCache()
    service = ProductService(
        object(),  # type: ignore[arg-type]
        products,  # type: ignore[arg-type]
        cache,  # type: ignore[arg-type]
        labels,  # type: ignore[arg-type]
        label_cache,  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    await service.add(
        AuthorizationObject(uid="operator"),
        ProductCreateInfo(
            name="Product",
            label_names="LABEL1, New label, label2",
            cost=Decimal("100.00"),
            price=Decimal("150.00"),
        ),
    )

    assert len(labels.values) == 3
    assert labels.values[-1].name == "New label"
    assert products.values[0].label_ids == f"1,{labels.values[-1].id},2"


@pytest.mark.asyncio
async def test_update_does_not_create_unknown_labels() -> None:
    product = Product(
        id="1790705105001",
        name="Product",
        label_ids="1",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        delete_flag=False,
        created_uid="creator",
        created_at=datetime(2026, 1, 1),
        updated_uid="updater",
        updated_at=datetime(2026, 1, 2),
    )
    products = FakeProducts()
    products.values = [product]
    labels = FakeLabels()
    service = ProductService(
        object(),  # type: ignore[arg-type]
        products,  # type: ignore[arg-type]
        FakeProductCache([product]),  # type: ignore[arg-type]
        labels,  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    with pytest.raises(ProductLabelNotFoundError):
        await service.update(
            AuthorizationObject(uid="operator"),
            ProductUpdateInfo(
                id=product.id,
                name="Updated",
                label_names="missing",
                cost=Decimal("100.00"),
                price=Decimal("150.00"),
            ),
        )

    assert labels.values == []


@pytest.mark.asyncio
async def test_cache_rebuild_failure_after_insert_returns_503() -> None:
    products = FakeProducts()
    cache = FailingProductCache()
    service = ProductService(
        object(),  # type: ignore[arg-type]
        products,  # type: ignore[arg-type]
        cache,  # type: ignore[arg-type]
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
    assert cache.post_commit_invalidations == 1
    assert cache.products is None


@pytest.mark.asyncio
async def test_batch_add_creates_missing_label_and_preserves_stock() -> None:
    products = FakeProducts()
    cache = FakeProductCache()
    labels = FakeLabels()
    service = ProductService(
        object(),  # type: ignore[arg-type]
        products,  # type: ignore[arg-type]
        cache,  # type: ignore[arg-type]
        labels,  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    result = await service.batch_products(
        AuthorizationObject(uid="operator"),
        "products.xlsx",
        make_batch_file(),
    )

    assert len(products.values) == 1
    assert products.values[0].stock == 3
    assert products.values[0].label_ids == "1"
    assert labels.values[0].name == "New label"
    assert result.info.root[0].stock == 3
    assert cache.products == products.values


@pytest.mark.asyncio
async def test_batch_insert_failure_returns_product_specific_message() -> None:
    class DuplicateProducts(FakeProducts):
        async def insert(
            self,
            product: Product,
            connection: object,
        ) -> Product:
            raise DuplicateProductRecordError

    service = ProductService(
        object(),  # type: ignore[arg-type]
        DuplicateProducts(),  # type: ignore[arg-type]
        FakeProductCache(),  # type: ignore[arg-type]
        FakeLabels(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    with pytest.raises(ProductBatchError) as error:
        await service.batch_products(
            AuthorizationObject(uid="operator"),
            "products.xlsx",
            make_batch_file(),
        )

    assert error.value.public_message == "新增Batch product失敗，請檢查Excel內容"


@pytest.mark.asyncio
async def test_batch_update_failure_returns_product_id_message() -> None:
    product_id = "1790705105001"
    original = Product(
        id=product_id,
        name="Existing product",
        label_ids="1",
        cost=Decimal("10.00"),
        price=Decimal("20.00"),
        stock=3,
        delete_flag=False,
        created_uid="creator",
        created_at=datetime(2026, 1, 1),
        updated_uid="updater",
        updated_at=datetime(2026, 1, 2),
        label_names=("Label1",),
    )

    class FailedUpdateProducts(FakeProducts):
        def __init__(self) -> None:
            super().__init__()
            self.values.append(original)

        async def update(self, product: Product, connection: object) -> bool:
            raise ProductRepositoryError

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Update Product"
    sheet.append(["商品ID", "商品名稱", "商品分類", "成本", "價錢", "庫存"])
    sheet.append([product_id, "Changed", "Label1", 11, 21, 4])
    output = BytesIO()
    workbook.save(output)
    service = ProductService(
        object(),  # type: ignore[arg-type]
        FailedUpdateProducts(),  # type: ignore[arg-type]
        FakeProductCache([original]),  # type: ignore[arg-type]
        FakeLabels(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    with pytest.raises(ProductBatchError) as error:
        await service.batch_products(
            AuthorizationObject(uid="operator"),
            "products.xlsx",
            output.getvalue(),
        )

    assert error.value.public_message == "修改1790705105001失敗，請檢查Excel內容"


@pytest.mark.asyncio
async def test_batch_invalid_file_returns_requested_message() -> None:
    products = FakeProducts()
    cache = FakeProductCache()
    service = ProductService(
        object(),  # type: ignore[arg-type]
        products,  # type: ignore[arg-type]
        cache,  # type: ignore[arg-type]
        FakeLabels(),  # type: ignore[arg-type]
        FakeLabelCache(),  # type: ignore[arg-type]
        FakeUsers(),  # type: ignore[arg-type]
        FakeAuthorization(),  # type: ignore[arg-type]
    )

    with pytest.raises(ProductBatchError) as error:
        await service.batch_products(
            AuthorizationObject(uid="operator"),
            "products.txt",
            b"invalid",
        )

    assert error.value.public_message == "檔案格式不正確，請上傳Excel檔案"
    assert products.values == []
    assert cache.products is None


@pytest.mark.asyncio
async def test_download_product_data_persists_uid_workbook(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.services.product_service.FILES_DIRECTORY", tmp_path)
    product = Product(
        id="1790705105001",
        name="Download product",
        label_ids="1",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        stock=7,
        delete_flag=False,
        created_uid="creator",
        created_at=datetime(2026, 1, 1),
        updated_uid="updater",
        updated_at=datetime(2026, 1, 2),
        label_names=("Label1",),
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

    result = await service.download_product_data(
        AuthorizationObject(uid="operator"),
        ProductDownloadInfo(ids=product.id),
    )

    assert result.filename == "operator.xlsx"
    assert (tmp_path / result.filename).read_bytes() == result.content
