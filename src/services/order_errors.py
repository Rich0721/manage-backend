from src.constants.order import OrderMessage
from src.constants.user import AuthStatus
from src.services.errors import ApplicationError


class OrderBadRequestError(ApplicationError):
    status_code = 400
    auth_status = AuthStatus.FAILED
    message = OrderMessage.BAD_REQUEST


class SoldProductNotFoundError(ApplicationError):
    status_code = 400
    auth_status = AuthStatus.FAILED
    message = OrderMessage.PRODUCT_NOT_FOUND


class OrderNotFoundError(ApplicationError):
    status_code = 404
    auth_status = AuthStatus.FAILED
    message = OrderMessage.ORDER_NOT_FOUND


class OrderServiceUnavailableError(ApplicationError):
    status_code = 503
    auth_status = AuthStatus.FAILED
    message = OrderMessage.SERVICE_UNAVAILABLE


