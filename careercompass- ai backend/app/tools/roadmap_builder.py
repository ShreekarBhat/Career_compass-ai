"""Deterministic roadmap builder: prioritised gaps -> dependency-ordered, time-boxed weekly plan."""
import math

from app.data.taxonomy import SKILLS, skill_hours


def _topo_order(selected: list[str], priority_rank: dict[str, int]) -> list[str]:
    """Kahn's algorithm on prerequisite edges (only among selected skills); ties broken by priority."""
    sel = set(selected)
    indeg = {s: 0 for s in selected}
    children: dict[str, list[str]] = {s: [] for s in selected}
    for s in selected:
        for p in SKILLS.get(s, {}).get("prereqs", []):
            if p in sel:
                indeg[s] += 1
                children[p].append(s)
    ready = sorted([s for s in selected if indeg[s] == 0], key=lambda s: priority_rank[s])
    order = []
    while ready:
        cur = ready.pop(0)
        order.append(cur)
        for c in children[cur]:
            indeg[c] -= 1
            if indeg[c] == 0:
                ready.append(c)
        ready.sort(key=lambda s: priority_rank[s])
    order += [s for s in selected if s not in order]  # cycle guard (should not happen)
    return order


def _tasks(skill: str) -> list[str]:
    cat = SKILLS.get(skill, {}).get("category", "")
    base = [f"Learn the core concepts of {skill}", f"Build a small hands-on exercise with {skill}"]
    if cat in ("ml", "genai", "backend", "devops", "data", "frontend", "database"):
        base.append(f"Add {skill} to a portfolio project and document it in the README")
    return base


def build_roadmap(role: str, missing: list[dict], weeks: int = 12, hours_per_week: int = 10,
                  resources: dict[str, list[dict]] | None = None) -> dict:
    """missing: gap rows sorted by priority (highest first); each has 'skill'."""
    weeks = max(4, min(weeks, 26))
    hours_per_week = max(3, min(hours_per_week, 60))
    reserve = 2 if weeks >= 8 else 1
    available = weeks - reserve

    ranked = [m["skill"] for m in missing]
    rank = {s: i for i, s in enumerate(ranked)}

    # how many weeks each skill needs at the given pace
    need = {s: max(1, math.ceil(skill_hours(s) / hours_per_week)) for s in ranked}

    # keep the highest-priority skills that fit; a skill drags in its unmet prerequisite gaps first
    gap_set = set(ranked)

    def prereq_chain(skill: str, seen: set[str]) -> list[str]:
        out: list[str] = []
        for p in SKILLS.get(skill, {}).get("prereqs", []):
            if p in gap_set and p not in seen:
                seen.add(p)
                out += prereq_chain(p, seen) + [p]
        return out

    selected: list[str] = []
    used = 0
    for s in ranked:
        if s in selected:
            continue
        deps = [d for d in dict.fromkeys(prereq_chain(s, {s})) if d not in selected]
        cost = sum(need[d] for d in deps) + need[s]
        if used + cost <= available:
            selected += deps + [s]
            used += cost
    dropped = [s for s in ranked if s not in selected]
    # spare weeks go to the top-priority skills (deeper practice), capped at 2x
    spare = available - used
    alloc = dict(need)
    i = 0
    while spare > 0 and selected:
        s = selected[i % len(selected)]
        if alloc[s] < need[s] * 2:
            alloc[s] += 1
            spare -= 1
        i += 1
        if i > len(selected) * 3:
            break

    order = _topo_order(selected, rank)
    plan, week = [], 1
    for s in order:
        span = alloc[s]
        start, end = week, week + span - 1
        plan.append({
            "weeks": f"{start}" if start == end else f"{start}-{end}",
            "start_week": start, "end_week": end, "focus": s,
            "skills": [s], "estimated_hours": skill_hours(s),
            "tasks": _tasks(s),
            "resources": (resources or {}).get(s, []),
        })
        week = end + 1
    cap_start = week
    plan.append({
        "weeks": f"{cap_start}" if reserve == 1 else f"{cap_start}-{cap_start + reserve - 1}",
        "start_week": cap_start, "end_week": cap_start + reserve - 1,
        "focus": "Capstone project + interview preparation",
        "skills": order[:3], "estimated_hours": reserve * hours_per_week,
        "tasks": [f"Build one deployed end-to-end {role} project using the new skills",
                  "Update your resume with the new project and keywords",
                  "Run mock interviews and fix weak answers",
                  "Apply to 5-10 matching roles and track them"],
        "resources": [],
    })
    return {"target_role": role, "total_weeks": cap_start + reserve - 1, "hours_per_week": hours_per_week,
            "skills_covered": order, "skills_deferred": dropped, "milestones": plan}
