from datetime import datetime
from typing import Any

import pytest
from psycopg import OperationalError

from src.constants.user import UserRole
from src.models.po.user import UserPO
from src.repositories.user_repository import UserRepository
from src.repositories.user_repository import UserRepositoryError


NOW = datetime(2026, 1, 1)
ROW = {
    "uid": "uid",
    "email": "user@example.com",
    "user_name": "User",
    "password": "A" * 64,
    "permission": "user",
    "created_at": NOW,
    "updated_at": NOW,
}


class FakeCursor(object):
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.executions: list[tuple[str, object]] = []
        self.executemany_call: tuple[str, object] | None = None

    async def __aenter__(self) -> "FakeCursor":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def execute(self, query: str, parameters: object) -> None:
        self.executions.append((query, parameters))

    async def fetchone(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None

    async def fetchall(self) -> list[dict[str, Any]]:
        return self.rows

    async def executemany(self, query: str, parameters: object) -> None:
        self.executemany_call = (query, parameters)


class FakeTransaction(object):
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeConnection(object):
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.cursor_value = FakeCursor(rows or [])
        self.insert_call: tuple[str, object] | None = None
        self.error: Exception | None = None

    def cursor(self, **kwargs: object) -> FakeCursor:
        return self.cursor_value

    async def execute(self, query: str, parameters: object) -> None:
        if self.error:
            raise self.error
        self.insert_call = (query, parameters)

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()


class ConnectionContext(object):
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self.connection

    async def __aexit__(self, *args: object) -> None:
        return None


class FakePool(object):
    def __init__(self, connection: FakeConnection) -> None:
        self.connection_value = connection

    def connection(self) -> ConnectionContext:
        return ConnectionContext(self.connection_value)


@pytest.mark.asyncio
async def test_get_by_email_uses_parameter_and_maps_row() -> None:
    connection = FakeConnection([ROW])
    repository = UserRepository(FakePool(connection))  # type: ignore[arg-type]

    user = await repository.get_by_email("user@example.com")

    assert user is not None
    assert user.permission is UserRole.USER
    query, parameters = connection.cursor_value.executions[0]
    assert "WHERE email = %s" in query
    assert parameters == ("user@example.com",)


@pytest.mark.asyncio
async def test_create_parameterizes_all_values() -> None:
    connection = FakeConnection()
    repository = UserRepository(FakePool(connection))  # type: ignore[arg-type]
    user = UserPO(
        uid="uid",
        email="user@example.com",
        user_name="User",
        password="A" * 64,
        permission=UserRole.USER,
        created_at=NOW,
        updated_at=NOW,
    )

    await repository.create(user)

    assert connection.insert_call is not None
    query, parameters = connection.insert_call
    assert "VALUES (%s, %s, %s, %s, %s, %s, %s)" in query
    assert parameters == (
        "uid",
        "user@example.com",
        "User",
        "A" * 64,
        "user",
        NOW,
        NOW,
    )


@pytest.mark.asyncio
async def test_list_visible_users_passes_explicit_role_filter() -> None:
    connection = FakeConnection([ROW])
    repository = UserRepository(FakePool(connection))  # type: ignore[arg-type]

    users = await repository.list_visible_users((UserRole.USER,))

    assert len(users) == 1
    _, parameters = connection.cursor_value.executions[0]
    assert parameters == (["user"],)


@pytest.mark.asyncio
async def test_permission_updates_use_executemany() -> None:
    connection = FakeConnection()
    repository = UserRepository(FakePool(connection))  # type: ignore[arg-type]

    await repository.update_permissions(
        {"user@example.com": UserRole.MANAGER},
        NOW,
        connection,  # type: ignore[arg-type]
    )

    assert connection.cursor_value.executemany_call is not None
    _, parameters = connection.cursor_value.executemany_call
    assert parameters == [("manager", NOW, "user@example.com")]


@pytest.mark.asyncio
async def test_database_error_is_hidden_behind_repository_error() -> None:
    connection = FakeConnection()
    connection.error = OperationalError("database unavailable")
    repository = UserRepository(FakePool(connection))  # type: ignore[arg-type]
    user = UserPO(
        uid="uid",
        email="user@example.com",
        user_name="User",
        password="A" * 64,
        permission=UserRole.USER,
        created_at=NOW,
        updated_at=NOW,
    )

    with pytest.raises(UserRepositoryError):
        await repository.create(user)
