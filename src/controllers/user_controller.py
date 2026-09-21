from typing import Any

from fastapi import APIRouter
from fastapi import Response
from pydantic import BaseModel

from src.constants.user import AuthStatus
from src.constants.user import UserMessage
from src.controllers.dependencies import UserServiceDependency
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.user import ErrorResponse
from src.models.schemas.user import GetUsersRequest
from src.models.schemas.user import GetUsersResponse
from src.models.schemas.user import LoginRequest
from src.models.schemas.user import LoginResponse
from src.models.schemas.user import LogoutRequest
from src.models.schemas.user import LogoutResponse
from src.models.schemas.user import RegisterRequest
from src.models.schemas.user import RegisterResponse
from src.models.schemas.user import UpdatePermissionRequest
from src.models.schemas.user import UpdatePermissionResponse


router = APIRouter(prefix="/userController", tags=["User Manager"])


def error_responses(*status_codes: int) -> dict[int, dict[str, Any]]:
    return {
        status_code: {"model": ErrorResponse}
        for status_code in status_codes
    }


def build_envelope(
    *,
    status: str,
    message: str,
    info: BaseModel | list[Any] | dict[str, Any],
    uid: str | None = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    if isinstance(info, BaseModel):
        serialized_info = info.model_dump(by_alias=True, mode="json")
    else:
        serialized_info = info
    auth = AuthorizationObject(
        status=status,
        message=message,
        uid=uid,
        authorization=authorization,
    )
    return {
        "header": {},
        "body": {
            "auth": auth.model_dump(mode="json"),
            "info": serialized_info,
        },
    }


def build_error_envelope(
    *,
    status: str,
    message: str,
    info: dict[str, Any],
) -> dict[str, Any]:
    envelope = ErrorResponse.model_validate(
        build_envelope(status=status, message=message, info=info),
    )
    return envelope.model_dump(by_alias=True, mode="json")


def synchronize_authorization_header(
    response: Response,
    authorization: str | None,
) -> None:
    if authorization is not None:
        response.headers["Authorization"] = authorization


@router.post(
    "/register",
    status_code=200,
    response_model=RegisterResponse,
    responses=error_responses(400, 422, 500, 503),
)
async def register(
    payload: RegisterRequest,
    service: UserServiceDependency,
) -> dict[str, Any]:
    info = await service.register(payload.body.info)
    return build_envelope(
        status=AuthStatus.SUCCESS,
        message=UserMessage.REGISTERED,
        info=info,
    )


@router.post(
    "/login",
    status_code=200,
    response_model=LoginResponse,
    responses=error_responses(401, 409, 422, 500, 503),
)
async def login(
    payload: LoginRequest,
    response: Response,
    service: UserServiceDependency,
) -> dict[str, Any]:
    result = await service.login(payload.body.info)
    synchronize_authorization_header(response, result.authorization)
    return build_envelope(
        status=AuthStatus.SUCCESS,
        message=UserMessage.LOGGED_IN,
        info=result.info,
        uid=result.uid,
        authorization=result.authorization,
    )


@router.post(
    "/logout",
    status_code=200,
    response_model=LogoutResponse,
    responses=error_responses(401, 404, 422, 500, 503),
)
async def logout(
    payload: LogoutRequest,
    service: UserServiceDependency,
) -> dict[str, Any]:
    info = await service.logout(payload.body.auth)
    return build_envelope(
        status=AuthStatus.SUCCESS,
        message=UserMessage.LOGGED_OUT,
        info=info,
    )


@router.post(
    "/getUsers",
    status_code=200,
    response_model=GetUsersResponse,
    responses=error_responses(401, 403, 404, 422, 500, 503),
)
async def get_users(
    payload: GetUsersRequest,
    response: Response,
    service: UserServiceDependency,
) -> dict[str, Any]:
    result = await service.get_users(payload.body.auth)
    synchronize_authorization_header(
        response,
        result.context.authorization,
    )
    return build_envelope(
        status=AuthStatus.SUCCESS,
        message=UserMessage.USERS_RETRIEVED,
        info=result.info,
        uid=result.context.uid,
        authorization=result.context.authorization,
    )


@router.put(
    "/updatePermission",
    status_code=200,
    response_model=UpdatePermissionResponse,
    responses=error_responses(400, 401, 403, 404, 422, 500, 503),
)
async def update_permissions(
    payload: UpdatePermissionRequest,
    response: Response,
    service: UserServiceDependency,
) -> dict[str, Any]:
    result = await service.update_permissions(
        payload.body.auth,
        payload.body.info.root,
    )
    synchronize_authorization_header(
        response,
        result.context.authorization,
    )
    return build_envelope(
        status=AuthStatus.SUCCESS,
        message=UserMessage.PERMISSIONS_UPDATED,
        info={},
        uid=result.context.uid,
        authorization=result.context.authorization,
    )
