"""Vector search helpers (pgvector in Postgres, numpy fallback elsewhere) + the RAG retriever."""
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import embedder
from app.db.models import KnowledgeDoc


def semantic_search(db: Session, model, query_vec, k: int = 20, where=None) -> list[tuple[object, float]]:
    """Return [(row, cosine_similarity)] best-first."""
    qv = np.asarray(query_vec, dtype=np.float32)
    if db.get_bind().dialect.name == "postgresql":
        dist = model.embedding.cosine_distance(qv.tolist())
        stmt = select(model, dist.label("distance")).where(model.embedding.is_not(None))
        if where is not None:
            stmt = stmt.where(where)
        rows = db.execute(stmt.order_by(dist).limit(k)).all()
        return [(r[0], 1.0 - float(r[1])) for r in rows]
    stmt = select(model)
    if where is not None:
        stmt = stmt.where(where)
    scored = []
    for item in db.scalars(stmt).all():
        if item.embedding is None:
            continue
        v = np.asarray(item.embedding, dtype=np.float32)
        n = np.linalg.norm(v) * np.linalg.norm(qv)
        scored.append((item, float(np.dot(v, qv) / n) if n else 0.0))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:k]


def retrieve(db: Session, query: str, k: int = 4, category: str | None = None,
             min_score: float = 0.0) -> list[dict]:
    where = KnowledgeDoc.category == category if category else None
    hits = semantic_search(db, KnowledgeDoc, embedder.embed_one(query), k=k, where=where)
    return [{"id": d.id, "title": d.title, "category": d.category, "skill": d.skill,
             "content": d.content, "score": round(s, 3)} for d, s in hits if s >= min_score]


def resources_for_skill(db: Session, skill: str, limit: int = 2) -> list[dict]:
    """Curated learning resources tagged with exactly this skill (no loose semantic guesses)."""
    docs = db.scalars(select(KnowledgeDoc).where(KnowledgeDoc.skill == skill,
                                                 KnowledgeDoc.category == "learning_resource")).all()
    return [{"title": d.title, "content": d.content} for d in docs[:limit]]
