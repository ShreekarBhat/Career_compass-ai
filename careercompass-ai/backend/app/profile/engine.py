"""Career Profile Engine: the single structured profile every agent reads and updates."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import embedder
from app.data.taxonomy import resolve_role
from app.db.models import CareerProfile, User
from app.profile.parser import parse_resume
from app.tools.matcher import normalize_level
from app.tools.skill_extractor import normalize_skill_names


def get_or_create(db: Session, user_id: int) -> CareerProfile:
    p = db.scalar(select(CareerProfile).where(CareerProfile.user_id == user_id))
    if p is None:
        p = CareerProfile(user_id=user_id, skills=[], declared_skills=[], education=[], projects=[],
                          experience=[], preferred_roles=[], preferred_locations=[])
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def effective_skills(p: CareerProfile) -> list[str]:
    return list(dict.fromkeys([*(p.skills or []), *(p.declared_skills or [])]))


def profile_text(p: CareerProfile) -> str:
    proj = ", ".join(x.get("title", "") for x in (p.projects or []))
    return (f"{p.target_role or ''}. Skills: {', '.join(effective_skills(p))}. {p.summary or ''} "
            f"Projects: {proj}. Level: {p.experience_level or ''}")


def refresh_embedding(db: Session, p: CareerProfile) -> None:
    p.embedding = embedder.embed_one(profile_text(p)).tolist()
    db.commit()


def update_from_resume(db: Session, user_id: int, text: str) -> CareerProfile:
    parsed = parse_resume(text)
    p = get_or_create(db, user_id)
    p.skills = parsed["skills"]
    if parsed["education"]:
        p.education = parsed["education"]
    if parsed["projects"]:
        p.projects = parsed["projects"]
    if parsed["experience"]:
        p.experience = parsed["experience"]
    if parsed["summary"]:
        p.summary = parsed["summary"]
    p.years_experience = parsed["years_experience"]
    if not p.experience_level or p.experience_level == "fresher":
        p.experience_level = parsed["experience_level"]
    db.commit()
    refresh_embedding(db, p)
    return p


def update_preferences(db: Session, user_id: int, data: dict) -> CareerProfile:
    p = get_or_create(db, user_id)
    if data.get("target_role") is not None:
        p.target_role = resolve_role(data["target_role"]) or data["target_role"].strip()[:120] or None
    for field in ("career_goal", "salary_preference"):
        if data.get(field) is not None:
            setattr(p, field, data[field])
    if data.get("preferred_roles") is not None:
        p.preferred_roles = [resolve_role(r) or r for r in data["preferred_roles"]]
    if data.get("preferred_locations") is not None:
        p.preferred_locations = data["preferred_locations"]
    if data.get("experience_level") is not None:
        p.experience_level = normalize_level(data["experience_level"]) or data["experience_level"]
    db.commit()
    refresh_embedding(db, p)
    return p


def declare_skills(db: Session, user_id: int, names: list[str]) -> list[str]:
    """User tells us they know a skill (e.g. 'I already know PyTorch'). Returns newly added ones."""
    p = get_or_create(db, user_id)
    canon = normalize_skill_names(names)
    new = [s for s in canon if s not in (p.declared_skills or []) and s not in (p.skills or [])]
    p.declared_skills = list(dict.fromkeys([*(p.declared_skills or []), *canon]))
    db.commit()
    refresh_embedding(db, p)
    return new


def remove_declared_skill(db: Session, user_id: int, name: str) -> bool:
    p = get_or_create(db, user_id)
    canon = normalize_skill_names([name])[0]
    if canon in (p.declared_skills or []):
        p.declared_skills = [s for s in p.declared_skills if s != canon]
        db.commit()
        refresh_embedding(db, p)
        return True
    return False


def to_dict(p: CareerProfile, user: User | None = None) -> dict:
    return {
        "user": None if user is None else {"id": user.id, "email": user.email, "full_name": user.full_name},
        "target_role": p.target_role, "career_goal": p.career_goal,
        "skills": p.skills or [], "declared_skills": p.declared_skills or [],
        "all_skills": effective_skills(p), "education": p.education or [], "projects": p.projects or [],
        "experience": p.experience or [], "preferred_roles": p.preferred_roles or [],
        "preferred_locations": p.preferred_locations or [], "experience_level": p.experience_level,
        "years_experience": p.years_experience, "salary_preference": p.salary_preference, "summary": p.summary,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
