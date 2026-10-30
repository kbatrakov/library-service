import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram_message(text: str) -> bool:
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.warning("Telegram settings are not configured")
        return False

    url = (f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/"
           f"sendMessage")
    try:
        response = requests.post(
            url,
            json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": text},
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Failed to send Telegram message")
        return False
    return True
