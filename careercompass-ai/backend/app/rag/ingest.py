from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import embedder
from app.db.models import KnowledgeDoc


def ingest_knowledge(db: Session, docs: list[dict]) -> int:
    """Upsert docs by (title, category) and embed them. Returns number of new/updated docs."""
    existing = {(d.title, d.category): d for d in db.scalars(select(KnowledgeDoc)).all()}
    todo: list[tuple[KnowledgeDoc, str]] = []
    for d in docs:
        key = (d["title"], d["category"])
        row = existing.get(key)
        if row is None:
            row = KnowledgeDoc(title=d["title"], category=d["category"], skill=d.get("skill"),
                               content=d["content"], source=d.get("source", "curated"))
            db.add(row)
            todo.append((row, d))
        elif row.content != d["content"] or row.skill != d.get("skill"):
            row.content, row.skill = d["content"], d.get("skill")
            todo.append((row, d))
    if todo:
        vecs = embedder.embed([f"{d['title']}. {d['content']}" for _, d in todo])
        for (row, _), v in zip(todo, vecs):
            row.embedding = v.tolist()
        db.commit()
    return len(todo)
