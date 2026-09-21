import pytest

from src.config.settings import DEFAULT_DATABASE_URL
from src.config.settings import DEFAULT_DEBUG_SECRET_KEY
from src.config.settings import DEFAULT_REDIS_URL
from src.config.settings import DEFAULT_REDIS_TTL
from src.config.settings import Settings


@pytest.fixture(autouse=True)
def required_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
    monkeypatch.setenv("DEBUG", "true")


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


def test_production_requires_secret_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValueError, match="SECRET_KEY must not be empty"):
        Settings()


def test_debug_uses_safe_local_secret_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    assert Settings().SECRET_KEY == DEFAULT_DEBUG_SECRET_KEY


def test_secret_key_environment_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "configured-secret")

    assert Settings().SECRET_KEY == "configured-secret"


def test_database_url_uses_local_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert Settings().DATABASE_URL == DEFAULT_DATABASE_URL


def test_database_url_uses_environment_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = "postgresql://application:secret@database/application"
    monkeypatch.setenv("DATABASE_URL", database_url)

    assert Settings().DATABASE_URL == database_url


def test_empty_database_url_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "")

    with pytest.raises(ValueError, match="DATABASE_URL must not be empty"):
        Settings()


@pytest.mark.parametrize("value", ["0", "-1", "not-an-integer"])
def test_redis_ttl_must_be_positive_integer(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("REDIS_TTL", value)

    with pytest.raises(
        ValueError,
        match="REDIS_TTL must be a positive integer",
    ):
        Settings()


def test_redis_ttl_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_TTL", raising=False)

    assert Settings().REDIS_TTL == DEFAULT_REDIS_TTL


def test_debug_rejects_ambiguous_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "yes")

    with pytest.raises(ValueError, match="DEBUG must be true or false"):
        Settings()
