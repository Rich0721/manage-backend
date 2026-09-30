from datetime import datetime
from decimal import Decimal

import pytest

from src.models.po.product import Product
from src.repositories.product_cache_repository import ProductCacheRepository


class FakeRedis(object):
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, **kwargs: object) -> bool:
        self.values[key] = value
        return True

    async def delete(self, key: str) -> int:
        return int(self.values.pop(key, None) is not None)


@pytest.mark.asyncio
async def test_products_cache_round_trips_soft_deleted_product() -> None:
    cache = ProductCacheRepository(FakeRedis())  # type: ignore[arg-type]
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

    await cache.replace_products([product])

    assert await cache.get_products() == [product]
