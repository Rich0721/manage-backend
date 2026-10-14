from datetime import datetime
from typing import Any

import pytest
from psycopg import OperationalError

from src.models.po.label import Label
from src.repositories.label_repository import LabelRepository
from src.repositories.label_repository import LabelRepositoryError


NOW = datetime(2026, 1, 1)
ROW = {
    "id": 1,
    "name": "Label",
    "created_uid": "user",
    "created_at": NOW,
    "updated_uid": "user",
    "updated_at": NOW,
}


class FakeCursor(object):
    def __init__(self, execute_error: Exception | None = None) -> None:
        self.execute_error = execute_error

    async def __aenter__(self) -> "FakeCursor":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def execute(self, query: str, parameters: object = ()) -> None:
        if self.execute_error is not None:
            raise self.execute_error
        self.query = query

    async def fetchall(self) -> list[dict[str, Any]]:
        return [ROW]

    async def fetchone(self) -> dict[str, Any]:
        return ROW


class FakeConnection(object):
    def __init__(self, execute_error: Exception | None = None) -> None:
        self.cursor_value = FakeCursor(execute_error)

    def cursor(self, **kwargs: object) -> FakeCursor:
        return self.cursor_value

    async def execute(self, query: str, parameters: object = ()) -> None:
        self.query = query


class ConnectionContext(object):
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self.connection

    async def __aexit__(self, *args: object) -> None:
        return None


class FakePool(object):
    def __init__(self, connection: FakeConnection | None = None) -> None:
        self.connection_value = connection or FakeConnection()

    def connection(self) -> ConnectionContext:
        return ConnectionContext(self.connection_value)


@pytest.mark.asyncio
async def test_list_all_maps_labels_in_id_order() -> None:
    repository = LabelRepository(FakePool())  # type: ignore[arg-type]

    labels = await repository.list_all()

    assert labels[0].id == 1
    assert labels[0].name == "Label"


@pytest.mark.asyncio
async def test_list_all_maps_database_error() -> None:
    repository = LabelRepository(
        FakePool(FakeConnection(OperationalError()))  # type: ignore[arg-type]
    )

    with pytest.raises(LabelRepositoryError):
        await repository.list_all()


@pytest.mark.asyncio
async def test_list_all_in_transaction_reuses_connection() -> None:
    connection = FakeConnection()
    repository = LabelRepository(FakePool())  # type: ignore[arg-type]

    labels = await repository.list_all_in_transaction(
        connection,  # type: ignore[arg-type]
    )

    assert labels[0].name == "Label"
    assert "FROM tb_labels" in connection.cursor_value.query


@pytest.mark.asyncio
async def test_insert_uses_transaction_and_returns_generated_id() -> None:
    connection = FakeConnection()
    repository = LabelRepository(FakePool())  # type: ignore[arg-type]
    label = await repository.insert(
        Label(
            id=0,
            name="New",
            created_uid="user",
            created_at=NOW,
            updated_uid="user",
            updated_at=NOW,
        ),
        connection,  # type: ignore[arg-type]
    )

    assert label.id == 1
    assert connection.cursor_value.query.strip().startswith(
        "INSERT INTO tb_labels"
    )
