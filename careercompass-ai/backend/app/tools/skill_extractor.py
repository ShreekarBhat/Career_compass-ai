"""Dictionary + alias based skill extraction (deterministic, fast, evaluable)."""
import re
from functools import lru_cache

from app.data.taxonomy import SKILLS, alias_map


@lru_cache(maxsize=1)
def _pattern() -> re.Pattern:
    aliases = sorted(alias_map(), key=len, reverse=True)
    body = "|".join(re.escape(a) for a in aliases)
    # not preceded/followed by alphanumerics, '+' or '#'  (so 'java' != 'javascript', 'sql' != 'postgresql')
    return re.compile(rf"(?<![A-Za-z0-9+#])(?:{body})(?![A-Za-z0-9+#])", re.IGNORECASE)


def extract_skills(text: str) -> list[str]:
    """Canonical skill names in order of first appearance."""
    if not text:
        return []
    amap = alias_map()
    seen: dict[str, None] = {}
    for m in _pattern().finditer(text):
        seen.setdefault(amap[m.group(0).lower()], None)
    return list(seen)


def count_mentions(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not text:
        return counts
    amap = alias_map()
    for m in _pattern().finditer(text):
        s = amap[m.group(0).lower()]
        counts[s] = counts.get(s, 0) + 1
    return counts


def normalize_skill_names(names: list[str]) -> list[str]:
    """Map user-typed names ('pytorch', 'k8s') to canonical ones; unknown names are kept title-cased."""
    out: dict[str, None] = {}
    amap = alias_map()
    for n in names:
        n = (n or "").strip()
        if not n:
            continue
        canon = amap.get(n.lower())
        if canon:
            out.setdefault(canon, None)
            continue
        found = extract_skills(n)
        if found:
            for f in found:
                out.setdefault(f, None)
        else:
            out.setdefault(n[:60], None)
    return list(out)


def is_known(skill: str) -> bool:
    return skill in SKILLS
