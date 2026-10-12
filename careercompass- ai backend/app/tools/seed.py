from sqlalchemy.orm import Session

from app.data.knowledge_base import KNOWLEDGE_DOCS
from app.rag.ingest import ingest_knowledge
from app.tools.job_store import ensure_seed_jobs


def seed_all(db: Session) -> dict:
    return {"jobs_added": ensure_seed_jobs(db), "knowledge_upserted": ingest_knowledge(db, KNOWLEDGE_DOCS)}
