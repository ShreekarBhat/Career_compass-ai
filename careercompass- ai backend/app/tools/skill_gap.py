"""Skill-gap computation: proficiency estimate, weighted coverage and market-frequency priority."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.taxonomy import ROLES, SKILLS, role_skill_weights
from app.db.models import Application, CareerProfile, Job, Resume
from app.profile.engine import effective_skills
from app.tools.skill_extractor import count_mentions


def estimate_proficiency(skill: str, profile: CareerProfile, mentions: dict[str, int], project_text: str) -> int:
    """0-100 heuristic. Declared = 85; resume evidence 65-100; related skill = 30; none = 0."""
    declared = {s.lower() for s in (profile.declared_skills or [])}
    resume = {s.lower() for s in (profile.skills or [])}
    s = skill.lower()
    if s in declared:
        return 85
    if s in resume:
        base = 65 + min(20, 7 * max(0, mentions.get(skill, 1) - 1))
        if skill.lower() in project_text:
            base += 12
        return min(100, base)
    have = declared | resume
    if any(r.lower() in have for r in SKILLS.get(skill, {}).get("related", [])):
        return 30
    return 0


def reference_jobs(db: Session, user_id: int, role: str, limit: int = 40) -> tuple[list[Job], str]:
    """Jobs used to compute market frequency: the user's saved/applied jobs, else jobs matching the role."""
    ids = [a.job_id for a in db.scalars(select(Application).where(Application.user_id == user_id)).all() if a.job_id]
    if len(ids) >= 3:
        return list(db.scalars(select(Job).where(Job.id.in_(ids))).all()), "your saved/applied jobs"
    role_skills = set(role_skill_weights(role))
    jobs = db.scalars(select(Job).where(Job.is_active.is_(True)).limit(500)).all()
    scored = []
    for j in jobs:
        overlap = len(role_skills & set(j.requirements or []))
        if overlap >= 3:
            scored.append((overlap, j))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [j for _, j in scored[:limit]], f"listings similar to {role}"


def compute_gap(db: Session, user_id: int, profile: CareerProfile, role: str, resume_text: str = "") -> dict:
    weights = role_skill_weights(role)
    if not weights:
        return {"target_role": role, "error": "unknown_role", "overall_match_pct": 0, "strong": [], "missing": [], "bars": []}
    mentions = count_mentions(resume_text)
    project_text = " ".join(f"{p.get('title','')} {p.get('description','')}" for p in (profile.projects or [])).lower()
    jobs, ref_label = reference_jobs(db, user_id, role)
    n_jobs = len(jobs)

    rows = []
    for skill, w in weights.items():
        prof = estimate_proficiency(skill, profile, mentions, project_text)
        freq = (sum(1 for j in jobs if skill in (j.requirements or [])) / n_jobs) if n_jobs else 0.0
        priority = w * (1 - prof / 100) * (1 + 2 * freq)
        rows.append({"skill": skill, "importance": w, "proficiency": prof, "market_frequency_pct": int(round(freq * 100)),
                     "priority": round(priority, 3)})
    total_w = sum(weights.values())
    overall = int(round(100 * sum(r["importance"] * r["proficiency"] / 100 for r in rows) / total_w))
    strong = sorted((r for r in rows if r["proficiency"] >= 60), key=lambda r: -r["proficiency"])
    missing = sorted((r for r in rows if r["proficiency"] < 60), key=lambda r: -r["priority"])

    insights = []
    for r in missing[:3]:
        if n_jobs >= 3 and r["market_frequency_pct"] >= 30:
            insights.append(f"{r['skill']} appears in {r['market_frequency_pct']}% of {ref_label}.")
    if missing:
        insights.append(f"Prioritise {', '.join(r['skill'] for r in missing[:3])} first.")
    return {
        "target_role": role,
        "overall_match_pct": overall,
        "strong": strong,
        "missing": missing,
        "bars": sorted(rows, key=lambda r: -r["proficiency"]),
        "reference": {"jobs_analyzed": n_jobs, "label": ref_label},
        "insights": insights,
    }


def latest_resume_text(db: Session, user_id: int) -> str:
    r = db.scalar(select(Resume).where(Resume.user_id == user_id, Resume.is_active.is_(True)).order_by(Resume.id.desc()))
    return r.text if r else ""


def suggest_role_from_skills(skills: list[str]) -> list[dict]:
    """Rule baseline for role suggestion (the trained classifier in app.ml refines this)."""
    have = {s.lower() for s in skills}
    out = []
    for role, info in ROLES.items():
        w = info["skills"]
        cov = sum(v for s, v in w.items() if s.lower() in have) / sum(w.values())
        out.append({"role": role, "score": round(cov, 3)})
    return sorted(out, key=lambda r: -r["score"])
