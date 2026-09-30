from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class LabelPO:
    id: int
    name: str
    created_uid: str
    created_at: datetime
    updated_uid: str
    updated_at: datetime


Label = LabelPO
