from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from psycopg import AsyncConnection
from psycopg import Error as PsycopgError
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from src.models.po.label import Label
from src.models.po.product import Product


class ProductRepositoryError(Exception):
    pass


class DuplicateProductRecordError(ProductRepositoryError):
    pass


class ProductRepository(object):
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self.__pool = pool

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncConnection[Any]]:
        try:
            async with self.__pool.connection() as connection:
                async with connection.transaction():
                    yield connection
        except ProductRepositoryError:
            raise
        except PsycopgError as error:
            raise ProductRepositoryError from error

    async def list_labels(self) -> list[Label]:
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
            raise ProductRepositoryError from error
        return [self.__to_label(row) for row in rows]

    async def list_products(self) -> list[Product]:
        try:
            async with self.__pool.connection() as connection:
                async with connection.cursor(row_factory=dict_row) as cursor:
                    await cursor.execute(
                        """
                        SELECT id, name, label_ids, cost, price, delete_flag,
                               created_uid, created_at, updated_uid, updated_at
                          FROM tb_products
                         ORDER BY id
                        """
                    )
                    rows = await cursor.fetchall()
        except PsycopgError as error:
            raise ProductRepositoryError from error
        return [self.__to_product(row) for row in rows]

    async def create(
        self,
        product: Product,
        connection: AsyncConnection[Any],
    ) -> Product:
        try:
            await connection.execute(
                """
                INSERT INTO tb_products (
                    id, name, label_ids, cost, price, delete_flag,
                    created_uid, created_at, updated_uid, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    product.id,
                    product.name,
                    product.label_ids,
                    product.cost,
                    product.price,
                    product.delete_flag,
                    product.created_uid,
                    product.created_at,
                    product.updated_uid,
                    product.updated_at,
                ),
            )
        except UniqueViolation as error:
            raise DuplicateProductRecordError from error
        except PsycopgError as error:
            raise ProductRepositoryError from error
        return product

    async def update(
        self,
        product: Product,
        connection: AsyncConnection[Any],
    ) -> bool:
        try:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    UPDATE tb_products
                       SET name = %s,
                           label_ids = %s,
                           cost = %s,
                           price = %s,
                           updated_uid = %s,
                           updated_at = %s
                     WHERE id = %s
                       AND delete_flag = FALSE
                    """,
                    (
                        product.name,
                        product.label_ids,
                        product.cost,
                        product.price,
                        product.updated_uid,
                        product.updated_at,
                        product.id,
                    ),
                )
                return cursor.rowcount == 1
        except PsycopgError as error:
            raise ProductRepositoryError from error

    async def soft_delete(
        self,
        product_id: str,
        updated_uid: str,
        updated_at: datetime,
        connection: AsyncConnection[Any],
    ) -> bool:
        try:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    UPDATE tb_products
                       SET delete_flag = TRUE,
                           updated_uid = %s,
                           updated_at = %s
                     WHERE id = %s
                       AND delete_flag = FALSE
                    """,
                    (updated_uid, updated_at, product_id),
                )
                return cursor.rowcount == 1
        except PsycopgError as error:
            raise ProductRepositoryError from error

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

    @staticmethod
    def __to_product(row: dict[str, Any]) -> Product:
        return Product(
            id=row["id"],
            name=row["name"],
            label_ids=row["label_ids"],
            cost=row["cost"],
            price=row["price"],
            delete_flag=row["delete_flag"],
            created_uid=row["created_uid"],
            created_at=row["created_at"],
            updated_uid=row["updated_uid"],
            updated_at=row["updated_at"],
        )
