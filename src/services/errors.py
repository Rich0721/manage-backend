from src.constants.user import AuthStatus
from src.constants.user import UserMessage


class ApplicationError(Exception):
    status_code = 500
    auth_status = AuthStatus.FAILED
    message = UserMessage.INTERNAL_ERROR

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.public_message = message or self.message


class DuplicateEmailError(ApplicationError):
    status_code = 400
    message = UserMessage.DUPLICATE_EMAIL


class PasswordMismatchError(ApplicationError):
    status_code = 400
    message = UserMessage.PASSWORD_MISMATCH


class DuplicatePermissionTargetError(ApplicationError):
    status_code = 400
    message = UserMessage.DUPLICATE_TARGET


class InvalidCredentialsError(ApplicationError):
    status_code = 401
    message = UserMessage.LOGIN_FAILED


class AuthorizationRequiredError(ApplicationError):
    status_code = 401
    auth_status = AuthStatus.UNAUTHORIZED
    message = UserMessage.AUTHORIZATION_REQUIRED


class AuthorizationInvalidError(ApplicationError):
    status_code = 401
    auth_status = AuthStatus.UNAUTHORIZED
    message = UserMessage.AUTHORIZATION_INVALID


class SessionInvalidError(ApplicationError):
    status_code = 401
    auth_status = AuthStatus.FORCE_LOGOUT
    message = UserMessage.SESSION_INVALID


class ExistingSessionError(ApplicationError):
    status_code = 409
    message = UserMessage.ALREADY_LOGGED_IN


class PermissionDeniedError(ApplicationError):
    status_code = 403
    auth_status = AuthStatus.UNAUTHORIZED
    message = UserMessage.PERMISSION_DENIED


class UserNotFoundError(ApplicationError):
    status_code = 404
    message = UserMessage.USER_NOT_FOUND


class ServiceUnavailableError(ApplicationError):
    status_code = 503
    message = UserMessage.SERVICE_UNAVAILABLE
