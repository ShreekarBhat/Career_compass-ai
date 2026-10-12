from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.notification_agent import NotificationAgent
from app.core.deps import get_current_user
from app.db.models import Notification, User
from app.db.session import get_db
from app.schemas import TelegramIn
from app.tools.telegram_link import create_link, process_updates

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _d(n: Notification) -> dict:
    return {"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "payload": n.payload, "channel": n.channel,
            "delivered": n.delivered, "is_read": n.is_read, "created_at": n.created_at.isoformat()}


@router.get("")
def list_notifications(unread_only: bool = False, limit: int = 50, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    return [_d(n) for n in db.scalars(stmt.order_by(Notification.id.desc()).limit(min(limit, 200))).all()]


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id))
    if not n:
        raise HTTPException(404, "Notification not found")
    n.is_read = True
    db.commit()
    return _d(n)


@router.post("/telegram/link")
def telegram_link_url(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return a one-click link that connects the user's Telegram chat after they press START."""
    result = create_link(db, user)
    if not result:
        raise HTTPException(503, "Telegram bot is not configured (set TELEGRAM_BOT_TOKEN)")
    return result


@router.get("/telegram/status")
def telegram_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Poll for the user's Telegram START message and complete linking when received."""
    if not user.telegram_chat_id:
        process_updates(db)
        db.refresh(user)
    return {"linked": bool(user.telegram_chat_id)}


@router.put("/telegram")
def link_telegram(body: TelegramIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Link Telegram: message your bot once, get your chat id (e.g. from @userinfobot), then send it here."""
    user.telegram_chat_id = body.chat_id.strip()
    db.commit()
    return {"linked": True}


@router.delete("/telegram")
def unlink_telegram(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.telegram_chat_id = None
    db.commit()
    return {"linked": False}


@router.post("/test")
def send_test(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = NotificationAgent(db).notify(user.id, "info", "Test notification", "CareerCompass notifications are working.")
    return _d(n)
