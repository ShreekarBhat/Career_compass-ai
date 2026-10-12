from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.core.timeutil import utcnow
from app.db.models import RefreshToken, User
from app.db.session import get_db
from app.profile import engine as profile_engine
from app.schemas import LoginIn, RefreshIn, RegisterIn

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User, db: Session) -> dict:
    refresh_token = create_refresh_token()
    now = utcnow()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=now + timedelta(days=settings.refresh_token_days),
    ))
    db.commit()
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "expires_in": settings.access_token_minutes * 60,
        "refresh_token": refresh_token,
        "refresh_expires_in": settings.refresh_token_days * 24 * 60 * 60,
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
    }


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=email, hashed_password=hash_password(body.password), full_name=body.full_name.strip())
    db.add(user)
    db.commit()
    db.refresh(user)
    profile_engine.get_or_create(db, user.id)
    return _token_response(user, db)


def _authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return user


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 form login (works with the Swagger 'Authorize' button; username = email)."""
    return _token_response(_authenticate(db, form.username, form.password), db)


@router.post("/login-json")
def login_json(body: LoginIn, db: Session = Depends(get_db)):
    """JSON login for the frontend."""
    return _token_response(_authenticate(db, body.email, body.password), db)


@router.post("/refresh")
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    token_hash = hash_refresh_token(body.refresh_token)
    stored = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )
    now = utcnow()
    if not stored:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    if stored.revoked_at is not None:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == stored.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token reuse detected; sign in again")
    if stored.expires_at <= now:
        stored.revoked_at = now
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    stored.revoked_at = now
    user = db.get(User, stored.user_id)
    if not user:
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    return _token_response(user, db)


@router.post("/logout")
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    stored = db.scalar(select(RefreshToken).where(
        RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
    ))
    if stored and stored.revoked_at is None:
        stored.revoked_at = utcnow()
        db.commit()
    return {"revoked": bool(stored)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name,
            "telegram_linked": bool(user.telegram_chat_id)}
