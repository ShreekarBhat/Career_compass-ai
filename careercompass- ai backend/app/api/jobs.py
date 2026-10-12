from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.agents.job_agent import JobAgent
from app.agents.orchestrator import Orchestrator
from app.ai.embeddings import embedder
from app.core.deps import get_current_user
from app.db.models import Application, Job, User
from app.db.session import get_db
from app.profile import engine as profile_engine
from app.schemas import DiscoverIn, JobIn
from app.tools import job_store, tracker
from app.tools.matcher import compute_match, explain_match

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_dict(j: Job) -> dict:
    return {"id": j.id, "title": j.title, "company": j.company, "location": j.location, "remote": j.remote,
            "level": j.level, "requirements": j.requirements, "url": j.url, "source": j.source,
            "posted_at": j.posted_at.isoformat() if j.posted_at else None}


@router.post("/discover")
def discover(body: DiscoverIn | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Job Discovery Agent: fetch, analyse, rank and explain matches for your profile."""
    body = body or DiscoverIn()
    run = Orchestrator(db).handle(user.id, "api", intent="find_jobs", refresh=body.refresh, limit=body.limit,
                                  min_score=body.min_score)
    return {"run_id": run["run_id"], **run["results"].get("job_discovery", {})}


@router.get("")
def list_jobs(q: str | None = Query(default=None, max_length=100), limit: int = Query(default=20, le=100),
              offset: int = 0, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job_store.ensure_seed_jobs(db)
    stmt = select(Job).where(Job.is_active.is_(True))
    if q:
        like = f"%{q.lower()}%"
        from sqlalchemy import func
        stmt = stmt.where(or_(func.lower(Job.title).like(like), func.lower(Job.company).like(like)))
    rows = db.scalars(stmt.order_by(Job.id.desc()).offset(offset).limit(limit)).all()
    return [_job_dict(j) for j in rows]


@router.post("", status_code=201)
def add_job(body: JobIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add a job manually (paste a posting you found elsewhere)."""
    import uuid
    job_store.ingest_jobs(db, [{"source": "manual", "external_id": uuid.uuid4().hex, **body.model_dump()}])
    job = db.scalar(select(Job).where(Job.source == "manual").order_by(Job.id.desc()))
    return _job_dict(job)


@router.get("/saved")
def saved(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Application).where(Application.user_id == user.id, Application.status == "saved")).all()
    return [tracker.to_dict(a) for a in rows]


@router.get("/{job_id}")
def get_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    j = db.get(Job, job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    p = profile_engine.get_or_create(db, user.id)
    skills = profile_engine.effective_skills(p)
    m = compute_match(skills, j.requirements or [], p.embedding or embedder.embed_one(" ".join(skills) or "general"),
                      j.embedding, p.experience_level, j.level, p.preferred_locations or [], j.location, j.remote)
    return {**_job_dict(j), "description": j.description, "match": m, "explanation": explain_match(j.title, j.company, m)}


@router.post("/{job_id}/save", status_code=201)
def save_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    j = db.get(Job, job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    existing = db.scalar(select(Application).where(Application.user_id == user.id, Application.job_id == job_id))
    if existing:
        return tracker.to_dict(existing)
    p = profile_engine.get_or_create(db, user.id)
    skills = profile_engine.effective_skills(p)
    score = compute_match(skills, j.requirements or [], p.embedding, j.embedding, p.experience_level, j.level,
                          p.preferred_locations or [], j.location, j.remote)["score"] if p.embedding is not None else None
    app = tracker.create_application(db, user.id, {"job_id": j.id, "company": j.company or "Unknown", "role": j.title,
                                                   "url": j.url, "match_score": score, "status": "saved"})
    return tracker.to_dict(app)
