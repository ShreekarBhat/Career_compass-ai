"""Tool/agent-selection accuracy of the orchestrator's intent router (offline, rule-based path).
Run from the project root:  python -m evaluation.eval_intent"""
import json
import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("GROQ_API_KEY", "")
from app.agents.orchestrator import INTENT_PLANS, classify_intent  # noqa: E402

cases = json.loads((Path(__file__).parent / "data" / "intent_tests.json").read_text(encoding="utf-8"))
ok, misses, per = 0, [], Counter()
for c in cases:
    got, _ = classify_intent(c["message"])
    hit = got == c["intent"] or INTENT_PLANS[got] == INTENT_PLANS[c["intent"]]  # same agent plan = correct tool choice
    ok += hit
    per[c["intent"], hit] += 1
    if not hit:
        misses.append((c["message"], c["intent"], got))
print(f"Tool-selection accuracy: {ok}/{len(cases)} = {100 * ok / len(cases):.1f}%")
for m, exp, got in misses:
    print(f"  MISS  {m!r}: expected {exp}, got {got}")
