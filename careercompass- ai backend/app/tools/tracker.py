"""Application tracker CRUD + career analytics."""
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import to_naive_utc, utcnow
from app.data.taxonomy import role_family
from app.db.models import Application

STATUSES = ["saved", "applied", "assessment", "interview", "offer", "rejected", "withdrawn"]
_REACHED_INTERVIEW = {"interview", "offer"}


def _push_history(app: Application, status: str) -> None:
    hist = list(app.stage_history or [])
    if not hist or hist[-1].get("status") != status:
        hist.append({"status": status, "at": utcnow().isoformat(timespec="seconds")})
    app.stage_history = hist


def create_application(db: Session, user_id: int, data: dict) -> Application:
    status = data.get("status", "saved")
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    app = Application(user_id=user_id, job_id=data.get("job_id"), company=data["company"], role=data["role"],
                      url=data.get("url"), match_score=data.get("match_score"), status=status,
                      applied_on=data.get("applied_on"), deadline=to_naive_utc(data.get("deadline")),
                      interview_at=to_naive_utc(data.get("interview_at")), notes=data.get("notes"), stage_history=[])
    _push_history(app, status)
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def update_application(db: Session, app: Application, data: dict) -> Application:
    for field in ("company", "role", "url", "notes", "match_score", "applied_on"):
        if data.get(field) is not None:
            setattr(app, field, data[field])
    for field in ("deadline", "interview_at"):
        if field in data and data[field] is not None:
            setattr(app, field, to_naive_utc(data[field]))
    if data.get("status") is not None:
        if data["status"] not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        app.status = data["status"]
        _push_history(app, data["status"])
    db.commit()
    db.refresh(app)
    return app


def to_dict(a: Application) -> dict:
    return {"id": a.id, "job_id": a.job_id, "company": a.company, "role": a.role, "url": a.url,
            "match_score": a.match_score, "status": a.status,
            "applied_on": a.applied_on.isoformat() if a.applied_on else None,
            "deadline": a.deadline.isoformat() if a.deadline else None,
            "interview_at": a.interview_at.isoformat() if a.interview_at else None,
            "notes": a.notes, "stage_history": a.stage_history or [],
            "created_at": a.created_at.isoformat() if a.created_at else None}


def analytics(db: Session, user_id: int) -> dict:
    apps = list(db.scalars(select(Application).where(Application.user_id == user_id)).all())
    applied = [a for a in apps if a.status != "saved"]
    by_status = Counter(a.status for a in apps)
    families = Counter(role_family(a.role) for a in applied)
    scores = [a.match_score for a in applied if a.match_score is not None]
    reached = [a for a in applied if any(h.get("status") in _REACHED_INTERVIEW for h in (a.stage_history or []))]
    avg = round(sum(scores) / len(scores), 1) if scores else None
    conv = round(100 * len(reached) / len(applied), 1) if applied else None
    insights = []
    if applied:
        insights.append(f"You applied to {len(applied)} position{'s' if len(applied) != 1 else ''}.")
        fam, cnt = families.most_common(1)[0]
        insights.append(f"{cnt} {'was' if cnt == 1 else 'were'} {fam}-related.")
    if avg is not None:
        insights.append(f"Your average match score was {avg}%.")
    if conv is not None:
        insights.append(f"Your interview conversion rate is {conv}%.")
    if applied and conv is not None and conv < 10 and len(applied) >= 5:
        insights.append("Low conversion: tailor your resume to each posting and target roles where your match is above 70%.")
    return {"total_tracked": len(apps), "total_applied": len(applied), "by_status": dict(by_status),
            "role_families": dict(families), "average_match_score": avg,
            "interview_conversion_pct": conv, "insights": insights}
