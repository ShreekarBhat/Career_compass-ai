"""One-click Telegram linking (no manual chat id).

Flow: the logged-in user asks for a link -> we create a short-lived one-time code and return
https://t.me/<bot>?start=<code>. The user taps it and presses START in Telegram; the bot receives
"/start <code>", and we store that chat's id on the user. The status endpoint polls Telegram's
getUpdates, so no public URL / webhook is needed (works on localhost).
"""
import logging
import secrets
import threading
from datetime import datetime, timedelta

import httpx
from sqlalchemy import DateTime, ForeignKey, Integer, String, delete, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.config import settings
from app.core.timeutil import utcnow
from app.db.models import User
from app.db.session import Base
from app.tools.telegram import send_telegram

logger = logging.getLogger(__name__)

CODE_TTL_MINUTES = 15
_lock = threading.Lock()
_state: dict = {"offset": None, "username": None}


class TelegramLinkCode(Base):
    __tablename__ = "telegram_link_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


def _call(method: str, **params):
    r = httpx.post(f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}", json=params, timeout=10.0)
    r.raise_for_status()
    return r.json().get("result")


def bot_username() -> str | None:
    if not settings.telegram_bot_token:
        return None
    if not _state["username"]:
        try:
            _state["username"] = _call("getMe")["username"]
        except Exception as exc:
            logger.warning("Telegram getMe failed: %s", exc)
            return None
    return _state["username"]


def create_link(db: Session, user: User) -> dict | None:
    username = bot_username()
    if not username:
        return None
    db.execute(delete(TelegramLinkCode).where(TelegramLinkCode.user_id == user.id))  # one active code per user
    code = secrets.token_urlsafe(9)
    db.add(TelegramLinkCode(user_id=user.id, code=code, expires_at=utcnow() + timedelta(minutes=CODE_TTL_MINUTES)))
    db.commit()
    return {"link": f"https://t.me/{username}?start={code}", "expires_in_minutes": CODE_TTL_MINUTES}


def process_updates(db: Session) -> int:
    """Read pending bot messages and complete any valid '/start <code>' links. Returns how many users got linked."""
    if not settings.telegram_bot_token:
        return 0
    linked = 0
    with _lock:
        params: dict = {"timeout": 0, "allowed_updates": ["message"]}
        if _state["offset"] is not None:
            params["offset"] = _state["offset"]
        try:
            updates = _call("getUpdates", **params) or []
        except Exception as exc:
            logger.warning("Telegram getUpdates failed: %s", exc)
            return 0
        for u in updates:
            _state["offset"] = u["update_id"] + 1
            msg = u.get("message") or {}
            chat = msg.get("chat") or {}
            text = (msg.get("text") or "").strip()
            if chat.get("type") != "private" or not text.startswith("/start"):
                continue
            chat_id = str(chat["id"])
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                send_telegram(chat_id, "Hi! Open the 'Connect Telegram' link inside Career Compass to link this chat.")
                continue
            row = db.scalar(select(TelegramLinkCode).where(
                TelegramLinkCode.code == parts[1].strip(), TelegramLinkCode.expires_at > utcnow()))
            user = db.get(User, row.user_id) if row else None
            if not user:
                send_telegram(chat_id, "That link has expired or was already used. Generate a new one in Career Compass.")
                continue
            user.telegram_chat_id = chat_id
            db.delete(row)
            db.commit()
            linked += 1
            send_telegram(chat_id, "✅ Telegram connected. You'll now get job matches, skill alerts and reminders here.")
    return linked
