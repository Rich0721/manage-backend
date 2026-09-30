import asyncio
import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.constants.product import ProductCacheKey
from src.models.po.label import Label


class LabelCacheRepositoryError(Exception):
    pass


class LabelCacheRepository(object):
    _LOCK_SECONDS = 10
    _LOCK_ATTEMPTS = 20
    _LOCK_RETRY_SECONDS = 0.05

    def __init__(self, client: Redis) -> None:
        self.__client = client

    @asynccontextmanager
    async def lock(self) -> AsyncIterator[None]:
        token = secrets.token_urlsafe(24)
        acquired = False
        lock_key = f"{ProductCacheKey.LABELS}:lock"
        try:
            for _ in range(self._LOCK_ATTEMPTS):
                try:
                    acquired = bool(
                        await self.__client.set(
                            lock_key,
                            token,
                            nx=True,
                            ex=self._LOCK_SECONDS,
                        )
                    )
                except RedisError as error:
                    raise LabelCacheRepositoryError from error
                if acquired:
                    break
                await asyncio.sleep(self._LOCK_RETRY_SECONDS)
            if not acquired:
                raise LabelCacheRepositoryError
            yield
        finally:
            if acquired:
                try:
                    await self.__client.eval(
                        """
                        if redis.call('get', KEYS[1]) == ARGV[1] then
                            return redis.call('del', KEYS[1])
                        end
                        return 0
                        """,
                        1,
                        lock_key,
                        token,
                    )
                except RedisError as error:
                    raise LabelCacheRepositoryError from error

    async def get(self) -> dict[str, tuple[int, str]] | None:
        try:
            raw_labels = await self.__client.get(ProductCacheKey.LABELS)
        except RedisError as error:
            raise LabelCacheRepositoryError from error
        if raw_labels is None:
            return None
        try:
            values = json.loads(raw_labels)
            return {
                normalized_name: (int(value["id"]), value["name"])
                for normalized_name, value in values.items()
            }
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise LabelCacheRepositoryError from error

    async def replace(self, labels: list[Label]) -> None:
        values: dict[str, dict[str, int | str]] = {}
        for label in labels:
            normalized_name = self.normalize_name(label.name)
            existing = values.get(normalized_name)
            if existing is not None and existing["id"] != label.id:
                raise LabelCacheRepositoryError
            values[normalized_name] = {"id": label.id, "name": label.name}
        try:
            await self.__client.set(ProductCacheKey.LABELS, json.dumps(values))
        except RedisError as error:
            raise LabelCacheRepositoryError from error

    async def invalidate(self) -> None:
        try:
            await self.__client.delete(ProductCacheKey.LABELS)
        except RedisError as error:
            raise LabelCacheRepositoryError from error

    @staticmethod
    def normalize_name(name: str) -> str:
        return name.strip().casefold()
