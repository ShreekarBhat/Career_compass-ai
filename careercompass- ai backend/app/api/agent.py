from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.core.deps import get_current_user
from app.db.models import AgentRun, User
from app.db.session import get_db
from app.rag.retriever import retrieve
from app.schemas import AgentChatIn

router = APIRouter(tags=["agent"])


@router.post("/agent/chat")
def chat(body: AgentChatIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Free-form request. The orchestrator classifies intent, plans which agents to run and in what order,
    executes them, and composes a response. `steps` shows exactly which agents ran."""
    run = Orchestrator(db).handle(user.id, "chat", body.message, job_id=body.job_id,
                                  job_description=body.job_description)
    return run


@router.get("/agent/runs")
def runs(limit: int = 20, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AgentRun).where(AgentRun.user_id == user.id).order_by(AgentRun.id.desc()).limit(min(limit, 100))).all()
    return [{"id": r.id, "trigger": r.trigger, "intent": r.intent, "message": r.message,
             "steps": [s["agent"] for s in r.steps], "success": r.success, "latency_ms": r.latency_ms,
             "flagged_injection": r.flagged_injection, "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/agent/metrics")
def metrics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Agent evaluation metrics aggregated from stored runs (task completion rate, latency)."""
    rows = db.execute(select(AgentRun.success, AgentRun.latency_ms, AgentRun.flagged_injection)
                      .where(AgentRun.user_id == user.id)).all()
    total = len(rows)
    lats = sorted(r[1] for r in rows)
    return {"runs": total,
            "task_completion_rate_pct": round(100 * sum(1 for r in rows if r[0]) / total, 1) if total else None,
            "avg_latency_ms": int(sum(lats) / total) if total else None,
            "p95_latency_ms": lats[int(0.95 * (total - 1))] if total else None,
            "injection_attempts_flagged": sum(1 for r in rows if r[2])}


@router.get("/knowledge/search")
def knowledge_search(q: str, k: int = 4, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Direct RAG retrieval (useful for debugging/demo)."""
    return retrieve(db, q, k=min(k, 10))

