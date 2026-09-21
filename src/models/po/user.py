from dataclasses import dataclass
from datetime import datetime

from src.constants.user import UserRole


@dataclass(frozen=True, slots=True)
class UserPO:
    uid: str
    email: str
    user_name: str
    password: str
    permission: UserRole
    created_at: datetime
    updated_at: datetime
