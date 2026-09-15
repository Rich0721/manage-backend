from config.settings import Settings
from main import create_app


def test_settings_build_connection_urls() -> None:
    settings = Settings(
        postgres_db="manage",
        postgres_user="manage",
        postgres_password="secret",
        smtp_host="localhost",
        smtp_from_email="no-reply@example.com",
    )

    assert settings.postgres_dsn == (
        "postgresql://manage:secret@localhost:5432/manage"
    )
    assert settings.redis_url == "redis://localhost:6379/0"


def test_application_registers_without_connecting_during_import() -> None:
    settings = Settings(
        postgres_db="manage",
        postgres_user="manage",
        postgres_password="secret",
        smtp_host="localhost",
        smtp_from_email="no-reply@example.com",
    )

    app = create_app(settings)

    assert app.title == "Manage Backend"
    assert any(route.path == "/docs" for route in app.routes)