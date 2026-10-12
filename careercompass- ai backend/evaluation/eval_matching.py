"""Job-matching evaluation against manually labelled relevance: precision/recall/F1 at a score threshold
and Top-K hit rate. Skills-only scoring (no embeddings) so it is deterministic.
Extend evaluation/data/matching_pairs.json with your own labelled pairs.  Run: python -m evaluation.eval_matching"""
import json
from pathlib import Path

from app.tools.matcher import compute_match
from evaluation._metrics import prf

data = json.loads((Path(__file__).parent / "data" / "matching_pairs.json").read_text(encoding="utf-8"))
scored = []  # (profile, job_id, score, relevant)
for p in data:
    for j in p["jobs"]:
        s = compute_match(p["profile_skills"], j["skills"])["score"]
        scored.append((p["profile"], j["id"], s, j["relevant"]))

print("threshold  precision  recall  f1")
for th in (40, 50, 60, 70):
    tp = sum(1 for *_, s, r in scored if s >= th and r)
    fp = sum(1 for *_, s, r in scored if s >= th and not r)
    fn = sum(1 for *_, s, r in scored if s < th and r)
    m = prf(tp, fp, fn)
    print(f"{th:>9}  {m['precision']:>9}  {m['recall']:>6}  {m['f1']}")

for k in (1, 2, 3):
    hits = 0
    for p in data:
        ranked = sorted((x for x in scored if x[0] == p["profile"]), key=lambda x: -x[2])[:k]
        hits += any(x[3] for x in ranked)
    print(f"Top-{k} hit rate: {hits}/{len(data)}")
