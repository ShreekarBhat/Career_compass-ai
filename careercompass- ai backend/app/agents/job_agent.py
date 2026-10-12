"""Job Discovery Agent: fetch -> extract requirements -> embed -> match -> rank -> explain."""
from sqlalchemy import select

from app.agents.base import BaseAgent
from app.ai.embeddings import embedder
from app.ai.llm import llm
from app.data.taxonomy import ROLES
from app.db.models import Job
from app.profile import engine as profile_engine
from app.tools import job_store
from app.tools.matcher import compute_match, explain_match


class JobAgent(BaseAgent):
    name = "job_discovery"

    def run(self, state) -> dict:
        opts = state.get("options") or {}
        profile = self.profile(state)
        role = self.target_role(state, profile)
        limit = int(opts.get("limit", 10))
        min_score = int(opts.get("min_score", 0))

        queries = [q for q in [role, *(profile.preferred_roles or [])[:2]] if q]
        refresh = bool(opts.get("refresh", state.get("trigger") in ("resume_uploaded", "goal_set", "scheduled_scan")))
        fetch_info = {"added": 0}
        if refresh or not self.db.scalar(select(Job.id).limit(1)):
            location = (profile.preferred_locations or [""])[0]
            fetch_info = job_store.refresh_jobs(self.db, queries, location, force=bool(opts.get("force_refresh")))
        else:
            job_store.ensure_seed_jobs(self.db)

        skills = profile_engine.effective_skills(profile)
        if profile.embedding is not None:
            qvec = profile.embedding
        else:
            qtext = f"{role or ''}. {ROLES[role]['description'] if role in ROLES else ''} Skills: {', '.join(skills)}"
            qvec = embedder.embed_one(qtext)

        matches = self._rank(profile, skills, qvec, role, limit * 4)
        ranked = [m for m in matches if m["match"]["score"] >= min_score][:limit]
        self._explain(ranked)
        return {
            "role": role, "count": len(ranked), "fetched": fetch_info,
            "top_score": ranked[0]["match"]["score"] if ranked else 0,
            "jobs": [self.public(m) for m in ranked],
        }

    def _rank(self, profile, skills, qvec, role, k: int) -> list[dict]:
        out = []
        for job, sim in job_store.candidate_jobs(self.db, qvec, k=max(k, 60)):
            m = compute_match(skills, job.requirements or [], profile.embedding or qvec, job.embedding,
                              profile.experience_level, job.level, profile.preferred_locations or [],
                              job.location, job.remote)
            out.append({"job": job, "match": m})
        out.sort(key=lambda x: x["match"]["score"], reverse=True)
        return out

    def _explain(self, ranked: list[dict]) -> None:
        for m in ranked:
            j = m["job"]
            m["explanation"] = explain_match(j.title, j.company, m["match"])
        if not (llm.available and ranked):
            return
        facts = [{"id": m["job"].id, "title": m["job"].title, "score": m["match"]["score"],
                  "matched": m["match"]["matched_skills"], "missing": m["match"]["missing_skills"]} for m in ranked[:5]]
        data = llm.json("You explain job matches to a candidate in one friendly sentence each, using ONLY the facts given. "
                        'Return JSON {"explanations":[{"id":int,"text":str}]}', str(facts), max_tokens=700)
        if isinstance(data, dict):
            by_id = {e.get("id"): e.get("text") for e in data.get("explanations", []) if isinstance(e, dict)}
            for m in ranked:
                if by_id.get(m["job"].id):
                    m["explanation"] = str(by_id[m["job"].id])[:400]

    @staticmethod
    def public(m: dict) -> dict:
        j, mt = m["job"], m["match"]
        return {"job_id": j.id, "title": j.title, "company": j.company, "location": j.location, "remote": j.remote,
                "url": j.url, "source": j.source, "level": j.level, "match": mt["score"],
                "matched_skills": mt["matched_skills"], "missing_skills": mt["missing_skills"],
                "partial_skills": mt["partial_skills"], "semantic_pct": mt["semantic_pct"],
                "explanation": m.get("explanation")}
