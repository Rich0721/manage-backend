from datetime import datetime
from typing import Any

import pytest
from psycopg import OperationalError
from psycopg.errors import UniqueViolation

from src.constants.user import UserRole
from src.models.po.user import UserPO
from src.repositories.user_repository import UserRepository
from src.repositories.user_repository import DuplicateUserRecordError
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
        self.executemany_error: Exception | None = None

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
        if self.executemany_error:
            raise self.executemany_error


class FakeTransaction(object):
    def __init__(self) -> None:
        self.is_committed = False
        self.is_rolled_back = False

    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        exception_type = args[0]
        self.is_committed = exception_type is None
        self.is_rolled_back = exception_type is not None
        return None


class FakeConnection(object):
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.cursor_value = FakeCursor(rows or [])
        self.insert_call: tuple[str, object] | None = None
        self.error: Exception | None = None
        self.transaction_value = FakeTransaction()

    def cursor(self, **kwargs: object) -> FakeCursor:
        return self.cursor_value

    async def execute(self, query: str, parameters: object) -> None:
        if self.error:
            raise self.error
        self.insert_call = (query, parameters)

    def transaction(self) -> FakeTransaction:
        return self.transaction_value


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


@pytest.mark.asyncio
async def test_get_by_uid_maps_row_and_not_found() -> None:
    found_connection = FakeConnection([ROW])
    found_repository = UserRepository(
        FakePool(found_connection),  # type: ignore[arg-type]
    )
    missing_connection = FakeConnection()
    missing_repository = UserRepository(
        FakePool(missing_connection),  # type: ignore[arg-type]
    )

    found = await found_repository.get_by_uid("uid")
    missing = await missing_repository.get_by_uid("missing")

    assert found is not None
    assert found.uid == "uid"
    assert missing is None
    _, parameters = found_connection.cursor_value.executions[0]
    assert parameters == ("uid",)


@pytest.mark.asyncio
async def test_get_by_emails_uses_batch_query_and_row_lock() -> None:
    connection = FakeConnection([ROW])
    repository = UserRepository(FakePool(connection))  # type: ignore[arg-type]

    users = await repository.get_by_emails(
        ["user@example.com"],
        connection,  # type: ignore[arg-type]
        for_update=True,
    )

    query, parameters = connection.cursor_value.executions[0]
    assert len(users) == 1
    assert "email = ANY(%s)" in query
    assert query.rstrip().endswith("FOR UPDATE")
    assert parameters == (["user@example.com"],)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("roles", "expected"),
    [
        ((UserRole.USER,), ["user"]),
        ((UserRole.MANAGER, UserRole.USER), ["manager", "user"]),
    ],
)
async def test_list_visible_users_uses_only_allowed_roles(
    roles: tuple[UserRole, ...],
    expected: list[str],
) -> None:
    connection = FakeConnection([])
    repository = UserRepository(FakePool(connection))  # type: ignore[arg-type]

    await repository.list_visible_users(roles)

    _, parameters = connection.cursor_value.executions[0]
    assert parameters == (expected,)


@pytest.mark.asyncio
async def test_unique_violation_maps_to_duplicate_record_error() -> None:
    connection = FakeConnection()
    connection.error = UniqueViolation("duplicate")
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

    with pytest.raises(DuplicateUserRecordError):
        await repository.create(user)


@pytest.mark.asyncio
async def test_transaction_commit_and_rollback() -> None:
    success_connection = FakeConnection()
    success_repository = UserRepository(
        FakePool(success_connection),  # type: ignore[arg-type]
    )
    async with success_repository.transaction():
        pass

    failure_connection = FakeConnection()
    failure_repository = UserRepository(
        FakePool(failure_connection),  # type: ignore[arg-type]
    )
    with pytest.raises(RuntimeError, match="failure"):
        async with failure_repository.transaction():
            raise RuntimeError("failure")

    assert success_connection.transaction_value.is_committed
    assert failure_connection.transaction_value.is_rolled_back


@pytest.mark.asyncio
async def test_update_failure_maps_error_and_rolls_back_transaction() -> None:
    connection = FakeConnection()
    connection.cursor_value.executemany_error = OperationalError("failed")
    repository = UserRepository(FakePool(connection))  # type: ignore[arg-type]

    with pytest.raises(UserRepositoryError):
        async with repository.transaction() as transactional_connection:
            await repository.update_permissions(
                {"user@example.com": UserRole.MANAGER},
                NOW,
                transactional_connection,
            )

    assert connection.transaction_value.is_rolled_back
