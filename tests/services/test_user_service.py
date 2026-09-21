from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch

import jwt
import pytest
from pydantic import ValidationError

from src.constants.user import UserRole
from src.models.po.user import UserPO
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.user import LoginRequestInfo
from src.models.schemas.user import PermissionUpdateItem
from src.models.schemas.user import RegisterRequestInfo
from src.repositories.session_repository import SessionRepositoryError
from src.repositories.user_repository import DuplicateUserRecordError
from src.repositories.user_repository import UserRepositoryError
from src.services.authorization_service import AuthorizationContext
from src.services.errors import DuplicateEmailError
from src.services.errors import DuplicatePermissionTargetError
from src.services.errors import ExistingSessionError
from src.services.errors import InvalidCredentialsError
from src.services.errors import PasswordMismatchError
from src.services.errors import PermissionDeniedError
from src.services.errors import ServiceUnavailableError
from src.services.errors import SessionInvalidError
from src.services.errors import UserNotFoundError
from src.services.user_service import UserService
from src.utils.security import hash_uid


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
        self.last_updated_at: datetime | None = None
        self.get_by_email_error: Exception | None = None
        self.create_error: Exception | None = None
        self.get_by_uid_error: Exception | None = None
        self.list_error: Exception | None = None
        self.get_by_emails_error: Exception | None = None
        self.update_error: Exception | None = None
        self.transaction_started = False
        self.transaction_committed = False
        self.transaction_rolled_back = False

    async def get_by_email(
        self,
        email: str,
        connection: object = None,
    ) -> UserPO | None:
        if self.get_by_email_error:
            raise self.get_by_email_error
        return self.users.get(email)

    async def get_by_uid(
        self,
        uid: str,
        connection: object = None,
    ) -> UserPO | None:
        if self.get_by_uid_error:
            raise self.get_by_uid_error
        return next(
            (user for user in self.users.values() if user.uid == uid),
            None,
        )

    async def create(self, user: UserPO) -> UserPO:
        if self.create_error:
            raise self.create_error
        self.created = user
        self.users[user.email] = user
        return user

    async def list_visible_users(
        self,
        roles: tuple[UserRole, ...],
    ) -> list[UserPO]:
        if self.list_error:
            raise self.list_error
        return [
            user
            for user in self.users.values()
            if user.permission in roles
        ]

    @asynccontextmanager
    async def transaction(self):
        self.transaction_started = True
        previous_updates = self.updated.copy()
        try:
            yield object()
        except BaseException:
            self.updated = previous_updates
            self.transaction_rolled_back = True
            raise
        else:
            self.transaction_committed = True

    async def get_by_emails(
        self,
        emails: list[str],
        connection: object,
        *,
        for_update: bool,
    ) -> list[UserPO]:
        if self.get_by_emails_error:
            raise self.get_by_emails_error
        return [self.users[email] for email in emails if email in self.users]

    async def update_permissions(
        self,
        updates: dict[str, UserRole],
        updated_at: datetime,
        connection: object,
    ) -> None:
        self.updated = updates
        self.last_updated_at = updated_at
        if self.update_error:
            raise self.update_error


def make_service(
    users: FakeUserRepository,
    sessions: AsyncMock | None = None,
    authorization: AsyncMock | None = None,
) -> tuple[UserService, AsyncMock, AsyncMock]:
    if sessions is None:
        sessions = AsyncMock()
        sessions.delete.return_value = True
    if authorization is None:
        authorization = AsyncMock()
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
async def test_register_stores_lowercase_email_and_hash_once() -> None:
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
    assert users.created.uid == hash_uid("user@example.com")
    assert users.created.created_at == users.created.updated_at
    assert result.uid == users.created.uid
    assert not hasattr(result, "confirm_password")


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


def test_register_rejects_invalid_email_at_schema_boundary() -> None:
    with pytest.raises(ValidationError):
        RegisterRequestInfo(
            email="invalid",
            userName="User",
            password=PASSWORD,
            confirmPassword=PASSWORD,
        )


@pytest.mark.asyncio
async def test_register_unique_race_maps_to_duplicate_email() -> None:
    users = FakeUserRepository()
    users.create_error = DuplicateUserRecordError()
    service, _, _ = make_service(users)
    info = RegisterRequestInfo(
        email="user@example.com",
        userName="User",
        password=PASSWORD,
        confirmPassword=PASSWORD,
    )

    with pytest.raises(DuplicateEmailError):
        await service.register(info)


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["lookup", "create"])
async def test_register_database_failure_is_service_unavailable(
    stage: str,
) -> None:
    users = FakeUserRepository()
    if stage == "lookup":
        users.get_by_email_error = UserRepositoryError()
    else:
        users.create_error = UserRepositoryError()
    service, _, _ = make_service(users)
    info = RegisterRequestInfo(
        email="user@example.com",
        userName="User",
        password=PASSWORD,
        confirmPassword=PASSWORD,
    )

    with pytest.raises(ServiceUnavailableError):
        await service.register(info)


@pytest.mark.asyncio
async def test_login_creates_and_force_replaces_session() -> None:
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
    sessions.force_replace.assert_awaited_once_with(
        user.uid,
        second.authorization,
    )


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
async def test_login_database_failure_is_service_unavailable() -> None:
    users = FakeUserRepository()
    users.get_by_email_error = UserRepositoryError()
    service, _, _ = make_service(users)

    with pytest.raises(ServiceUnavailableError):
        await service.login(
            LoginRequestInfo(
                email="user@example.com",
                password=PASSWORD,
                isForceLogin=False,
            ),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["get", "set", "force_replace"])
async def test_login_redis_failure_is_service_unavailable(stage: str) -> None:
    user = make_user("user@example.com")
    sessions = AsyncMock()
    if stage == "get":
        sessions.get.side_effect = SessionRepositoryError()
        is_force_login = False
    elif stage == "set":
        sessions.get.return_value = None
        sessions.set.side_effect = SessionRepositoryError()
        is_force_login = False
    else:
        sessions.get.return_value = "Bearer existing"
        sessions.force_replace.side_effect = SessionRepositoryError()
        is_force_login = True
    service, _, _ = make_service(FakeUserRepository([user]), sessions)

    with pytest.raises(ServiceUnavailableError):
        await service.login(
            LoginRequestInfo(
                email=user.email,
                password=PASSWORD,
                isForceLogin=is_force_login,
            ),
        )


@pytest.mark.asyncio
async def test_login_token_generation_failure_never_stores_session() -> None:
    user = make_user("user@example.com")
    sessions = AsyncMock()
    sessions.get.return_value = None
    service, _, _ = make_service(FakeUserRepository([user]), sessions)

    with patch(
        "src.services.user_service.issue_access_token",
        side_effect=jwt.InvalidKeyError("invalid key"),
    ):
        with pytest.raises(jwt.InvalidKeyError):
            await service.login(
                LoginRequestInfo(
                    email=user.email,
                    password=PASSWORD,
                    isForceLogin=False,
                ),
            )
    sessions.set.assert_not_awaited()


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
async def test_normal_logout_rejects_session_that_disappeared() -> None:
    operator = make_user("user@example.com", uid="operator")
    sessions = AsyncMock()
    sessions.delete.return_value = False
    service, _, _ = make_service(FakeUserRepository([operator]), sessions)

    with pytest.raises(SessionInvalidError):
        await service.logout(AuthorizationObject(uid="operator"))


@pytest.mark.asyncio
async def test_debug_logout_allows_missing_key() -> None:
    operator = make_user("user@example.com", uid="operator")
    sessions = AsyncMock()
    sessions.delete.return_value = False
    authorization = AsyncMock()
    authorization.validate_session.return_value = AuthorizationContext(
        "operator",
        None,
        True,
    )
    service, _, _ = make_service(
        FakeUserRepository([operator]),
        sessions,
        authorization,
    )

    result = await service.logout(AuthorizationObject(uid="operator"))

    assert result.user_name == "user"


@pytest.mark.asyncio
async def test_logout_redis_failure_is_service_unavailable() -> None:
    operator = make_user("user@example.com", uid="operator")
    sessions = AsyncMock()
    sessions.delete.side_effect = SessionRepositoryError()
    service, _, _ = make_service(FakeUserRepository([operator]), sessions)

    with pytest.raises(ServiceUnavailableError):
        await service.logout(AuthorizationObject(uid="operator"))


@pytest.mark.asyncio
async def test_logout_missing_database_user_is_rejected() -> None:
    service, sessions, _ = make_service(FakeUserRepository())

    with pytest.raises(UserNotFoundError):
        await service.logout(AuthorizationObject(uid="operator"))
    sessions.delete.assert_not_awaited()


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
async def test_manager_lists_only_users() -> None:
    operator = make_user(
        "manager@example.com",
        UserRole.MANAGER,
        uid="operator",
    )
    manager = make_user("other-manager@example.com", UserRole.MANAGER)
    user = make_user("user@example.com", UserRole.USER)
    service, _, _ = make_service(
        FakeUserRepository([operator, manager, user]),
    )

    result = await service.get_users(AuthorizationObject(uid="operator"))

    assert [item.email for item in result.info.root] == [user.email]


@pytest.mark.asyncio
async def test_authorized_empty_user_list_is_successful() -> None:
    operator = make_user(
        "manager@example.com",
        UserRole.MANAGER,
        uid="operator",
    )
    service, _, authorization = make_service(FakeUserRepository([operator]))

    result = await service.get_users(AuthorizationObject(uid="operator"))

    assert result.info.root == []
    authorization.refresh_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_users_missing_operator_is_rejected() -> None:
    service, _, authorization = make_service(FakeUserRepository())

    with pytest.raises(UserNotFoundError):
        await service.get_users(AuthorizationObject(uid="operator"))
    authorization.refresh_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_users_repository_failure_does_not_refresh() -> None:
    operator = make_user("admin@example.com", UserRole.ADMIN, uid="operator")
    users = FakeUserRepository([operator])
    users.list_error = UserRepositoryError()
    service, _, authorization = make_service(users)

    with pytest.raises(ServiceUnavailableError):
        await service.get_users(AuthorizationObject(uid="operator"))
    authorization.refresh_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_users_refresh_failure_is_propagated() -> None:
    operator = make_user("admin@example.com", UserRole.ADMIN, uid="operator")
    authorization = AsyncMock()
    authorization.validate_session.return_value = AuthorizationContext(
        "operator",
        "Bearer token",
        False,
    )
    authorization.refresh_session.side_effect = ServiceUnavailableError()
    service, _, _ = make_service(
        FakeUserRepository([operator]),
        authorization=authorization,
    )

    with pytest.raises(ServiceUnavailableError):
        await service.get_users(AuthorizationObject(uid="operator"))


@pytest.mark.asyncio
async def test_get_users_session_mismatch_stops_before_query() -> None:
    operator = make_user("admin@example.com", UserRole.ADMIN, uid="operator")
    authorization = AsyncMock()
    authorization.validate_session.side_effect = SessionInvalidError()
    service, _, _ = make_service(
        FakeUserRepository([operator]),
        authorization=authorization,
    )

    with pytest.raises(SessionInvalidError):
        await service.get_users(AuthorizationObject(uid="operator"))
    authorization.refresh_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_permission_matrix_allows_manager_to_promote_user() -> None:
    operator = make_user(
        "manager@example.com",
        UserRole.MANAGER,
        uid="operator",
    )
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
    operator = make_user(
        "operator@example.com",
        UserRole.MANAGER,
        uid="operator",
    )
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
async def test_duplicate_target_is_rejected_before_transaction() -> None:
    operator = make_user(
        "operator@example.com",
        UserRole.ADMIN,
        uid="operator",
    )
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
    assert not users.transaction_started


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operator_role", "current_role", "target_role", "is_allowed"),
    [
        (UserRole.ADMIN, UserRole.USER, UserRole.USER, True),
        (UserRole.ADMIN, UserRole.USER, UserRole.MANAGER, True),
        (UserRole.ADMIN, UserRole.MANAGER, UserRole.USER, True),
        (UserRole.ADMIN, UserRole.MANAGER, UserRole.MANAGER, True),
        (UserRole.ADMIN, UserRole.ADMIN, UserRole.USER, False),
        (UserRole.ADMIN, UserRole.ADMIN, UserRole.MANAGER, False),
        (UserRole.ADMIN, UserRole.ADMIN, UserRole.ADMIN, False),
        (UserRole.MANAGER, UserRole.USER, UserRole.USER, True),
        (UserRole.MANAGER, UserRole.USER, UserRole.MANAGER, True),
        (UserRole.MANAGER, UserRole.MANAGER, UserRole.USER, False),
        (UserRole.MANAGER, UserRole.ADMIN, UserRole.USER, False),
        (UserRole.USER, UserRole.USER, UserRole.MANAGER, False),
    ],
)
async def test_complete_permission_matrix(
    operator_role: UserRole,
    current_role: UserRole,
    target_role: UserRole,
    is_allowed: bool,
) -> None:
    operator = make_user(
        "operator@example.com",
        operator_role,
        uid="operator",
    )
    target = make_user("target@example.com", current_role)
    users = FakeUserRepository([operator, target])
    service, _, authorization = make_service(users)
    operation = service.update_permissions(
        AuthorizationObject(uid="operator"),
        [
            PermissionUpdateItem(
                email=target.email,
                Permission=target_role,
            ),
        ],
    )

    if is_allowed:
        await operation
        assert users.updated == {target.email: target_role}
        assert users.transaction_committed
        authorization.refresh_session.assert_awaited_once()
    else:
        with pytest.raises(PermissionDeniedError):
            await operation
        assert users.updated == {}
        assert users.transaction_rolled_back
        authorization.refresh_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_permission_update_accepts_multiple_valid_targets() -> None:
    operator = make_user("admin@example.com", UserRole.ADMIN, uid="operator")
    first = make_user("first@example.com", UserRole.USER)
    second = make_user("second@example.com", UserRole.MANAGER)
    users = FakeUserRepository([operator, first, second])
    service, _, _ = make_service(users)

    await service.update_permissions(
        AuthorizationObject(uid="operator"),
        [
            PermissionUpdateItem(
                email=first.email,
                Permission=UserRole.MANAGER,
            ),
            PermissionUpdateItem(
                email=second.email,
                Permission=UserRole.USER,
            ),
        ],
    )

    assert users.updated == {
        first.email: UserRole.MANAGER,
        second.email: UserRole.USER,
    }
    assert users.last_updated_at is not None
    assert users.last_updated_at.tzinfo is None


@pytest.mark.asyncio
async def test_unknown_permission_target_rolls_back_without_write() -> None:
    operator = make_user("admin@example.com", UserRole.ADMIN, uid="operator")
    users = FakeUserRepository([operator])
    service, _, authorization = make_service(users)

    with pytest.raises(UserNotFoundError):
        await service.update_permissions(
            AuthorizationObject(uid="operator"),
            [
                PermissionUpdateItem(
                    email="missing@example.com",
                    Permission=UserRole.USER,
                ),
            ],
        )

    assert users.updated == {}
    assert users.transaction_rolled_back
    authorization.refresh_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_mixed_valid_invalid_permission_batch_rolls_back() -> None:
    operator = make_user(
        "manager@example.com",
        UserRole.MANAGER,
        uid="operator",
    )
    valid = make_user("valid@example.com", UserRole.USER)
    invalid = make_user("invalid@example.com", UserRole.MANAGER)
    users = FakeUserRepository([operator, valid, invalid])
    service, _, _ = make_service(users)

    with pytest.raises(PermissionDeniedError):
        await service.update_permissions(
            AuthorizationObject(uid="operator"),
            [
                PermissionUpdateItem(
                    email=valid.email,
                    Permission=UserRole.MANAGER,
                ),
                PermissionUpdateItem(
                    email=invalid.email,
                    Permission=UserRole.USER,
                ),
            ],
        )

    assert users.updated == {}
    assert users.transaction_rolled_back


@pytest.mark.asyncio
async def test_permission_database_failure_rolls_back_full_batch() -> None:
    operator = make_user("admin@example.com", UserRole.ADMIN, uid="operator")
    target = make_user("target@example.com", UserRole.USER)
    users = FakeUserRepository([operator, target])
    users.update_error = UserRepositoryError()
    service, _, authorization = make_service(users)

    with pytest.raises(ServiceUnavailableError):
        await service.update_permissions(
            AuthorizationObject(uid="operator"),
            [
                PermissionUpdateItem(
                    email=target.email,
                    Permission=UserRole.MANAGER,
                ),
            ],
        )

    assert users.updated == {}
    assert users.transaction_rolled_back
    authorization.refresh_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_permission_target_fetch_failure_rolls_back() -> None:
    operator = make_user("admin@example.com", UserRole.ADMIN, uid="operator")
    target = make_user("target@example.com", UserRole.USER)
    users = FakeUserRepository([operator, target])
    users.get_by_emails_error = UserRepositoryError()
    service, _, authorization = make_service(users)

    with pytest.raises(ServiceUnavailableError):
        await service.update_permissions(
            AuthorizationObject(uid="operator"),
            [
                PermissionUpdateItem(
                    email=target.email,
                    Permission=UserRole.MANAGER,
                ),
            ],
        )

    assert users.transaction_rolled_back
    authorization.refresh_session.assert_not_awaited()
