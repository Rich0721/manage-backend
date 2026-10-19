import os
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from psycopg import AsyncConnection
from redis.asyncio import Redis
import pytest

from src.constants.user import UserRole
from src.models.po.user import UserPO
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.order import SellOrderInfo
from src.repositories.label_cache_repository import LabelCacheRepository
from src.repositories.label_repository import LabelRepository
from src.repositories.order_repository import OrderRepository
from src.repositories.product_cache_repository import ProductCacheRepository
from src.repositories.product_repository import ProductRepository
from src.repositories.user_repository import UserRepository
from src.services.authorization_service import AuthorizationContext
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
        assert cached[0].stock == persisted.stock
        assert cached[0].updated_uid == persisted.updated_uid
        assert cached[0].updated_at == persisted.updated_at

        snapshot_before_missing_sale = await redis.get(
            f"{key_prefix}:products:info"
        )
        missing_info = SellOrderInfo.model_validate(
            {
                "totalAmount": 20,
                "totalDiscount": 15,
                "orderItems": [
                    {
                        "productId": "1790705105999",
                        "quantity": 1,
                        "price": 10,
                        "discount": 8,
                    },
                ],
            }
        )
        from src.services.order_errors import SoldProductNotFoundError

        with pytest.raises(SoldProductNotFoundError):
            await service.sell(
                AuthorizationObject(uid="seller", authorization=None),
                missing_info,
            )
        assert await redis.get(f"{key_prefix}:products:info") == snapshot_before_missing_sale
        assert len(await OrderRepository(pool).get_orders(order_id="0000000001")) == 1
        after_missing_sale = await products.get_by_id("1790705105001")
        assert after_missing_sale is not None
        assert after_missing_sale.stock == 0
        assert after_missing_sale.updated_uid == "seller"
    finally:
        keys = [key async for key in redis.scan_iter(match=f"{key_prefix}:*")]
        if keys:
            await redis.delete(*keys)
        await redis.aclose()
        await connection.close()
