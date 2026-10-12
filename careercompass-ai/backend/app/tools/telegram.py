import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_telegram(chat_id: str | None, text: str) -> bool:
    """Send via the Telegram Bot API. Returns False (never raises) if not configured or on error."""
    if not (settings.telegram_bot_token and chat_id):
        return False
    try:
        r = httpx.post(f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                       json={"chat_id": chat_id, "text": text[:4000]}, timeout=8.0)
        return r.status_code == 200
    except Exception as exc:
        logger.warning("Telegram send failed: %s", exc)
        return False


def send_fcm(fcm_token: str | None, title: str, body: str) -> bool:
    """Optional extension point: wire firebase-admin here to enable native Android push."""
    return False
