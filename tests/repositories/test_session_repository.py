from typing import Any

import pytest
from redis.exceptions import ConnectionError

from src.repositories.session_repository import SessionRepository
from src.repositories.session_repository import SessionRepositoryError


class FakePipeline(object):
    def __init__(self, redis: "FakeRedis") -> None:
        self.redis = redis
        self.commands: list[tuple[Any, ...]] = []

    async def __aenter__(self) -> "FakePipeline":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def delete(self, key: str) -> None:
        self.commands.append(("delete", key))

    def set(self, key: str, value: str, *, ex: int) -> None:
        self.commands.append(("set", key, value, ex))

    async def execute(self) -> None:
        if self.redis.error:
            raise self.redis.error
        self.redis.pipeline_commands = self.commands


class FakeRedis(object):
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}
        self.pipeline_commands: list[tuple[Any, ...]] = []
        self.error: Exception | None = None

    async def get(self, key: str) -> str | None:
        if self.error:
            raise self.error
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ex: int) -> None:
        if self.error:
            raise self.error
        self.values[key] = value
        self.expirations[key] = ex

    async def delete(self, key: str) -> int:
        if self.error:
            raise self.error
        return 1 if self.values.pop(key, None) is not None else 0

    async def expire(self, key: str, ttl: int) -> bool:
        if self.error:
            raise self.error
        if key not in self.values:
            return False
        self.expirations[key] = ttl
        return True

    def pipeline(self, *, transaction: bool) -> FakePipeline:
        assert transaction is True
        return FakePipeline(self)


@pytest.mark.asyncio
async def test_session_crud_and_ttl() -> None:
    client = FakeRedis()
    repository = SessionRepository(client, 300)  # type: ignore[arg-type]

    await repository.set("uid", "Bearer token")
    assert await repository.get("uid") == "Bearer token"
    assert client.expirations["uid:login"] == 300
    await repository.refresh("uid")
    assert await repository.delete("uid")
    assert await repository.get("uid") is None


@pytest.mark.asyncio
async def test_force_replace_uses_transaction_pipeline() -> None:
    client = FakeRedis()
    repository = SessionRepository(client, 300)  # type: ignore[arg-type]

    await repository.force_replace("uid", "Bearer replacement")

    assert client.pipeline_commands == [
        ("delete", "uid:login"),
        ("set", "uid:login", "Bearer replacement", 300),
    ]


@pytest.mark.asyncio
async def test_redis_failure_is_mapped() -> None:
    client = FakeRedis()
    client.error = ConnectionError("unavailable")
    repository = SessionRepository(client, 300)  # type: ignore[arg-type]

    with pytest.raises(SessionRepositoryError):
        await repository.get("uid")


@pytest.mark.asyncio
async def test_refresh_missing_session_is_failure() -> None:
    repository = SessionRepository(FakeRedis(), 300)  # type: ignore[arg-type]

    with pytest.raises(SessionRepositoryError):
        await repository.refresh("uid")


@pytest.mark.asyncio
async def test_delete_missing_session_returns_false() -> None:
    repository = SessionRepository(FakeRedis(), 300)  # type: ignore[arg-type]

    assert not await repository.delete("uid")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation",
    ["set", "force_replace", "delete", "refresh"],
)
async def test_write_operation_redis_failure_is_mapped(
    operation: str,
) -> None:
    client = FakeRedis()
    client.error = ConnectionError("unavailable")
    repository = SessionRepository(client, 300)  # type: ignore[arg-type]

    with pytest.raises(SessionRepositoryError):
        if operation == "set":
            await repository.set("uid", "Bearer token")
        elif operation == "force_replace":
            await repository.force_replace("uid", "Bearer token")
        elif operation == "delete":
            await repository.delete("uid")
        else:
            await repository.refresh("uid")
