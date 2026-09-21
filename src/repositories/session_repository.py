from redis.asyncio import Redis
from redis.exceptions import RedisError


class SessionRepositoryError(Exception):
    pass


class SessionRepository(object):
    def __init__(self, client: Redis, ttl: int) -> None:
        self.__client = client
        self.__ttl = ttl

    @staticmethod
    def key(uid: str) -> str:
        return f"{uid}:login"

    async def get(self, uid: str) -> str | None:
        try:
            return await self.__client.get(self.key(uid))
        except RedisError as error:
            raise SessionRepositoryError from error

    async def set(self, uid: str, authorization: str) -> None:
        try:
            await self.__client.set(
                self.key(uid),
                authorization,
                ex=self.__ttl,
            )
        except RedisError as error:
            raise SessionRepositoryError from error

    async def force_replace(self, uid: str, authorization: str) -> None:
        try:
            async with self.__client.pipeline(transaction=True) as pipeline:
                pipeline.delete(self.key(uid))
                pipeline.set(
                    self.key(uid),
                    authorization,
                    ex=self.__ttl,
                )
                await pipeline.execute()
        except RedisError as error:
            raise SessionRepositoryError from error

    async def delete(self, uid: str) -> None:
        try:
            await self.__client.delete(self.key(uid))
        except RedisError as error:
            raise SessionRepositoryError from error

    async def refresh(self, uid: str) -> None:
        try:
            refreshed = await self.__client.expire(self.key(uid), self.__ttl)
        except RedisError as error:
            raise SessionRepositoryError from error
        if not refreshed:
            raise SessionRepositoryError("Session disappeared before refresh")
