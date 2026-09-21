from enum import Enum


JWT_ALGORITHM = "HS256"
BEARER_PREFIX = "Bearer "


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class AuthStatus(object):
    SUCCESS = "Success"
    FAILED = "Failed"
    UNAUTHORIZED = "Unauthorized"
    FORCE_LOGOUT = "ForceLogout"


class UserMessage(object):
    REGISTERED = "註冊成功"
    LOGGED_IN = "User logged in successfully"
    LOGGED_OUT = "登出成功"
    USERS_RETRIEVED = "User data retrieved successfully"
    PERMISSIONS_UPDATED = "User permission updated successfully"
    DUPLICATE_EMAIL = "帳號已存在"
    PASSWORD_MISMATCH = "密碼不一致"
    LOGIN_FAILED = "User login failed"
    ALREADY_LOGGED_IN = (
        "User login failed because already logged in on another device"
    )
    AUTHORIZATION_REQUIRED = "非法使用者"
    AUTHORIZATION_INVALID = "Authorization invalid"
    SESSION_INVALID = "Authorization資訊不一致，操作被拒絕"
    PERMISSION_DENIED = "User Permission Denied"
    USER_NOT_FOUND = "User not found"
    DUPLICATE_TARGET = "Duplicate permission target"
    VALIDATION_ERROR = "Validation error"
    SERVICE_UNAVAILABLE = "Service unavailable"
    INTERNAL_ERROR = "Internal server error"
