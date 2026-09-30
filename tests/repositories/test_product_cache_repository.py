import asyncio
import json
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest
from redis.exceptions import RedisError

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
        *arguments: object,
    ) -> int:
        keys = [str(key) for key in arguments[:key_count]]
        args = [str(argument) for argument in arguments[key_count:]]
        if "incr" in script and "ARGV[1]" not in script:
            version_key = keys[1]
            self.values[version_key] = str(
                int(self.values.get(version_key, "0")) + 1
            )
            await self.delete(keys[0])
            return 1
        if self.values.get(keys[0]) != args[0]:
            return 0
        if "incr" in script:
            version_key = keys[2]
            version = int(self.values.get(version_key, "0")) + 1
            self.values[version_key] = str(version)
            await self.delete(keys[1])
            return version
        if "KEYS[3]" in script and "set" in script:
            if self.values.get(keys[2], "0") != args[1]:
                return 0
            self.values[keys[1]] = args[2]
            return 1
        if "pexpire" in script:
            self.renewals += 1
            return 1
        await self.delete(keys[0])
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

    async with cache.products_lock() as lease:
        await cache.replace_products(
            [product], {1: "Label1", 2: "Label2"}, lease
        )

    cached_products = await cache.get_products()
    assert cached_products is not None
    assert cached_products[0].label_names == ("Label1", "Label2")
    cached_product = json.loads(client.values["products:info"])[0]
    assert cached_product["label_names"] == ["Label1", "Label2"]


@pytest.mark.asyncio
async def test_empty_snapshot_differs_from_missing_key() -> None:
    client = FakeRedis()
    cache = ProductCacheRepository(client)  # type: ignore[arg-type]

    assert await cache.get_products() is None
    async with cache.products_lock() as lease:
        await cache.replace_products([], {}, lease)

    assert await cache.get_products() == []


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
async def test_products_lock_cannot_overwrite_a_newer_snapshot_after_lease_loss() -> None:
    client = FakeRedis()
    cache = ProductCacheRepository(client)  # type: ignore[arg-type]
    product = Product(
        id="1790705105001",
        name="Old snapshot",
        label_ids="1",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        delete_flag=False,
        created_uid="creator",
        created_at=datetime(2026, 1, 1),
        updated_uid="updater",
        updated_at=datetime(2026, 1, 2),
    )

    async with cache.products_lock() as lease:
        client.values["products:info:lock"] = "new-owner"
        client.values["products:info"] = "newer snapshot"
        with pytest.raises(ProductCacheRepositoryError):
            await cache.replace_products([product], {1: "Label1"}, lease)

    assert client.values["products:info"] == "newer snapshot"


@pytest.mark.asyncio
async def test_lost_writer_cannot_invalidate_new_writer_snapshot() -> None:
    client = FakeRedis()
    cache = ProductCacheRepository(client)  # type: ignore[arg-type]
    product = Product(
        id="1790705105001",
        name="New product",
        label_ids="1",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        delete_flag=False,
        created_uid="creator",
        created_at=datetime(2026, 1, 1),
        updated_uid="updater",
        updated_at=datetime(2026, 1, 2),
    )

    async with cache.products_lock() as first_lease:
        client.values.pop("products:info:lock")  # Simulate lease expiry.
        async with cache.products_lock() as second_lease:
            await cache.invalidate_products(second_lease)
            await cache.replace_products(
                [product], {1: "Label1"}, second_lease
            )
            with pytest.raises(ProductCacheRepositoryError):
                await cache.invalidate_products(first_lease)
            assert (await cache.get_products())[0].name == "New product"


@pytest.mark.asyncio
async def test_commit_fences_a_writer_and_waiting_cold_loader() -> None:
    client = FakeRedis()
    cache = ProductCacheRepository(client)  # type: ignore[arg-type]
    old_product = Product(
        id="1790705105001",
        name="Old product",
        label_ids="1",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        delete_flag=False,
        created_uid="creator",
        created_at=datetime(2026, 1, 1),
        updated_uid="updater",
        updated_at=datetime(2026, 1, 2),
    )
    new_product = replace(old_product, name="Committed product")

    async with cache.products_lock() as first_writer:
        await cache.invalidate_products(first_writer)
        client.values.pop("products:info:lock")  # First writer loses lease.
        async with cache.products_lock() as second_writer:
            await cache.invalidate_products(second_writer)

            async def cold_load() -> list[Product] | None:
                async with cache.products_lock() as cold_lease:
                    products = await cache.get_products()
                    if products is None:
                        await cache.replace_products(
                            [new_product], {1: "Label1"}, cold_lease
                        )
                    return await cache.get_products()

            cold_task = asyncio.create_task(cold_load())
            await asyncio.sleep(0)

            # The first DB transaction commits after the second writer read.
            await cache.invalidate_after_commit()
            with pytest.raises(ProductCacheRepositoryError):
                await cache.replace_products(
                    [old_product], {1: "Label1"}, second_writer
                )
            with pytest.raises(ProductCacheRepositoryError):
                await cache.replace_products(
                    [old_product], {1: "Label1"}, first_writer
                )

        loaded = await cold_task

    assert loaded is not None
    assert loaded[0].name == "Committed product"
    assert (await cache.get_products())[0].name == "Committed product"


@pytest.mark.asyncio
async def test_commit_removes_earlier_snapshot() -> None:
    client = FakeRedis()
    cache = ProductCacheRepository(client)  # type: ignore[arg-type]
    product = Product(
        id="1790705105001",
        name="Stale snapshot",
        label_ids="1",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        delete_flag=False,
        created_uid="creator",
        created_at=datetime(2026, 1, 1),
        updated_uid="updater",
        updated_at=datetime(2026, 1, 2),
    )

    async with cache.products_lock() as first_writer:
        await cache.invalidate_products(first_writer)
        client.values.pop("products:info:lock")
        async with cache.products_lock() as second_writer:
            await cache.invalidate_products(second_writer)
            await cache.replace_products(
                [product], {1: "Label1"}, second_writer
            )
            await cache.invalidate_after_commit()

    assert await cache.get_products() is None


@pytest.mark.asyncio
async def test_snapshot_rejects_missing_label_names() -> None:
    client = FakeRedis()
    cache = ProductCacheRepository(client)  # type: ignore[arg-type]
    product = Product(
        id="1790705105001",
        name="Product",
        label_ids="1",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        delete_flag=False,
        created_uid="creator",
        created_at=datetime(2026, 1, 1),
        updated_uid="updater",
        updated_at=datetime(2026, 1, 2),
    )

    async with cache.products_lock() as lease:
        with pytest.raises(ProductCacheRepositoryError):
            await cache.replace_products([product], {}, lease)

    assert await cache.get_products() is None


@pytest.mark.asyncio
async def test_redis_read_failure_is_a_cache_error() -> None:
    class FailingRedis(FakeRedis):
        async def get(self, key: str) -> str | None:
            raise RedisError("unavailable")

    cache = ProductCacheRepository(FailingRedis())  # type: ignore[arg-type]

    with pytest.raises(ProductCacheRepositoryError):
        await cache.get_products()


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
