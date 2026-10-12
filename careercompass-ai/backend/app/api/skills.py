from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.core.deps import get_current_user
from app.data.taxonomy import ROLES, SKILLS
from app.db.models import User
from app.db.session import get_db

router = APIRouter(tags=["skills"])


@router.get("/skills/gap")
def skill_gap(role: str | None = Query(default=None, max_length=120), user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    """Skill Gap Agent: strong skills, prioritised gaps and per-skill proficiency bars."""
    run = Orchestrator(db).handle(user.id, "api", intent="skill_gap", target_role=role)
    return {"run_id": run["run_id"], **run["results"].get("skill_gap", {})}


@router.get("/skills/taxonomy")
def taxonomy():
    return {"skills": [{"name": n, "category": i["category"], "hours": i["hours"]} for n, i in SKILLS.items()]}


@router.get("/roles")
def roles():
    return [{"role": r, "description": i["description"], "required_skills": i["skills"]} for r, i in ROLES.items()]
