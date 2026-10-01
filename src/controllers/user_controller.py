from typing import Annotated
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter
from fastapi import Header
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

UidHeader = Annotated[str | None, Header(alias="Uid")]
AuthorizationHeader = Annotated[
    str | None,
    Header(alias="Authorization"),
]


def error_responses(*status_codes: int) -> dict[int, dict[str, Any]]:
    header_schema = {
        "schema": {"type": "string"},
    }
    response_headers = {
        "Status": {
            **header_schema,
            "description": "Application result status.",
        },
        "Message": {
            **header_schema,
            "description": (
                "Application result message. Non-ASCII text is UTF-8 "
                "percent encoded."
            ),
        },
        "Uid": {
            **header_schema,
            "description": "Authenticated user identifier when available.",
        },
        "Authorization": {
            **header_schema,
            "description": "Bearer token when available.",
        },
    }
    responses: dict[int, dict[str, Any]] = {
        200: {"headers": response_headers},
    }
    responses.update(
        {
            status_code: {
                "model": ErrorResponse,
                "headers": response_headers,
            }
            for status_code in status_codes
        },
    )
    return responses


def _authorization_headers(
    *,
    status: str,
    message: str,
    uid: str | None = None,
    authorization: str | None = None,
    encode_message: bool = False,
) -> dict[str, str]:
    header_message = message
    if encode_message and not message.isascii():
        header_message = quote(message, safe=" ")
    headers = {
        "Status": status,
        "Message": header_message,
    }
    if uid is not None:
        headers["Uid"] = uid
    if authorization is not None:
        headers["Authorization"] = authorization
    return headers


def build_http_authorization_headers(
    *,
    status: str,
    message: str,
    uid: str | None = None,
    authorization: str | None = None,
) -> dict[str, str]:
    return _authorization_headers(
        status=status,
        message=message,
        uid=uid,
        authorization=authorization,
        encode_message=True,
    )


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
    headers = _authorization_headers(
        status=status,
        message=message,
        uid=uid,
        authorization=authorization,
    )
    return {
        "header": headers,
        "body": {
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


def synchronize_authorization_headers(
    response: Response,
    *,
    status: str,
    message: str,
    uid: str | None = None,
    authorization: str | None = None,
) -> None:
    response.headers.update(
        build_http_authorization_headers(
            status=status,
            message=message,
            uid=uid,
            authorization=authorization,
        ),
    )


def header_auth(
    uid: str | None,
    authorization: str | None,
) -> AuthorizationObject:
    return AuthorizationObject(uid=uid, authorization=authorization)


@router.post(
    "/register",
    status_code=200,
    response_model=RegisterResponse,
    responses=error_responses(400, 422, 500, 503),
)
async def register(
    payload: RegisterRequest,
    response: Response,
    service: UserServiceDependency,
) -> dict[str, Any]:
    info = await service.register(payload.body.info)
    synchronize_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=UserMessage.REGISTERED,
    )
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
    synchronize_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=UserMessage.LOGGED_IN,
        uid=result.uid,
        authorization=result.authorization,
    )
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
    response: Response,
    service: UserServiceDependency,
    uid: UidHeader = None,
    authorization: AuthorizationHeader = None,
) -> dict[str, Any]:
    info = await service.logout(header_auth(uid, authorization))
    synchronize_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=UserMessage.LOGGED_OUT,
    )
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
    uid: UidHeader = None,
    authorization: AuthorizationHeader = None,
) -> dict[str, Any]:
    result = await service.get_users(header_auth(uid, authorization))
    synchronize_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=UserMessage.USERS_RETRIEVED,
        uid=result.context.uid,
        authorization=result.context.authorization,
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
    uid: UidHeader = None,
    authorization: AuthorizationHeader = None,
) -> dict[str, Any]:
    result = await service.update_permissions(
        header_auth(uid, authorization),
        payload.body.info.root,
    )
    synchronize_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=UserMessage.PERMISSIONS_UPDATED,
        uid=result.context.uid,
        authorization=result.context.authorization,
    )
    return build_envelope(
        status=AuthStatus.SUCCESS,
        message=UserMessage.PERMISSIONS_UPDATED,
        info={},
        uid=result.context.uid,
        authorization=result.context.authorization,
    )
