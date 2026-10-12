"""Persist jobs with extracted requirements + embeddings, and select semantic candidates."""
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.embeddings import embedder
from app.core.config import settings
from app.db.models import Job
from app.rag.retriever import semantic_search
from app.tools.job_providers import fetch_external, fetch_seed
from app.tools.matcher import infer_job_level
from app.tools.skill_extractor import extract_skills

_last_fetch: dict[str, float] = {}
FETCH_TTL = 6 * 3600


def job_text(title: str, company: str, skills: list[str], description: str) -> str:
    return f"{title}. {company}. Skills: {', '.join(skills)}. {description[:1500]}"


def ingest_jobs(db: Session, raw_jobs: list[dict]) -> int:
    if not raw_jobs:
        return 0
    keys = {(j["source"], str(j["external_id"])) for j in raw_jobs}
    existing = set(db.execute(select(Job.source, Job.external_id).where(
        Job.source.in_({k[0] for k in keys}), Job.external_id.in_({k[1] for k in keys}))).all())
    new_rows, texts = [], []
    for r in raw_jobs:
        key = (r["source"], str(r["external_id"]))
        if key in existing:
            continue
        existing.add(key)
        title, desc = r.get("title", "")[:255], r.get("description", "")
        reqs = r.get("requirements") or extract_skills(f"{title}. {desc}")
        job = Job(source=r["source"], external_id=str(r["external_id"]), title=title,
                  company=(r.get("company") or "")[:255], location=(r.get("location") or "")[:255],
                  remote=bool(r.get("remote")), description=desc, requirements=reqs,
                  level=infer_job_level(f"{title} {desc[:600]}"), url=r.get("url"), posted_at=r.get("posted_at"))
        new_rows.append(job)
        texts.append(job_text(title, job.company, reqs, desc))
    if not new_rows:
        return 0
    for job, vec in zip(new_rows, embedder.embed(texts)):
        job.embedding = vec.tolist()
    db.add_all(new_rows)
    db.commit()
    return len(new_rows)


def ensure_seed_jobs(db: Session) -> int:
    if "seed" not in settings.providers_list:
        return 0
    if db.scalar(select(func.count()).select_from(Job).where(Job.source == "seed")):
        return 0
    return ingest_jobs(db, fetch_seed())


def refresh_jobs(db: Session, queries: list[str], location: str = "", force: bool = False) -> dict:
    """Pull from external providers (rate-limited by an in-process TTL cache)."""
    added = 0
    ensure_seed_jobs(db)
    for q in dict.fromkeys(q for q in queries if q):
        if not force and time.time() - _last_fetch.get(q.lower(), 0) < FETCH_TTL:
            continue
        _last_fetch[q.lower()] = time.time()
        added += ingest_jobs(db, fetch_external(q, location))
    return {"added": added, "providers": settings.providers_list}


def candidate_jobs(db: Session, query_vec, k: int = 60) -> list[tuple[Job, float]]:
    return semantic_search(db, Job, query_vec, k=k, where=Job.is_active.is_(True))
