import hmac
from dataclasses import dataclass

import jwt

from src.config.settings import Settings
from src.models.schemas.authorization import AuthorizationObject
from src.repositories.session_repository import SessionRepository
from src.repositories.session_repository import SessionRepositoryError
from src.services.errors import AuthorizationInvalidError
from src.services.errors import AuthorizationRequiredError
from src.services.errors import ServiceUnavailableError
from src.services.errors import SessionInvalidError
from src.utils.security import decode_access_token


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    uid: str
    authorization: str | None
    is_debug_bypass: bool


class AuthorizationService(object):
    def __init__(
        self,
        settings: Settings,
        session_repository: SessionRepository,
    ) -> None:
        self.__settings = settings
        self.__sessions = session_repository

    async def validate_session(
        self,
        authorization: AuthorizationObject,
    ) -> AuthorizationContext:
        uid = authorization.uid
        if uid is None or not uid.strip():
            raise AuthorizationRequiredError

        token = authorization.authorization
        if token is None or not token.strip():
            if self.__settings.DEBUG:
                return AuthorizationContext(uid, None, True)
            raise AuthorizationRequiredError

        try:
            payload = decode_access_token(token, self.__settings.SECRET_KEY)
        except jwt.PyJWTError as error:
            raise AuthorizationInvalidError from error
        if payload.get("sub") != uid:
            raise AuthorizationInvalidError

        try:
            stored_token = await self.__sessions.get(uid)
        except SessionRepositoryError as error:
            raise ServiceUnavailableError from error
        if stored_token is None or not hmac.compare_digest(stored_token, token):
            raise SessionInvalidError

        return AuthorizationContext(uid, token, False)

    async def refresh_session(self, context: AuthorizationContext) -> None:
        if context.is_debug_bypass:
            return
        try:
            await self.__sessions.refresh(context.uid)
        except SessionRepositoryError as error:
            raise ServiceUnavailableError from error
