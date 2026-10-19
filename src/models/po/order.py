from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class OrderPO:
    id: str
    total_amount: Decimal
    total_discount: Decimal
    created_uid: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class OrderItemPO:
    order_id: str
    product_id: str
    quantity: int
    price: Decimal
    discount: Decimal
    created_at: datetime
    created_by: str


@dataclass(frozen=True, slots=True)
class OrderItemResult:
    product_id: str
    product_name: str
    quantity: int
    price: Decimal
    discount: Decimal


@dataclass(frozen=True, slots=True)
class OrderResult:
    id: str
    total_amount: Decimal
    total_discount: Decimal
    created_at: datetime
    created_by: str
    items: tuple[OrderItemResult, ...]
