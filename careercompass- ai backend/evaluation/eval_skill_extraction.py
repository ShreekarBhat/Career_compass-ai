"""Skill-extraction precision / recall / F1.  Run: python -m evaluation.eval_skill_extraction"""
import json
from pathlib import Path

from app.tools.skill_extractor import extract_skills
from evaluation._metrics import prf

cases = json.loads((Path(__file__).parent / "data" / "skill_extraction.json").read_text(encoding="utf-8"))
tp = fp = fn = 0
for c in cases:
    pred, gold = {s.lower() for s in extract_skills(c["text"])}, {s.lower() for s in c["skills"]}
    tp += len(pred & gold); fp += len(pred - gold); fn += len(gold - pred)
    if pred != gold:
        print(f"  diff: extra={sorted(pred - gold)} missing={sorted(gold - pred)}")
print("Skill extraction:", prf(tp, fp, fn), f"(n={len(cases)} snippets)")
