from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.core.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.ml.role_classifier import predict_roles
from app.profile import engine
from app.schemas import ProfileUpdateIn, SkillsIn

router = APIRouter(prefix="/profile", tags=["career profile"])


@router.get("")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = engine.get_or_create(db, user.id)
    out = engine.to_dict(p, user)
    out["suggested_roles"] = predict_roles(engine.effective_skills(p))[:3]
    return out


@router.put("")
def update_profile(body: ProfileUpdateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update preferences. Setting a NEW target role triggers the full goal pipeline
    (skill gap -> jobs -> roadmap -> notifications)."""
    before = engine.get_or_create(db, user.id).target_role
    p = engine.update_preferences(db, user.id, body.model_dump(exclude_unset=True))
    out = {"profile": engine.to_dict(p, user)}
    if p.target_role and p.target_role != before:
        out["pipeline"] = _compact(Orchestrator(db).handle(user.id, "goal_set", target_role=p.target_role))
    return out


@router.post("/skills")
def declare_skills(body: SkillsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tell the system you know a skill; the roadmap and job matches adapt automatically."""
    added = engine.declare_skills(db, user.id, body.skills)
    run = Orchestrator(db).handle(user.id, "skills_updated", known_skills=body.skills)
    return {"added": added, "pipeline": _compact(run)}


@router.delete("/skills/{name}")
def remove_skill(name: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    removed = engine.remove_declared_skill(db, user.id, name)
    return {"removed": removed}


def _compact(run: dict) -> dict:
    return {"run_id": run["run_id"], "intent": run["intent"], "response": run["response"],
            "steps": [s["agent"] for s in run["steps"]]}
