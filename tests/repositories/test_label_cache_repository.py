from datetime import datetime

import pytest

from src.models.po.label import Label
from src.repositories.label_cache_repository import LabelCacheRepository


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
        key: str,
        token: str,
    ) -> int:
        if self.values.get(key) != token:
            return 0
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

    await cache.replace([label])

    assert await cache.get() == {"label": (1, " Label ")}
    async with cache.lock():
        assert "product:labels:lock" in client.values
    assert "product:labels:lock" not in client.values
