import logging
from types import TracebackType

from psycopg_pool import AsyncConnectionPool

from src.config.settings import Settings


LOGGER = logging.getLogger(__name__)


class DatabaseConnectionManager(object):
    def __init__(self, settings: Settings) -> None:
        self.__settings = settings
        self.__pool: AsyncConnectionPool | None = None

    async def __aenter__(self) -> AsyncConnectionPool:
        await self.connect()
        return self.get_pool()

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exception is None:
            await self.close()
        else:
            try:
                await self.close()
            except BaseException:
                LOGGER.exception(
                    "Failed to close database pool while handling "
                    "another error",
                )
        return False

    async def connect(self) -> None:
        if self.__pool is not None:
            return
        pool = AsyncConnectionPool(
            conninfo=self.__settings.DATABASE_URL,
            open=False,
        )
        try:
            await pool.open()
            await pool.wait()
        except BaseException:
            try:
                await pool.close()
            except BaseException:
                LOGGER.exception(
                    "Failed to close database pool after connection failure",
                )
            raise
        self.__pool = pool

    def get_pool(self) -> AsyncConnectionPool:
        if self.__pool is None:
            raise RuntimeError("Database pool is not connected")
        return self.__pool

    async def close(self) -> None:
        if self.__pool is None:
            return
        pool = self.__pool
        self.__pool = None
        await pool.close()
