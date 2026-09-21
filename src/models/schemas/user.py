from typing import Annotated
from typing import Any
from typing import Generic
from typing import TypeVar

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import EmailStr
from pydantic import Field
from pydantic import RootModel
from pydantic import StringConstraints
from pydantic import field_validator

from src.constants.user import UserRole
from src.models.schemas.authorization import AuthorizationObject


InfoT = TypeVar("InfoT")
EncryptedPassword = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9A-Fa-f]{64}$"),
]


class UserBody(BaseModel, Generic[InfoT]):
    model_config = ConfigDict(extra="forbid")

    auth: AuthorizationObject = Field(default_factory=AuthorizationObject)
    info: InfoT


class UserEnvelope(BaseModel, Generic[InfoT]):
    model_config = ConfigDict(extra="forbid")

    header: dict[str, Any] = Field(default_factory=dict)
    body: UserBody[InfoT]


class _EmailInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    email: EmailStr

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, email: EmailStr) -> str:
        return str(email).lower()


class RegisterRequestInfo(_EmailInfo):
    user_name: str = Field(alias="userName", min_length=1, max_length=256)
    password: EncryptedPassword
    confirm_password: EncryptedPassword = Field(alias="confirmPassword")


class LoginRequestInfo(_EmailInfo):
    password: EncryptedPassword
    is_force_login: bool = Field(alias="isForceLogin")


class LogoutRequestInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    user_name: str = Field(alias="userName", min_length=1, max_length=256)


class GetUsersRequestInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    user_name: str = Field(alias="userName", min_length=1, max_length=256)


class EmptyInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PermissionUpdateItem(_EmailInfo):
    permission: UserRole = Field(alias="Permission")


class UpdatePermissionRequestInfo(RootModel[list[PermissionUpdateItem]]):
    pass


class RegisterResponseInfo(_EmailInfo):
    uid: str
    user_name: str = Field(alias="userName")


class LoginResponseInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    user_name: str = Field(alias="userName")


class LogoutResponseInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    user_name: str = Field(alias="userName")


class UserSummary(_EmailInfo):
    user_name: str = Field(alias="userName")
    permission: UserRole


class GetUsersResponseInfo(RootModel[list[UserSummary]]):
    pass


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: list[str | int]
    message: str
    error_type: str


class ErrorResponseInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    errors: list[ErrorDetail] = Field(default_factory=list)


RegisterRequest = UserEnvelope[RegisterRequestInfo]
LoginRequest = UserEnvelope[LoginRequestInfo]
LogoutRequest = UserEnvelope[LogoutRequestInfo]
GetUsersRequest = UserEnvelope[GetUsersRequestInfo]
UpdatePermissionRequest = UserEnvelope[UpdatePermissionRequestInfo]
RegisterResponse = UserEnvelope[RegisterResponseInfo]
LoginResponse = UserEnvelope[LoginResponseInfo | dict[str, Any]]
LogoutResponse = UserEnvelope[LogoutResponseInfo]
GetUsersResponse = UserEnvelope[GetUsersResponseInfo]
UpdatePermissionResponse = UserEnvelope[EmptyInfo]
ErrorResponse = UserEnvelope[ErrorResponseInfo]
