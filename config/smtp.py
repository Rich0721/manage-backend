from aiosmtplib import SMTP

from config.settings import Settings


def create_smtp_client(settings: Settings) -> SMTP:
    return SMTP(
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        use_tls=settings.smtp_use_tls,
    )