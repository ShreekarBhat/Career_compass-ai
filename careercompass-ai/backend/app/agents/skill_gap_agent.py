"""Skill Gap Agent: current capabilities vs target role requirements, ranked by priority."""
from app.agents.base import BaseAgent
from app.data.taxonomy import resolve_role
from app.ml.role_classifier import predict_roles
from app.profile import engine as profile_engine
from app.tools import skill_gap


class SkillGapAgent(BaseAgent):
    name = "skill_gap"

    def run(self, state) -> dict:
        profile = self.profile(state)
        role = resolve_role(self.target_role(state, profile))
        note = None
        if not role:
            guess = predict_roles(profile_engine.effective_skills(profile))
            role = guess[0]["role"] if guess else "Software Engineer"
            note = f"No (known) target role set, so I used the closest match to your skills: {role}."
        text = skill_gap.latest_resume_text(self.db, state["user_id"])
        gap = skill_gap.compute_gap(self.db, state["user_id"], profile, role, text)
        if note:
            gap["note"] = note
        return gap
