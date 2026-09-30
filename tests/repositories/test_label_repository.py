from datetime import datetime
from typing import Any

import pytest

from src.repositories.label_repository import LabelRepository


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
    async def __aenter__(self) -> "FakeCursor":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def execute(self, query: str) -> None:
        self.query = query

    async def fetchall(self) -> list[dict[str, Any]]:
        return [ROW]


class FakeConnection(object):
    def __init__(self) -> None:
        self.cursor_value = FakeCursor()

    def cursor(self, **kwargs: object) -> FakeCursor:
        return self.cursor_value


class ConnectionContext(object):
    async def __aenter__(self) -> FakeConnection:
        return FakeConnection()

    async def __aexit__(self, *args: object) -> None:
        return None


class FakePool(object):
    def connection(self) -> ConnectionContext:
        return ConnectionContext()


@pytest.mark.asyncio
async def test_list_all_maps_labels_in_id_order() -> None:
    repository = LabelRepository(FakePool())  # type: ignore[arg-type]

    labels = await repository.list_all()

    assert labels[0].id == 1
    assert labels[0].name == "Label"
