import asyncio
import os
from collections.abc import Mapping
from contextlib import asynccontextmanager
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from psycopg import AsyncConnection
from redis.asyncio import Redis
import pytest

from src.constants.user import UserRole
from src.models.po.product import Product
from src.models.po.user import UserPO
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.order import SellOrderInfo
from src.models.schemas.product import ProductUpdateInfo
from src.repositories.label_cache_repository import LabelCacheRepository
from src.repositories.label_repository import LabelRepository
from src.repositories.order_repository import OrderRepository
from src.repositories.product_cache_repository import ProductCacheRepository
from src.repositories.product_cache_repository import ProductCacheLockLease
from src.repositories.product_cache_repository import ProductCacheRepositoryError
from src.repositories.product_repository import ProductRepository
from src.services.authorization_service import AuthorizationContext
from src.services.order_errors import OrderServiceUnavailableError
from src.services.order_errors import SoldProductNotFoundError
from src.services.product_service import ProductService
from src.services.sell_service import SellService


class DirectConnectionPool:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection_value = connection

    @asynccontextmanager
    async def connection(self):
        try:
            yield self.connection_value
        except BaseException:
            await self.connection_value.rollback()
            raise
        else:
            await self.connection_value.commit()


class IntegrationAuthorization:
    async def validate_session(
        self,
        auth: AuthorizationObject,
    ) -> AuthorizationContext:
        return AuthorizationContext(auth.uid or "seller", None, True)

    async def refresh_session(self, context: AuthorizationContext) -> None:
        return None


class IntegrationUsers:
    def __init__(self, user: UserPO) -> None:
        self.user = user

    async def get_by_uid(self, uid: str) -> UserPO | None:
        return self.user if uid == self.user.uid else None


class FailingReplaceProductCache(ProductCacheRepository):
    async def replace_products(
        self,
        products: list[Product],
        label_names_by_id: Mapping[int, str],
        lease: ProductCacheLockLease,
    ) -> None:
        raise ProductCacheRepositoryError


DATABASE_URL = os.getenv("INTEGRATION_DATABASE_URL")
REDIS_URL = os.getenv("INTEGRATION_REDIS_URL")
TABLES_DIRECTORY = Path("database/DDL/tables")


async def create_sell_test_tables(connection: AsyncConnection) -> None:
    await connection.execute(
        """
        CREATE TEMP TABLE tb_users (
            uid VARCHAR(256) PRIMARY KEY,
            email VARCHAR(256) NOT NULL,
            user_name VARCHAR(256) NOT NULL,
            password VARCHAR(64) NOT NULL,
            permission VARCHAR(256) NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
        """
    )
    labels_ddl = (TABLES_DIRECTORY / "TB_LABELS.sql").read_text(
        encoding="utf-8"
    ).replace("CREATE TABLE tb_labels", "CREATE TEMP TABLE tb_labels", 1)
    products_ddl = (TABLES_DIRECTORY / "TB_PRODUCTS.sql").read_text(
        encoding="utf-8"
    ).replace("CREATE TABLE tb_products", "CREATE TEMP TABLE tb_products", 1)
    orders_ddl = (TABLES_DIRECTORY / "TB_ORDERS.sql").read_text(
        encoding="utf-8"
    )
    orders_ddl = orders_ddl.replace(
        "CREATE SEQUENCE seq_tb_orders_id",
        "CREATE TEMP SEQUENCE seq_tb_orders_id",
        1,
    ).replace("CREATE TABLE tb_orders", "CREATE TEMP TABLE tb_orders", 1)
    items_ddl = (TABLES_DIRECTORY / "TB_ORDERS_ITEMS.sql").read_text(
        encoding="utf-8"
    ).replace(
        "CREATE TABLE tb_orders_items",
        "CREATE TEMP TABLE tb_orders_items",
        1,
    )
    await connection.execute(labels_ddl)
    await connection.execute(products_ddl)
    await connection.execute(orders_ddl)
    await connection.execute(items_ddl)
    await connection.commit()


async def create_sell_schema_tables(
    connection: AsyncConnection,
    schema_name: str,
) -> None:
    await connection.execute(f'CREATE SCHEMA "{schema_name}"')
    await connection.execute(f'SET search_path TO "{schema_name}"')
    await connection.execute(
        """
        CREATE TABLE tb_users (
            uid VARCHAR(256) PRIMARY KEY,
            email VARCHAR(256) NOT NULL,
            user_name VARCHAR(256) NOT NULL,
            password VARCHAR(64) NOT NULL,
            permission VARCHAR(256) NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
        """
    )
    await connection.execute(
        (TABLES_DIRECTORY / "TB_LABELS.sql").read_text(encoding="utf-8")
    )
    await connection.execute(
        (TABLES_DIRECTORY / "TB_PRODUCTS.sql").read_text(encoding="utf-8")
    )
    await connection.execute(
        (TABLES_DIRECTORY / "TB_ORDERS.sql").read_text(encoding="utf-8")
    )
    await connection.execute(
        (TABLES_DIRECTORY / "TB_ORDERS_ITEMS.sql").read_text(
            encoding="utf-8"
        )
    )
    await connection.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(
    DATABASE_URL is None or REDIS_URL is None,
    reason="INTEGRATION_DATABASE_URL and INTEGRATION_REDIS_URL are required",
)
async def test_sell_product_updates_database_and_cache_atomically() -> None:
    connection = await AsyncConnection.connect(DATABASE_URL)
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    key_prefix = f"test:sell:{uuid4().hex}"
    now = datetime(2026, 1, 1, 12, 0, 0)
    try:
        await create_sell_test_tables(connection)
        await connection.execute(
            """
            INSERT INTO tb_users (
                uid, email, user_name, password, permission,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                "seller",
                "seller@example.com",
                "Seller",
                "0" * 64,
                UserRole.USER.value,
                now,
                now,
            ),
        )
        await connection.execute(
            """
            INSERT INTO tb_labels (
                id, name, created_uid, created_at, updated_uid, updated_at
            ) VALUES (1, 'General', 'seller', %s, 'seller', %s)
            """,
            (now, now),
        )
        await connection.execute(
            """
            INSERT INTO tb_products (
                id, name, label_ids, cost, price, stock, delete_flag,
                created_uid, created_at, updated_uid, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s, %s, %s, %s)
            """,
            (
                "1790705105001",
                "Product A",
                "1",
                Decimal("5"),
                Decimal("10"),
                1,
                "seller",
                now,
                "old-user",
                now,
            ),
        )
        await connection.execute(
            """
            INSERT INTO tb_products (
                id, name, label_ids, cost, price, stock, delete_flag,
                created_uid, created_at, updated_uid, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s, %s, %s, %s)
            """,
            (
                "1790705105002",
                "Product B",
                "1",
                Decimal("8"),
                Decimal("12"),
                5,
                "seller",
                now,
                "old-user",
                now,
            ),
        )
        await connection.commit()

        pool = DirectConnectionPool(connection)
        products = ProductRepository(pool)  # type: ignore[arg-type]
        product_cache = ProductCacheRepository(
            redis,
            f"{key_prefix}:products:info",
        )
        label_cache = LabelCacheRepository(
            redis,
            f"{key_prefix}:product:labels",
        )
        labels = LabelRepository(pool)  # type: ignore[arg-type]
        service = SellService(
            OrderRepository(pool),  # type: ignore[arg-type]
            products,
            product_cache,
            labels,
            label_cache,
            IntegrationUsers(
                UserPO(
                    uid="seller",
                    email="seller@example.com",
                    user_name="Seller",
                    password="0" * 64,
                    permission=UserRole.USER,
                    created_at=now,
                    updated_at=now,
                )
            ),  # type: ignore[arg-type]
            IntegrationAuthorization(),  # type: ignore[arg-type]
        )
        info = SellOrderInfo.model_validate(
            {
                "totalAmount": 20,
                "totalDiscount": 15,
                "orderItems": [
                    {
                        "productId": "1790705105001",
                        "quantity": 2,
                        "price": 10,
                        "discount": 7.5,
                    },
                    {
                        "productId": "1790705105002",
                        "quantity": 2,
                        "price": 12,
                        "discount": 10,
                    },
                ],
            }
        )
        result = await service.sell(
            AuthorizationObject(uid="seller", authorization=None),
            info,
        )

        persisted = await products.get_by_id("1790705105001")
        cached = await product_cache.get_products()
        assert result.info.order_id == "0000000001"
        assert persisted is not None
        assert persisted.stock == 0
        assert persisted.updated_uid == "seller"
        assert persisted.updated_at > now
        assert cached is not None
        cached_by_id = {product.id: product for product in cached}
        assert cached_by_id["1790705105001"].stock == persisted.stock
        assert (
            cached_by_id["1790705105001"].updated_uid
            == persisted.updated_uid
        )
        assert cached_by_id["1790705105001"].updated_at == persisted.updated_at
        persisted_second = await products.get_by_id("1790705105002")
        assert persisted_second is not None
        assert persisted_second.stock == 3
        assert persisted_second.updated_uid == "seller"
        assert persisted_second.updated_at > now
        assert cached_by_id["1790705105002"].stock == persisted_second.stock
        assert cached_by_id["1790705105002"].updated_uid == "seller"
        assert (
            cached_by_id["1790705105002"].updated_at
            == persisted_second.updated_at
        )

        snapshot_before_missing_sale = await redis.get(
            f"{key_prefix}:products:info"
        )
        missing_info = SellOrderInfo.model_validate(
            {
                "totalAmount": 20,
                "totalDiscount": 15,
                "orderItems": [
                    {
                        "productId": "1790705105001",
                        "quantity": 1,
                        "price": 10,
                        "discount": 8,
                    },
                    {
                        "productId": "1790705105999",
                        "quantity": 1,
                        "price": 10,
                        "discount": 8,
                    },
                ],
            }
        )
        with pytest.raises(SoldProductNotFoundError):
            await service.sell(
                AuthorizationObject(uid="seller", authorization=None),
                missing_info,
            )
        assert (
            await redis.get(f"{key_prefix}:products:info")
            == snapshot_before_missing_sale
        )
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) FROM tb_orders")
            order_count = (await cursor.fetchone())[0]
            await cursor.execute("SELECT COUNT(*) FROM tb_orders_items")
            item_count = (await cursor.fetchone())[0]
        assert order_count == 1
        assert item_count == 2
        after_missing_sale = await products.get_by_id("1790705105001")
        assert after_missing_sale is not None
        assert after_missing_sale.stock == 0
        assert after_missing_sale.updated_uid == "seller"
        after_missing_sale_second = await products.get_by_id("1790705105002")
        assert after_missing_sale_second is not None
        assert after_missing_sale_second.stock == 3
        assert after_missing_sale_second.updated_uid == "seller"

        failing_service = SellService(
            OrderRepository(pool),  # type: ignore[arg-type]
            products,
            FailingReplaceProductCache(
                redis,
                f"{key_prefix}:products:info",
            ),
            labels,
            label_cache,
            IntegrationUsers(
                UserPO(
                    uid="seller",
                    email="seller@example.com",
                    user_name="Seller",
                    password="0" * 64,
                    permission=UserRole.USER,
                    created_at=now,
                    updated_at=now,
                )
            ),  # type: ignore[arg-type]
            IntegrationAuthorization(),  # type: ignore[arg-type]
        )
        with pytest.raises(OrderServiceUnavailableError):
            await failing_service.sell(
                AuthorizationObject(uid="seller", authorization=None),
                info,
            )
        assert await redis.get(f"{key_prefix}:products:info") is None
        persisted_after_cache_failure = await products.get_by_id(
            "1790705105002"
        )
        assert persisted_after_cache_failure is not None
        assert persisted_after_cache_failure.stock == 1
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) FROM tb_orders")
            assert (await cursor.fetchone())[0] == 2
            await cursor.execute("SELECT COUNT(*) FROM tb_orders_items")
            assert (await cursor.fetchone())[0] == 4
    finally:
        keys = [key async for key in redis.scan_iter(match=f"{key_prefix}:*")]
        if keys:
            await redis.delete(*keys)
        await redis.aclose()
        await connection.close()


@pytest.mark.asyncio
@pytest.mark.skipif(
    DATABASE_URL is None or REDIS_URL is None,
    reason="INTEGRATION_DATABASE_URL and INTEGRATION_REDIS_URL are required",
)
async def test_concurrent_sales_and_product_update_preserve_stock() -> None:
    schema_name = f"test_sell_{uuid4().hex}"
    key_prefix = f"test:sell-concurrent:{uuid4().hex}"
    setup_connection = await AsyncConnection.connect(DATABASE_URL)
    connection_a = None
    connection_b = None
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    now = datetime(2026, 1, 1, 12, 0, 0)
    try:
        await create_sell_schema_tables(setup_connection, schema_name)
        connection_a = await AsyncConnection.connect(DATABASE_URL)
        connection_b = await AsyncConnection.connect(DATABASE_URL)
        await connection_a.execute(f'SET search_path TO "{schema_name}"')
        await connection_b.execute(f'SET search_path TO "{schema_name}"')
        await connection_a.commit()
        await connection_b.commit()
        await connection_a.execute(
            """
            INSERT INTO tb_users (
                uid, email, user_name, password, permission,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                "seller",
                "seller@example.com",
                "Seller",
                "0" * 64,
                UserRole.USER.value,
                now,
                now,
            ),
        )
        await connection_a.execute(
            """
            INSERT INTO tb_labels (
                id, name, created_uid, created_at, updated_uid, updated_at
            ) VALUES (1, 'General', 'seller', %s, 'seller', %s)
            """,
            (now, now),
        )
        await connection_a.execute(
            """
            INSERT INTO tb_products (
                id, name, label_ids, cost, price, stock, delete_flag,
                created_uid, created_at, updated_uid, updated_at
            ) VALUES (
                '1790705105001', 'Product A', '1', 5, 10, 5, FALSE,
                'seller', %s, 'seller', %s
            )
            """,
            (now, now),
        )
        await connection_a.commit()

        pool_a = DirectConnectionPool(connection_a)
        pool_b = DirectConnectionPool(connection_b)
        user = UserPO(
            uid="seller",
            email="seller@example.com",
            user_name="Seller",
            password="0" * 64,
            permission=UserRole.USER,
            created_at=now,
            updated_at=now,
        )

        class PausedProductService(ProductService):
            async def _ProductService__find_visible_product(
                self,
                product_id: str,
            ) -> Product:
                current = await super()._ProductService__find_visible_product(
                    product_id
                )
                product_read_event.set()
                await continue_update_event.wait()
                return current

        def make_service(pool: DirectConnectionPool) -> SellService:
            return SellService(
                OrderRepository(pool),  # type: ignore[arg-type]
                ProductRepository(pool),  # type: ignore[arg-type]
                ProductCacheRepository(
                    redis,
                    f"{key_prefix}:products:info",
                ),
                LabelRepository(pool),  # type: ignore[arg-type]
                LabelCacheRepository(
                    redis,
                    f"{key_prefix}:product:labels",
                ),
                IntegrationUsers(user),  # type: ignore[arg-type]
                IntegrationAuthorization(),  # type: ignore[arg-type]
            )

        info = SellOrderInfo.model_validate(
            {
                "totalAmount": 40,
                "totalDiscount": 32,
                "orderItems": [
                    {
                        "productId": "1790705105001",
                        "quantity": 4,
                        "price": 10,
                        "discount": 8,
                    },
                ],
            }
        )
        auth = AuthorizationObject(uid="seller", authorization=None)
        product_cache = ProductCacheRepository(
            redis,
            f"{key_prefix}:products:info",
        )
        initial_product = await ProductRepository(pool_a).get_by_id(
            "1790705105001"
        )
        assert initial_product is not None
        async with product_cache.products_lock() as lease:
            await product_cache.replace_products(
                [initial_product],
                {1: "General"},
                lease,
            )
        product_read_event = asyncio.Event()
        continue_update_event = asyncio.Event()
        product_service = PausedProductService(
            object(),  # type: ignore[arg-type]
            ProductRepository(pool_a),  # type: ignore[arg-type]
            product_cache,
            LabelRepository(pool_a),  # type: ignore[arg-type]
            LabelCacheRepository(
                redis,
                f"{key_prefix}:product:labels",
            ),
            IntegrationUsers(user),  # type: ignore[arg-type]
            IntegrationAuthorization(),  # type: ignore[arg-type]
        )
        update_task = asyncio.create_task(
            product_service.update(
                auth,
                ProductUpdateInfo(
                    id="1790705105001",
                    name="Updated Product A",
                    label_names="General",
                    cost=Decimal("5"),
                    price=Decimal("10"),
                    stock=None,
                ),
            )
        )
        await product_read_event.wait()
        first_sale = await make_service(pool_a).sell(auth, info)
        continue_update_event.set()
        await update_task

        results = await asyncio.gather(
            make_service(pool_a).sell(auth, info),
            make_service(pool_b).sell(auth, info),
        )

        order_ids = {
            first_sale.info.order_id,
            *(result.info.order_id for result in results),
        }
        assert order_ids == {
            "0000000001",
            "0000000002",
            "0000000003",
        }
        product = await ProductRepository(pool_a).get_by_id(
            "1790705105001"
        )
        assert product is not None
        assert product.stock == 0
        assert product.updated_uid == "seller"
        orders = await OrderRepository(pool_a).get_orders(
            start_date=date.today(),
            end_date_exclusive=date.today() + timedelta(days=1),
        )
        assert len(orders) == 3
        cached = await product_cache.get_products()
        assert cached is not None
        assert cached[0].stock == product.stock
        assert cached[0].updated_uid == product.updated_uid
        assert cached[0].name == "Updated Product A"
    finally:
        for connection in (connection_a, connection_b, setup_connection):
            if connection is not None:
                await connection.close()
        keys = [key async for key in redis.scan_iter(match=f"{key_prefix}:*")]
        if keys:
            await redis.delete(*keys)
        await redis.aclose()
        cleanup_connection = await AsyncConnection.connect(DATABASE_URL)
        try:
            await cleanup_connection.execute(
                f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'
            )
            await cleanup_connection.commit()
        finally:
            await cleanup_connection.close()
