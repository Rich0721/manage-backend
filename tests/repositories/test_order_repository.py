import os
from contextlib import asynccontextmanager
from datetime import date
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from psycopg import AsyncConnection
import pytest

from src.models.po.order import OrderItemPO
from src.models.po.order import OrderPO
from src.repositories.order_repository import OrderRepository
from src.repositories.order_repository import OrderRepositoryError
from src.repositories.product_repository import ProductRepository


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


DATABASE_URL = os.getenv("INTEGRATION_DATABASE_URL")
TABLES_DIRECTORY = Path("database/DDL/tables")


async def create_order_test_tables(connection: AsyncConnection) -> None:
    await connection.execute(
        """
        CREATE TEMP TABLE tb_users (
            uid VARCHAR(256) PRIMARY KEY,
            user_name VARCHAR(256) NOT NULL
        )
        """
    )
    product_ddl = (TABLES_DIRECTORY / "TB_PRODUCTS.sql").read_text(
        encoding="utf-8"
    ).replace("CREATE TABLE tb_products", "CREATE TEMP TABLE tb_products", 1)
    order_ddl = (TABLES_DIRECTORY / "TB_ORDERS.sql").read_text(
        encoding="utf-8"
    )
    order_ddl = order_ddl.replace(
        "CREATE SEQUENCE seq_tb_orders_id",
        "CREATE TEMP SEQUENCE seq_tb_orders_id",
        1,
    ).replace("CREATE TABLE tb_orders", "CREATE TEMP TABLE tb_orders", 1)
    item_ddl = (TABLES_DIRECTORY / "TB_ORDERS_ITEMS.sql").read_text(
        encoding="utf-8"
    ).replace(
        "CREATE TABLE tb_orders_items",
        "CREATE TEMP TABLE tb_orders_items",
        1,
    )
    await connection.execute(product_ddl)
    await connection.execute(order_ddl)
    await connection.execute(item_ddl)
    await connection.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(
    DATABASE_URL is None,
    reason="INTEGRATION_DATABASE_URL is not configured",
)
async def test_order_repository_creates_and_queries_order_with_product_names() -> None:
    connection = await AsyncConnection.connect(DATABASE_URL)
    now = datetime(2026, 10, 19, 12, 0, 0)
    try:
        await create_order_test_tables(connection)
        await connection.execute(
            "INSERT INTO tb_users (uid, user_name) VALUES (%s, %s)",
            ("seller", "Seller"),
        )
        next_midnight = datetime(2026, 10, 20, 0, 0, 0)
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
                "",
                Decimal("5"),
                Decimal("10"),
                4,
                "seller",
                now,
                "seller",
                now,
            ),
        )
        await connection.execute(
            """
            INSERT INTO tb_orders (
                id, total_amount, total_discount, created_uid, created_at
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (
                "0000000002",
                Decimal("10"),
                Decimal("8"),
                "seller",
                next_midnight,
            ),
        )
        await connection.commit()

        pool = DirectConnectionPool(connection)
        orders = OrderRepository(pool)  # type: ignore[arg-type]
        products = ProductRepository(pool)  # type: ignore[arg-type]
        async with products.transaction() as transaction:
            order_id = await orders.next_order_id(transaction)
            await orders.insert_order(
                OrderPO(
                    id=order_id,
                    total_amount=Decimal("20"),
                    total_discount=Decimal("15"),
                    created_uid="seller",
                    created_at=now,
                ),
                transaction,
            )
            await orders.insert_items(
                [
                    OrderItemPO(
                        order_id=order_id,
                        product_id="1790705105001",
                        quantity=2,
                        price=Decimal("10"),
                        discount=Decimal("7.50"),
                        created_at=now,
                        created_by="seller",
                    ),
                ],
                transaction,
            )
        by_id = await orders.get_orders(order_id=order_id)
        by_date = await orders.get_orders(
            start_date=date(2026, 10, 19),
            end_date_exclusive=date(2026, 10, 20),
        )
        after_midnight = await orders.get_orders(
            start_date=date(2026, 10, 20),
            end_date_exclusive=date(2026, 10, 21),
        )

        assert order_id == "0000000001"
        assert by_id[0].created_by == "Seller"
        assert by_id[0].items[0].product_name == "Product A"
        assert len(by_date) == 1
        assert len(after_midnight) == 1
        assert after_midnight[0].id == "0000000002"
    finally:
        await connection.close()


@pytest.mark.asyncio
@pytest.mark.skipif(
    DATABASE_URL is None,
    reason="INTEGRATION_DATABASE_URL is not configured",
)
async def test_order_items_reject_duplicate_product_for_same_order() -> None:
    connection = await AsyncConnection.connect(DATABASE_URL)
    now = datetime(2026, 10, 19, 12, 0, 0)
    try:
        await create_order_test_tables(connection)
        await connection.execute(
            "INSERT INTO tb_users (uid, user_name) VALUES (%s, %s)",
            ("seller", "Seller"),
        )
        await connection.execute(
            """
            INSERT INTO tb_products (
                id, name, label_ids, cost, price, stock,
                created_uid, created_at, updated_uid, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                "1790705105001",
                "Product A",
                "",
                Decimal("5"),
                Decimal("10"),
                4,
                "seller",
                now,
                "seller",
                now,
            ),
        )
        await connection.execute(
            """
            INSERT INTO tb_orders (
                id, total_amount, total_discount, created_uid, created_at
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            ("0000000001", Decimal("20"), Decimal("15"), "seller", now),
        )
        await connection.commit()
        pool = DirectConnectionPool(connection)
        orders = OrderRepository(pool)  # type: ignore[arg-type]
        item = OrderItemPO(
            order_id="0000000001",
            product_id="1790705105001",
            quantity=1,
            price=Decimal("10"),
            discount=Decimal("8"),
            created_at=now,
            created_by="seller",
        )
        with pytest.raises(OrderRepositoryError):
            async with ProductRepository(pool).transaction() as transaction:  # type: ignore[arg-type]
                await orders.insert_items([item, item], transaction)
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) FROM tb_orders_items")
            row = await cursor.fetchone()
        assert row[0] == 0
    finally:
        await connection.close()
