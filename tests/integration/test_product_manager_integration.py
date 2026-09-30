import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from psycopg import AsyncConnection
from redis.asyncio import Redis

from src.models.po.product import Product
from src.repositories.product_cache_repository import ProductCacheRepository


DATABASE_URL = os.getenv("INTEGRATION_DATABASE_URL")
REDIS_URL = os.getenv("INTEGRATION_REDIS_URL")
LABEL_DDL_PATH = Path("database/DDL/tables/TB_LABELS.sql")
PRODUCT_DDL_PATH = Path("database/DDL/tables/TB_PRODUCTS.sql")


@pytest.mark.asyncio
@pytest.mark.skipif(
    DATABASE_URL is None,
    reason="INTEGRATION_DATABASE_URL is not configured",
)
async def test_product_and_label_ddl_support_soft_deleted_products() -> None:
    connection = await AsyncConnection.connect(DATABASE_URL)
    try:
        labels_ddl = LABEL_DDL_PATH.read_text(encoding="utf-8").replace(
            "CREATE TABLE tb_labels",
            "CREATE TEMP TABLE tb_labels",
            1,
        )
        products_ddl = PRODUCT_DDL_PATH.read_text(encoding="utf-8").replace(
            "CREATE TABLE tb_products",
            "CREATE TEMP TABLE tb_products",
            1,
        )
        await connection.execute(labels_ddl)
        await connection.execute(products_ddl)
        now = datetime(2026, 1, 1)
        await connection.execute(
            """
            INSERT INTO tb_labels (
                id, name, created_uid, created_at, updated_uid, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (1, "Label", "user", now, "user", now),
        )
        await connection.execute(
            """
            INSERT INTO tb_products (
                id, name, label_ids, cost, price, delete_flag,
                created_uid, created_at, updated_uid, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                "1790705105001",
                "Deleted",
                "1",
                Decimal("100.00"),
                Decimal("150.00"),
                True,
                "user",
                now,
                "user",
                now,
            ),
        )
        cursor = await connection.execute(
            "SELECT delete_flag FROM tb_products WHERE id = %s",
            ("1790705105001",),
        )
        row = await cursor.fetchone()
        assert row == (True,)
    finally:
        await connection.close()


@pytest.mark.asyncio
@pytest.mark.skipif(
    REDIS_URL is None,
    reason="INTEGRATION_REDIS_URL is not configured",
)
async def test_products_cache_preserves_complete_snapshot() -> None:
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    prefix = uuid4().hex
    cache = ProductCacheRepository(client, f"test:{prefix}:products:info")
    product = Product(
        id="1790705105001",
        name=f"Deleted-{prefix}",
        label_ids="1",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        delete_flag=True,
        created_uid="user",
        created_at=datetime(2026, 1, 1),
        updated_uid="user",
        updated_at=datetime(2026, 1, 2),
    )
    try:
        await cache.replace_products([product])
        assert await cache.get_products() == [product]
    finally:
        await cache.invalidate_products()
        await client.aclose()
