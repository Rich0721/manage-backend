import os
from datetime import datetime
from uuid import uuid4

import asyncpg
import pytest

from src.repositories.user_repository import UserRepository


@pytest.fixture
async def connection():
    try:
        connection = await asyncpg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER", "manage"),
            password=os.getenv("POSTGRES_PASSWORD", "change-me"),
            database=os.getenv("POSTGRES_DB", "manage"),
        )
    except (OSError, asyncpg.PostgresError) as error:
        pytest.skip(f"PostgreSQL integration service unavailable: {error}")

    try:
        yield connection
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_user_repository_crud_and_role_scoped_lists(connection) -> None:
    suffix = uuid4().hex
    users = [
        (f"admin-{suffix}", "admin"),
        (f"manager-{suffix}", "manager"),
        (f"user-{suffix}", "user"),
    ]
    repository = UserRepository(connection)

    try:
        for uid, permission in users:
            await repository.create(
                uid=uid,
                email=f"{uid}@example.com",
                user_name="shared-name",
                password="hash",
                permission=permission,
            )

        manager = await repository.get_by_uid(users[1][0])
        assert manager is not None
        assert manager.user_name == "shared-name"
        assert manager.password == "hash"

        admin_list = await repository.list_non_admin_excluding_uid(
            users[0][0]
        )
        assert {user.uid for user in admin_list} == {
            users[1][0],
            users[2][0],
        }

        manager_list = await repository.list_by_permission_excluding_uid(
            "user",
            users[1][0],
        )
        assert [user.uid for user in manager_list] == [users[2][0]]

        updated = await repository.update_permission(users[2][0], "manager")
        assert updated is not None
        assert updated.permission == "manager"
        assert updated.user_name == "shared-name"
    finally:
        await connection.execute(
            "DELETE FROM TB_USERS WHERE uid LIKE $1",
            f"%-{suffix}",
        )