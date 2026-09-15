from datetime import datetime

import pytest

from src.objects.user import StoredUser
from src.services.errors import AuthorizationError
from src.services.user_permission_service import UserPermissionService


class FakeRepository:
    def __init__(self, users: list[StoredUser]) -> None:
        self.users = {user.uid: user for user in users}

    async def get_by_uid(self, uid: str) -> StoredUser | None:
        return self.users.get(uid)

    async def list_non_admin_excluding_uid(self, uid: str):
        return [
            user
            for user in self.users.values()
            if user.uid != uid and user.permission != "admin"
        ]

    async def list_by_permission_excluding_uid(
        self,
        permission: str,
        uid: str,
    ):
        return [
            user
            for user in self.users.values()
            if user.uid != uid and user.permission == permission
        ]

    async def update_permission(self, uid: str, permission: str):
        user = self.users[uid]
        updated = StoredUser(
            uid=user.uid,
            email=user.email,
            user_name=user.user_name,
            password=user.password,
            permission=permission,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self.users[uid] = updated
        return updated


def make_user(uid: str, permission: str) -> StoredUser:
    now = datetime.now()
    return StoredUser(
        uid=uid,
        email=f"{uid}@example.com",
        user_name=uid,
        password="hash",
        permission=permission,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_admin_listing_excludes_admin_and_operator() -> None:
    repository = FakeRepository(
        [
            make_user("admin", "admin"),
            make_user("other-admin", "admin"),
            make_user("manager", "manager"),
            make_user("user", "user"),
        ]
    )

    users = await UserPermissionService(repository).list_users("admin")

    assert {user.uid for user in users} == {"manager", "user"}


@pytest.mark.asyncio
async def test_manager_cannot_update_manager() -> None:
    repository = FakeRepository(
        [make_user("manager", "manager"), make_user("target", "manager")]
    )

    with pytest.raises(AuthorizationError):
        await UserPermissionService(repository).update_permission(
            "manager",
            "target",
            "user",
        )


@pytest.mark.asyncio
async def test_user_cannot_list_users() -> None:
    repository = FakeRepository([make_user("user", "user")])

    with pytest.raises(AuthorizationError):
        await UserPermissionService(repository).list_users("user")