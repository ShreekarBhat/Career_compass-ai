from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.models import Application, User
from app.db.session import get_db
from app.schemas import ApplicationIn, ApplicationUpdateIn
from app.tools import tracker

router = APIRouter(prefix="/applications", tags=["application tracker"])


def _own(db: Session, user: User, app_id: int) -> Application:
    a = db.scalar(select(Application).where(Application.id == app_id, Application.user_id == user.id))
    if not a:
        raise HTTPException(404, "Application not found")
    return a


@router.get("")
def list_apps(status: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Application).where(Application.user_id == user.id)
    if status:
        stmt = stmt.where(Application.status == status)
    return [tracker.to_dict(a) for a in db.scalars(stmt.order_by(Application.updated_at.desc())).all()]


@router.post("", status_code=201)
def create(body: ApplicationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return tracker.to_dict(tracker.create_application(db, user.id, body.model_dump()))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/analytics")
def analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Career analytics: applications, role mix, average match, interview conversion."""
    return tracker.analytics(db, user.id)


@router.get("/{app_id}")
def get_app(app_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return tracker.to_dict(_own(db, user, app_id))


@router.patch("/{app_id}")
def update(app_id: int, body: ApplicationUpdateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = _own(db, user, app_id)
    try:
        return tracker.to_dict(tracker.update_application(db, a, body.model_dump(exclude_unset=True)))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.delete("/{app_id}", status_code=204)
def delete(app_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_own(db, user, app_id))
    db.commit()
