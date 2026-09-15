from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config.settings import get_settings
from src.objects.api import ApiHeader, make_response
from src.repositories.user_repository import UserRepository
from src.services.errors import AuthenticationError
from src.services.user_login_service import UserLoginService

router = APIRouter()


class LoginBody(BaseModel):
    email: str
    password: str | None = None
    temporary_code: str | None = None


class LoginRequest(BaseModel):
    header: ApiHeader = ApiHeader()
    body: LoginBody


@router.post("/userController/login")
async def login(request: Request, payload: LoginRequest) -> Any:
    body = payload.body
    async with request.app.state.database_pool.acquire() as connection:
        service = UserLoginService(
            UserRepository(connection),
            request.app.state.redis_client,
            get_settings(),
        )
        try:
            if body.password is not None and body.temporary_code is None:
                await service.request_temporary_code(body.email, body.password)
                response_body, status_code = make_response(
                    200,
                    "Success",
                    "User logged in successfully, Temporary code has been "
                    "sent to your email",
                )
            elif body.temporary_code is not None and body.password is None:
                await service.verify_temporary_code(
                    body.email,
                    body.temporary_code,
                )
                response_body, status_code = make_response(
                    200,
                    "Success",
                    "User logged in successfully",
                )
            else:
                raise AuthenticationError("User login failed")
        except (AuthenticationError, OSError, RuntimeError):
            message = (
                "Temporary code verification failed"
                if body.temporary_code is not None
                else "User login failed"
            )
            response_body, status_code = make_response(401, "Failed", message)
    return JSONResponse(response_body, status_code=status_code)