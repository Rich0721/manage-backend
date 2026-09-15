class UserManagerError(Exception):
    """Base error for documented user-management failures."""


class RegistrationError(UserManagerError):
    """Raised when registration input or persistence is invalid."""


class AuthenticationError(UserManagerError):
    """Raised when login credentials or temporary code are invalid."""


class AuthorizationError(UserManagerError):
    """Raised when an operator cannot perform an action."""