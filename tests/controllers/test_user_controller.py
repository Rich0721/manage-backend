from unittest.mock import AsyncMock
from urllib.parse import unquote

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


def assert_authorization_headers(
    response: object,
    *,
    status: str,
    message: str,
    uid: str | None = None,
    authorization: str | None = None,
) -> None:
    assert response.headers["Status"] == status
    assert unquote(response.headers["Message"]) == message
    assert response.headers.get("Uid") == uid
    assert response.headers.get("Authorization") == authorization


def test_all_exact_routes_are_registered() -> None:
    application = create_app(
        settings_factory=TestSettings,
        database_manager_factory=lambda settings: FakeManager(object()),
        redis_manager_factory=lambda settings: FakeManager(object()),
    )
    paths = application.openapi()["paths"]
    schemas = application.openapi()["components"]["schemas"]

    def resolve_schema(schema: dict[str, object]) -> dict[str, object]:
        reference = schema.get("$ref")
        if isinstance(reference, str):
            schema_name = reference.rsplit("/", maxsplit=1)[-1]
            return schemas[schema_name]
        return schema

    assert "post" in paths["/userController/register"]
    assert "post" in paths["/userController/login"]
    assert "post" in paths["/userController/logout"]
    assert "post" in paths["/userController/getUsers"]
    assert "put" in paths["/userController/updatePermission"]
    for path in paths.values():
        operation = (
            path.get("post")
            or path.get("put")
            or path.get("get")
            or path.get("delete")
        )
        schema = operation["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        response_schema = resolve_schema(schema)
        assert "headers" in response_schema["properties"]
        assert "header" not in response_schema["properties"]
        assert schema.get("additionalProperties") is not True
        assert set(operation["responses"]["200"]["headers"]) == {
            "Status",
            "Message",
            "Uid",
            "Authorization",
        }
        validation_schema = operation["responses"]["422"]["content"][
            "application/json"
        ]["schema"]
        validation_schema = resolve_schema(validation_schema)
        assert "headers" in validation_schema["properties"]
        assert "header" not in validation_schema["properties"]
        assert validation_schema.get("additionalProperties") is not True
        assert set(operation["responses"]["422"]["headers"]) == {
            "Status",
            "Message",
            "Uid",
            "Authorization",
        }

        request_body = operation.get("requestBody")
        if request_body is not None:
            request_schema = request_body["content"][
                "application/json"
            ]["schema"]
            request_schema = resolve_schema(request_schema)
            assert "headers" in request_schema["properties"]
            assert "header" not in request_schema["properties"]


def test_register_response_uses_status_headers_without_token() -> None:
    service = AsyncMock()
    service.register.return_value = RegisterResponseInfo(
        uid="uid",
        email="user@example.com",
        userName="User",
    )
    payload = {
        "headers": {},
        "body": {
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
    assert_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=UserMessage.REGISTERED,
    )
    assert response.json() == {
        "headers": {
            "Status": AuthStatus.SUCCESS,
            "Message": UserMessage.REGISTERED,
        },
        "body": {
            "info": {
                "email": "user@example.com",
                "uid": "uid",
                "userName": "User",
            },
        },
    }


def test_login_returns_authorization_in_http_headers() -> None:
    service = AsyncMock()
    service.login.return_value = LoginResult(
        uid="uid",
        authorization="Bearer token",
        info=LoginResponseInfo(userName="User"),
    )
    payload = {
        "headers": {},
        "body": {
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
    assert_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=UserMessage.LOGGED_IN,
        uid="uid",
        authorization="Bearer token",
    )
    assert response.json()["headers"] == {
        "Status": AuthStatus.SUCCESS,
        "Message": UserMessage.LOGGED_IN,
        "Uid": "uid",
        "Authorization": "Bearer token",
    }
    assert response.json()["body"] == {
        "info": {"userName": "User"},
    }


def test_existing_session_maps_to_409_without_token() -> None:
    service = AsyncMock()
    service.login.side_effect = ExistingSessionError()
    payload = {
        "body": {
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
    assert_authorization_headers(
        response,
        status=AuthStatus.FAILED,
        message=UserMessage.ALREADY_LOGGED_IN,
    )
    assert response.json()["headers"] == {
        "Status": AuthStatus.FAILED,
        "Message": UserMessage.ALREADY_LOGGED_IN,
    }


def test_get_users_uses_http_headers_when_json_headers_conflict() -> None:
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
        "headers": {
            "Uid": "json-user",
            "Authorization": "Bearer json-token",
        },
        "body": {
            "info": {"userName": "Caller"},
        },
    }

    with make_client(service) as client:
        response = client.post(
            "/userController/getUsers",
            headers={
                "Uid": "uid",
                "Authorization": "Bearer request",
            },
            json=payload,
        )

    assert response.status_code == 200
    auth = service.get_users.await_args.args[0]
    assert auth.uid == "uid"
    assert auth.authorization == "Bearer request"
    assert_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=UserMessage.USERS_RETRIEVED,
        uid="uid",
        authorization="Bearer token",
    )
    assert response.json()["body"] == {
        "info": [
            {
                "email": "user@example.com",
                "userName": "User",
                "permission": "user",
            },
        ],
    }


def test_get_users_does_not_use_json_header_as_authorization() -> None:
    service = AsyncMock()
    service.get_users.side_effect = AuthorizationRequiredError()
    payload = {
        "headers": {
            "Uid": "json-user",
            "Authorization": "Bearer json-token",
        },
        "body": {
            "info": {"userName": "Caller"},
        },
    }

    with make_client(service) as client:
        response = client.post("/userController/getUsers", json=payload)

    assert response.status_code == 401
    auth = service.get_users.await_args.args[0]
    assert auth.uid is None
    assert auth.authorization is None


def test_get_users_rejects_legacy_json_header() -> None:
    service = AsyncMock()
    payload = {
        "header": {
            "Uid": "json-user",
            "Authorization": "Bearer json-token",
        },
        "body": {
            "info": {"userName": "Caller"},
        },
    }

    with make_client(service) as client:
        response = client.post("/userController/getUsers", json=payload)

    assert response.status_code == 422
    service.get_users.assert_not_awaited()


def test_logout_does_not_return_authorization_header() -> None:
    service = AsyncMock()
    service.logout.return_value = LogoutResponseInfo(userName="Stored Name")
    payload = {
        "body": {
            "info": {"userName": "Untrusted Name"},
        },
    }

    with make_client(service) as client:
        response = client.post(
            "/userController/logout",
            headers={
                "Uid": "uid",
                "Authorization": "Bearer token",
            },
            json=payload,
        )

    assert response.status_code == 200
    auth = service.logout.await_args.args[0]
    assert auth.uid == "uid"
    assert auth.authorization == "Bearer token"
    assert_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=UserMessage.LOGGED_OUT,
    )
    assert response.json()["body"] == {
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
            "info": [
                {"email": "user@example.com", "permission": "manager"},
            ],
        },
    }

    with make_client(service) as client:
        response = client.put(
            "/userController/updatePermission",
            headers={
                "Uid": "uid",
                "Authorization": "Bearer request",
            },
            json=payload,
        )

    assert response.status_code == 200
    auth = service.update_permissions.await_args.args[0]
    assert auth.uid == "uid"
    assert auth.authorization == "Bearer request"
    assert_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=UserMessage.PERMISSIONS_UPDATED,
        uid="uid",
        authorization="Bearer token",
    )
    assert response.json()["body"] == {
        "info": {},
    }


def test_update_permission_rejects_capitalized_field() -> None:
    service = AsyncMock()
    payload = {
        "body": {
            "info": [{"email": "user@example.com", "Permission": "manager"}],
        },
    }

    with make_client(service) as client:
        response = client.put("/userController/updatePermission", json=payload)

    assert response.status_code == 422
    assert_authorization_headers(
        response,
        status=AuthStatus.FAILED,
        message=UserMessage.VALIDATION_ERROR,
    )
    assert response.json()["body"] == {
        "info": {
            "errors": [
                {
                    "location": ["body", "body", "info", 0, "permission"],
                    "message": "Field required",
                    "error_type": "missing",
                },
                {
                    "location": ["body", "body", "info", 0, "Permission"],
                    "message": "Extra inputs are not permitted",
                    "error_type": "extra_forbidden",
                },
            ],
        },
    }
    service.update_permissions.assert_not_awaited()


def test_schema_error_uses_standard_envelope() -> None:
    with make_client(AsyncMock()) as client:
        response = client.post(
            "/userController/login",
            json={"body": {"info": {}}},
        )

    assert response.status_code == 422
    body = response.json()["body"]
    assert body["info"]["errors"]
    assert_authorization_headers(
        response,
        status=AuthStatus.FAILED,
        message=UserMessage.VALIDATION_ERROR,
    )


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
    assert_authorization_headers(
        response,
        status=auth_status,
        message=message,
    )
    assert response.json() == {
        "headers": {
            "Status": auth_status,
            "Message": message,
        },
        "body": {
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
    assert_authorization_headers(
        response,
        status=AuthStatus.FAILED,
        message=UserMessage.INTERNAL_ERROR,
    )
