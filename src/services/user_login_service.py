import secrets
import string
from email.message import EmailMessage

from aiosmtplib import SMTP

from config.settings import Settings
from src.repositories.user_repository import UserRepository
from src.services.errors import AuthenticationError

TEMPORARY_CODE_LENGTH = 6
TEMPORARY_CODE_TTL_SECONDS = 180
TEMPORARY_CODE_ALPHABET = string.ascii_letters + string.digits
TEMPORARY_CODE_SUBJECT = "您的臨時登入編號"


class UserLoginService:
    def __init__(
        self,
        repository: UserRepository,
        redis_client,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._redis_client = redis_client
        self._settings = settings

    async def request_temporary_code(
        self,
        email: str,
        password: str,
    ) -> None:
        user = await self._repository.get_by_email(email)
        if user is None or user.password != password:
            raise AuthenticationError("User login failed")

        temporary_code = "".join(
            secrets.choice(TEMPORARY_CODE_ALPHABET)
            for _ in range(TEMPORARY_CODE_LENGTH)
        )
        await self._redis_client.set(
            email,
            temporary_code,
            ex=TEMPORARY_CODE_TTL_SECONDS,
        )
        await self._send_code(email, temporary_code)

    async def verify_temporary_code(
        self,
        email: str,
        temporary_code: str,
    ) -> None:
        stored_code = await self._redis_client.get(email)
        if stored_code is None or not secrets.compare_digest(
            stored_code,
            temporary_code,
        ):
            raise AuthenticationError("Temporary code verification failed")

    async def _send_code(self, email: str, temporary_code: str) -> None:
        message = EmailMessage()
        message["From"] = self._settings.smtp_from_email
        message["To"] = email
        message["Subject"] = TEMPORARY_CODE_SUBJECT
        message.set_content(
            "主旨: 您的臨時登入編號\n\n"
            "親愛的使用者，您好：\n\n"
            f"您本次的臨時登入編號為：{temporary_code}\n"
            "此編號有效期限為3分鐘，請在有效期限內使用。\n\n"
            "若非您本人操作，請忽略此郵件。\n\n"
            "謝謝。"
        )
        smtp = SMTP(
            hostname=self._settings.smtp_host,
            port=self._settings.smtp_port,
            use_tls=self._settings.smtp_use_tls,
        )
        await smtp.connect()
        try:
            if self._settings.smtp_username:
                await smtp.login(
                    self._settings.smtp_username,
                    self._settings.smtp_password or "",
                )
            await smtp.send_message(message)
        finally:
            await smtp.quit()