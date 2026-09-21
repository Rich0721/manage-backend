from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.constants.user import AuthStatus
from src.constants.user import UserMessage
from src.controllers.dependencies import get_user_service
from src.main import create_app
from src.models.schemas.user import GetUsersResponseInfo
from src.models.schemas.user import LoginResponseInfo
from src.models.schemas.user import LogoutResponseInfo
from src.models.schemas.user import RegisterResponseInfo
from src.models.schemas.user import UserSummary
from src.services.authorization_service import AuthorizationContext
from src.services.errors import AuthorizationInvalidError
from src.services.errors import AuthorizationRequiredError
from src.services.errors import DuplicateEmailError
from src.services.errors import ExistingSessionError
from src.services.errors import InvalidCredentialsError
from src.services.errors import PasswordMismatchError
from src.services.errors import PermissionDeniedError
from src.services.errors import ServiceUnavailableError
from src.services.errors import SessionInvalidError
from src.services.errors import UserNotFoundError
from src.services.user_service import LoginResult
from src.services.user_service import ProtectedResult


PASSWORD = "A" * 64


class TestSettings(object):
    REDIS_TTL = 300
    SECRET_KEY = "s" * 64
    DEBUG = True


class FakeManager(object):
    def __init__(self, value: object) -> None:
        self.value = value

    async def __aenter__(self) -> object:
        return self.value

    async def __aexit__(self, *args: object) -> None:
        return None


def make_client(service: AsyncMock) -> TestClient:
    application = create_app(
        settings_factory=TestSettings,
        database_manager_factory=lambda settings: FakeManager(object()),
        redis_manager_factory=lambda settings: FakeManager(object()),
    )
    application.dependency_overrides[get_user_service] = lambda: service
    return TestClient(application, raise_server_exceptions=False)


def test_all_exact_routes_are_registered() -> None:
    application = create_app(
        settings_factory=TestSettings,
        database_manager_factory=lambda settings: FakeManager(object()),
        redis_manager_factory=lambda settings: FakeManager(object()),
    )
    paths = application.openapi()["paths"]

    assert "post" in paths["/userController/register"]
    assert "post" in paths["/userController/login"]
    assert "post" in paths["/userController/logout"]
    assert "post" in paths["/userController/getUsers"]
    assert "put" in paths["/userController/updatePermission"]
    for path in paths.values():
        operation = path.get("post") or path.get("put")
        schema = operation["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert schema.get("additionalProperties") is not True
        validation_schema = operation["responses"]["422"]["content"][
            "application/json"
        ]["schema"]
        assert validation_schema.get("additionalProperties") is not True


def test_register_response_has_no_authorization_header() -> None:
    service = AsyncMock()
    service.register.return_value = RegisterResponseInfo(
        uid="uid",
        email="user@example.com",
        userName="User",
    )
    payload = {
        "header": {},
        "body": {
            "auth": {},
            "info": {
                "email": "user@example.com",
                "userName": "User",
                "password": PASSWORD,
                "confirmPassword": PASSWORD,
            },
        },
    }

    with make_client(service) as client:
        response = client.post("/userController/register", json=payload)

    assert response.status_code == 200
    assert "authorization" not in response.headers
    assert response.json() == {
        "header": {},
        "body": {
            "auth": {
                "status": AuthStatus.SUCCESS,
                "message": UserMessage.REGISTERED,
                "uid": None,
                "authorization": None,
            },
            "info": {
                "email": "user@example.com",
                "uid": "uid",
                "userName": "User",
            },
        },
    }


def test_login_synchronizes_body_and_http_authorization() -> None:
    service = AsyncMock()
    service.login.return_value = LoginResult(
        uid="uid",
        authorization="Bearer token",
        info=LoginResponseInfo(userName="User"),
    )
    payload = {
        "header": {},
        "body": {
            "auth": {},
            "info": {
                "email": "user@example.com",
                "password": PASSWORD,
                "isForceLogin": False,
            },
        },
    }

    with make_client(service) as client:
        response = client.post("/userController/login", json=payload)

    assert response.status_code == 200
    assert response.headers["Authorization"] == "Bearer token"
    assert response.json()["body"] == {
        "auth": {
            "status": AuthStatus.SUCCESS,
            "message": UserMessage.LOGGED_IN,
            "uid": "uid",
            "authorization": "Bearer token",
        },
        "info": {"userName": "User"},
    }


def test_existing_session_maps_to_409_without_token() -> None:
    service = AsyncMock()
    service.login.side_effect = ExistingSessionError()
    payload = {
        "body": {
            "auth": {},
            "info": {
                "email": "user@example.com",
                "password": PASSWORD,
                "isForceLogin": False,
            },
        },
    }

    with make_client(service) as client:
        response = client.post("/userController/login", json=payload)

    assert response.status_code == 409
    assert "authorization" not in response.headers
    assert response.json()["body"]["auth"] == {
        "status": AuthStatus.FAILED,
        "message": UserMessage.ALREADY_LOGGED_IN,
        "uid": None,
        "authorization": None,
    }


def test_get_users_echoes_validated_body_token() -> None:
    service = AsyncMock()
    service.get_users.return_value = ProtectedResult(
        context=AuthorizationContext("uid", "Bearer token", False),
        info=GetUsersResponseInfo(
            [
                UserSummary(
                    email="user@example.com",
                    userName="User",
                    permission="user",
                ),
            ],
        ),
    )
    payload = {
        "body": {
            "auth": {"uid": "uid", "authorization": "Bearer token"},
            "info": {"userName": "Caller"},
        },
    }

    with make_client(service) as client:
        response = client.post("/userController/getUsers", json=payload)

    assert response.status_code == 200
    assert response.headers["Authorization"] == "Bearer token"
    assert response.json()["body"] == {
        "auth": {
            "status": AuthStatus.SUCCESS,
            "message": UserMessage.USERS_RETRIEVED,
            "uid": "uid",
            "authorization": "Bearer token",
        },
        "info": [
            {
                "email": "user@example.com",
                "userName": "User",
                "permission": "user",
            },
        ],
    }


def test_logout_does_not_return_authorization_header() -> None:
    service = AsyncMock()
    service.logout.return_value = LogoutResponseInfo(userName="Stored Name")
    payload = {
        "body": {
            "auth": {"uid": "uid", "authorization": "Bearer token"},
            "info": {"userName": "Untrusted Name"},
        },
    }

    with make_client(service) as client:
        response = client.post("/userController/logout", json=payload)

    assert response.status_code == 200
    assert "authorization" not in response.headers
    assert response.json()["body"] == {
        "auth": {
            "status": AuthStatus.SUCCESS,
            "message": UserMessage.LOGGED_OUT,
            "uid": None,
            "authorization": None,
        },
        "info": {"userName": "Stored Name"},
    }


def test_update_permission_uses_list_contract_and_echoes_token() -> None:
    service = AsyncMock()
    service.update_permissions.return_value = ProtectedResult(
        context=AuthorizationContext("uid", "Bearer token", False),
        info={},
    )
    payload = {
        "body": {
            "auth": {"uid": "uid", "authorization": "Bearer token"},
            "info": [
                {"email": "user@example.com", "Permission": "manager"},
            ],
        },
    }

    with make_client(service) as client:
        response = client.put(
            "/userController/updatePermission",
            json=payload,
        )

    assert response.status_code == 200
    assert response.headers["Authorization"] == "Bearer token"
    assert response.json()["body"] == {
        "auth": {
            "status": AuthStatus.SUCCESS,
            "message": UserMessage.PERMISSIONS_UPDATED,
            "uid": "uid",
            "authorization": "Bearer token",
        },
        "info": {},
    }


def test_schema_error_uses_standard_envelope() -> None:
    with make_client(AsyncMock()) as client:
        response = client.post(
            "/userController/login",
            json={"body": {"auth": {}, "info": {}}},
        )

    assert response.status_code == 422
    body = response.json()["body"]
    assert body["auth"]["status"] == AuthStatus.FAILED
    assert body["auth"]["message"] == UserMessage.VALIDATION_ERROR
    assert body["info"]["errors"]


@pytest.mark.parametrize(
    ("error", "status_code", "auth_status", "message"),
    [
        (
            DuplicateEmailError(),
            400,
            AuthStatus.FAILED,
            UserMessage.DUPLICATE_EMAIL,
        ),
        (
            PasswordMismatchError(),
            400,
            AuthStatus.FAILED,
            UserMessage.PASSWORD_MISMATCH,
        ),
        (
            InvalidCredentialsError(),
            401,
            AuthStatus.FAILED,
            UserMessage.LOGIN_FAILED,
        ),
        (
            AuthorizationRequiredError(),
            401,
            AuthStatus.UNAUTHORIZED,
            UserMessage.AUTHORIZATION_REQUIRED,
        ),
        (
            AuthorizationInvalidError(),
            401,
            AuthStatus.UNAUTHORIZED,
            UserMessage.AUTHORIZATION_INVALID,
        ),
        (
            SessionInvalidError(),
            401,
            AuthStatus.FORCE_LOGOUT,
            UserMessage.SESSION_INVALID,
        ),
        (
            PermissionDeniedError(),
            403,
            AuthStatus.UNAUTHORIZED,
            UserMessage.PERMISSION_DENIED,
        ),
        (
            UserNotFoundError(),
            404,
            AuthStatus.FAILED,
            UserMessage.USER_NOT_FOUND,
        ),
        (
            ExistingSessionError(),
            409,
            AuthStatus.FAILED,
            UserMessage.ALREADY_LOGGED_IN,
        ),
        (
            ServiceUnavailableError(),
            503,
            AuthStatus.FAILED,
            UserMessage.SERVICE_UNAVAILABLE,
        ),
    ],
)
def test_application_error_mapping_uses_standard_envelope(
    error: Exception,
    status_code: int,
    auth_status: str,
    message: str,
) -> None:
    service = AsyncMock()
    service.login.side_effect = error
    payload = {
        "body": {
            "auth": {},
            "info": {
                "email": "user@example.com",
                "password": PASSWORD,
                "isForceLogin": False,
            },
        },
    }

    with make_client(service) as client:
        response = client.post("/userController/login", json=payload)

    assert response.status_code == status_code
    assert "authorization" not in response.headers
    assert response.json() == {
        "header": {},
        "body": {
            "auth": {
                "status": auth_status,
                "message": message,
                "uid": None,
                "authorization": None,
            },
            "info": {},
        },
    }


def test_unexpected_error_maps_to_safe_500_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = AsyncMock()
    service.login.side_effect = RuntimeError("sensitive internal detail")
    payload = {
        "body": {
            "auth": {},
            "info": {
                "email": "user@example.com",
                "password": PASSWORD,
                "isForceLogin": False,
            },
        },
    }

    with make_client(service) as client:
        response = client.post("/userController/login", json=payload)

    assert response.status_code == 500
    assert "sensitive internal detail" not in response.text
    assert "sensitive internal detail" not in caplog.text
    assert response.json()["body"]["auth"]["message"] == (
        UserMessage.INTERNAL_ERROR
    )
