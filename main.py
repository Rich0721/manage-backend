from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from config.database import close_database_pool, create_database_pool
from config.redis import close_redis_client, create_redis_client
from config.settings import Settings, get_settings
from src.routers import router


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app_settings = settings or get_settings()
        app.state.database_pool = await create_database_pool(app_settings)
        app.state.redis_client = create_redis_client(app_settings)
        try:
            yield
        finally:
            await close_redis_client(app.state.redis_client)
            await close_database_pool(app.state.database_pool)

    app = FastAPI(title="Manage Backend", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()