"""Role prediction from a skill set.

If a trained model exists (models/role_classifier.joblib, produced by app/ml/train_role_classifier.py)
it is used; otherwise a transparent weighted-coverage baseline over the role taxonomy is used.
"""
import logging
from functools import lru_cache
from pathlib import Path

from app.data.taxonomy import ROLES

logger = logging.getLogger(__name__)
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "role_classifier.joblib"


def skill_tokenizer(text: str) -> list[str]:
    """Module-level (picklable) tokenizer: 'Python, SQL' -> ['python', 'sql']."""
    return [t.strip().lower() for t in text.split(",") if t.strip()]


def _baseline(skills: list[str]) -> list[dict]:
    have = {s.lower() for s in skills}
    out = []
    for role, info in ROLES.items():
        w = info["skills"]
        cov = sum(v for s, v in w.items() if s.lower() in have) / sum(w.values())
        out.append({"role": role, "score": round(cov, 3), "method": "coverage_baseline"})
    return sorted(out, key=lambda r: -r["score"])


@lru_cache(maxsize=1)
def _load():
    if not MODEL_PATH.exists():
        return None
    try:
        import joblib

        return joblib.load(MODEL_PATH)
    except Exception as exc:
        logger.warning("Could not load role classifier: %s", exc)
        return None


def predict_roles(skills: list[str]) -> list[dict]:
    if not skills:
        return []
    model = _load()
    if model is None:
        return [r for r in _baseline(skills) if r["score"] > 0]
    try:
        proba = model.predict_proba([", ".join(skills)])[0]
        ranked = sorted(zip(model.classes_, proba), key=lambda t: -t[1])
        return [{"role": r, "score": round(float(p), 3), "method": "trained_model"} for r, p in ranked]
    except Exception as exc:
        logger.warning("Role classifier failed (%s); using baseline", exc)
        return _baseline(skills)


def reload_model() -> None:
    _load.cache_clear()
