"""Resume Intelligence Agent: parse -> ATS analysis -> profile update -> (optional) job-targeted plan."""
from sqlalchemy import select

from app.agents.base import BaseAgent
from app.ai.llm import llm
from app.core.sanitize import sanitize_untrusted, wrap_untrusted
from app.db.models import Job
from app.profile import engine as profile_engine
from app.tools import ats
from app.tools.skill_extractor import extract_skills


class ResumeAgent(BaseAgent):
    name = "resume"

    def run(self, state) -> dict:
        resume = self.latest_resume(state)
        if resume is None:
            return {"status": "no_resume", "message": "Upload a resume first so I can analyse it."}
        profile = self.profile(state)
        role = self.target_role(state, profile)

        job_desc, job_title, job = state.get("job_description"), None, None
        if state.get("job_id"):
            job = self.db.get(Job, state["job_id"])
            if job:
                job_desc, job_title = job.description, job.title
        targeted = bool(job_desc)

        analysis = ats.analyze_resume(resume.text, role=role, job_description=job_desc,
                                      job_skills=(job.requirements or None) if job else None)
        out = {"status": "ok", "resume_id": resume.id, "role": role, "ats_score": analysis["ats_score"],
               "analysis": analysis, "targeted": targeted, "job_title": job_title}

        if not targeted:
            resume.ats_score, resume.analysis = analysis["ats_score"], analysis
            self.db.commit()
            if state.get("trigger") in ("resume_uploaded", "chat", "api") or not profile.skills:
                profile = profile_engine.update_from_resume(self.db, state["user_id"], resume.text)
            out["profile_skills"] = profile.skills
            out["suggested_roles"] = self._suggest_roles(profile)
        else:
            out["targeted_plan"] = self._targeted_plan(resume.text, job_desc, analysis)
        out["ai_suggestions"] = self._llm_rewrites(resume.text, analysis, job_desc, role)
        return out

    @staticmethod
    def _suggest_roles(profile) -> list[dict]:
        from app.ml.role_classifier import predict_roles
        return predict_roles(profile_engine.effective_skills(profile))[:3]

    @staticmethod
    def _targeted_plan(resume_text: str, job_desc: str, analysis: dict) -> dict:
        missing = analysis["missing_keywords"]
        steps = [f"Add '{k}' to your Skills section and to a project bullet, only if you have genuinely used it." for k in missing[:6]]
        steps.append("Mirror the job's wording for tools you already know (e.g. use the exact tool names from the posting).")
        steps.append("Move the most relevant project to the top and add a measurable result to it.")
        learn = [k for k in missing[:6]]
        return {"keywords_to_add_if_true": missing[:8], "action_steps": steps,
                "consider_learning": learn[:4], "job_keywords": extract_skills(job_desc)[:15]}

    def _llm_rewrites(self, resume_text: str, analysis: dict, job_desc: str | None, role: str | None):
        if not llm.available:
            return None
        weak = analysis.get("weak_statements") or []
        if not weak:
            return None
        system = ("You are a resume coach. Rewrite weak resume bullets to be specific and impact-oriented. "
                  "NEVER invent employers, tools, results or numbers; where a metric is needed use a placeholder like [X%]. "
                  'Return JSON: {"rewrites":[{"original":str,"improved":str}]}')
        user = (f"Target: {role or 'general'}\n"
                f"{wrap_untrusted('BULLETS', chr(10).join(weak[:4]), 2000)}\n"
                f"{wrap_untrusted('JOB', job_desc or '', 2500) if job_desc else ''}")
        data = llm.json(system, user, max_tokens=700)
        if isinstance(data, dict) and isinstance(data.get("rewrites"), list):
            return [r for r in data["rewrites"] if isinstance(r, dict) and r.get("improved")][:4]
        return None
