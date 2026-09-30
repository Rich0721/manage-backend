from typing import Any

from psycopg import Error as PsycopgError
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from src.models.po.label import Label


class LabelRepositoryError(Exception):
    pass


class LabelRepository(object):
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self.__pool = pool

    async def list_all(self) -> list[Label]:
        try:
            async with self.__pool.connection() as connection:
                async with connection.cursor(row_factory=dict_row) as cursor:
                    await cursor.execute(
                        """
                        SELECT id, name, created_uid, created_at,
                               updated_uid, updated_at
                          FROM tb_labels
                         ORDER BY id
                        """
                    )
                    rows = await cursor.fetchall()
        except PsycopgError as error:
            raise LabelRepositoryError from error
        return [self.__to_label(row) for row in rows]

    @staticmethod
    def __to_label(row: dict[str, Any]) -> Label:
        return Label(
            id=row["id"],
            name=row["name"],
            created_uid=row["created_uid"],
            created_at=row["created_at"],
            updated_uid=row["updated_uid"],
            updated_at=row["updated_at"],
        )
