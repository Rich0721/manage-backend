import asyncio
import json
from datetime import datetime
from decimal import Decimal

import pytest

from src.models.po.product import Product
from src.repositories.product_cache_repository import ProductCacheRepository
from src.repositories.product_cache_repository import ProductCacheRepositoryError


class FakeRedis(object):
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.renewals = 0

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
        *arguments: object,
    ) -> int:
        if self.values.get(key) != token:
            return 0
        if "pexpire" in script:
            self.renewals += 1
            return 1
        await self.delete(key)
        return 1


@pytest.mark.asyncio
async def test_products_cache_round_trips_soft_deleted_product() -> None:
    client = FakeRedis()
    cache = ProductCacheRepository(client)  # type: ignore[arg-type]
    product = Product(
        id="1790705105001",
        name="Deleted product",
        label_ids="1,2",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        delete_flag=True,
        created_uid="creator",
        created_at=datetime(2026, 1, 1, 1, 2, 3),
        updated_uid="updater",
        updated_at=datetime(2026, 1, 2, 1, 2, 3),
    )

    await cache.replace_products([product], {1: "Label1", 2: "Label2"})

    assert await cache.get_products() == [product]
    cached_product = json.loads(client.values["products:info"])[0]
    assert cached_product["label_names"] == ["Label1", "Label2"]


@pytest.mark.asyncio
async def test_products_lock_is_released_by_owner_only() -> None:
    client = FakeRedis()
    cache = ProductCacheRepository(client)  # type: ignore[arg-type]

    async with cache.products_lock() as lease:
        assert "products:info:lock" in client.values
        await lease.ensure_held()

    assert "products:info:lock" not in client.values
    assert client.renewals == 1


@pytest.mark.asyncio
async def test_products_lock_refuses_cache_publication_after_lease_loss() -> None:
    client = FakeRedis()
    cache = ProductCacheRepository(client)  # type: ignore[arg-type]

    async with cache.products_lock() as lease:
        client.values["products:info:lock"] = "another-owner"
        with pytest.raises(ProductCacheRepositoryError):
            await lease.ensure_held()

    assert client.values["products:info:lock"] == "another-owner"


@pytest.mark.asyncio
async def test_products_lock_renews_while_a_writer_holds_it() -> None:
    client = FakeRedis()
    cache = ProductCacheRepository(client)  # type: ignore[arg-type]
    cache._LOCK_RENEW_SECONDS = 0.001

    async with cache.products_lock():
        await asyncio.sleep(0.01)

    assert client.renewals > 0


@pytest.mark.asyncio
async def test_products_lock_times_out_when_another_writer_holds_it() -> None:
    client = FakeRedis()
    client.values["products:info:lock"] = "another-owner"
    cache = ProductCacheRepository(client)  # type: ignore[arg-type]
    cache._LOCK_ATTEMPTS = 1

    with pytest.raises(ProductCacheRepositoryError):
        async with cache.products_lock():
            pass
