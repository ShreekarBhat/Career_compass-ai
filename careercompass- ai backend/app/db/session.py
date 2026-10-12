import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

_connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create the pgvector extension, all tables and vector indexes (idempotent)."""
    from app.db import models  # noqa: F401  (register tables)

    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        for table in ("jobs", "knowledge_docs"):
            try:
                with engine.begin() as conn:
                    conn.execute(text(
                        f"CREATE INDEX IF NOT EXISTS ix_{table}_embedding_hnsw "
                        f"ON {table} USING hnsw (embedding vector_cosine_ops)"))
            except Exception as exc:  # older pgvector without HNSW: exact search still works
                logger.warning("Could not create HNSW index on %s: %s", table, exc)
