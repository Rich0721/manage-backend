import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from contextlib import asynccontextmanager
from typing import Any
from typing import Callable

from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.config.database import DatabaseConnectionManager
from src.config.redis import RedisConnectionManager
from src.config.settings import Settings
from src.constants.user import AuthStatus
from src.constants.user import UserMessage
from src.controllers.user_controller import build_envelope
from src.controllers.user_controller import router
from src.services.errors import ApplicationError


LOGGER = logging.getLogger(__name__)


def create_app(
    settings_factory: Callable[[], Settings] = Settings,
    database_manager_factory: Callable[
        [Settings], DatabaseConnectionManager
    ] = DatabaseConnectionManager,
    redis_manager_factory: Callable[
        [Settings], RedisConnectionManager
    ] = RedisConnectionManager,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
        settings = settings_factory()
        database_manager = database_manager_factory(settings)
        redis_manager = redis_manager_factory(settings)
        async with AsyncExitStack() as stack:
            database_pool = await stack.enter_async_context(database_manager)
            redis_client = await stack.enter_async_context(redis_manager)
            app_instance.state.settings = settings
            app_instance.state.database_pool = database_pool
            app_instance.state.redis_client = redis_client
            yield

    application = FastAPI(lifespan=lifespan)
    application.include_router(router)

    @application.exception_handler(ApplicationError)
    async def handle_application_error(
        request: Request,
        error: ApplicationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content=build_envelope(
                status=error.auth_status,
                message=error.public_message,
                info={},
            ),
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        details = [
            {
                "location": list(item["loc"]),
                "message": item["msg"],
                "error_type": item["type"],
            }
            for item in error.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=build_envelope(
                status=AuthStatus.FAILED,
                message=UserMessage.VALIDATION_ERROR,
                info={"errors": details},
            ),
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        LOGGER.exception("Unhandled application error", exc_info=error)
        return JSONResponse(
            status_code=500,
            content=build_envelope(
                status=AuthStatus.FAILED,
                message=UserMessage.INTERNAL_ERROR,
                info={},
            ),
        )

    return application


app = create_app()
