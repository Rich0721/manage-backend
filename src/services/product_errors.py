from src.constants.product import ProductMessage
from src.constants.user import AuthStatus
from src.services.errors import ApplicationError


class ProductLabelNotFoundError(ApplicationError):
    status_code = 400
    auth_status = AuthStatus.SUCCESS
    message = ProductMessage.LABEL_NOT_FOUND


class ProductNotFoundError(ApplicationError):
    status_code = 404
    auth_status = AuthStatus.SUCCESS
    message = ProductMessage.NOT_FOUND


class ProductConflictError(ApplicationError):
    status_code = 409
    auth_status = AuthStatus.SUCCESS
    message = ProductMessage.CONFLICT


class ProductPermissionError(ApplicationError):
    status_code = 401
    auth_status = AuthStatus.UNAUTHORIZED
    message = ProductMessage.UNAUTHORIZED


class ProductCacheUnavailableError(ApplicationError):
    status_code = 503
    auth_status = AuthStatus.SUCCESS
    message = ProductMessage.CACHE_UNAVAILABLE
