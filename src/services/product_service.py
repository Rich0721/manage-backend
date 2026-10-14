import logging
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.config.settings import Settings
from src.constants.user import UserRole
from src.models.po.product import Product
from src.models.po.label import Label
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.product import ProductCreateInfo
from src.models.schemas.product import ProductCreateResponseInfo
from src.models.schemas.product import ProductDeleteInfo
from src.models.schemas.product import ProductListResponseInfo
from src.models.schemas.product import ProductResponseInfo
from src.models.schemas.product import ProductUpdateInfo
from src.models.schemas.product import ProductDownloadInfo
from src.repositories.label_cache_repository import LabelCacheRepository
from src.repositories.label_cache_repository import LabelCacheRepositoryError
from src.repositories.label_cache_repository import LabelCacheLockLease
from src.repositories.label_repository import LabelRepository
from src.repositories.label_repository import LabelRepositoryError
from src.repositories.product_cache_repository import ProductCacheRepository
from src.repositories.product_cache_repository import ProductCacheRepositoryError
from src.repositories.product_cache_repository import ProductCacheLockLease
from src.repositories.product_repository import DuplicateProductRecordError
from src.repositories.product_repository import ProductRepository
from src.repositories.product_repository import ProductRepositoryError
from src.repositories.user_repository import UserRepository
from src.repositories.user_repository import UserRepositoryError
from src.services.authorization_service import AuthorizationContext
from src.services.authorization_service import AuthorizationService
from src.services.errors import ServiceUnavailableError
from src.services.product_errors import ProductCacheUnavailableError
from src.services.product_errors import ProductBatchError
from src.services.product_errors import ProductConflictError
from src.services.product_errors import ProductLabelNotFoundError
from src.services.product_errors import ProductNotFoundError
from src.services.product_errors import ProductPermissionError
from src.services.product_excel_service import ProductExcelError
from src.services.product_excel_service import ProductExcelRow
from src.services.product_excel_service import ProductExcelService


LOGGER = logging.getLogger(__name__)
FILES_DIRECTORY = Path(__file__).resolve().parents[2] / "files"


@dataclass(frozen=True, slots=True)
class ProtectedProductResult:
    context: AuthorizationContext
    info: ProductCreateResponseInfo | ProductListResponseInfo


@dataclass(frozen=True, slots=True)
class ProtectedFileResult:
    context: AuthorizationContext
    filename: str
    content: bytes


class ProductService(object):
    def __init__(
        self,
        settings: Settings,
        products: ProductRepository,
        product_cache: ProductCacheRepository,
        labels: LabelRepository,
        label_cache: LabelCacheRepository,
        users: UserRepository,
        authorization: AuthorizationService,
    ) -> None:
        self.__settings = settings
        self.__products = products
        self.__product_cache = product_cache
        self.__labels = labels
        self.__label_cache = label_cache
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
            stock=info.stock,
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
            stock=current.stock if info.stock is None else info.stock,
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
            stock=current.stock,
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

    async def batch_products(
        self,
        auth: AuthorizationObject,
        filename: str,
        content: bytes,
    ) -> ProtectedProductResult:
        context = await self.__authorize(auth)
        try:
            rows = ProductExcelService.parse(filename, content)
        except ProductExcelError as error:
            raise ProductBatchError(error.public_message) from error
        try:
            written_products = await self.__write_batch(rows, context.uid)
        except ProductCacheRepositoryError as error:
            raise ProductCacheUnavailableError from error
        except LabelCacheRepositoryError as error:
            raise ProductCacheUnavailableError from error
        await self.__refresh_session(context)
        return ProtectedProductResult(
            context=context,
            info=ProductListResponseInfo(
                [await self.__to_response(product) for product in written_products]
            ),
        )

    async def __write_batch(
        self,
        rows: list[ProductExcelRow],
        uid: str,
    ) -> list[Product]:
        updated_ids: set[str] = set()
        created_ids: set[str] = set()
        written_products: list[Product] = []
        committed = False
        published = False
        async with self.__product_cache.products_lock() as product_lease:
            await product_lease.ensure_held()
            async with self.__label_cache.lock() as label_lease:
                await label_lease.ensure_held()
                old_products = await self.__product_cache.get_products()
                await self.__product_cache.invalidate_products(product_lease)
                try:
                    async with self.__products.transaction() as connection:
                        labels = await self.__labels.list_all_in_transaction(
                            connection
                        )
                        labels_by_name = self.__labels_by_name(labels)
                        for row in rows:
                            product = await self.__batch_product(
                                row,
                                uid,
                                connection,
                                labels,
                                labels_by_name,
                                updated_ids,
                                created_ids,
                            )
                            written_products.append(product)
                    committed = True
                    labels = await self.__labels.list_all()
                    await self.__label_cache.replace(labels, label_lease)
                    await product_lease.ensure_held()
                    await self.__replace_product_cache(
                        "batch",
                        "batch",
                        product_lease,
                    )
                    published = True
                except ProductNotFoundError:
                    await self.__restore_product_cache(
                        old_products,
                        product_lease,
                    )
                    raise
                except ProductBatchError:
                    await self.__restore_product_cache(
                        old_products,
                        product_lease,
                    )
                    raise
                except DuplicateProductRecordError as error:
                    await self.__restore_product_cache(
                        old_products,
                        product_lease,
                    )
                    raise ProductBatchError(
                        ProductExcelService.ADD_DATA_ERROR
                    ) from error
                except (ProductRepositoryError, LabelRepositoryError) as error:
                    if committed:
                        await self.__invalidate_batch_caches(
                            product_lease,
                            label_lease,
                        )
                    else:
                        await self.__restore_product_cache(
                            old_products,
                            product_lease,
                        )
                    raise ServiceUnavailableError from error
                except ProductCacheRepositoryError as error:
                    if committed:
                        await self.__invalidate_batch_caches(
                            product_lease,
                            label_lease,
                        )
                    else:
                        await self.__restore_product_cache(
                            old_products,
                            product_lease,
                        )
                    raise ProductCacheUnavailableError from error
        if not published:
            raise ProductCacheUnavailableError
        return written_products

    async def download_template(
        self,
        auth: AuthorizationObject,
    ) -> ProtectedFileResult:
        context = await self.__authorize(auth)
        template_path = FILES_DIRECTORY / "Batch Add Products.xlsx"
        try:
            content = template_path.read_bytes()
        except OSError as error:
            raise ServiceUnavailableError from error
        await self.__refresh_session(context)
        return ProtectedFileResult(context, template_path.name, content)

    async def download_product_data(
        self,
        auth: AuthorizationObject,
        info: ProductDownloadInfo,
    ) -> ProtectedFileResult:
        context = await self.__authorize(auth)
        requested_ids = [value.strip() for value in info.ids.split(",")]
        products = await self.__get_all_products()
        products_by_id = {
            product.id: product
            for product in products
            if not product.delete_flag
        }
        selected_products: list[Product] = []
        for product_id in requested_ids:
            product = products_by_id.get(product_id)
            if product is None:
                raise ProductNotFoundError
            selected_products.append(product)
        excel_products = []
        for product in selected_products:
            response = await self.__to_response(product)
            excel_products.append(
                {
                    "id": response.id,
                    "name": response.name,
                    "label_names": response.label_names,
                    "cost": response.cost,
                    "price": response.price,
                    "stock": response.stock,
                }
            )
        content = ProductExcelService.create_workbook(excel_products)
        if re.fullmatch(r"[A-Za-z0-9_-]+", context.uid) is None:
            raise ProductBatchError("無法建立下載檔案")
        files_directory = FILES_DIRECTORY
        target_path = files_directory / f"{context.uid}.xlsx"
        temp_path: Path | None = None
        try:
            files_directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=files_directory,
                prefix=f".{context.uid}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_file.write(content)
                temp_path = Path(temp_file.name)
            temp_path.replace(target_path)
        except OSError as error:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    LOGGER.exception("Failed to remove temporary product workbook")
            raise ServiceUnavailableError from error
        await self.__refresh_session(context)
        return ProtectedFileResult(context, target_path.name, content)

    async def __batch_product(
        self,
        row: ProductExcelRow,
        uid: str,
        connection: object,
        labels: list[Label],
        labels_by_name: dict[str, Label],
        updated_ids: set[str],
        created_ids: set[str],
    ) -> Product:
        normalized_names = [
            self.__label_cache.normalize_name(name)
            for name in row.label_names.split(",")
        ]
        if not normalized_names or any(not name for name in normalized_names):
            raise ProductBatchError(self.__batch_error_for(row))
        product_label_names: list[str] = []
        label_ids: list[str] = []
        now = self.__utc_now()
        for raw_name, normalized_name in zip(
            row.label_names.split(","),
            normalized_names,
            strict=True,
        ):
            label = labels_by_name.get(normalized_name)
            if label is None:
                name = raw_name.strip()
                label = await self.__labels.insert(
                    Label(
                        id=0,
                        name=name,
                        created_uid=uid,
                        created_at=now,
                        updated_uid=uid,
                        updated_at=now,
                    ),
                    connection,  # type: ignore[arg-type]
                )
                labels.append(label)
                labels_by_name[normalized_name] = label
            product_label_names.append(label.name)
            label_ids.append(str(label.id))

        if row.operation == "add":
            product_id = await self.__next_product_id(
                created_ids,
                connection,
            )
            created_ids.add(product_id)
            product = Product(
                id=product_id,
                name=row.name,
                label_ids=",".join(label_ids),
                cost=row.cost,
                price=row.price,
                stock=row.stock,
                delete_flag=False,
                created_uid=uid,
                created_at=now,
                updated_uid=uid,
                updated_at=now,
                label_names=tuple(product_label_names),
            )
            try:
                await self.__products.insert(
                    product,
                    connection,  # type: ignore[arg-type]
                )
            except DuplicateProductRecordError as error:
                raise ProductBatchError(self.__batch_error_for(row)) from error
            return product

        product_id = row.product_id or ""
        if product_id in updated_ids:
            raise ProductBatchError(self.__batch_error_for(row))
        updated_ids.add(product_id)
        current = await self.__products.get_by_id_in_transaction(
            product_id,
            connection,  # type: ignore[arg-type]
        )
        if current is None or current.delete_flag:
            raise ProductNotFoundError(f"{row.name} Not Found")
        product = Product(
            id=current.id,
            name=row.name,
            label_ids=",".join(label_ids),
            cost=row.cost,
            price=row.price,
            stock=row.stock,
            delete_flag=False,
            created_uid=current.created_uid,
            created_at=current.created_at,
            updated_uid=uid,
            updated_at=now,
            label_names=tuple(product_label_names),
        )
        if not await self.__products.update(
            product,
            connection,  # type: ignore[arg-type]
        ):
            raise ProductNotFoundError(f"{row.name} Not Found")
        return product

    async def __restore_product_cache(
        self,
        old_products: list[Product] | None,
        lease: ProductCacheLockLease,
    ) -> None:
        if old_products is None:
            return
        try:
            await self.__product_cache.replace_products(
                old_products,
                {},
                lease,
            )
        except ProductCacheRepositoryError as error:
            raise ProductCacheUnavailableError from error

    async def __invalidate_batch_caches(
        self,
        product_lease: ProductCacheLockLease,
        label_lease: LabelCacheLockLease,
    ) -> None:
        try:
            await self.__product_cache.invalidate_products(product_lease)
        except ProductCacheRepositoryError:
            LOGGER.exception("Failed to invalidate product cache after batch commit")
        try:
            await self.__label_cache.invalidate(label_lease)
        except LabelCacheRepositoryError:
            LOGGER.exception("Failed to invalidate label cache after batch commit")
        try:
            await self.__product_cache.invalidate_after_commit()
        except ProductCacheRepositoryError:
            LOGGER.exception("Failed to fence product cache after batch commit")

    @staticmethod
    def __labels_by_name(labels: list[Label]) -> dict[str, Label]:
        labels_by_name: dict[str, Label] = {}
        for label in labels:
            key = label.name.strip().casefold()
            existing = labels_by_name.get(key)
            if existing is not None and existing.id != label.id:
                raise LabelRepositoryError("Duplicate normalized label name")
            labels_by_name[key] = label
        return labels_by_name

    @staticmethod
    def __batch_error_for(row: ProductExcelRow) -> str:
        return (
            ProductExcelService.ADD_DATA_ERROR
            if row.operation == "add"
            else ProductExcelService.UPDATE_DATA_ERROR
        )

    async def __next_product_id(
        self,
        used_ids: set[str],
        connection: object,
    ) -> str:
        timestamp = time.time_ns() // 1_000_000
        while (
            str(timestamp) in used_ids
            or await self.__products.get_by_id_in_transaction(
                str(timestamp),
                connection,  # type: ignore[arg-type]
            )
            is not None
        ):
            timestamp += 1
        return str(timestamp)

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
        committed = False
        published = False
        try:
            async with self.__product_cache.products_lock() as lease:
                await lease.ensure_held()
                await self.__product_cache.invalidate_products(lease)
                try:
                    async with self.__products.transaction() as connection:
                        if operation == "add":
                            await self.__products.insert(product, connection)
                        else:
                            updated = await self.__products.update(product, connection)
                            if not updated:
                                raise ProductNotFoundError
                except DuplicateProductRecordError as error:
                    raise ProductConflictError from error
                committed = True
                await lease.ensure_held()
                await self.__replace_product_cache(product.id, operation, lease)
                published = True
        except (ProductConflictError, ProductNotFoundError):
            raise
        except ProductRepositoryError as error:
            raise ServiceUnavailableError from error
        except ProductCacheRepositoryError as error:
            raise ProductCacheUnavailableError from error
        finally:
            if committed and not published:
                await self.__invalidate_failed_publication(
                    product.id, operation
                )

    async def __delete_product(self, product: Product) -> None:
        committed = False
        published = False
        try:
            async with self.__product_cache.products_lock() as lease:
                await lease.ensure_held()
                await self.__product_cache.invalidate_products(lease)
                async with self.__products.transaction() as connection:
                    deleted = await self.__products.soft_delete(
                        product.id,
                        product.updated_uid,
                        product.updated_at,
                        connection,
                    )
                    if not deleted:
                        raise ProductNotFoundError
                committed = True
                await lease.ensure_held()
                await self.__replace_product_cache(product.id, "delete", lease)
                published = True
        except ProductNotFoundError:
            raise
        except ProductRepositoryError as error:
            raise ServiceUnavailableError from error
        except ProductCacheRepositoryError as error:
            raise ProductCacheUnavailableError from error
        finally:
            if committed and not published:
                await self.__invalidate_failed_publication(
                    product.id, "delete"
                )

    async def __invalidate_failed_publication(
        self,
        product_id: str,
        operation: str,
    ) -> None:
        try:
            await self.__product_cache.invalidate_after_commit()
        except ProductCacheRepositoryError:
            LOGGER.exception(
                "Product cache invalidation failed after commit "
                "operation=%s product_id=%s",
                operation,
                product_id,
            )

    async def __replace_product_cache(
        self,
        product_id: str,
        operation: str,
        lease: ProductCacheLockLease,
    ) -> None:
        try:
            products = await self.__products.list_all()
            labels = await self.__get_labels()
            label_names_by_id = {
                label_id: label_name for label_id, label_name in labels.values()
            }
            await self.__product_cache.replace_products(
                products,
                label_names_by_id,
                lease,
            )
        except (ProductRepositoryError, ProductCacheRepositoryError):
            LOGGER.exception(
                "Product cache replacement failed operation=%s product_id=%s",
                operation,
                product_id,
            )
            raise

    async def __get_all_products(self) -> list[Product]:
        try:
            products = await self.__product_cache.get_products()
            if products is not None:
                return products
            async with self.__product_cache.products_lock() as lease:
                await lease.ensure_held()
                products = await self.__product_cache.get_products()
                if products is None:
                    await self.__replace_product_cache("cold-load", "load", lease)
                    products = await self.__product_cache.get_products()
                    if products is None:
                        raise ProductCacheRepositoryError
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
            async with self.__label_cache.lock() as lease:
                await lease.ensure_held()
                await self.__label_cache.invalidate(lease)
                labels = await self.__reload_labels(lease)
        except LabelRepositoryError as error:
            raise ServiceUnavailableError from error
        except LabelCacheRepositoryError as error:
            raise ProductCacheUnavailableError from error
        label_ids = self.__lookup_label_ids(requested_names, labels)
        if label_ids is None:
            raise ProductLabelNotFoundError
        return label_ids

    async def __get_labels(self) -> dict[str, tuple[int, str]]:
        try:
            labels = await self.__label_cache.get()
            if labels is not None:
                return labels
            async with self.__label_cache.lock() as lease:
                await lease.ensure_held()
                labels = await self.__label_cache.get()
                if labels is None:
                    labels = await self.__reload_labels(lease)
                return labels
        except LabelRepositoryError as error:
            raise ServiceUnavailableError from error
        except LabelCacheRepositoryError as error:
            raise ProductCacheUnavailableError from error

    async def __reload_labels(
        self,
        lease: LabelCacheLockLease,
    ) -> dict[str, tuple[int, str]]:
        labels = await self.__labels.list_all()
        await self.__label_cache.replace(labels, lease)
        return {
            self.__label_cache.normalize_name(label.name): (label.id, label.name)
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
        if product.label_names is None:
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
        else:
            label_names = list(product.label_names)
        return ProductResponseInfo(
            id=product.id,
            name=product.name,
            label_names=",".join(label_names),
            cost=product.cost,
            price=product.price,
            stock=product.stock,
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
            stock=product.stock,
        )

    async def __refresh_session(self, context: AuthorizationContext) -> None:
        await self.__authorization.refresh_session(context)

    @staticmethod
    def __utc_now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
