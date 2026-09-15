from dataclasses import dataclass

import pytest

from config.settings import Settings
from src.objects.user import StoredUser
from src.services.errors import AuthenticationError
from src.services.user_login_service import (
    TEMPORARY_CODE_TTL_SECONDS,
    UserLoginService,
)


@dataclass
class FakeRedis:
    values: dict[str, str]
    expiry: dict[str, int]

    async def set(self, key: str, value: str, *, ex: int) -> None:
        self.values[key] = value
        self.expiry[key] = ex

    async def get(self, key: str) -> str | None:
        return self.values.get(key)


class FakeRepository:
    def __init__(self, user: StoredUser | None) -> None:
        self.user = user

    async def get_by_email(self, email: str) -> StoredUser | None:
        return self.user


class FakeSmtp:
    sent_messages = []

    async def connect(self) -> None:
        pass

    async def send_message(self, message) -> None:
        self.sent_messages.append(message)

    async def quit(self) -> None:
        pass


def make_user() -> StoredUser:
    from datetime import datetime

    now = datetime.now()
    return StoredUser(
        uid="uid",
        email="user@example.com",
        user_name="user",
        password="hashed-password",
        permission="user",
        created_at=now,
        updated_at=now,
    )


def make_settings() -> Settings:
    return Settings(
        postgres_db="manage",
        postgres_user="manage",
        postgres_password="secret",
        smtp_host="localhost",
        smtp_from_email="no-reply@example.com",
    )


@pytest.mark.asyncio
async def test_login_stores_six_character_code_with_ttl(monkeypatch) -> None:
    fake_smtp = FakeSmtp()
    monkeypatch.setattr(
        "src.services.user_login_service.SMTP",
        lambda **kwargs: fake_smtp,
    )
    redis = FakeRedis({}, {})
    service = UserLoginService(
        FakeRepository(make_user()),
        redis,
        make_settings(),
    )

    await service.request_temporary_code(
        "user@example.com",
        "hashed-password",
    )

    assert len(redis.values["user@example.com"]) == 6
    assert redis.expiry["user@example.com"] == TEMPORARY_CODE_TTL_SECONDS
    assert len(fake_smtp.sent_messages) == 1


@pytest.mark.asyncio
async def test_login_rejects_wrong_password() -> None:
    service = UserLoginService(
        FakeRepository(make_user()),
        FakeRedis({}, {}),
        make_settings(),
    )

    with pytest.raises(AuthenticationError):
        await service.request_temporary_code(
            "user@example.com",
            "wrong-password",
        )


@pytest.mark.asyncio
async def test_temporary_code_verification_uses_latest_value() -> None:
    redis = FakeRedis({"user@example.com": "new123"}, {})
    service = UserLoginService(
        FakeRepository(make_user()),
        redis,
        make_settings(),
    )

    await service.verify_temporary_code("user@example.com", "new123")

    with pytest.raises(AuthenticationError):
        await service.verify_temporary_code("user@example.com", "old123")