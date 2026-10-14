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
        version_key: str,
        token: str,
        seconds: int,
        version: int,
    ) -> None:
        self.__client = client
        self.__key = key
        self.__version_key = version_key
        self.__token = token
        self.__seconds = seconds
        self.__version = version
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

    async def invalidate(self, key: str) -> None:
        if self.__lost:
            raise LabelCacheRepositoryError
        try:
            invalidated = await self.__client.eval(
                """
                if redis.call('get', KEYS[1]) == ARGV[1] then
                    local version = redis.call('incr', KEYS[3])
                    redis.call('del', KEYS[2])
                    return version
                end
                return 0
                """,
                3,
                self.__key,
                key,
                self.__version_key,
                self.__token,
            )
        except RedisError as error:
            self.__lost = True
            raise LabelCacheRepositoryError from error
        if not invalidated:
            self.__lost = True
            raise LabelCacheRepositoryError
        self.__version = int(invalidated)

    async def replace(self, key: str, value: str) -> None:
        """Replace a cache value only while this lease still owns its lock."""
        if self.__lost:
            raise LabelCacheRepositoryError
        try:
            replaced = await self.__client.eval(
                """
                if redis.call('get', KEYS[1]) == ARGV[1]
                    and (redis.call('get', KEYS[3]) or '0') == ARGV[2] then
                    redis.call('set', KEYS[2], ARGV[3])
                    return 1
                end
                return 0
                """,
                3,
                self.__key,
                key,
                self.__version_key,
                self.__token,
                str(self.__version),
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

    def __init__(
        self,
        client: Redis,
        labels_key: str = ProductCacheKey.LABELS,
    ) -> None:
        self.__client = client
        self.__labels_key = labels_key
        self.__version_key = f"{labels_key}:version"

    @asynccontextmanager
    async def lock(self) -> AsyncIterator[LabelCacheLockLease]:
        token = secrets.token_urlsafe(24)
        acquired = False
        lock_key = f"{self.__labels_key}:lock"
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
            try:
                version = int(await self.__client.get(self.__version_key) or 0)
            except (RedisError, ValueError) as error:
                raise LabelCacheRepositoryError from error
            lease = LabelCacheLockLease(
                self.__client,
                lock_key,
                self.__version_key,
                token,
                self._LOCK_SECONDS,
                version,
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
            raw_labels = await self.__client.get(self.__labels_key)
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
        lease: LabelCacheLockLease,
    ) -> None:
        values: dict[str, dict[str, int | str]] = {}
        for label in labels:
            normalized_name = self.normalize_name(label.name)
            existing = values.get(normalized_name)
            if existing is not None and existing["id"] != label.id:
                raise LabelCacheRepositoryError
            values[normalized_name] = {"id": label.id, "name": label.name}
        value = json.dumps(values)
        await lease.replace(self.__labels_key, value)

    async def invalidate(self, lease: LabelCacheLockLease) -> None:
        await lease.invalidate(self.__labels_key)

    async def invalidate_after_commit(self) -> None:
        """Drop a potentially stale label snapshot after a committed write."""
        try:
            await self.__client.eval(
                """
                redis.call('incr', KEYS[2])
                redis.call('del', KEYS[1])
                return 1
                """,
                2,
                self.__labels_key,
                self.__version_key,
            )
        except RedisError as error:
            raise LabelCacheRepositoryError from error

    @staticmethod
    def normalize_name(name: str) -> str:
        return name.strip().casefold()
