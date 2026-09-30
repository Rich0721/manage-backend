from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ProductPO:
    id: str
    name: str
    label_ids: str
    cost: Decimal
    price: Decimal
    delete_flag: bool
    created_uid: str
    created_at: datetime
    updated_uid: str
    updated_at: datetime


Product = ProductPO
