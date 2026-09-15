from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiHeader(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    content_type: str = Field(
        default="application/json",
        alias="content-type",
    )
    accept: str = "application/json"
    user_agent: str | None = Field(default=None, alias="user-agent")
    status_code: int | None = Field(default=None, alias="status-code")
    status: str | None = None
    message: str | None = None
    uid: str | None = None
    permission: str | None = None


class ApiEnvelope(BaseModel):
    header: ApiHeader = ApiHeader()
    body: Any = None


def make_response(
    status_code: int,
    status: str,
    message: str,
    body: Any = None,
    *,
    uid: str | None = None,
    permission: str | None = None,
) -> tuple[dict[str, Any], int]:
    header = ApiHeader(
        status_code=status_code,
        status=status,
        message=message,
        uid=uid,
        permission=permission,
    )
    return {
        "header": header.model_dump(by_alias=True, exclude_none=True),
        "body": {} if body is None else body,
    }, status_code