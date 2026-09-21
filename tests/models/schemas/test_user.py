import pytest
from pydantic import ValidationError

from src.constants.user import UserRole
from src.models.schemas.user import LoginRequestInfo
from src.models.schemas.user import LoginResponse
from src.models.schemas.user import LoginResponseInfo
from src.models.schemas.user import LogoutRequest
from src.models.schemas.user import PermissionUpdateItem
from src.models.schemas.user import RegisterRequest
from src.models.schemas.user import RegisterRequestInfo
from src.models.schemas.user import RegisterResponse
from src.models.schemas.user import RegisterResponseInfo
from src.models.schemas.user import UpdatePermissionRequest
from src.models.schemas.user import UserEnvelope
from src.models.schemas.user import ValidationErrorItem


PASSWORD = "A" * 64


def test_register_schema_normalizes_email_and_serializes_aliases() -> None:
    request = RegisterRequest(
        header={},
        body={
            "auth": {},
            "info": {
                "email": "User@Example.COM",
                "userName": "測試者",
                "password": PASSWORD,
                "confirmPassword": PASSWORD,
            },
        },
    )

    assert str(request.body.info.email) == "user@example.com"
    assert request.model_dump(by_alias=True)["body"]["info"] == {
        "email": "user@example.com",
        "userName": "測試者",
        "password": PASSWORD,
        "confirmPassword": PASSWORD,
    }


@pytest.mark.parametrize("password", ["a" * 63, "g" * 64, "a" * 65])
def test_password_must_be_exact_64_character_hex(password: str) -> None:
    with pytest.raises(ValidationError):
        LoginRequestInfo(
            email="user@example.com",
            password=password,
            isForceLogin=False,
        )


def test_unknown_business_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RegisterRequestInfo(
            email="user@example.com",
            userName="name",
            password=PASSWORD,
            confirmPassword=PASSWORD,
            unexpected=True,
        )


def test_permission_contract_uses_capitalized_alias() -> None:
    item = PermissionUpdateItem(
        email="USER@EXAMPLE.COM",
        Permission="manager",
    )

    assert item.permission is UserRole.MANAGER
    assert item.model_dump(by_alias=True)["Permission"] == UserRole.MANAGER


def test_permission_request_info_is_json_list() -> None:
    request = UpdatePermissionRequest(
        body={
            "auth": {"uid": "uid", "authorization": "Bearer token"},
            "info": [
                {"email": "user@example.com", "Permission": "user"},
            ],
        },
    )

    assert len(request.body.info.root) == 1
    assert isinstance(request.model_dump(by_alias=True)["body"]["info"], list)


@pytest.mark.parametrize("value", ["false", "true", 0, 1, None])
def test_force_login_rejects_non_boolean_json_types(value: object) -> None:
    with pytest.raises(ValidationError):
        LoginRequestInfo(
            email="user@example.com",
            password=PASSWORD,
            isForceLogin=value,
        )


@pytest.mark.parametrize("email", ["invalid", "@example.com", "user@"])
def test_email_rejects_invalid_format(email: str) -> None:
    with pytest.raises(ValidationError):
        RegisterRequestInfo(
            email=email,
            userName="User",
            password=PASSWORD,
            confirmPassword=PASSWORD,
        )


def test_permission_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        PermissionUpdateItem(
            email="user@example.com",
            Permission="owner",
        )


def test_permission_list_rejects_invalid_element() -> None:
    with pytest.raises(ValidationError):
        UpdatePermissionRequest(
            body={
                "auth": {},
                "info": ["invalid"],
            },
        )


def test_user_name_boundary_is_enforced() -> None:
    valid = RegisterRequestInfo(
        email="user@example.com",
        userName="u" * 256,
        password=PASSWORD,
        confirmPassword=PASSWORD,
    )
    assert len(valid.user_name) == 256

    with pytest.raises(ValidationError):
        RegisterRequestInfo(
            email="user@example.com",
            userName="u" * 257,
            password=PASSWORD,
            confirmPassword=PASSWORD,
        )


def test_required_request_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        LogoutRequest(body={"auth": {}, "info": {}})


def test_response_models_serialize_public_aliases() -> None:
    register = RegisterResponse(
        body={
            "auth": {"status": "Success"},
            "info": RegisterResponseInfo(
                uid="uid",
                email="user@example.com",
                userName="User",
            ),
        },
    )
    login = LoginResponse(
        body={
            "auth": {"status": "Success"},
            "info": LoginResponseInfo(userName="User"),
        },
    )

    register_info = register.model_dump(by_alias=True)["body"]["info"]
    assert register_info["userName"] == "User"
    assert login.model_dump(by_alias=True)["body"]["info"] == {
        "userName": "User",
    }


def test_envelope_mutable_header_is_not_shared() -> None:
    first = UserEnvelope[LoginResponseInfo](
        body={"auth": {}, "info": {"userName": "First"}},
    )
    second = UserEnvelope[LoginResponseInfo](
        body={"auth": {}, "info": {"userName": "Second"}},
    )

    first.header["request"] = "first"

    assert second.header == {}


def test_validation_error_item_matches_plan_target() -> None:
    item = ValidationErrorItem(
        location=["body", "email"],
        message="invalid",
        error_type="value_error",
    )

    assert item.location == ["body", "email"]
