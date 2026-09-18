import logging
from types import TracebackType

from redis.asyncio import Redis

from src.config.settings import Settings


LOGGER = logging.getLogger(__name__)


class RedisConnectionManager(object):
    def __init__(self, settings: Settings) -> None:
        self.__settings = settings
        self.__client: Redis | None = None

    async def __aenter__(self) -> Redis:
        await self.connect()
        return self.get_client()

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
                    "Failed to close Redis client while handling "
                    "another error",
                )

        return False

    async def connect(self) -> None:
        if self.__client is not None:
            return

        client = Redis.from_url(
            self.__settings.REDIS_URL,
            decode_responses=True,
        )
        try:
            await client.ping()
        except BaseException:
            try:
                await client.aclose()
            except BaseException:
                LOGGER.exception(
                    "Failed to close Redis client after connection failure",
                )
            raise

        self.__client = client

    def get_client(self) -> Redis:
        if self.__client is None:
            raise RuntimeError("Redis client is not connected")

        return self.__client

    async def close(self) -> None:
        if self.__client is None:
            return

        client = self.__client
        self.__client = None
        await client.aclose()
