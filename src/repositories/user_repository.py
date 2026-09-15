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
            SELECT uid, email, password, permission, created_at, updated_at
            FROM TB_USERS
            WHERE email = $1
            """,
            email,
        )
        return self._to_stored_user(row) if row else None

    async def get_by_uid(self, uid: str) -> StoredUser | None:
        row = await self._connection.fetchrow(
            """
            SELECT uid, email, password, permission, created_at, updated_at
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
        password: str,
        permission: str = "user",
    ) -> User:
        try:
            row = await self._connection.fetchrow(
                """
                INSERT INTO TB_USERS (uid, email, password, permission)
                VALUES ($1, $2, $3, $4)
                RETURNING uid, email, permission, created_at, updated_at
                """,
                uid,
                email,
                password,
                permission,
            )
        except asyncpg.UniqueViolationError as error:
            raise DuplicateEmailError(email) from error

        return self._to_user(row)

    async def list_all(self) -> list[User]:
        rows = await self._connection.fetch(
            """
            SELECT uid, email, permission, created_at, updated_at
            FROM TB_USERS
            ORDER BY email
            """
        )
        return [self._to_user(row) for row in rows]

    async def list_by_permission(self, permission: str) -> list[User]:
        rows = await self._connection.fetch(
            """
            SELECT uid, email, permission, created_at, updated_at
            FROM TB_USERS
            WHERE permission = $1
            ORDER BY email
            """,
            permission,
        )
        return [self._to_user(row) for row in rows]

    async def update_permission(self, uid: str, permission: str) -> User | None:
        row = await self._connection.fetchrow(
            """
            UPDATE TB_USERS
            SET permission = $1
            WHERE uid = $2
            RETURNING uid, email, permission, created_at, updated_at
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
            permission=row[2],
            created_at=row[3],
            updated_at=row[4],
        )

    @staticmethod
    def _to_stored_user(row: Sequence[object]) -> StoredUser:
        return StoredUser(
            uid=row[0],
            email=row[1],
            password=row[2],
            permission=row[3],
            created_at=row[4],
            updated_at=row[5],
        )