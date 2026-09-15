from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.objects.api import ApiHeader, make_response
from src.repositories.user_repository import UserRepository
from src.services.errors import AuthorizationError
from src.services.user_permission_service import UserPermissionService

router = APIRouter()


class PermissionUpdateBody(BaseModel):
    uid: str
    target_role: str


class PermissionUpdateRequest(BaseModel):
    header: ApiHeader
    body: PermissionUpdateBody


class UserListRequest(BaseModel):
    header: ApiHeader = ApiHeader()


def _user_body(user) -> dict[str, str]:
    return {
        "uid": user.uid,
        "email": user.email,
        "user_name": user.user_name,
        "permission": user.permission,
    }


@router.get("/userController/getUsers")
async def get_users(
    request: Request,
    uid: str = Query(...),
) -> Any:
    async with request.app.state.database_pool.acquire() as connection:
        service = UserPermissionService(UserRepository(connection))
        try:
            users = await service.list_users(uid)
        except AuthorizationError:
            body, status_code = make_response(401, "Failed", "Unauthorized")
            return JSONResponse(body, status_code=status_code)

    body, status_code = make_response(
        200,
        "Success",
        "User data retrieved successfully",
        [_user_body(user) for user in users],
    )
    return JSONResponse(body, status_code=status_code)


@router.put("/userController/updatePermission")
async def update_permission(
    request: Request,
    payload: PermissionUpdateRequest,
) -> Any:
    async with request.app.state.database_pool.acquire() as connection:
        service = UserPermissionService(UserRepository(connection))
        try:
            await service.update_permission(
                operator_uid=payload.header.uid or "",
                target_uid=payload.body.uid,
                target_permission=payload.body.target_role,
            )
        except AuthorizationError:
            body, status_code = make_response(401, "Failed", "Unauthorized")
            return JSONResponse(body, status_code=status_code)

    body, status_code = make_response(
        200,
        "Success",
        "User permission updated successfully",
    )
    return JSONResponse(body, status_code=status_code)