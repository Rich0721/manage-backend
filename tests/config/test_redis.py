from collections.abc import Iterator
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from redis.asyncio import Redis

from src.config.redis import RedisConnectionManager


class TestSettings(object):
    REDIS_URL = "redis://user:secret@redis:6379/0"


@pytest.fixture
def redis_client() -> AsyncMock:
    client = AsyncMock(spec=Redis)
    client.ping = AsyncMock(return_value=True)
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def manager() -> RedisConnectionManager:
    return RedisConnectionManager(TestSettings())


@pytest.fixture
def from_url(redis_client: AsyncMock) -> Iterator[MagicMock]:
    with patch(
        "src.config.redis.Redis.from_url",
        return_value=redis_client,
    ) as mocked_from_url:
        yield mocked_from_url


@pytest.mark.asyncio
async def test_connect_uses_configured_url_and_decodes_responses(
    manager: RedisConnectionManager,
    redis_client: AsyncMock,
    from_url: MagicMock,
) -> None:
    await manager.connect()

    from_url.assert_called_once_with(
        TestSettings.REDIS_URL,
        decode_responses=True,
    )
    redis_client.ping.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_successful_ping_enables_get_client(
    manager: RedisConnectionManager,
    redis_client: AsyncMock,
    from_url: MagicMock,
) -> None:
    await manager.connect()

    assert manager.get_client() is redis_client


@pytest.mark.asyncio
async def test_ping_failure_closes_partial_client_and_disconnects_manager(
    manager: RedisConnectionManager,
    redis_client: AsyncMock,
    from_url: MagicMock,
) -> None:
    connection_error = ConnectionError("Redis is unavailable")
    redis_client.ping.side_effect = connection_error

    with pytest.raises(ConnectionError) as error:
        await manager.connect()

    assert error.value is connection_error
    redis_client.aclose.assert_awaited_once_with()
    with pytest.raises(RuntimeError, match="Redis client is not connected"):
        manager.get_client()


@pytest.mark.asyncio
async def test_normal_context_exit_closes_client_once(
    manager: RedisConnectionManager,
    redis_client: AsyncMock,
    from_url: MagicMock,
) -> None:
    async with manager as connected_client:
        assert connected_client is redis_client

    redis_client.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_exceptional_context_exit_preserves_original_error(
    manager: RedisConnectionManager,
    redis_client: AsyncMock,
    from_url: MagicMock,
) -> None:
    original_error = RuntimeError("caller failed")

    with pytest.raises(RuntimeError) as error:
        async with manager:
            raise original_error

    assert error.value is original_error
    redis_client.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_context_exit_close_failure_does_not_replace_caller_error(
    manager: RedisConnectionManager,
    redis_client: AsyncMock,
    from_url: MagicMock,
) -> None:
    original_error = RuntimeError("caller failed")
    redis_client.aclose.side_effect = ConnectionError("close failed")

    with pytest.raises(RuntimeError) as error:
        async with manager:
            raise original_error

    assert error.value is original_error
    redis_client.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_context_exit_close_only_failure_propagates(
    manager: RedisConnectionManager,
    redis_client: AsyncMock,
    from_url: MagicMock,
) -> None:
    close_error = ConnectionError("close failed")
    redis_client.aclose.side_effect = close_error

    with pytest.raises(ConnectionError) as error:
        async with manager:
            pass

    assert error.value is close_error


@pytest.mark.asyncio
async def test_context_entry_failure_does_not_leave_open_client(
    manager: RedisConnectionManager,
    redis_client: AsyncMock,
    from_url: MagicMock,
) -> None:
    redis_client.ping.side_effect = ConnectionError("connect failed")

    with pytest.raises(ConnectionError, match="connect failed"):
        async with manager:
            pass

    redis_client.aclose.assert_awaited_once_with()
    with pytest.raises(RuntimeError, match="Redis client is not connected"):
        manager.get_client()


@pytest.mark.asyncio
async def test_repeated_connect_does_not_create_another_client(
    manager: RedisConnectionManager,
    redis_client: AsyncMock,
    from_url: MagicMock,
) -> None:
    await manager.connect()
    await manager.connect()

    from_url.assert_called_once_with(
        TestSettings.REDIS_URL,
        decode_responses=True,
    )
    redis_client.ping.assert_awaited_once_with()


def test_get_client_before_connect_fails(
    manager: RedisConnectionManager,
) -> None:
    with pytest.raises(RuntimeError, match="Redis client is not connected"):
        manager.get_client()


@pytest.mark.asyncio
async def test_close_clears_state_and_is_idempotent(
    manager: RedisConnectionManager,
    redis_client: AsyncMock,
    from_url: MagicMock,
) -> None:
    await manager.connect()

    await manager.close()
    await manager.close()

    redis_client.aclose.assert_awaited_once_with()
    with pytest.raises(RuntimeError, match="Redis client is not connected"):
        manager.get_client()
