from datetime import datetime

import pytest
from redis.exceptions import RedisError

from src.models.po.label import Label
from src.repositories.label_cache_repository import LabelCacheRepository
from src.repositories.label_cache_repository import LabelCacheRepositoryError


class FakeRedis(object):
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, **kwargs: object) -> bool:
        if kwargs.get("nx") and key in self.values:
            return False
        self.values[key] = value
        return True

    async def delete(self, key: str) -> int:
        return int(self.values.pop(key, None) is not None)

    async def eval(
        self,
        script: str,
        key_count: int,
        *arguments: object,
    ) -> int:
        key = str(arguments[0])
        token = str(arguments[key_count])
        if self.values.get(key) != token:
            return 0
        if "redis.call('del', KEYS[2])" in script:
            await self.delete(str(arguments[1]))
            return 1
        if "KEYS[2]" in script:
            self.values[str(arguments[1])] = str(arguments[key_count + 1])
            return 1
        if "pexpire" in script:
            return 1
        await self.delete(key)
        return 1


@pytest.mark.asyncio
async def test_label_cache_normalizes_names_and_releases_lock() -> None:
    client = FakeRedis()
    cache = LabelCacheRepository(client)  # type: ignore[arg-type]
    label = Label(
        id=1,
        name=" Label ",
        created_uid="user",
        created_at=datetime(2026, 1, 1),
        updated_uid="user",
        updated_at=datetime(2026, 1, 1),
    )

    async with cache.lock() as lease:
        await cache.replace([label], lease)

    assert await cache.get() == {"label": (1, " Label ")}
    async with cache.lock() as lease:
        assert "product:labels:lock" in client.values
        await lease.ensure_held()
    assert "product:labels:lock" not in client.values


@pytest.mark.asyncio
async def test_label_cache_rejects_duplicate_normalized_names() -> None:
    cache = LabelCacheRepository(FakeRedis())  # type: ignore[arg-type]
    timestamp = datetime(2026, 1, 1)
    first = Label(1, "Label", "user", timestamp, "user", timestamp)
    second = Label(2, " label ", "user", timestamp, "user", timestamp)

    with pytest.raises(LabelCacheRepositoryError):
        async with cache.lock() as lease:
            await cache.replace([first, second], lease)


@pytest.mark.asyncio
async def test_label_cache_cannot_publish_after_lease_loss() -> None:
    client = FakeRedis()
    cache = LabelCacheRepository(client)  # type: ignore[arg-type]
    timestamp = datetime(2026, 1, 1)
    label = Label(1, "Label", "user", timestamp, "user", timestamp)

    async with cache.lock() as lease:
        client.values["product:labels:lock"] = "new-owner"
        client.values["product:labels"] = "newer snapshot"
        with pytest.raises(LabelCacheRepositoryError):
            await cache.replace([label], lease)

    assert client.values["product:labels"] == "newer snapshot"


@pytest.mark.asyncio
async def test_label_cache_cannot_invalidate_after_lease_loss() -> None:
    client = FakeRedis()
    cache = LabelCacheRepository(client)  # type: ignore[arg-type]

    async with cache.lock() as lease:
        client.values["product:labels:lock"] = "new-owner"
        client.values["product:labels"] = "newer snapshot"
        with pytest.raises(LabelCacheRepositoryError):
            await cache.invalidate(lease)

    assert client.values["product:labels"] == "newer snapshot"


@pytest.mark.asyncio
async def test_label_redis_read_failure_is_a_cache_error() -> None:
    class FailingRedis(FakeRedis):
        async def get(self, key: str) -> str | None:
            raise RedisError("unavailable")

    cache = LabelCacheRepository(FailingRedis())  # type: ignore[arg-type]

    with pytest.raises(LabelCacheRepositoryError):
        await cache.get()
