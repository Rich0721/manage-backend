from datetime import datetime
from datetime import timedelta
from datetime import timezone

import jwt
import pytest

from src.constants.user import JWT_ALGORITHM
from src.utils.security import decode_access_token
from src.utils.security import hash_uid
from src.utils.security import issue_access_token
from src.utils.security import verify_encrypted_password


SECRET = "test-secret" * 6


def test_uid_hash_uses_lowercase_email() -> None:
    assert hash_uid("User@Example.COM") == hash_uid("user@example.com")
    assert len(hash_uid("user@example.com")) == 64


def test_encrypted_password_comparison_is_case_sensitive() -> None:
    assert verify_encrypted_password("A" * 64, "A" * 64)
    assert not verify_encrypted_password("A" * 64, "a" * 64)


def test_issue_and_decode_access_token() -> None:
    token = issue_access_token("uid-1", SECRET, 300)
    payload = decode_access_token(token, SECRET)

    assert token.startswith("Bearer ")
    assert payload["sub"] == "uid-1"
    assert payload["exp"] - payload["iat"] == 300


@pytest.mark.parametrize("token", ["token", "Bearer ", "Bearer has space"])
def test_decode_rejects_malformed_bearer_token(token: str) -> None:
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, SECRET)


def test_decode_rejects_expired_token() -> None:
    now = datetime.now(timezone.utc)
    encoded = jwt.encode(
        {
            "sub": "uid",
            "iat": now - timedelta(seconds=10),
            "exp": now - timedelta(seconds=1),
        },
        SECRET,
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(f"Bearer {encoded}", SECRET)


def test_decode_rejects_missing_required_claim() -> None:
    encoded = jwt.encode(
        {"sub": "uid"},
        SECRET,
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(f"Bearer {encoded}", SECRET)


def test_decode_rejects_tampered_token() -> None:
    token = issue_access_token("uid", SECRET, 300)
    encoded = token.removeprefix("Bearer ")
    replacement = "a" if encoded[-1] != "a" else "b"

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(f"Bearer {encoded[:-1]}{replacement}", SECRET)


def test_decode_rejects_wrong_key() -> None:
    token = issue_access_token("uid", SECRET, 300)

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token, "another-secret" * 6)


def test_decode_rejects_wrong_algorithm() -> None:
    now = datetime.now(timezone.utc)
    encoded = jwt.encode(
        {
            "sub": "uid",
            "iat": now,
            "exp": now + timedelta(seconds=300),
        },
        SECRET,
        algorithm="HS384",
    )

    with pytest.raises(jwt.InvalidAlgorithmError):
        decode_access_token(f"Bearer {encoded}", SECRET)
