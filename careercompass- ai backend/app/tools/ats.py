"""ATS / resume analysis engine: rules + keyword coverage + semantic similarity (no LLM needed)."""
import re

from app.ai.embeddings import cosine, embedder
from app.data.taxonomy import ROLES, role_skill_weights
from app.profile.parser import split_sections
from app.tools.skill_extractor import extract_skills

ACTION_VERBS = {
    "built", "developed", "designed", "implemented", "created", "led", "managed", "improved", "optimized",
    "optimised", "deployed", "automated", "analyzed", "analysed", "engineered", "architected", "launched",
    "reduced", "increased", "delivered", "trained", "integrated", "collaborated", "migrated", "wrote",
    "tested", "achieved", "established", "streamlined", "researched", "evaluated", "mentored", "scaled",
    "refactored", "configured", "maintained", "coordinated", "organized", "organised", "presented",
    "fine-tuned", "constructed", "produced", "generated", "resolved", "enhanced", "drove", "executed",
}
WEAK_STARTS = ("responsible for", "worked on", "helped", "assisted", "involved in", "duties included", "tasked with")
_BULLET = re.compile(r"^\s*[-•*▪●◦·➢►]\s*")
_NUM = re.compile(r"\d")


def _statements(text: str) -> list[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    bullets = [_BULLET.sub("", l) for l in lines if _BULLET.match(l)]
    if len(bullets) >= 3:
        return bullets
    return [l for l in lines if len(l.split()) >= 6]  # PDF extraction often loses bullet glyphs


def _scaled_sim(a: float) -> float:
    return max(0.0, min(1.0, (a - 0.1) / 0.6))


def analyze_resume(text: str, role: str | None = None, job_description: str | None = None,
                   job_skills: list[str] | None = None) -> dict:
    words = re.findall(r"\w+", text)
    wc = len(words)
    sections = split_sections(text)
    found_skills = extract_skills(text)
    low = text.lower()
    stmts = _statements(sections.get("experience", "") + "\n" + sections.get("projects", "")) or _statements(text)

    # -------- sections (20)
    pts = {"skills": 5, "education": 5, "projects": 5, "experience": 3, "summary": 2}
    sec_score = sum(v for k, v in pts.items() if k in sections)
    missing_sections = [k for k in pts if k not in sections]

    # -------- contact (10)
    has_email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text))
    has_phone = bool(re.search(r"\d{3,5}[\s-]?\d{3,5}[\s-]?\d{2,5}", text))
    has_link = "linkedin.com" in low or "github.com" in low
    contact_score = 4 * has_email + 3 * has_phone + 3 * has_link

    # -------- keywords (25)
    if job_skills is None and job_description:
        job_skills = extract_skills(job_description)
    weights: dict[str, int]
    target_label = None
    if job_skills:
        weights = {s: 2 for s in job_skills}
        target_label = "job"
    elif role and role in ROLES:
        weights = role_skill_weights(role)
        target_label = role
    else:
        weights = {}
    have = {s.lower() for s in found_skills}
    if weights:
        total_w = sum(weights.values())
        got_w = sum(w for s, w in weights.items() if s.lower() in have)
        kw_cov = got_w / total_w if total_w else 0.0
        matched = [s for s in weights if s.lower() in have]
        missing = sorted((s for s in weights if s.lower() not in have), key=lambda s: -weights[s])
    else:
        kw_cov = min(1.0, len(found_skills) / 12)
        matched, missing = found_skills, []
    kw_score = 25 * kw_cov

    # -------- quantified achievements (15)
    quant = [s for s in stmts if _NUM.search(s) or "%" in s]
    q_ratio = len(quant) / len(stmts) if stmts else 0.0
    q_score = 15 * min(1.0, q_ratio / 0.35)

    # -------- action verbs (10)
    def starts_with_verb(s: str) -> bool:
        first = re.sub(r"[^a-z\-]", "", s.lower().split()[0]) if s.split() else ""
        return first in ACTION_VERBS
    strong = [s for s in stmts if starts_with_verb(s)]
    weak = [s for s in stmts if s.lower().startswith(WEAK_STARTS)]
    v_ratio = len(strong) / len(stmts) if stmts else 0.0
    v_score = 10 * min(1.0, v_ratio / 0.6)

    # -------- length (5)
    if 300 <= wc <= 900:
        len_score = 5
    elif 150 <= wc < 300 or 900 < wc <= 1300:
        len_score = 3
    else:
        len_score = 1

    # -------- semantic fit (15)
    sem_score = None
    sem_raw = None
    ref_text = None
    if job_description:
        ref_text = job_description[:3000]
    elif role in ROLES:
        ref_text = f"{role}. {ROLES[role]['description']} Skills: {', '.join(role_skill_weights(role))}"
    if ref_text:
        va, vb = embedder.embed([text[:4000], ref_text])
        sem_raw = cosine(va, vb)
        sem_score = 15 * _scaled_sim(sem_raw)

    earned = sec_score + contact_score + kw_score + q_score + v_score + len_score + (sem_score or 0)
    maximum = 20 + 10 + 25 + 15 + 10 + 5 + (15 if sem_score is not None else 0)
    score = int(round(100 * earned / maximum))

    problems, strengths = [], []
    if missing_sections:
        problems.append({"severity": "high" if "skills" in missing_sections or "education" in missing_sections else "medium",
                         "issue": f"Missing sections: {', '.join(missing_sections)}",
                         "fix": "Add clearly labelled sections using standard headings (Education, Skills, Projects, Experience)."})
    else:
        strengths.append("All key sections present with standard headings")
    if stmts and q_ratio < 0.25:
        problems.append({"severity": "high", "issue": "Missing measurable achievements",
                         "fix": "Add numbers to bullets: accuracy %, latency, users, dataset size, time saved."})
    elif stmts:
        strengths.append("Good use of measurable results")
    if weak:
        problems.append({"severity": "medium", "issue": f"{len(weak)} bullets start with weak phrases ('worked on', 'responsible for')",
                         "fix": "Start bullets with strong verbs: Built, Designed, Deployed, Optimised."})
    elif stmts and v_ratio >= 0.6:
        strengths.append("Bullets start with strong action verbs")
    if "projects" in sections and len(stmts) and v_ratio < 0.4:
        problems.append({"severity": "medium", "issue": "Weak project descriptions",
                         "fix": "For each project state the problem, your approach/tools, and the measurable outcome."})
    if missing:
        top = ", ".join(missing[:5])
        problems.append({"severity": "high" if kw_cov < 0.5 else "medium",
                         "issue": f"Missing keywords for {'this job' if target_label == 'job' else target_label}: {top}",
                         "fix": "If you genuinely have these skills, add them to Skills and to project bullets. Otherwise treat them as learning priorities."})
    if "skills" in sections and len(found_skills) < 6:
        problems.append({"severity": "medium", "issue": "Skills section is thin or poorly structured",
                         "fix": "Group skills by category (Languages, ML/AI, Backend, Databases, DevOps, Tools)."})
    if not has_link:
        problems.append({"severity": "medium", "issue": "No GitHub/LinkedIn link found",
                         "fix": "Add your GitHub and LinkedIn URLs in the header."})
    else:
        strengths.append("Professional links present")
    if not has_email or not has_phone:
        problems.append({"severity": "high", "issue": "Contact details incomplete",
                         "fix": "Include a professional email and a phone number."})
    if wc < 150:
        problems.append({"severity": "high", "issue": "Resume is very short", "fix": "Expand projects and experience with specifics."})
    elif wc > 1300:
        problems.append({"severity": "low", "issue": "Resume is too long", "fix": "Trim to one page (fresher) or two pages."})
    if kw_cov >= 0.7 and weights:
        strengths.append("Strong keyword coverage for the target")

    return {
        "ats_score": score,
        "target": target_label,
        "breakdown": {
            "sections": {"score": round(sec_score, 1), "max": 20},
            "contact": {"score": contact_score, "max": 10},
            "keywords": {"score": round(kw_score, 1), "max": 25, "coverage_pct": int(round(kw_cov * 100))},
            "quantified_achievements": {"score": round(q_score, 1), "max": 15, "ratio_pct": int(round(q_ratio * 100))},
            "action_verbs": {"score": round(v_score, 1), "max": 10, "ratio_pct": int(round(v_ratio * 100))},
            "length": {"score": len_score, "max": 5, "words": wc},
            "semantic_fit": {"score": None if sem_score is None else round(sem_score, 1), "max": 15 if sem_score is not None else 0,
                             "cosine": None if sem_raw is None else round(sem_raw, 3)},
        },
        "strengths": strengths,
        "problems": problems,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "detected_skills": found_skills,
        "word_count": wc,
        "weak_statements": weak[:5] or [s for s in stmts if not starts_with_verb(s)][:5],
    }
