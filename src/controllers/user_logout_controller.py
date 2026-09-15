from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.objects.api import ApiHeader, make_response
from src.repositories.user_repository import UserRepository

router = APIRouter()


class LogoutBody(BaseModel):
    email: str


class LogoutRequest(BaseModel):
    header: ApiHeader = ApiHeader()
    body: LogoutBody


@router.post("/userController/logout")
async def logout(request: Request, payload: LogoutRequest) -> Any:
    uid = payload.header.uid
    async with request.app.state.database_pool.acquire() as connection:
        user = await UserRepository(connection).get_by_uid(uid or "")
    if user is None:
        body, status_code = make_response(401, "Failed", "Unauthorized")
    else:
        body, status_code = make_response(
            200,
            "Success",
            "User logged out successfully",
        )
    return JSONResponse(body, status_code=status_code)