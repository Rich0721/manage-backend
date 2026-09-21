from unittest.mock import AsyncMock

import pytest

from src.models.schemas.authorization import AuthorizationObject
from src.repositories.session_repository import SessionRepositoryError
from src.services.authorization_service import AuthorizationService
from src.services.errors import AuthorizationInvalidError
from src.services.errors import AuthorizationRequiredError
from src.services.errors import ServiceUnavailableError
from src.services.errors import SessionInvalidError
from src.utils.security import issue_access_token


class TestSettings(object):
    DEBUG = False
    SECRET_KEY = "s" * 64
    REDIS_TTL = 300


@pytest.mark.asyncio
async def test_matching_token_and_session_are_accepted() -> None:
    token = issue_access_token("uid", TestSettings.SECRET_KEY, 300)
    sessions = AsyncMock()
    sessions.get.return_value = token
    service = AuthorizationService(TestSettings(), sessions)

    context = await service.validate_session(
        AuthorizationObject(uid="uid", authorization=token),
    )

    assert context.uid == "uid"
    assert not context.is_debug_bypass


@pytest.mark.asyncio
async def test_missing_uid_is_rejected() -> None:
    service = AuthorizationService(TestSettings(), AsyncMock())

    with pytest.raises(AuthorizationRequiredError):
        await service.validate_session(AuthorizationObject())


@pytest.mark.asyncio
async def test_token_subject_must_match_uid() -> None:
    token = issue_access_token("other", TestSettings.SECRET_KEY, 300)
    service = AuthorizationService(TestSettings(), AsyncMock())

    with pytest.raises(AuthorizationInvalidError):
        await service.validate_session(
            AuthorizationObject(uid="uid", authorization=token),
        )


@pytest.mark.asyncio
async def test_session_mismatch_forces_logout() -> None:
    token = issue_access_token("uid", TestSettings.SECRET_KEY, 300)
    sessions = AsyncMock()
    sessions.get.return_value = "Bearer another-token"
    service = AuthorizationService(TestSettings(), sessions)

    with pytest.raises(SessionInvalidError):
        await service.validate_session(
            AuthorizationObject(uid="uid", authorization=token),
        )


@pytest.mark.asyncio
async def test_debug_allows_token_absent_but_does_not_refresh() -> None:
    settings = TestSettings()
    settings.DEBUG = True
    sessions = AsyncMock()
    service = AuthorizationService(settings, sessions)

    context = await service.validate_session(AuthorizationObject(uid="uid"))
    await service.refresh_session(context)

    assert context.is_debug_bypass
    sessions.get.assert_not_awaited()
    sessions.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_redis_error_is_service_unavailable() -> None:
    token = issue_access_token("uid", TestSettings.SECRET_KEY, 300)
    sessions = AsyncMock()
    sessions.get.side_effect = SessionRepositoryError()
    service = AuthorizationService(TestSettings(), sessions)

    with pytest.raises(ServiceUnavailableError):
        await service.validate_session(
            AuthorizationObject(uid="uid", authorization=token),
        )
