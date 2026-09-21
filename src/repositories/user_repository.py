from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from psycopg import AsyncConnection
from psycopg import Error as PsycopgError
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from src.constants.user import UserRole
from src.models.po.user import UserPO


class UserRepositoryError(Exception):
    pass


class DuplicateUserRecordError(UserRepositoryError):
    pass


class UserRepository(object):
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self.__pool = pool

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncConnection[Any]]:
        try:
            async with self.__pool.connection() as connection:
                async with connection.transaction():
                    yield connection
        except UserRepositoryError:
            raise
        except PsycopgError as error:
            raise UserRepositoryError from error

    async def get_by_uid(
        self,
        uid: str,
        connection: AsyncConnection[Any] | None = None,
    ) -> UserPO | None:
        return await self.__fetch_one(
            """
            SELECT uid, email, user_name, password, permission,
                   created_at, updated_at
              FROM tb_users
             WHERE uid = %s
            """,
            (uid,),
            connection,
        )

    async def get_by_email(
        self,
        email: str,
        connection: AsyncConnection[Any] | None = None,
    ) -> UserPO | None:
        return await self.__fetch_one(
            """
            SELECT uid, email, user_name, password, permission,
                   created_at, updated_at
              FROM tb_users
             WHERE email = %s
            """,
            (email,),
            connection,
        )

    async def create(self, user: UserPO) -> UserPO:
        try:
            async with self.__pool.connection() as connection:
                await connection.execute(
                    """
                    INSERT INTO tb_users (
                        uid, email, user_name, password, permission,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user.uid,
                        user.email,
                        user.user_name,
                        user.password,
                        user.permission.value,
                        user.created_at,
                        user.updated_at,
                    ),
                )
        except UniqueViolation as error:
            raise DuplicateUserRecordError from error
        except PsycopgError as error:
            raise UserRepositoryError from error
        return user

    async def list_visible_users(
        self,
        roles: tuple[UserRole, ...],
    ) -> list[UserPO]:
        try:
            async with self.__pool.connection() as connection:
                async with connection.cursor(row_factory=dict_row) as cursor:
                    await cursor.execute(
                        """
                        SELECT uid, email, user_name, password, permission,
                               created_at, updated_at
                          FROM tb_users
                         WHERE permission = ANY(%s)
                         ORDER BY email
                        """,
                        ([role.value for role in roles],),
                    )
                    rows = await cursor.fetchall()
        except PsycopgError as error:
            raise UserRepositoryError from error
        return [self.__to_user(row) for row in rows]

    async def get_by_emails(
        self,
        emails: list[str],
        connection: AsyncConnection[Any],
        *,
        for_update: bool = False,
    ) -> list[UserPO]:
        suffix = " FOR UPDATE" if for_update else ""
        try:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(
                    """
                    SELECT uid, email, user_name, password, permission,
                           created_at, updated_at
                      FROM tb_users
                     WHERE email = ANY(%s)
                    """
                    + suffix,
                    (emails,),
                )
                rows = await cursor.fetchall()
        except PsycopgError as error:
            raise UserRepositoryError from error
        return [self.__to_user(row) for row in rows]

    async def update_permissions(
        self,
        updates: dict[str, UserRole],
        updated_at: datetime,
        connection: AsyncConnection[Any],
    ) -> None:
        try:
            async with connection.cursor() as cursor:
                await cursor.executemany(
                    """
                    UPDATE tb_users
                       SET permission = %s,
                           updated_at = %s
                     WHERE email = %s
                    """,
                    [
                        (permission.value, updated_at, email)
                        for email, permission in updates.items()
                    ],
                )
        except PsycopgError as error:
            raise UserRepositoryError from error

    async def __fetch_one(
        self,
        query: str,
        parameters: tuple[str],
        connection: AsyncConnection[Any] | None,
    ) -> UserPO | None:
        if connection is not None:
            return await self.__fetch_one_on_connection(
                connection,
                query,
                parameters,
            )
        try:
            async with self.__pool.connection() as pooled_connection:
                return await self.__fetch_one_on_connection(
                    pooled_connection,
                    query,
                    parameters,
                )
        except PsycopgError as error:
            raise UserRepositoryError from error

    async def __fetch_one_on_connection(
        self,
        connection: AsyncConnection[Any],
        query: str,
        parameters: tuple[str],
    ) -> UserPO | None:
        try:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, parameters)
                row = await cursor.fetchone()
        except PsycopgError as error:
            raise UserRepositoryError from error
        return self.__to_user(row) if row is not None else None

    @staticmethod
    def __to_user(row: dict[str, Any]) -> UserPO:
        return UserPO(
            uid=row["uid"],
            email=row["email"],
            user_name=row["user_name"],
            password=row["password"],
            permission=UserRole(row["permission"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
