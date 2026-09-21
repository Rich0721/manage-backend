import pytest
from pydantic import ValidationError

from src.constants.user import UserRole
from src.models.schemas.user import LoginRequestInfo
from src.models.schemas.user import PermissionUpdateItem
from src.models.schemas.user import RegisterRequest
from src.models.schemas.user import RegisterRequestInfo
from src.models.schemas.user import UpdatePermissionRequest


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
