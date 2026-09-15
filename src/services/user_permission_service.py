from src.objects.user import User
from src.repositories.user_repository import UserRepository
from src.services.errors import AuthorizationError

ALLOWED_TARGET_PERMISSIONS = {"user", "manager"}


class UserPermissionService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def list_users(self, operator_uid: str) -> list[User]:
        operator = await self._repository.get_by_uid(operator_uid)
        if operator is None:
            raise AuthorizationError("Unauthorized")
        if operator.permission == "admin":
            return await self._repository.list_non_admin_excluding_uid(
                operator_uid
            )
        if operator.permission == "manager":
            return await self._repository.list_by_permission_excluding_uid(
                "user",
                operator_uid,
            )
        raise AuthorizationError("Unauthorized")

    async def update_permission(
        self,
        operator_uid: str,
        target_uid: str,
        target_permission: str,
    ) -> User:
        if target_permission not in ALLOWED_TARGET_PERMISSIONS:
            raise AuthorizationError("Unauthorized")

        operator = await self._repository.get_by_uid(operator_uid)
        target = await self._repository.get_by_uid(target_uid)
        if operator is None or target is None:
            raise AuthorizationError("Unauthorized")
        if target.permission == "admin":
            raise AuthorizationError("Unauthorized")
        if operator.permission == "admin":
            pass
        elif operator.permission == "manager":
            if target.permission != "user":
                raise AuthorizationError("Unauthorized")
        else:
            raise AuthorizationError("Unauthorized")

        updated_user = await self._repository.update_permission(
            target_uid,
            target_permission,
        )
        if updated_user is None:
            raise AuthorizationError("Unauthorized")
        return updated_user