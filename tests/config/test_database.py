from collections.abc import Iterator
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from src.config.database import DatabaseConnectionManager


class TestSettings(object):
    DATABASE_URL = "postgresql://user:secret@db/test"


@pytest.fixture
def pool() -> AsyncMock:
    instance = AsyncMock()
    instance.open = AsyncMock()
    instance.wait = AsyncMock()
    instance.close = AsyncMock()
    return instance


@pytest.fixture
def pool_factory(pool: AsyncMock) -> Iterator[MagicMock]:
    with patch(
        "src.config.database.AsyncConnectionPool",
        return_value=pool,
    ) as factory:
        yield factory


@pytest.mark.asyncio
async def test_connect_opens_and_waits_for_pool(
    pool: AsyncMock,
    pool_factory: MagicMock,
) -> None:
    manager = DatabaseConnectionManager(TestSettings())

    await manager.connect()

    pool_factory.assert_called_once_with(
        conninfo=TestSettings.DATABASE_URL,
        open=False,
    )
    pool.open.assert_awaited_once_with()
    pool.wait.assert_awaited_once_with()
    assert manager.get_pool() is pool


@pytest.mark.asyncio
async def test_connect_failure_closes_partial_pool(
    pool: AsyncMock,
    pool_factory: MagicMock,
) -> None:
    pool.wait.side_effect = ConnectionError("unavailable")
    manager = DatabaseConnectionManager(TestSettings())

    with pytest.raises(ConnectionError, match="unavailable"):
        await manager.connect()

    pool.close.assert_awaited_once_with()
    with pytest.raises(RuntimeError, match="Database pool is not connected"):
        manager.get_pool()


@pytest.mark.asyncio
async def test_close_is_idempotent(
    pool: AsyncMock,
    pool_factory: MagicMock,
) -> None:
    manager = DatabaseConnectionManager(TestSettings())
    await manager.connect()

    await manager.close()
    await manager.close()

    pool.close.assert_awaited_once_with()
