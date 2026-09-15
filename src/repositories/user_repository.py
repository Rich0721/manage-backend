from collections.abc import Sequence

import asyncpg

from src.objects.user import StoredUser, User


class DuplicateEmailError(Exception):
    """Raised when an email conflicts with an existing user."""


class UserRepository:
    def __init__(self, connection: asyncpg.Connection) -> None:
        self._connection = connection

    async def get_by_email(self, email: str) -> StoredUser | None:
        row = await self._connection.fetchrow(
            """
            SELECT uid, email, user_name, password, permission,
                   created_at, updated_at
            FROM TB_USERS
            WHERE email = $1
            """,
            email,
        )
        return self._to_stored_user(row) if row else None

    async def get_by_uid(self, uid: str) -> StoredUser | None:
        row = await self._connection.fetchrow(
            """
            SELECT uid, email, user_name, password, permission,
                   created_at, updated_at
            FROM TB_USERS
            WHERE uid = $1
            """,
            uid,
        )
        return self._to_stored_user(row) if row else None

    async def create(
        self,
        uid: str,
        email: str,
        user_name: str,
        password: str,
        permission: str = "user",
    ) -> User:
        try:
            row = await self._connection.fetchrow(
                """
                INSERT INTO TB_USERS (
                    uid, email, user_name, password, permission
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING uid, email, user_name, permission,
                          created_at, updated_at
                """,
                uid,
                email,
                user_name,
                password,
                permission,
            )
        except asyncpg.UniqueViolationError as error:
            raise DuplicateEmailError(email) from error

        return self._to_user(row)

    async def list_all(self) -> list[User]:
        rows = await self._connection.fetch(
            """
            SELECT uid, email, user_name, permission, created_at, updated_at
            FROM TB_USERS
            ORDER BY email
            """
        )
        return [self._to_user(row) for row in rows]

    async def list_by_permission(self, permission: str) -> list[User]:
        rows = await self._connection.fetch(
            """
            SELECT uid, email, user_name, permission, created_at, updated_at
            FROM TB_USERS
            WHERE permission = $1
            ORDER BY email
            """,
            permission,
        )
        return [self._to_user(row) for row in rows]

    async def list_non_admin_excluding_uid(self, uid: str) -> list[User]:
        rows = await self._connection.fetch(
            """
            SELECT uid, email, user_name, permission, created_at, updated_at
            FROM TB_USERS
            WHERE permission <> 'admin' AND uid <> $1
            ORDER BY email
            """,
            uid,
        )
        return [self._to_user(row) for row in rows]

    async def list_by_permission_excluding_uid(
        self,
        permission: str,
        uid: str,
    ) -> list[User]:
        rows = await self._connection.fetch(
            """
            SELECT uid, email, user_name, permission, created_at, updated_at
            FROM TB_USERS
            WHERE permission = $1 AND uid <> $2
            ORDER BY email
            """,
            permission,
            uid,
        )
        return [self._to_user(row) for row in rows]

    async def update_permission(self, uid: str, permission: str) -> User | None:
        row = await self._connection.fetchrow(
            """
            UPDATE TB_USERS
            SET permission = $1
            WHERE uid = $2
            RETURNING uid, email, user_name, permission,
                      created_at, updated_at
            """,
            permission,
            uid,
        )
        return self._to_user(row) if row else None

    @staticmethod
    def _to_user(row: Sequence[object]) -> User:
        return User(
            uid=row[0],
            email=row[1],
            user_name=row[2],
            permission=row[3],
            created_at=row[4],
            updated_at=row[5],
        )

    @staticmethod
    def _to_stored_user(row: Sequence[object]) -> StoredUser:
        return StoredUser(
            uid=row[0],
            email=row[1],
            user_name=row[2],
            password=row[3],
            permission=row[4],
            created_at=row[5],
            updated_at=row[6],
        )