from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

from src.models.po.product import Product
from src.repositories.product_repository import ProductRepository


NOW = datetime(2026, 1, 1)
ROW = {
    "id": "1790705105001",
    "name": "Product",
    "label_ids": "1",
    "cost": Decimal("100.00"),
    "price": Decimal("150.00"),
    "delete_flag": False,
    "created_uid": "user",
    "created_at": NOW,
    "updated_uid": "user",
    "updated_at": NOW,
}


class FakeCursor(object):
    def __init__(self, rowcount: int = 1) -> None:
        self.rowcount = rowcount
        self.executions: list[tuple[str, object]] = []

    async def __aenter__(self) -> "FakeCursor":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def execute(self, query: str, parameters: object = ()) -> None:
        self.executions.append((query, parameters))

    async def fetchall(self) -> list[dict[str, Any]]:
        return [ROW]

    async def fetchone(self) -> dict[str, Any] | None:
        return ROW


class FakeConnection(object):
    def __init__(self, rowcount: int = 1) -> None:
        self.cursor_value = FakeCursor(rowcount)

    def cursor(self, **kwargs: object) -> FakeCursor:
        return self.cursor_value


class ConnectionContext(object):
    def __init__(self, connection: FakeConnection) -> None:
        self.connection_value = connection

    async def __aenter__(self) -> FakeConnection:
        return self.connection_value

    async def __aexit__(self, *args: object) -> None:
        return None


class FakePool(object):
    def __init__(self, connection: FakeConnection) -> None:
        self.connection_value = connection

    def connection(self) -> ConnectionContext:
        return ConnectionContext(self.connection_value)


def make_product() -> Product:
    return Product(
        id="1790705105001",
        name="Product",
        label_ids="1",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
        delete_flag=False,
        created_uid="user",
        created_at=NOW,
        updated_uid="user",
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_list_products_maps_all_rows() -> None:
    connection = FakeConnection()
    repository = ProductRepository(FakePool(connection))  # type: ignore[arg-type]

    products = await repository.list_all()

    assert products == [make_product()]
    assert "FROM tb_products" in connection.cursor_value.executions[0][0]


@pytest.mark.asyncio
async def test_get_by_id_uses_parameterized_query() -> None:
    connection = FakeConnection()
    repository = ProductRepository(FakePool(connection))  # type: ignore[arg-type]

    product = await repository.get_by_id("1790705105001")

    assert product == make_product()
    query, parameters = connection.cursor_value.executions[0]
    assert "WHERE id = %s" in query
    assert parameters == ("1790705105001",)


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["update", "soft_delete"])
async def test_update_and_soft_delete_require_visible_row(method: str) -> None:
    connection = FakeConnection(rowcount=0)
    repository = ProductRepository(FakePool(connection))  # type: ignore[arg-type]

    if method == "update":
        changed = await repository.update(make_product(), connection)  # type: ignore[arg-type]
    else:
        changed = await repository.soft_delete(
            "1790705105001",
            "user",
            NOW,
            connection,  # type: ignore[arg-type]
        )

    assert not changed
    assert "delete_flag = FALSE" in connection.cursor_value.executions[0][0]
