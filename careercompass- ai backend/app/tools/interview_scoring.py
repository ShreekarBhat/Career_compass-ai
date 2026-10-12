"""Question selection + heuristic answer scoring (fallback when the LLM is unavailable)."""
import random
import re

from app.data.interview_bank import BEHAVIORAL, TECHNICAL

STOP = set("the a an and or of to in is are was were for on with that this it as by be at from your you how what why when do does did can would".split())
HEDGES = ["maybe", "i think", "probably", "not sure", "i guess", "kind of", "sort of", "i don't know", "um ", "uh "]
CONNECTORS = ["because", "therefore", "for example", "for instance", "first", "then", "finally", "however", "so that", "as a result"]


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9\+#/]+", text.lower()) if t not in STOP and len(t) > 2}


def select_technical(skills_priority: list[str], profile_skills: list[str], n: int, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    pool = list(TECHNICAL)
    rng.shuffle(pool)
    want = {s.lower() for s in skills_priority} | {s.lower() for s in profile_skills}
    first = [q for q in pool if q["skill"].lower() in {s.lower() for s in skills_priority}]
    second = [q for q in pool if q["skill"].lower() in want and q not in first]
    rest = [q for q in pool if q not in first and q not in second]
    chosen = (first + second + rest)[:n]
    return [{"round": "Technical", "skill": q["skill"], "question": q["question"], "expected_points": q["points"]} for q in chosen]


def resume_questions(projects: list[dict], skills: list[str], n: int) -> list[dict]:
    qs = []
    for p in projects[:n]:
        title = p.get("title", "your project")
        qs.append({"round": "Resume-based", "skill": None,
                   "question": f"You mentioned '{title}'. What was the hardest technical decision you made, and why did you choose that approach?",
                   "expected_points": ["decision", "because", "trade-off", "alternative", "result", "tool"]})
    for s in skills:
        if len(qs) >= n:
            break
        qs.append({"round": "Resume-based", "skill": s,
                   "question": f"Your resume lists {s}. Describe a concrete situation where you used it and what you learned.",
                   "expected_points": ["used", "project", "problem", "result", "learned"]})
    return qs[:n]


def behavioral_questions(n: int, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    pool = list(BEHAVIORAL)
    rng.shuffle(pool)
    return [{"round": "Behavioral", "skill": None, "question": q["question"], "expected_points": q["points"]} for q in pool[:n]]


def heuristic_score(question: str, answer: str, expected_points: list[str]) -> dict:
    ans = answer.lower()
    words = len(answer.split())
    hit = [p for p in expected_points if p.lower() in ans]
    cov = len(hit) / len(expected_points) if expected_points else 0.5
    technical = min(100, int(round(cov * 85 + min(words, 80) / 80 * 15)))
    sentences = [s for s in re.split(r"[.!?]+", answer) if s.strip()]
    conn = sum(1 for c in CONNECTORS if c in ans)
    communication = 35 + min(25, len(sentences) * 6) + min(25, conn * 8) + (15 if 40 <= words <= 220 else 0)
    communication = min(100, communication)
    hedges = sum(ans.count(h) for h in HEDGES)
    confidence = max(30, 100 - hedges * 12)
    if words < 12:
        confidence = int(confidence * 0.7)
    q_overlap = len(_tokens(question) & _tokens(answer)) / max(1, len(_tokens(question)))
    relevance = int(round(min(100, 100 * (0.65 * cov + 0.35 * min(1.0, q_overlap * 2)))))
    if words >= 10:
        relevance = max(relevance, 25)
    missing = [p for p in expected_points if p.lower() not in ans][:4]
    tips = []
    if missing:
        tips.append(f"Mention key ideas such as: {', '.join(missing)}.")
    if words < 30:
        tips.append("Expand the answer: define the concept, explain how it works, then give an example.")
    if hedges:
        tips.append("Reduce hedging phrases ('maybe', 'I think') and state your reasoning directly.")
    if conn == 0:
        tips.append("Use connectors (because, for example, therefore) to structure your reasoning.")
    feedback = " ".join(tips) or "Solid answer. Add a concrete example from your own project to make it stronger."
    return {"technical_knowledge": technical, "communication": int(communication), "confidence": int(confidence),
            "answer_relevance": relevance, "feedback": feedback, "covered_points": hit, "missing_points": missing}


def overall_score(scores: dict) -> int:
    return int(round(0.4 * scores["technical_knowledge"] + 0.2 * scores["communication"]
                     + 0.15 * scores["confidence"] + 0.25 * scores["answer_relevance"]))
