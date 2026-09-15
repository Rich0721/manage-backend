import hashlib
import re

from src.repositories.user_repository import DuplicateEmailError, UserRepository
from src.services.errors import RegistrationError

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserRegistrationService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def register(
        self,
        email: str,
        user_name: str,
        password: str,
        confirm_password: str,
    ):
        if not EMAIL_PATTERN.fullmatch(email):
            raise RegistrationError("User registration failed")
        if password != confirm_password:
            raise RegistrationError("User registration failed")
        if await self._repository.get_by_email(email) is not None:
            raise RegistrationError("User registration failed")

        uid = hashlib.sha256(email.encode("utf-8")).hexdigest()
        try:
            return await self._repository.create(
                uid=uid,
                email=email,
                user_name=user_name,
                password=password,
            )
        except DuplicateEmailError as error:
            raise RegistrationError("User registration failed") from error