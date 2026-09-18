import pytest
from pydantic import ValidationError

from src.models.schemas.authorization import AuthorizationBody
from src.models.schemas.authorization import AuthorizationEnvelope
from src.models.schemas.authorization import AuthorizationObject


def test_empty_envelope_serializes_expected_structure() -> None:
    envelope = AuthorizationEnvelope()

    assert envelope.model_dump() == {
        "header": {},
        "body": {
            "auth": {
                "status": None,
                "message": None,
                "uid": None,
                "authorization": None,
            },
            "info": {},
        },
    }


@pytest.mark.parametrize(
    "field_name",
    ["status", "message", "uid", "authorization"],
)
@pytest.mark.parametrize("value", ["value", None])
def test_authorization_fields_accept_string_or_none(
    field_name: str,
    value: str | None,
) -> None:
    authorization = AuthorizationObject(**{field_name: value})

    assert getattr(authorization, field_name) == value


@pytest.mark.parametrize(
    "field_name",
    ["status", "message", "uid", "authorization"],
)
def test_authorization_fields_reject_non_string_values(
    field_name: str,
) -> None:
    with pytest.raises(ValidationError):
        AuthorizationObject(**{field_name: 1})


@pytest.mark.parametrize(
    ("model", "value"),
    [
        (AuthorizationObject, {"status": {"invalid": "object"}}),
        (AuthorizationBody, {"auth": "invalid"}),
        (AuthorizationBody, {"info": "invalid"}),
        (AuthorizationEnvelope, {"header": "invalid"}),
        (AuthorizationEnvelope, {"body": "invalid"}),
    ],
)
def test_invalid_scalar_or_object_types_fail_validation(
    model: type[AuthorizationObject]
    | type[AuthorizationBody]
    | type[AuthorizationEnvelope],
    value: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        model(**value)


def test_unknown_authorization_field_fails_validation() -> None:
    with pytest.raises(ValidationError):
        AuthorizationObject(unknown="value")


def test_dynamic_header_and_info_content_is_preserved() -> None:
    envelope = AuthorizationEnvelope(
        header={"request_id": "request-1", "attempt": 2},
        body={
            "auth": {"uid": "user-1"},
            "info": {"roles": ["admin"], "active": True},
        },
    )

    assert envelope.header == {
        "request_id": "request-1",
        "attempt": 2,
    }
    assert envelope.body.info == {
        "roles": ["admin"],
        "active": True,
    }


def test_mutable_defaults_are_not_shared_between_instances() -> None:
    first = AuthorizationEnvelope()
    second = AuthorizationEnvelope()

    first.header["request_id"] = "request-1"
    first.body.info["value"] = "first"
    first.body.auth.status = "success"

    assert second.header == {}
    assert second.body.info == {}
    assert second.body.auth.status is None
    assert first.body is not second.body
    assert first.body.auth is not second.body.auth
