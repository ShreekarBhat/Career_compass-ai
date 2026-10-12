from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.core.deps import get_current_user
from app.db.models import Roadmap, User
from app.db.session import get_db
from app.profile import engine as profile_engine
from app.schemas import RoadmapAdjustIn, RoadmapIn

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


@router.get("")
def current_roadmap(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.scalar(select(Roadmap).where(Roadmap.user_id == user.id, Roadmap.is_active.is_(True)).order_by(Roadmap.id.desc()))
    if not r:
        raise HTTPException(404, "No roadmap yet. POST /roadmap/generate first.")
    return {"id": r.id, "version": r.version, "target_role": r.target_role, "created_at": r.created_at.isoformat(),
            "roadmap": r.plan}


@router.get("/history")
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Roadmap).where(Roadmap.user_id == user.id).order_by(Roadmap.id.desc())).all()
    return [{"id": r.id, "version": r.version, "target_role": r.target_role, "is_active": r.is_active,
             "total_weeks": r.plan.get("total_weeks"), "created_at": r.created_at.isoformat()} for r in rows]


@router.post("/generate")
def generate(body: RoadmapIn | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    body = body or RoadmapIn()
    run = Orchestrator(db).handle(user.id, "api", intent="roadmap", target_role=body.target_role,
                                  weeks=body.weeks, hours_per_week=body.hours_per_week)
    return {"run_id": run["run_id"], **run["results"].get("planner", {}),
            "skill_gap_summary": {k: run["results"].get("skill_gap", {}).get(k) for k in ("overall_match_pct", "insights")}}


@router.post("/adjust")
def adjust(body: RoadmapAdjustIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """'I already know PyTorch.' -> record the skills, re-run Skill Gap + Planner, return the new roadmap."""
    run = Orchestrator(db).handle(user.id, "api", intent="skill_update", known_skills=body.known_skills,
                                  weeks=body.weeks, hours_per_week=body.hours_per_week)
    return {"run_id": run["run_id"], "response": run["response"], **run["results"].get("planner", {})}
