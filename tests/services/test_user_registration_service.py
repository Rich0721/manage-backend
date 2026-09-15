from datetime import datetime

import pytest

from src.objects.user import User
from src.services.errors import RegistrationError
from src.services.user_registration_service import UserRegistrationService


class FakeUserRepository:
    def __init__(self, existing_user: User | None = None) -> None:
        self.existing_user = existing_user
        self.created_arguments = None

    async def get_by_email(self, email: str) -> User | None:
        return self.existing_user

    async def create(self, **kwargs) -> User:
        self.created_arguments = kwargs
        now = datetime.now()
        return User(
            uid=kwargs["uid"],
            email=kwargs["email"],
            user_name=kwargs["user_name"],
            permission=kwargs.get("permission", "user"),
            created_at=now,
            updated_at=now,
        )


@pytest.mark.asyncio
async def test_register_creates_sha256_uid_and_user_name() -> None:
    repository = FakeUserRepository()
    service = UserRegistrationService(repository)

    user = await service.register(
        "user@example.com",
        "testuser",
        "hashed-password",
        "hashed-password",
    )

    assert user.user_name == "testuser"
    assert user.permission == "user"
    assert len(user.uid) == 64
    assert repository.created_arguments["password"] == "hashed-password"


@pytest.mark.asyncio
async def test_register_rejects_invalid_email() -> None:
    service = UserRegistrationService(FakeUserRepository())

    with pytest.raises(RegistrationError):
        await service.register(
            "invalid",
            "testuser",
            "password",
            "password",
        )


@pytest.mark.asyncio
async def test_register_rejects_password_mismatch() -> None:
    service = UserRegistrationService(FakeUserRepository())

    with pytest.raises(RegistrationError):
        await service.register(
            "user@example.com",
            "testuser",
            "password",
            "different",
        )