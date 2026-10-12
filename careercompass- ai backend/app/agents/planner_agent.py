"""Career Planner Agent: turns prioritised skill gaps into an adaptive roadmap and stores it."""
from sqlalchemy import select, update

from app.agents.base import BaseAgent
from app.agents.skill_gap_agent import SkillGapAgent
from app.db.models import Roadmap
from app.rag.retriever import resources_for_skill
from app.tools.roadmap_builder import build_roadmap


class PlannerAgent(BaseAgent):
    name = "planner"

    def run(self, state) -> dict:
        opts = state.get("options") or {}
        gap = (state.get("results") or {}).get("skill_gap")
        if not gap or gap.get("error"):
            gap = SkillGapAgent(self.db).run(state)
        role = gap["target_role"]
        missing = gap["missing"]
        if not missing:
            return {"status": "no_gaps", "message": f"You already cover the core {role} skills. Focus on projects and interviews.",
                    "target_role": role}
        resources = {m["skill"]: resources_for_skill(self.db, m["skill"]) for m in missing[:12]}
        plan = build_roadmap(role, missing, weeks=int(opts.get("weeks", 12)),
                             hours_per_week=int(opts.get("hours_per_week", 10)), resources=resources)
        prev = self.db.scalar(select(Roadmap).where(Roadmap.user_id == state["user_id"]).order_by(Roadmap.version.desc()))
        version = (prev.version + 1) if prev else 1
        self.db.execute(update(Roadmap).where(Roadmap.user_id == state["user_id"]).values(is_active=False))
        row = Roadmap(user_id=state["user_id"], target_role=role, plan=plan, version=version, is_active=True)
        self.db.add(row)
        self.db.commit()
        return {"status": "ok", "roadmap_id": row.id, "version": version, "roadmap": plan,
                "reason": state.get("trigger")}
