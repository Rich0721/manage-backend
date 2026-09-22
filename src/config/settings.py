import os


DEFAULT_DATABASE_URL = (
    "postgresql://progresql:progresql@127.0.0.1:5432/progresql"
)
DEFAULT_REDIS_URL = "redis://default:progresql@127.0.0.1:6379/0"
DEFAULT_REDIS_TTL = 300
DEFAULT_DEBUG_SECRET_KEY = (
    "284568295f471f6ab68edc47fd831b709c0baafd697784d69b964d7cfe3f8f19"
)


def _parse_bool(name: str, default: str) -> bool:
    raw_value = os.getenv(name, default).strip().lower()
    if raw_value == "true":
        return True
    if raw_value == "false":
        return False
    raise ValueError(f"{name} must be true or false")


class Settings(object):
    REDIS_URL: str
    REDIS_TTL: int
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG: bool

    def __init__(self) -> None:
        redis_url = os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
        if not redis_url.strip():
            raise ValueError("REDIS_URL must not be empty")

        database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        if not database_url.strip():
            raise ValueError("DATABASE_URL must not be empty")

        debug = _parse_bool("DEBUG", "true")
        secret_key = os.getenv(
            "SECRET_KEY",
            DEFAULT_DEBUG_SECRET_KEY if debug else "",
        )
        if not secret_key.strip():
            raise ValueError("SECRET_KEY must not be empty")

        raw_redis_ttl = os.getenv("REDIS_TTL", str(DEFAULT_REDIS_TTL))
        try:
            redis_ttl = int(raw_redis_ttl)
        except ValueError as error:
            raise ValueError("REDIS_TTL must be a positive integer") from error
        if redis_ttl <= 0:
            raise ValueError("REDIS_TTL must be a positive integer")

        self.REDIS_URL = redis_url
        self.REDIS_TTL = redis_ttl
        self.DATABASE_URL = database_url
        self.SECRET_KEY = secret_key
        self.DEBUG = debug
