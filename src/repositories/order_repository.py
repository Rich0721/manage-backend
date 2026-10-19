from collections.abc import Sequence
from datetime import date
from typing import Any

from psycopg import AsyncConnection
from psycopg import Error as PsycopgError
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from src.models.po.order import OrderItemPO
from src.models.po.order import OrderPO
from src.models.po.order import OrderItemResult
from src.models.po.order import OrderResult


class OrderRepositoryError(Exception):
    pass


class OrderRepository(object):
    _MAX_ORDER_ID = 9_999_999_999

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self.__pool = pool

    async def next_order_id(
        self,
        connection: AsyncConnection[Any],
    ) -> str:
        try:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT nextval('seq_tb_orders_id')")
                row = await cursor.fetchone()
        except PsycopgError as error:
            raise OrderRepositoryError from error
        if row is None:
            raise OrderRepositoryError("Unable to allocate order identifier")
        value = int(row[0])
        if value < 1 or value > self._MAX_ORDER_ID:
            raise OrderRepositoryError("Order identifier sequence exhausted")
        return str(value).zfill(10)

    async def insert_order(
        self,
        order: OrderPO,
        connection: AsyncConnection[Any],
    ) -> None:
        try:
            await connection.execute(
                """
                INSERT INTO tb_orders (
                    id, total_amount, total_discount, created_uid, created_at
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    order.id,
                    order.total_amount,
                    order.total_discount,
                    order.created_uid,
                    order.created_at,
                ),
            )
        except PsycopgError as error:
            raise OrderRepositoryError from error

    async def insert_items(
        self,
        items: Sequence[OrderItemPO],
        connection: AsyncConnection[Any],
    ) -> None:
        try:
            async with connection.cursor() as cursor:
                await cursor.executemany(
                    """
                    INSERT INTO tb_orders_items (
                        order_id, product_id, quantity, price, discount,
                        created_at, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            item.order_id,
                            item.product_id,
                            item.quantity,
                            item.price,
                            item.discount,
                            item.created_at,
                            item.created_by,
                        )
                        for item in items
                    ],
                )
        except PsycopgError as error:
            raise OrderRepositoryError from error

    async def get_orders(
        self,
        *,
        order_id: str | None = None,
        start_date: date | None = None,
        end_date_exclusive: date | None = None,
    ) -> list[OrderResult]:
        try:
            async with self.__pool.connection() as connection:
                async with connection.cursor(row_factory=dict_row) as cursor:
                    if order_id is not None:
                        await cursor.execute(
                            """
                            SELECT o.id, o.total_amount, o.total_discount,
                                   o.created_at, u.user_name AS created_by
                              FROM tb_orders AS o
                              JOIN tb_users AS u ON u.uid = o.created_uid
                             WHERE o.id = %s
                             ORDER BY o.id
                            """,
                            (order_id,),
                        )
                    else:
                        await cursor.execute(
                            """
                            SELECT o.id, o.total_amount, o.total_discount,
                                   o.created_at, u.user_name AS created_by
                              FROM tb_orders AS o
                              JOIN tb_users AS u ON u.uid = o.created_uid
                             WHERE o.created_at >= %s
                               AND o.created_at < %s
                             ORDER BY o.created_at, o.id
                            """,
                            (start_date, end_date_exclusive),
                        )
                    order_rows = await cursor.fetchall()
                    if not order_rows:
                        return []

                    ids = [row["id"] for row in order_rows]
                    await cursor.execute(
                        """
                        SELECT item.order_id, item.product_id,
                               product.name AS product_name,
                               item.quantity, item.price, item.discount
                          FROM tb_orders_items AS item
                          JOIN tb_products AS product
                            ON product.id = item.product_id
                         WHERE item.order_id = ANY(%s)
                         ORDER BY item.order_id, item.id
                        """,
                        (ids,),
                    )
                    item_rows = await cursor.fetchall()
        except PsycopgError as error:
            raise OrderRepositoryError from error

        items_by_order: dict[str, list[OrderItemResult]] = {
            order_id: [] for order_id in ids
        }
        for row in item_rows:
            items_by_order[row["order_id"]].append(
                OrderItemResult(
                    product_id=row["product_id"],
                    product_name=row["product_name"],
                    quantity=row["quantity"],
                    price=row["price"],
                    discount=row["discount"],
                )
            )
        return [
            OrderResult(
                id=row["id"],
                total_amount=row["total_amount"],
                total_discount=row["total_discount"],
                created_at=row["created_at"],
                created_by=row["created_by"],
                items=tuple(items_by_order[row["id"]]),
            )
            for row in order_rows
        ]
