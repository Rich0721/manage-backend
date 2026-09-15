from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.objects.api import ApiHeader, make_response
from src.repositories.user_repository import UserRepository
from src.services.errors import RegistrationError
from src.services.user_registration_service import UserRegistrationService

router = APIRouter()


class RegistrationBody(BaseModel):
    email: str
    user_name: str = Field(alias="userName")
    password: str
    confirm_password: str = Field(alias="confirmPassword")

    model_config = {"populate_by_name": True}


class RegistrationRequest(BaseModel):
    header: ApiHeader = ApiHeader()
    body: RegistrationBody


@router.post("/userController/register", status_code=200)
async def register(request: Request, payload: RegistrationRequest) -> Any:
    async with request.app.state.database_pool.acquire() as connection:
        service = UserRegistrationService(UserRepository(connection))
        try:
            user = await service.register(
                email=payload.body.email,
                user_name=payload.body.user_name,
                password=payload.body.password,
                confirm_password=payload.body.confirm_password,
            )
        except RegistrationError:
            body, status_code = make_response(
                401,
                "Failed",
                "User registration failed",
            )
            return JSONResponse(body, status_code=status_code)

    response_body = {
        "uid": user.uid,
        "email": user.email,
        "user_name": user.user_name,
        "permission": user.permission,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }
    body, status_code = make_response(
        200,
        "Success",
        "User registered successfully",
        response_body,
    )
    return JSONResponse(body, status_code=status_code)