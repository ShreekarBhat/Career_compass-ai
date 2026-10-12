"""Job <-> profile compatibility: weighted skill coverage + semantic similarity + level + location."""
import re

from app.ai.embeddings import cosine
from app.data.taxonomy import SKILLS

LEVELS = {"intern": 0, "fresher": 1, "junior": 1, "mid": 2, "senior": 3}


def infer_job_level(text: str) -> str | None:
    t = text.lower()
    if re.search(r"\b(intern|internship|trainee|apprentice)\b", t):
        return "intern"
    if re.search(r"\b(senior|sr\.?|lead|principal|staff|head of|manager)\b", t) or re.search(r"\b([5-9]|1\d)\+?\s*years", t):
        return "senior"
    if re.search(r"\b(entry[- ]level|fresher|graduate|junior|jr\.?|associate|0-[12]\s*years|new grad)\b", t):
        return "junior"
    if re.search(r"\b(mid|intermediate|[2-4]\+?\s*years|2-5 years|3-5 years)\b", t):
        return "mid"
    return None


def normalize_level(level: str | None) -> str | None:
    if not level:
        return None
    l = level.lower()
    for key in LEVELS:
        if key in l:
            return key
    if "entry" in l or "student" in l or "graduate" in l:
        return "fresher"
    return None


def _scaled(sim: float) -> float:
    return max(0.0, min(1.0, (sim - 0.1) / 0.6))


def level_fit(profile_level: str | None, job_level: str | None) -> float:
    p, j = normalize_level(profile_level), job_level
    if p is None or j is None:
        return 0.75
    diff = abs(LEVELS[p] - LEVELS[j])
    # interns/freshers can apply to junior roles, so penalise only large gaps
    return {0: 1.0, 1: 0.7}.get(diff, 0.2)


def location_fit(preferred: list[str], job_location: str, remote: bool) -> float:
    if remote:
        return 1.0
    if not preferred:
        return 0.7
    jl = (job_location or "").lower()
    return 1.0 if any(p.lower() in jl for p in preferred) else 0.3


def compute_match(profile_skills: list[str], job_skills: list[str], profile_vec=None, job_vec=None,
                  profile_level: str | None = None, job_level: str | None = None,
                  preferred_locations: list[str] | None = None, job_location: str = "",
                  remote: bool = False) -> dict:
    ps = {s.lower() for s in profile_skills}
    required = list(dict.fromkeys(job_skills))
    matched = [s for s in required if s.lower() in ps]
    partial = []
    for s in required:
        if s.lower() in ps:
            continue
        related = SKILLS.get(s, {}).get("related", [])
        if any(r.lower() in ps for r in related):
            partial.append(s)
    missing = [s for s in required if s not in matched]

    coverage = ((len(matched) + 0.4 * len(partial)) / len(required)) if required else None
    semantic = _scaled(cosine(profile_vec, job_vec)) if profile_vec is not None and job_vec is not None else None
    lvl = level_fit(profile_level, job_level)
    loc = location_fit(preferred_locations or [], job_location, remote)

    parts, weights = [], []
    if coverage is not None:
        parts.append(coverage); weights.append(0.55)
    if semantic is not None:
        parts.append(semantic); weights.append(0.30)
    parts += [lvl, loc]; weights += [0.10, 0.05]
    score = sum(p * w for p, w in zip(parts, weights)) / sum(weights)
    return {
        "score": int(round(score * 100)),
        "coverage_pct": None if coverage is None else int(round(coverage * 100)),
        "semantic_pct": None if semantic is None else int(round(semantic * 100)),
        "level_fit": lvl,
        "location_fit": loc,
        "matched_skills": matched,
        "partial_skills": partial,
        "missing_skills": missing,
    }


def explain_match(job_title: str, company: str, m: dict) -> str:
    total = len(m["matched_skills"]) + len(m["missing_skills"])
    bits = []
    if total:
        bits.append(f"You already cover {len(m['matched_skills'])} of {total} listed requirements"
                    + (f" ({', '.join(m['matched_skills'][:4])})" if m["matched_skills"] else ""))
    if m["missing_skills"]:
        bits.append(f"main gaps: {', '.join(m['missing_skills'][:3])}")
    if m["partial_skills"]:
        bits.append(f"related experience helps with {', '.join(m['partial_skills'][:2])}")
    if m["semantic_pct"] is not None:
        bits.append(f"overall profile similarity {m['semantic_pct']}%")
    verdict = "Strong match" if m["score"] >= 80 else "Good match" if m["score"] >= 65 else "Stretch" if m["score"] >= 45 else "Weak match"
    return f"{verdict} for {job_title}{' at ' + company if company else ''}: " + "; ".join(bits) + "."
