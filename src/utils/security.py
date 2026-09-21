import hashlib
import hmac
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any

import jwt

from src.constants.user import BEARER_PREFIX
from src.constants.user import JWT_ALGORITHM


def hash_uid(email: str) -> str:
    return hashlib.sha256(email.lower().encode("utf-8")).hexdigest()


def verify_encrypted_password(received: str, stored: str) -> bool:
    return hmac.compare_digest(received, stored)


def issue_access_token(uid: str, secret_key: str, ttl: int) -> str:
    issued_at = datetime.now(timezone.utc)
    payload = {
        "sub": uid,
        "iat": issued_at,
        "exp": issued_at + timedelta(seconds=ttl),
    }
    encoded = jwt.encode(payload, secret_key, algorithm=JWT_ALGORITHM)
    return f"{BEARER_PREFIX}{encoded}"


def decode_access_token(token: str, secret_key: str) -> dict[str, Any]:
    if not token.startswith(BEARER_PREFIX):
        raise jwt.InvalidTokenError("Invalid bearer token format")
    encoded = token[len(BEARER_PREFIX) :]
    if not encoded or any(character.isspace() for character in encoded):
        raise jwt.InvalidTokenError("Invalid bearer token format")
    return jwt.decode(
        encoded,
        secret_key,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "iat", "exp"]},
    )
