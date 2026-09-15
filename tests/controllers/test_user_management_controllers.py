from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config.settings import Settings
from src.controllers import user_login_controller
from src.controllers import user_logout_controller
from src.controllers import user_permission_controller
from src.controllers import user_registration_controller
from src.objects.user import StoredUser, User
from src.routers import router
from src.services.errors import AuthenticationError, AuthorizationError
from src.services.errors import RegistrationError


class FakeAcquire:
    def __init__(self, connection) -> None:
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exception_type, exception, traceback) -> None:
        return None


class FakePool:
    def __init__(self) -> None:
        self.connection = object()

    def acquire(self) -> FakeAcquire:
        return FakeAcquire(self.connection)


def make_user(permission: str = "user") -> User:
    now = datetime.now()
    return User(
        uid="user-uid",
        email="user@example.com",
        user_name="testuser",
        permission=permission,
        created_at=now,
        updated_at=now,
    )


def make_stored_user(permission: str = "user") -> StoredUser:
    now = datetime.now()
    return StoredUser(
        uid="user-uid",
        email="user@example.com",
        user_name="testuser",
        password="hashed-password",
        permission=permission,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.state.database_pool = FakePool()
    app.state.redis_client = object()
    return TestClient(app)


def test_register_returns_success_envelope(client, monkeypatch) -> None:
    class FakeRepository:
        def __init__(self, connection) -> None:
            pass

        async def get_by_email(self, email: str):
            return None

        async def create(self, **kwargs):
            return make_user()

    monkeypatch.setattr(
        user_registration_controller,
        "UserRepository",
        FakeRepository,
    )

    response = client.post(
        "/userController/register",
        json={
            "header": {},
            "body": {
                "email": "user@example.com",
                "userName": "testuser",
                "password": "hashed-password",
                "confirmPassword": "hashed-password",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["header"]["message"] == (
        "User registered successfully"
    )
    assert response.json()["body"]["user_name"] == "testuser"


def test_register_returns_failure_for_invalid_input(client) -> None:
    response = client.post(
        "/userController/register",
        json={
            "header": {},
            "body": {
                "email": "invalid",
                "userName": "testuser",
                "password": "hash",
                "confirmPassword": "hash",
            },
        },
    )

    assert response.status_code == 401
    assert response.json()["header"]["status"] == "Failed"


def test_login_first_stage_returns_success(client, monkeypatch) -> None:
    class FakeLoginService:
        def __init__(self, *args) -> None:
            pass

        async def request_temporary_code(self, email: str, password: str):
            return None

    monkeypatch.setattr(
        user_login_controller,
        "UserLoginService",
        FakeLoginService,
    )
    monkeypatch.setattr(
        user_login_controller,
        "get_settings",
        lambda: Settings(
            postgres_db="manage",
            postgres_user="manage",
            postgres_password="secret",
            smtp_host="localhost",
            smtp_from_email="no-reply@example.com",
        ),
    )

    response = client.post(
        "/userController/login",
        json={
            "header": {},
            "body": {
                "email": "user@example.com",
                "password": "hashed-password",
            },
        },
    )

    assert response.status_code == 200
    assert "Temporary code has been sent" in response.json()["header"][
        "message"
    ]


def test_login_second_stage_returns_failure(client, monkeypatch) -> None:
    class FakeLoginService:
        def __init__(self, *args) -> None:
            pass

        async def verify_temporary_code(self, email: str, code: str):
            raise AuthenticationError("Temporary code verification failed")

    monkeypatch.setattr(
        user_login_controller,
        "UserLoginService",
        FakeLoginService,
    )
    monkeypatch.setattr(
        user_login_controller,
        "get_settings",
        lambda: Settings(
            postgres_db="manage",
            postgres_user="manage",
            postgres_password="secret",
            smtp_host="localhost",
            smtp_from_email="no-reply@example.com",
        ),
    )

    response = client.post(
        "/userController/login",
        json={
            "header": {},
            "body": {
                "email": "user@example.com",
                "temporary_code": "wrong1",
            },
        },
    )

    assert response.status_code == 401
    assert response.json()["header"]["message"] == (
        "Temporary code verification failed"
    )


def test_logout_rejects_unknown_uid(client, monkeypatch) -> None:
    class FakeRepository:
        def __init__(self, connection) -> None:
            pass

        async def get_by_uid(self, uid: str):
            return None

    monkeypatch.setattr(user_logout_controller, "UserRepository", FakeRepository)

    response = client.post(
        "/userController/logout",
        json={
            "header": {"uid": "unknown"},
            "body": {"email": "user@example.com"},
        },
    )

    assert response.status_code == 401
    assert response.json()["header"]["message"] == "Unauthorized"


def test_get_users_returns_role_scoped_users(client, monkeypatch) -> None:
    class FakePermissionService:
        def __init__(self, repository) -> None:
            pass

        async def list_users(self, operator_uid: str):
            return [make_user()]

    monkeypatch.setattr(
        user_permission_controller,
        "UserPermissionService",
        FakePermissionService,
    )

    response = client.get("/userController/getUsers?uid=admin-uid")

    assert response.status_code == 200
    assert response.json()["body"][0]["user_name"] == "testuser"
    assert "password" not in response.json()["body"][0]


def test_update_permission_returns_unauthorized(client, monkeypatch) -> None:
    class FakePermissionService:
        def __init__(self, repository) -> None:
            pass

        async def update_permission(self, **kwargs):
            raise AuthorizationError("Unauthorized")

    monkeypatch.setattr(
        user_permission_controller,
        "UserPermissionService",
        FakePermissionService,
    )

    response = client.put(
        "/userController/updatePermission",
        json={
            "header": {"uid": "operator-uid"},
            "body": {"uid": "target-uid", "target_role": "admin"},
        },
    )

    assert response.status_code == 401
    assert response.json()["header"]["message"] == "Unauthorized"