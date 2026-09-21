from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.constants.user import UserRole
from src.models.po.user import UserPO
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.user import LoginRequestInfo
from src.models.schemas.user import PermissionUpdateItem
from src.models.schemas.user import RegisterRequestInfo
from src.services.authorization_service import AuthorizationContext
from src.services.errors import DuplicateEmailError
from src.services.errors import DuplicatePermissionTargetError
from src.services.errors import ExistingSessionError
from src.services.errors import InvalidCredentialsError
from src.services.errors import PasswordMismatchError
from src.services.errors import PermissionDeniedError
from src.services.user_service import UserService


PASSWORD = "A" * 64


class TestSettings(object):
    SECRET_KEY = "s" * 64
    REDIS_TTL = 300


def make_user(
    email: str,
    role: UserRole = UserRole.USER,
    *,
    uid: str | None = None,
) -> UserPO:
    now = datetime(2026, 1, 1)
    return UserPO(
        uid=uid or f"uid-{email}",
        email=email,
        user_name=email.split("@")[0],
        password=PASSWORD,
        permission=role,
        created_at=now,
        updated_at=now,
    )


class FakeUserRepository(object):
    def __init__(self, users: list[UserPO] | None = None) -> None:
        self.users = {user.email: user for user in users or []}
        self.created: UserPO | None = None
        self.updated: dict[str, UserRole] = {}

    async def get_by_email(self, email: str, connection: object = None) -> UserPO | None:
        return self.users.get(email)

    async def get_by_uid(self, uid: str, connection: object = None) -> UserPO | None:
        return next((user for user in self.users.values() if user.uid == uid), None)

    async def create(self, user: UserPO) -> UserPO:
        self.created = user
        self.users[user.email] = user
        return user

    async def list_visible_users(self, roles: tuple[UserRole, ...]) -> list[UserPO]:
        return [user for user in self.users.values() if user.permission in roles]

    @asynccontextmanager
    async def transaction(self):
        yield object()

    async def get_by_emails(
        self,
        emails: list[str],
        connection: object,
        *,
        for_update: bool,
    ) -> list[UserPO]:
        return [self.users[email] for email in emails if email in self.users]

    async def update_permissions(
        self,
        updates: dict[str, UserRole],
        updated_at: datetime,
        connection: object,
    ) -> None:
        self.updated = updates


def make_service(
    users: FakeUserRepository,
    sessions: AsyncMock | None = None,
    authorization: AsyncMock | None = None,
) -> tuple[UserService, AsyncMock, AsyncMock]:
    sessions = sessions or AsyncMock()
    authorization = authorization or AsyncMock()
    authorization.validate_session.return_value = AuthorizationContext(
        "operator",
        "Bearer token",
        False,
    )
    return (
        UserService(TestSettings(), users, sessions, authorization),
        sessions,
        authorization,
    )


@pytest.mark.asyncio
async def test_register_stores_lowercase_email_and_original_hash_once() -> None:
    users = FakeUserRepository()
    service, _, _ = make_service(users)
    info = RegisterRequestInfo(
        email="USER@EXAMPLE.COM",
        userName="User",
        password=PASSWORD,
        confirmPassword=PASSWORD,
    )

    result = await service.register(info)

    assert users.created is not None
    assert users.created.email == "user@example.com"
    assert users.created.password == PASSWORD
    assert users.created.permission is UserRole.USER
    assert result.uid == users.created.uid


@pytest.mark.asyncio
async def test_register_rejects_password_mismatch_and_duplicate() -> None:
    users = FakeUserRepository([make_user("user@example.com")])
    service, _, _ = make_service(users)
    mismatch = RegisterRequestInfo(
        email="other@example.com",
        userName="Other",
        password=PASSWORD,
        confirmPassword="B" * 64,
    )
    duplicate = RegisterRequestInfo(
        email="user@example.com",
        userName="User",
        password=PASSWORD,
        confirmPassword=PASSWORD,
    )

    with pytest.raises(PasswordMismatchError):
        await service.register(mismatch)
    with pytest.raises(DuplicateEmailError):
        await service.register(duplicate)


@pytest.mark.asyncio
async def test_login_creates_session_and_force_replaces_existing_session() -> None:
    user = make_user("user@example.com")
    sessions = AsyncMock()
    sessions.get.side_effect = [None, "Bearer old"]
    service, _, _ = make_service(FakeUserRepository([user]), sessions)
    normal = LoginRequestInfo(
        email=user.email,
        password=PASSWORD,
        isForceLogin=False,
    )
    forced = LoginRequestInfo(
        email=user.email,
        password=PASSWORD,
        isForceLogin=True,
    )

    first = await service.login(normal)
    second = await service.login(forced)

    sessions.set.assert_awaited_once_with(user.uid, first.authorization)
    sessions.force_replace.assert_awaited_once_with(user.uid, second.authorization)


@pytest.mark.asyncio
async def test_login_existing_session_without_force_has_no_mutation() -> None:
    user = make_user("user@example.com")
    sessions = AsyncMock()
    sessions.get.return_value = "Bearer existing"
    service, _, _ = make_service(FakeUserRepository([user]), sessions)

    with pytest.raises(ExistingSessionError):
        await service.login(
            LoginRequestInfo(
                email=user.email,
                password=PASSWORD,
                isForceLogin=False,
            ),
        )
    sessions.set.assert_not_awaited()
    sessions.force_replace.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_user_and_wrong_password_share_error() -> None:
    user = make_user("user@example.com")
    service, _, _ = make_service(FakeUserRepository([user]))

    for email, password in [
        ("missing@example.com", PASSWORD),
        (user.email, "B" * 64),
    ]:
        with pytest.raises(InvalidCredentialsError):
            await service.login(
                LoginRequestInfo(
                    email=email,
                    password=password,
                    isForceLogin=False,
                ),
            )


@pytest.mark.asyncio
async def test_logout_uses_stored_user_name_and_deletes_session() -> None:
    operator = make_user("user@example.com", uid="operator")
    service, sessions, _ = make_service(FakeUserRepository([operator]))

    result = await service.logout(
        AuthorizationObject(uid="operator", authorization="Bearer token"),
    )

    assert result.user_name == "user"
    sessions.delete.assert_awaited_once_with("operator")


@pytest.mark.asyncio
async def test_admin_list_excludes_admins_and_refreshes_session() -> None:
    operator = make_user("admin@example.com", UserRole.ADMIN, uid="operator")
    manager = make_user("manager@example.com", UserRole.MANAGER)
    user = make_user("user@example.com", UserRole.USER)
    service, _, authorization = make_service(
        FakeUserRepository([operator, manager, user]),
    )

    result = await service.get_users(AuthorizationObject(uid="operator"))

    assert [item.permission for item in result.info.root] == [
        UserRole.MANAGER,
        UserRole.USER,
    ]
    authorization.refresh_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_role_cannot_list_users() -> None:
    operator = make_user("user@example.com", UserRole.USER, uid="operator")
    service, _, _ = make_service(FakeUserRepository([operator]))

    with pytest.raises(PermissionDeniedError):
        await service.get_users(AuthorizationObject(uid="operator"))


@pytest.mark.asyncio
async def test_permission_matrix_allows_manager_to_promote_user() -> None:
    operator = make_user("manager@example.com", UserRole.MANAGER, uid="operator")
    target = make_user("user@example.com", UserRole.USER)
    users = FakeUserRepository([operator, target])
    service, _, authorization = make_service(users)

    await service.update_permissions(
        AuthorizationObject(uid="operator"),
        [PermissionUpdateItem(email=target.email, Permission="manager")],
    )

    assert users.updated == {target.email: UserRole.MANAGER}
    authorization.refresh_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_manager_cannot_modify_manager() -> None:
    operator = make_user("operator@example.com", UserRole.MANAGER, uid="operator")
    target = make_user("target@example.com", UserRole.MANAGER)
    users = FakeUserRepository([operator, target])
    service, _, _ = make_service(users)

    with pytest.raises(PermissionDeniedError):
        await service.update_permissions(
            AuthorizationObject(uid="operator"),
            [PermissionUpdateItem(email=target.email, Permission="user")],
        )
    assert users.updated == {}


@pytest.mark.asyncio
async def test_duplicate_permission_target_is_rejected_before_transaction() -> None:
    operator = make_user("operator@example.com", UserRole.ADMIN, uid="operator")
    users = FakeUserRepository([operator])
    service, _, _ = make_service(users)
    items = [
        PermissionUpdateItem(email="user@example.com", Permission="user"),
        PermissionUpdateItem(email="USER@example.com", Permission="manager"),
    ]

    with pytest.raises(DuplicatePermissionTargetError):
        await service.update_permissions(
            AuthorizationObject(uid="operator"),
            items,
        )
    assert users.updated == {}
