import pytest
from fastapi.testclient import TestClient

from src.main import create_app


class TestSettings(object):
    pass


class TrackingManager(object):
    def __init__(self, value: object, *, fail: bool = False) -> None:
        self.value = value
        self.fail = fail
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> object:
        self.entered = True
        if self.fail:
            raise ConnectionError("startup failed")
        return self.value

    async def __aexit__(self, *args: object) -> None:
        self.exited = True


def test_lifespan_initializes_shared_resources_and_closes_them() -> None:
    database = TrackingManager("database")
    redis = TrackingManager("redis")
    application = create_app(
        settings_factory=TestSettings,
        database_manager_factory=lambda settings: database,
        redis_manager_factory=lambda settings: redis,
    )

    with TestClient(application):
        assert application.state.database_pool == "database"
        assert application.state.redis_client == "redis"
        assert database.entered and redis.entered

    assert database.exited and redis.exited


def test_partial_startup_failure_closes_database() -> None:
    database = TrackingManager("database")
    redis = TrackingManager("redis", fail=True)
    application = create_app(
        settings_factory=TestSettings,
        database_manager_factory=lambda settings: database,
        redis_manager_factory=lambda settings: redis,
    )

    with pytest.raises(ConnectionError, match="startup failed"):
        with TestClient(application):
            pass

    assert database.exited
