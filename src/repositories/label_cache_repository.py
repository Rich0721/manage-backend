import asyncio
import json
import secrets
from collections.abc import AsyncIterator
from contextlib import suppress
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.constants.product import ProductCacheKey
from src.models.po.label import Label


class LabelCacheRepositoryError(Exception):
    pass


class LabelCacheLockLease(object):
    def __init__(
        self,
        client: Redis,
        key: str,
        token: str,
        seconds: int,
    ) -> None:
        self.__client = client
        self.__key = key
        self.__token = token
        self.__seconds = seconds
        self.__lost = False

    async def renew(self) -> bool:
        try:
            renewed = await self.__client.eval(
                """
                if redis.call('get', KEYS[1]) == ARGV[1] then
                    return redis.call('pexpire', KEYS[1], ARGV[2] * 1000)
                end
                return 0
                """,
                1,
                self.__key,
                self.__token,
                self.__seconds,
            )
        except RedisError as error:
            self.__lost = True
            raise LabelCacheRepositoryError from error
        self.__lost = not bool(renewed)
        return not self.__lost

    async def ensure_held(self) -> None:
        if self.__lost or not await self.renew():
            raise LabelCacheRepositoryError

    async def replace(self, key: str, value: str) -> None:
        """Replace a cache value only while this lease still owns its lock."""
        if self.__lost:
            raise LabelCacheRepositoryError
        try:
            replaced = await self.__client.eval(
                """
                if redis.call('get', KEYS[1]) == ARGV[1] then
                    redis.call('set', KEYS[2], ARGV[2])
                    return 1
                end
                return 0
                """,
                2,
                self.__key,
                key,
                self.__token,
                value,
            )
        except RedisError as error:
            self.__lost = True
            raise LabelCacheRepositoryError from error
        if not replaced:
            self.__lost = True
            raise LabelCacheRepositoryError


class LabelCacheRepository(object):
    _LOCK_SECONDS = 10
    _LOCK_RENEW_SECONDS = 3
    _LOCK_ATTEMPTS = 20
    _LOCK_RETRY_SECONDS = 0.05

    def __init__(self, client: Redis) -> None:
        self.__client = client

    @asynccontextmanager
    async def lock(self) -> AsyncIterator[LabelCacheLockLease]:
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
            lease = LabelCacheLockLease(
                self.__client,
                lock_key,
                token,
                self._LOCK_SECONDS,
            )
            renewal_task = asyncio.create_task(self.__renew_lease(lease))
            try:
                yield lease
            finally:
                renewal_task.cancel()
                with suppress(asyncio.CancelledError):
                    await renewal_task
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

    async def __renew_lease(self, lease: LabelCacheLockLease) -> None:
        while True:
            await asyncio.sleep(self._LOCK_RENEW_SECONDS)
            if not await lease.renew():
                return

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

    async def replace(
        self,
        labels: list[Label],
        lease: LabelCacheLockLease | None = None,
    ) -> None:
        values: dict[str, dict[str, int | str]] = {}
        for label in labels:
            normalized_name = self.normalize_name(label.name)
            existing = values.get(normalized_name)
            if existing is not None and existing["id"] != label.id:
                raise LabelCacheRepositoryError
            values[normalized_name] = {"id": label.id, "name": label.name}
        value = json.dumps(values)
        if lease is None:
            try:
                await self.__client.set(ProductCacheKey.LABELS, value)
            except RedisError as error:
                raise LabelCacheRepositoryError from error
        else:
            await lease.replace(ProductCacheKey.LABELS, value)

    async def invalidate(self) -> None:
        try:
            await self.__client.delete(ProductCacheKey.LABELS)
        except RedisError as error:
            raise LabelCacheRepositoryError from error

    @staticmethod
    def normalize_name(name: str) -> str:
        return name.strip().casefold()
