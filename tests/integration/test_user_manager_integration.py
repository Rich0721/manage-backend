import os
from pathlib import Path
from uuid import uuid4

import pytest
from psycopg import AsyncConnection
from psycopg import IntegrityError
from redis.asyncio import Redis


DATABASE_URL = os.getenv("INTEGRATION_DATABASE_URL")
REDIS_URL = os.getenv("INTEGRATION_REDIS_URL")
DDL_PATH = Path("database/DDL/tables/TB_USERS.sql")


@pytest.mark.asyncio
@pytest.mark.skipif(
    DATABASE_URL is None,
    reason="INTEGRATION_DATABASE_URL is not configured",
)
async def test_postgresql_17_ddl_and_constraints() -> None:
    connection = await AsyncConnection.connect(DATABASE_URL)
    try:
        version_cursor = await connection.execute("SHOW server_version_num")
        version_row = await version_cursor.fetchone()
        assert version_row is not None
        assert str(version_row[0]).startswith("17")

        ddl = DDL_PATH.read_text(encoding="utf-8").replace(
            "CREATE TABLE tb_users",
            "CREATE TEMP TABLE tb_users",
            1,
        )
        await connection.execute(ddl)
        await connection.execute(
            """
            INSERT INTO tb_users (
                uid, email, user_name, password, permission,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP,
                      CURRENT_TIMESTAMP)
            """,
            (
                "u" * 64,
                "valid@example.com",
                "Valid",
                "A" * 64,
                "user",
            ),
        )

        invalid_rows = [
            (
                "v" * 64,
                "valid@example.com",
                "Duplicate",
                "A" * 64,
                "user",
            ),
            (
                "w" * 64,
                "password@example.com",
                "Password",
                "invalid",
                "user",
            ),
            (
                "x" * 64,
                "role@example.com",
                "Role",
                "A" * 64,
                "owner",
            ),
            (
                "y" * 64,
                "null@example.com",
                None,
                "A" * 64,
                "user",
            ),
        ]
        for row in invalid_rows:
            with pytest.raises(IntegrityError):
                async with connection.transaction():
                    await connection.execute(
                        """
                        INSERT INTO tb_users (
                            uid, email, user_name, password, permission,
                            created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s,
                                  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """,
                        row,
                    )
    finally:
        await connection.close()


@pytest.mark.asyncio
@pytest.mark.skipif(
    REDIS_URL is None,
    reason="INTEGRATION_REDIS_URL is not configured",
)
async def test_redis_8_session_ttl_and_transaction() -> None:
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    uid = f"integration-{uuid4().hex}"
    key = f"{uid}:login"
    try:
        server_info = await client.info("server")
        assert str(server_info["redis_version"]).startswith("8.")

        await client.set(key, "Bearer first", ex=300)
        assert await client.get(key) == "Bearer first"
        assert 0 < await client.ttl(key) <= 300

        async with client.pipeline(transaction=True) as pipeline:
            pipeline.delete(key)
            pipeline.set(key, "Bearer replacement", ex=300)
            await pipeline.execute()

        assert await client.get(key) == "Bearer replacement"
        assert 0 < await client.ttl(key) <= 300
    finally:
        await client.delete(key)
        await client.aclose()
