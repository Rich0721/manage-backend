import asyncio
import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.constants.product import ProductCacheKey
from src.models.po.label import Label
from src.models.po.product import Product


class ProductCacheRepositoryError(Exception):
    pass


class ProductCacheRepository(object):
    _LOCK_SECONDS = 10
    _LOCK_ATTEMPTS = 20
    _LOCK_RETRY_SECONDS = 0.05

    def __init__(self, client: Redis) -> None:
        self.__client = client

    @asynccontextmanager
    async def products_lock(self) -> AsyncIterator[None]:
        async with self.__lock(f"{ProductCacheKey.PRODUCTS}:lock"):
            yield

    @asynccontextmanager
    async def labels_lock(self) -> AsyncIterator[None]:
        async with self.__lock(f"{ProductCacheKey.LABELS}:lock"):
            yield

    async def get_products(self) -> list[Product] | None:
        raw_products = await self.__get(ProductCacheKey.PRODUCTS)
        if raw_products is None:
            return None
        try:
            values = json.loads(raw_products)
            return [self.__product_from_value(value) for value in values]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ProductCacheRepositoryError from error

    async def replace_products(self, products: list[Product]) -> None:
        values = [self.__product_to_value(product) for product in products]
        await self.__set(ProductCacheKey.PRODUCTS, json.dumps(values))

    async def invalidate_products(self) -> None:
        try:
            await self.__client.delete(ProductCacheKey.PRODUCTS)
        except RedisError as error:
            raise ProductCacheRepositoryError from error

    async def get_labels(self) -> dict[str, tuple[int, str]] | None:
        raw_labels = await self.__get(ProductCacheKey.LABELS)
        if raw_labels is None:
            return None
        try:
            values = json.loads(raw_labels)
            return {
                normalized_name: (int(value["id"]), value["name"])
                for normalized_name, value in values.items()
            }
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ProductCacheRepositoryError from error

    async def replace_labels(self, labels: list[Label]) -> None:
        values: dict[str, dict[str, int | str]] = {}
        for label in labels:
            normalized_name = self.normalize_label_name(label.name)
            existing = values.get(normalized_name)
            if existing is not None and existing["id"] != label.id:
                raise ProductCacheRepositoryError
            values[normalized_name] = {"id": label.id, "name": label.name}
        await self.__set(ProductCacheKey.LABELS, json.dumps(values))

    async def invalidate_labels(self) -> None:
        try:
            await self.__client.delete(ProductCacheKey.LABELS)
        except RedisError as error:
            raise ProductCacheRepositoryError from error

    @staticmethod
    def normalize_label_name(name: str) -> str:
        return name.strip().casefold()

    async def __get(self, key: ProductCacheKey) -> str | None:
        try:
            return await self.__client.get(key)
        except RedisError as error:
            raise ProductCacheRepositoryError from error

    async def __set(self, key: ProductCacheKey, value: str) -> None:
        try:
            await self.__client.set(key, value)
        except RedisError as error:
            raise ProductCacheRepositoryError from error

    @asynccontextmanager
    async def __lock(self, key: str) -> AsyncIterator[None]:
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
                        key,
                        token,
                    )
                except RedisError as error:
                    raise ProductCacheRepositoryError from error

    @staticmethod
    def __product_to_value(product: Product) -> dict[str, str | bool]:
        return {
            "id": product.id,
            "name": product.name,
            "label_ids": product.label_ids,
            "cost": str(product.cost),
            "price": str(product.price),
            "delete_flag": product.delete_flag,
            "created_uid": product.created_uid,
            "created_at": product.created_at.isoformat(),
            "updated_uid": product.updated_uid,
            "updated_at": product.updated_at.isoformat(),
        }

    @staticmethod
    def __product_from_value(value: dict[str, str | bool]) -> Product:
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
        )
