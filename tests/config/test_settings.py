import pytest

from src.config.settings import DEFAULT_REDIS_URL
from src.config.settings import Settings


def test_redis_url_uses_local_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)

    settings = Settings()

    assert settings.REDIS_URL == DEFAULT_REDIS_URL


def test_redis_url_uses_environment_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_url = "redis://redis:6379/2"
    monkeypatch.setenv("REDIS_URL", redis_url)

    settings = Settings()

    assert settings.REDIS_URL == redis_url


def test_empty_redis_url_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REDIS_URL", "")

    with pytest.raises(ValueError, match="REDIS_URL must not be empty"):
        Settings()


def test_redis_url_credentials_are_not_exposed_in_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential_value = "redis://user:secret@redis:6379/0"
    monkeypatch.setenv("REDIS_URL", "")

    with pytest.raises(ValueError) as error:
        Settings()

    assert credential_value not in str(error.value)

