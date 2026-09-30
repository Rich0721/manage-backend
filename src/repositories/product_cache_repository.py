import asyncio
import json
import secrets
from collections.abc import AsyncIterator
from collections.abc import Mapping
from contextlib import suppress
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.constants.product import ProductCacheKey
from src.models.po.product import Product


class ProductCacheRepositoryError(Exception):
    pass


class ProductCacheLockLease(object):
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
            raise ProductCacheRepositoryError from error
        self.__lost = not bool(renewed)
        return not self.__lost

    async def ensure_held(self) -> None:
        if self.__lost or not await self.renew():
            raise ProductCacheRepositoryError

    async def replace(self, key: str, value: str) -> None:
        """Replace a cache value only while this lease still owns its lock."""
        if self.__lost:
            raise ProductCacheRepositoryError
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
            raise ProductCacheRepositoryError from error
        if not replaced:
            self.__lost = True
            raise ProductCacheRepositoryError


class ProductCacheRepository(object):
    _LOCK_SECONDS = 10
    _LOCK_RENEW_SECONDS = 3
    _LOCK_ATTEMPTS = 20
    _LOCK_RETRY_SECONDS = 0.05

    def __init__(
        self,
        client: Redis,
        products_key: str = ProductCacheKey.PRODUCTS,
    ) -> None:
        self.__client = client
        self.__products_key = products_key

    @asynccontextmanager
    async def products_lock(self) -> AsyncIterator[ProductCacheLockLease]:
        async with self.__lock(f"{self.__products_key}:lock") as lease:
            yield lease

    async def get_products(self) -> list[Product] | None:
        raw_products = await self.__get(self.__products_key)
        if raw_products is None:
            return None
        try:
            values = json.loads(raw_products)
            return [self.__product_from_value(value) for value in values]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ProductCacheRepositoryError from error

    async def replace_products(
        self,
        products: list[Product],
        label_names_by_id: Mapping[int, str] | None = None,
        lease: ProductCacheLockLease | None = None,
    ) -> None:
        values = [
            self.__product_to_value(product, label_names_by_id)
            for product in products
        ]
        value = json.dumps(values)
        if lease is None:
            await self.__set(self.__products_key, value)
        else:
            await lease.replace(self.__products_key, value)

    async def invalidate_products(self) -> None:
        try:
            await self.__client.delete(self.__products_key)
        except RedisError as error:
            raise ProductCacheRepositoryError from error

    async def __get(self, key: str) -> str | None:
        try:
            return await self.__client.get(key)
        except RedisError as error:
            raise ProductCacheRepositoryError from error

    async def __set(self, key: str, value: str) -> None:
        try:
            await self.__client.set(key, value)
        except RedisError as error:
            raise ProductCacheRepositoryError from error

    @asynccontextmanager
    async def __lock(self, key: str) -> AsyncIterator[ProductCacheLockLease]:
        token = secrets.token_urlsafe(24)
        acquired = False
        try:
            for _ in range(self._LOCK_ATTEMPTS):
                try:
                    acquired = bool(
                        await self.__client.set(
                            key,
                            token,
                            nx=True,
                            ex=self._LOCK_SECONDS,
                        )
                    )
                except RedisError as error:
                    raise ProductCacheRepositoryError from error
                if acquired:
                    break
                await asyncio.sleep(self._LOCK_RETRY_SECONDS)
            if not acquired:
                raise ProductCacheRepositoryError
            lease = ProductCacheLockLease(
                self.__client,
                key,
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
                        key,
                        token,
                    )
                except RedisError as error:
                    raise ProductCacheRepositoryError from error

    async def __renew_lease(self, lease: ProductCacheLockLease) -> None:
        while True:
            await asyncio.sleep(self._LOCK_RENEW_SECONDS)
            if not await lease.renew():
                return

    @staticmethod
    def __product_to_value(
        product: Product,
        label_names_by_id: Mapping[int, str] | None,
    ) -> dict[str, str | bool | list[str]]:
        if product.label_names is not None:
            label_names = list(product.label_names)
        elif label_names_by_id is None:
            label_names = []
        else:
            try:
                label_names = [
                    label_names_by_id[int(label_id)]
                    for label_id in product.label_ids.split(",")
                ]
            except (KeyError, ValueError) as error:
                raise ProductCacheRepositoryError from error
        return {
            "id": product.id,
            "name": product.name,
            "label_ids": product.label_ids,
            "label_names": label_names,
            "cost": str(product.cost),
            "price": str(product.price),
            "delete_flag": product.delete_flag,
            "created_uid": product.created_uid,
            "created_at": product.created_at.isoformat(),
            "updated_uid": product.updated_uid,
            "updated_at": product.updated_at.isoformat(),
        }

    @staticmethod
    def __product_from_value(value: Mapping[str, object]) -> Product:
        raw_label_names = value.get("label_names")
        if raw_label_names is not None and not isinstance(raw_label_names, list):
            raise TypeError
        label_names = (
            tuple(str(name) for name in raw_label_names)
            if raw_label_names is not None
            and len(raw_label_names) == len(str(value["label_ids"]).split(","))
            else None
        )
        return Product(
            id=str(value["id"]),
            name=str(value["name"]),
            label_ids=str(value["label_ids"]),
            cost=Decimal(str(value["cost"])),
            price=Decimal(str(value["price"])),
            delete_flag=bool(value["delete_flag"]),
            created_uid=str(value["created_uid"]),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            updated_uid=str(value["updated_uid"]),
            updated_at=datetime.fromisoformat(str(value["updated_at"])),
            label_names=label_names,
        )
