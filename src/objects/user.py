from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    uid: str
    email: str
    user_name: str
    permission: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class StoredUser(User):
    password: str