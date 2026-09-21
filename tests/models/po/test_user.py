from datetime import datetime

from src.constants.user import UserRole
from src.models.po.user import UserPO


def test_user_po_preserves_database_row_values() -> None:
    created_at = datetime(2026, 1, 1)
    updated_at = datetime(2026, 1, 2)

    user = UserPO(
        uid="uid",
        email="user@example.com",
        user_name="User",
        password="A" * 64,
        permission=UserRole.MANAGER,
        created_at=created_at,
        updated_at=updated_at,
    )

    assert user.uid == "uid"
    assert user.permission is UserRole.MANAGER
    assert user.created_at is created_at
    assert user.updated_at is updated_at
