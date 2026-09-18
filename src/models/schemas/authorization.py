from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class AuthorizationObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    message: str | None = None
    uid: str | None = None
    authorization: str | None = None


class AuthorizationBody(BaseModel):
    auth: AuthorizationObject = Field(
        default_factory=AuthorizationObject,
    )
    info: dict[str, Any] = Field(default_factory=dict)


class AuthorizationEnvelope(BaseModel):
    header: dict[str, Any] = Field(default_factory=dict)
    body: AuthorizationBody = Field(default_factory=AuthorizationBody)
