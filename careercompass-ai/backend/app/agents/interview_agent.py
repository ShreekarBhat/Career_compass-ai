"""AI Interview Agent: personalised multi-round interview, answer scoring, follow-ups."""
import random

from sqlalchemy import select

from app.agents.base import BaseAgent
from app.ai.llm import llm
from app.core.sanitize import wrap_untrusted
from app.data.taxonomy import resolve_role
from app.db.models import InterviewSession, Job
from app.profile import engine as profile_engine
from app.tools import interview_scoring as sc
from app.tools import skill_gap


class InterviewAgent(BaseAgent):
    name = "interview"

    # ---------------------------------------------------------------- orchestrator entry
    def run(self, state) -> dict:
        opts = state.get("options") or {}
        session = self.start_session(state["user_id"], state.get("target_role"), state.get("job_id"),
                                     int(opts.get("n_questions", 6)))
        return {"session_id": session.id, "target_role": session.target_role, "total_questions": len(session.questions),
                "first_question": self.public_question(session, 0)}

    # ---------------------------------------------------------------- sessions
    def start_session(self, user_id: int, role: str | None, job_id: int | None, n: int = 6) -> InterviewSession:
        n = max(3, min(n, 12))
        profile = profile_engine.get_or_create(self.db, user_id)
        job = self.db.get(Job, job_id) if job_id else None
        role = resolve_role(role) or role or profile.target_role or (job.title if job else None) or "Software Engineer"
        skills = profile_engine.effective_skills(profile)
        gap_skills: list[str] = []
        if resolve_role(role):
            g = skill_gap.compute_gap(self.db, user_id, profile, resolve_role(role),
                                      skill_gap.latest_resume_text(self.db, user_id))
            gap_skills = [r["skill"] for r in g.get("strong", [])][:6]  # interview on what the resume claims
        n_tech = max(2, n // 2)
        n_resume = max(1, (n - n_tech) // 2 + (1 if n >= 6 else 0))
        n_beh = max(1, n - n_tech - n_resume)
        questions = None
        if llm.available:
            questions = self._llm_questions(role, job, profile, skills, n_tech, n_resume, n_beh)
        if not questions:
            seed = random.randint(0, 10_000)
            questions = (sc.select_technical(gap_skills or (job.requirements if job else []), skills, n_tech, seed)
                         + sc.resume_questions(profile.projects or [], skills, n_resume)
                         + sc.behavioral_questions(n_beh, seed))
        for i, q in enumerate(questions):
            q["index"] = i
        session = InterviewSession(user_id=user_id, job_id=job_id, target_role=role, questions=questions,
                                   answers=[], status="active")
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def _llm_questions(self, role, job, profile, skills, n_tech, n_resume, n_beh):
        system = ("You are a technical interviewer. Create interview questions tailored to the candidate. "
                  'Return JSON {"questions":[{"round":"Technical|Resume-based|Behavioral","question":str,"expected_points":[str]}]}. '
                  f"Exactly {n_tech} Technical, {n_resume} Resume-based, {n_beh} Behavioral. expected_points: 4-7 short lowercase keywords.")
        projects = "; ".join(p.get("title", "") for p in (profile.projects or [])[:4])
        user = (f"Target role: {role}\nCandidate skills: {', '.join(skills[:25])}\nProjects: {projects}\n"
                f"{wrap_untrusted('JOB', job.description, 2000) if job else ''}")
        data = llm.json(system, user, max_tokens=1400)
        if not isinstance(data, dict):
            return None
        out = []
        for q in data.get("questions", []):
            if isinstance(q, dict) and q.get("question") and q.get("round") in ("Technical", "Resume-based", "Behavioral"):
                pts = [str(p).lower() for p in q.get("expected_points", []) if isinstance(p, (str, int))][:8]
                out.append({"round": q["round"], "skill": None, "question": str(q["question"])[:500], "expected_points": pts})
        return out if len(out) >= max(3, n_tech) else None

    @staticmethod
    def public_question(session: InterviewSession, idx: int) -> dict | None:
        if idx >= len(session.questions):
            return None
        q = session.questions[idx]
        return {"index": idx, "round": q["round"], "question": q["question"], "total": len(session.questions)}

    # ---------------------------------------------------------------- answers
    def submit_answer(self, session: InterviewSession, answer: str) -> dict:
        idx = len(session.answers)
        if idx >= len(session.questions):
            return {"done": True, "message": "All questions answered. Call /finish for the summary."}
        q = session.questions[idx]
        scores = self._evaluate(q, answer)
        record = {"index": idx, "answer": answer[:4000], **scores}
        session.answers = [*session.answers, record]
        self.db.commit()
        nxt = self.public_question(session, idx + 1)
        return {"evaluation": {k: scores[k] for k in ("technical_knowledge", "communication", "confidence",
                                                      "answer_relevance", "feedback", "follow_up", "overall")},
                "next_question": nxt, "done": nxt is None}

    def _evaluate(self, q: dict, answer: str) -> dict:
        base = sc.heuristic_score(q["question"], answer, q.get("expected_points", []))
        result = {k: base[k] for k in ("technical_knowledge", "communication", "confidence", "answer_relevance", "feedback")}
        result["follow_up"] = None
        if llm.available:
            system = ("You are a strict but fair interviewer scoring a candidate answer. Score each dimension 0-100. "
                      'Return JSON {"technical_knowledge":int,"communication":int,"confidence":int,"answer_relevance":int,'
                      '"feedback":str (2-3 sentences, say what was good and what to add),"follow_up":str}')
            user = (f"Question: {q['question']}\nExpected ideas: {', '.join(q.get('expected_points', []))}\n"
                    f"{wrap_untrusted('ANSWER', answer, 3000)}")
            data = llm.json(system, user, max_tokens=500)
            if isinstance(data, dict):
                try:
                    for k in ("technical_knowledge", "communication", "confidence", "answer_relevance"):
                        result[k] = max(0, min(100, int(data[k])))
                    result["feedback"] = str(data.get("feedback") or result["feedback"])[:800]
                    result["follow_up"] = str(data.get("follow_up") or "")[:300] or None
                except (KeyError, TypeError, ValueError):
                    pass
        if not result["follow_up"] and q.get("expected_points"):
            missing = base["missing_points"][:2]
            if missing:
                result["follow_up"] = f"Can you also explain how {' and '.join(missing)} relate to your answer?"
        result["overall"] = sc.overall_score(result)
        return result

    def finish(self, session: InterviewSession) -> dict:
        answers = session.answers or []
        if not answers:
            return {"error": "No answers submitted yet"}
        avg = lambda key: int(round(sum(a[key] for a in answers) / len(answers)))
        overall = {"technical_knowledge": avg("technical_knowledge"), "communication": avg("communication"),
                   "confidence": avg("confidence"), "answer_relevance": avg("answer_relevance")}
        overall["overall"] = sc.overall_score(overall)
        by_round: dict[str, list[int]] = {}
        for a in answers:
            by_round.setdefault(session.questions[a["index"]]["round"], []).append(a["overall"])
        overall["by_round"] = {k: int(round(sum(v) / len(v))) for k, v in by_round.items()}
        weakest = sorted(answers, key=lambda a: a["overall"])[:2]
        overall["focus_areas"] = [session.questions[a["index"]]["question"] for a in weakest]
        overall["answered"] = len(answers)
        overall["total_questions"] = len(session.questions)
        session.overall, session.status = overall, "finished"
        self.db.commit()
        return overall

    def get(self, user_id: int, session_id: int) -> InterviewSession | None:
        return self.db.scalar(select(InterviewSession).where(InterviewSession.id == session_id,
                                                              InterviewSession.user_id == user_id))
