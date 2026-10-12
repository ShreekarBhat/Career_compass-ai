import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agent, auth, interview, jobs, notifications, profile, resumes, roadmap, skills, tracker
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.db.session import SessionLocal, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("careercompass")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.auto_seed:
        from app.tools.seed import seed_all
        with SessionLocal() as db:
            logger.info("Seed: %s", seed_all(db))
    if settings.scheduler_enabled:
        from app import scheduler
        scheduler.start()
    yield
    if settings.scheduler_enabled:
        from app import scheduler
        scheduler.stop()


app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan,
              description="Agentic AI career intelligence platform: orchestrator + specialised agents + RAG.")

app.add_middleware(RateLimitMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth, profile, resumes, jobs, skills, roadmap, interview, tracker, notifications, agent):
    app.include_router(r.router)


@app.get("/health", tags=["system"])
def health():
    from app.ai.embeddings import embedder
    from app.ai.llm import llm
    return {"status": "ok", "llm": "groq" if llm.available else "fallback (no GROQ_API_KEY)",
            "embeddings": embedder.backend, "providers": settings.providers_list}
