from collections.abc import AsyncIterator

import asyncpg

from config.settings import Settings


async def create_database_pool(settings: Settings) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn=settings.postgres_dsn)


async def close_database_pool(pool: asyncpg.Pool | None) -> None:
    if pool is not None:
        await pool.close()


async def database_connection(
    pool: asyncpg.Pool,
) -> AsyncIterator[asyncpg.Connection]:
    async with pool.acquire() as connection:
        yield connection