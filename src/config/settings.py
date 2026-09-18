import os


DEFAULT_REDIS_URL = "redis://localhost:6379/0"


class Settings(object):
    REDIS_URL: str

    def __init__(self) -> None:
        redis_url = os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
        if not redis_url.strip():
            raise ValueError("REDIS_URL must not be empty")

        self.REDIS_URL = redis_url
