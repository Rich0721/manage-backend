from dataclasses import dataclass
from datetime import datetime
from datetime import timezone

from src.config.settings import Settings
from src.constants.user import UserRole
from src.models.po.user import UserPO
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.user import GetUsersResponseInfo
from src.models.schemas.user import LoginRequestInfo
from src.models.schemas.user import LoginResponseInfo
from src.models.schemas.user import LogoutResponseInfo
from src.models.schemas.user import PermissionUpdateItem
from src.models.schemas.user import RegisterRequestInfo
from src.models.schemas.user import RegisterResponseInfo
from src.models.schemas.user import UserSummary
from src.repositories.session_repository import SessionRepository
from src.repositories.session_repository import SessionRepositoryError
from src.repositories.user_repository import DuplicateUserRecordError
from src.repositories.user_repository import UserRepository
from src.repositories.user_repository import UserRepositoryError
from src.services.authorization_service import AuthorizationContext
from src.services.authorization_service import AuthorizationService
from src.services.errors import DuplicateEmailError
from src.services.errors import DuplicatePermissionTargetError
from src.services.errors import ExistingSessionError
from src.services.errors import InvalidCredentialsError
from src.services.errors import PasswordMismatchError
from src.services.errors import PermissionDeniedError
from src.services.errors import ServiceUnavailableError
from src.services.errors import SessionInvalidError
from src.services.errors import UserNotFoundError
from src.utils.security import hash_uid
from src.utils.security import issue_access_token
from src.utils.security import verify_encrypted_password


@dataclass(frozen=True, slots=True)
class LoginResult:
    uid: str
    authorization: str
    info: LoginResponseInfo


@dataclass(frozen=True, slots=True)
class ProtectedResult:
    context: AuthorizationContext
    info: object


class UserService(object):
    def __init__(
        self,
        settings: Settings,
        users: UserRepository,
        sessions: SessionRepository,
        authorization: AuthorizationService,
    ) -> None:
        self.__settings = settings
        self.__users = users
        self.__sessions = sessions
        self.__authorization = authorization

    async def register(
        self,
        info: RegisterRequestInfo,
    ) -> RegisterResponseInfo:
        if not verify_encrypted_password(
            info.password,
            info.confirm_password,
        ):
            raise PasswordMismatchError

        email = str(info.email).lower()
        try:
            existing = await self.__users.get_by_email(email)
        except UserRepositoryError as error:
            raise ServiceUnavailableError from error
        if existing is not None:
            raise DuplicateEmailError

        now = self.__utc_now()
        user = UserPO(
            uid=hash_uid(email),
            email=email,
            user_name=info.user_name,
            password=info.password,
            permission=UserRole.USER,
            created_at=now,
            updated_at=now,
        )
        try:
            await self.__users.create(user)
        except DuplicateUserRecordError as error:
            raise DuplicateEmailError from error
        except UserRepositoryError as error:
            raise ServiceUnavailableError from error

        return RegisterResponseInfo(
            uid=user.uid,
            email=user.email,
            userName=user.user_name,
        )

    async def login(self, info: LoginRequestInfo) -> LoginResult:
        try:
            user = await self.__users.get_by_email(str(info.email).lower())
        except UserRepositoryError as error:
            raise ServiceUnavailableError from error
        if user is None or not verify_encrypted_password(
            info.password,
            user.password,
        ):
            raise InvalidCredentialsError

        try:
            existing_token = await self.__sessions.get(user.uid)
        except SessionRepositoryError as error:
            raise ServiceUnavailableError from error
        if existing_token is not None and not info.is_force_login:
            raise ExistingSessionError

        try:
            authorization = issue_access_token(
                user.uid,
                self.__settings.SECRET_KEY,
                self.__settings.REDIS_TTL,
            )
            if existing_token is None:
                await self.__sessions.set(user.uid, authorization)
            else:
                await self.__sessions.force_replace(
                    user.uid,
                    authorization,
                )
        except SessionRepositoryError as error:
            raise ServiceUnavailableError from error

        return LoginResult(
            uid=user.uid,
            authorization=authorization,
            info=LoginResponseInfo(userName=user.user_name),
        )

    async def logout(
        self,
        auth: AuthorizationObject,
    ) -> LogoutResponseInfo:
        context = await self.__authorization.validate_session(auth)
        user = await self.__get_operator(context.uid)
        try:
            is_deleted = await self.__sessions.delete(context.uid)
        except SessionRepositoryError as error:
            raise ServiceUnavailableError from error
        if not is_deleted and not context.is_debug_bypass:
            raise SessionInvalidError
        return LogoutResponseInfo(userName=user.user_name)

    async def get_users(
        self,
        auth: AuthorizationObject,
    ) -> ProtectedResult:
        context = await self.__authorization.validate_session(auth)
        operator = await self.__get_operator(context.uid)
        if operator.permission is UserRole.ADMIN:
            roles = (UserRole.MANAGER, UserRole.USER)
        elif operator.permission is UserRole.MANAGER:
            roles = (UserRole.USER,)
        else:
            raise PermissionDeniedError

        try:
            users = await self.__users.list_visible_users(roles)
        except UserRepositoryError as error:
            raise ServiceUnavailableError from error
        await self.__authorization.refresh_session(context)
        summaries = [
            UserSummary(
                email=user.email,
                userName=user.user_name,
                permission=user.permission,
            )
            for user in users
        ]
        return ProtectedResult(
            context=context,
            info=GetUsersResponseInfo(summaries),
        )

    async def update_permissions(
        self,
        auth: AuthorizationObject,
        items: list[PermissionUpdateItem],
    ) -> ProtectedResult:
        context = await self.__authorization.validate_session(auth)
        emails = [str(item.email).lower() for item in items]
        if len(set(emails)) != len(emails):
            raise DuplicatePermissionTargetError

        try:
            async with self.__users.transaction() as connection:
                operator = await self.__users.get_by_uid(
                    context.uid,
                    connection,
                )
                if operator is None:
                    raise UserNotFoundError
                targets = await self.__users.get_by_emails(
                    emails,
                    connection,
                    for_update=True,
                )
                targets_by_email = {user.email: user for user in targets}
                if any(email not in targets_by_email for email in emails):
                    raise UserNotFoundError

                updates = {
                    email: item.permission
                    for email, item in zip(emails, items, strict=True)
                }
                for email, target_role in updates.items():
                    target = targets_by_email[email]
                    if not self.__is_transition_allowed(
                        operator.permission,
                        target.permission,
                        target_role,
                    ):
                        raise PermissionDeniedError
                await self.__users.update_permissions(
                    updates,
                    self.__utc_now(),
                    connection,
                )
        except (PermissionDeniedError, UserNotFoundError):
            raise
        except UserRepositoryError as error:
            raise ServiceUnavailableError from error

        await self.__authorization.refresh_session(context)
        return ProtectedResult(context=context, info={})

    async def __get_operator(self, uid: str) -> UserPO:
        try:
            user = await self.__users.get_by_uid(uid)
        except UserRepositoryError as error:
            raise ServiceUnavailableError from error
        if user is None:
            raise UserNotFoundError
        return user

    @staticmethod
    def __is_transition_allowed(
        operator: UserRole,
        current: UserRole,
        target: UserRole,
    ) -> bool:
        if operator is UserRole.ADMIN:
            return (
                current in (UserRole.USER, UserRole.MANAGER)
                and target in (UserRole.USER, UserRole.MANAGER)
            )
        if operator is UserRole.MANAGER:
            return (
                current is UserRole.USER
                and target in (UserRole.USER, UserRole.MANAGER)
            )
        return False

    @staticmethod
    def __utc_now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
