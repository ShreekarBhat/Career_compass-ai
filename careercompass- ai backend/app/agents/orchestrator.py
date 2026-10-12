"""Career Manager / Orchestrator (LangGraph).

                route ──► dispatch ──► [agent] ──┐
                            ▲                    │
                            └────────────────────┘      (loop until the plan is empty)
                            │
                            ▼
                         respond ──► END

* `route` understands the request (event trigger or free-form chat) and builds a PLAN (ordered agent list).
* `dispatch` pops the next step; it can re-plan adaptively based on intermediate results.
* every agent is deterministic code that reads/writes the shared state; the LLM never picks tools freely
  (it can only suggest an intent from a fixed allow-list), which is also the prompt-injection defence.
"""
import logging
import re
import time

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.interview_agent import InterviewAgent
from app.agents.job_agent import JobAgent
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.resume_agent import ResumeAgent
from app.agents.skill_gap_agent import SkillGapAgent
from app.agents.state import AgentState
from app.agents.tracker_agent import TrackerAgent
from app.ai.llm import llm
from app.core.sanitize import sanitize_untrusted, wrap_untrusted
from app.core.timeutil import utcnow
from app.data.taxonomy import find_role_in_text
from app.db.models import AgentRun
from app.profile import engine as profile_engine
from app.tools.skill_extractor import extract_skills

logger = logging.getLogger(__name__)

AGENT_NAMES = ["profile_update", "resume", "skill_gap", "job_discovery", "planner", "interview",
               "tracker", "knowledge", "notification"]

INTENT_PLANS: dict[str, list[str]] = {
    "analyze_resume": ["resume"],
    "improve_resume_for_job": ["resume"],
    "find_jobs": ["job_discovery"],
    "skill_gap": ["skill_gap"],
    "roadmap": ["skill_gap", "planner"],
    "skill_update": ["profile_update", "skill_gap", "planner"],
    "set_goal": ["profile_update", "skill_gap", "job_discovery", "planner", "notification"],
    "interview": ["interview"],
    "tracker_summary": ["tracker"],
    "general": ["knowledge"],
    # event-driven pipelines
    "resume_uploaded": ["resume", "skill_gap", "job_discovery", "planner", "notification"],
    "skills_updated": ["skill_gap", "job_discovery", "planner"],
    "scheduled_scan": ["job_discovery", "notification"],
}
ALLOWED_INTENTS = set(INTENT_PLANS)
TRIGGER_INTENT = {"resume_uploaded": "resume_uploaded", "goal_set": "set_goal",
                  "skills_updated": "skills_updated", "scheduled_scan": "scheduled_scan"}

_KNOW = re.compile(r"\b(i (already )?know|i('| a)?m (already )?(comfortable|familiar|proficient) with|i have (already )?learn(ed|t)|"
                   r"i('ve| have) (already )?(studied|completed|mastered)|i can already|i already (use|have))\b", re.I)
_GOAL = re.compile(r"\b(want to (become|be|work as|switch to|transition)|my goal is|aspire to|aim(ing)? to (become|be)|"
                   r"target role|become an?|switch(ing)? (careers? )?to|looking to become)\b", re.I)


def classify_intent(message: str) -> tuple[str, str]:
    """Rule-based intent detection. Returns (intent, confidence)."""
    m = message.lower()
    role = find_role_in_text(m)
    if _KNOW.search(message) and extract_skills(message):
        return "skill_update", "high"
    if _GOAL.search(message) and role:
        return "set_goal", "high"
    # Application-tracking questions that merely mention "interview" (e.g. conversion rate) go to the tracker.
    if re.search(r"\b(conversion rate|how many applications|applications? (have i|did i)|application (status|stats|statistics))\b", m):
        return "tracker_summary", "high"
    if re.search(r"\b(interview|mock)\b", m):
        return "interview", "high"
    if re.search(r"\b(resume|cv|ats)\b", m):
        return "improve_resume_for_job" if re.search(r"\b(for (this|that|the) job|tailor|target)\b", m) else "analyze_resume", "high"
    if re.search(r"\b(skill gap|skills gap|missing skills?|what am i missing|gap analysis|what skills|skills? (do )?i (lack|need)|what do i lack)\b", m):
        return "skill_gap", "high"
    if re.search(r"\b(roadmap|study plan|learning (path|plan)|learning roadmap|road map|plan for me)\b", m):
        return "roadmap", "high"
    if re.search(r"\b(applications?|tracker|applied|my status|conversion rate)\b", m):
        return "tracker_summary", "medium"
    if re.search(r"\b(jobs?|openings?|internships?|vacanc(y|ies)|hiring|positions?|opportunit(y|ies))\b", m):
        return "find_jobs", "medium"
    if role:
        return "set_goal", "low"
    return "general", "low"


class Orchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.agents = {
            "resume": ResumeAgent(db), "skill_gap": SkillGapAgent(db), "job_discovery": JobAgent(db),
            "planner": PlannerAgent(db), "interview": InterviewAgent(db), "tracker": TrackerAgent(db),
            "knowledge": KnowledgeAgent(db), "notification": NotificationAgent(db),
        }
        self.graph = self._build()

    # ------------------------------------------------------------------ graph
    def _build(self):
        g = StateGraph(AgentState)
        g.add_node("route", self._route)
        g.add_node("dispatch", self._dispatch)
        g.add_node("respond", self._respond)
        for name in AGENT_NAMES:
            g.add_node(name, self._wrap(name))
        g.set_entry_point("route")
        g.add_edge("route", "dispatch")
        g.add_conditional_edges("dispatch", lambda s: s.get("current") or "respond",
                                {**{n: n for n in AGENT_NAMES}, "respond": "respond"})
        for name in AGENT_NAMES:
            g.add_edge(name, "dispatch")
        g.add_edge("respond", END)
        return g.compile()

    def _wrap(self, name: str):
        def node(state: AgentState) -> dict:
            t0 = time.perf_counter()
            step = {"agent": name}
            try:
                out = self._profile_update(state) if name == "profile_update" else self.agents[name].run(state)
                step["ok"] = True
            except Exception as exc:  # one failing agent must not take the whole run down
                logger.exception("Agent %s failed", name)
                self.db.rollback()
                out, step["ok"], step["error"] = {"error": str(exc)[:300]}, False, str(exc)[:300]
            step["ms"] = int((time.perf_counter() - t0) * 1000)
            return {"results": {**state.get("results", {}), name: out},
                    "done": [*state.get("done", []), name],
                    "trace": [*state.get("trace", []), step], "current": None}
        return node

    # ------------------------------------------------------------------ nodes
    def _profile_update(self, state: AgentState) -> dict:
        out: dict = {}
        uid = state["user_id"]
        if state.get("target_role"):
            p = profile_engine.update_preferences(self.db, uid, {"target_role": state["target_role"]})
            out["target_role"] = p.target_role
        if state.get("known_skills"):
            out["declared_skills_added"] = profile_engine.declare_skills(self.db, uid, state["known_skills"])
            out["declared_skills"] = state["known_skills"]
        return out

    def _route(self, state: AgentState) -> dict:
        trigger = state.get("trigger", "chat")
        message, flagged = sanitize_untrusted(state.get("message", ""), 2000)
        update: dict = {"message": message, "flagged_injection": bool(flagged)}
        opts = state.get("options") or {}

        if trigger in TRIGGER_INTENT:
            intent, conf = TRIGGER_INTENT[trigger], "high"
        elif trigger == "api" and opts.get("intent") in ALLOWED_INTENTS:
            intent, conf = opts["intent"], "high"
        else:
            intent, conf = classify_intent(message)
            if intent == "general" and conf == "low" and llm.available and message:
                intent = self._llm_intent(message) or intent  # allow-list validated

        role = state.get("target_role") or find_role_in_text(message)
        known = list(state.get("known_skills") or [])
        if intent == "skill_update" and not known:
            known = extract_skills(message)
        if intent == "set_goal" and not role:
            intent = "general"
        update.update(intent=intent, target_role=role, known_skills=known,
                      plan=list(INTENT_PLANS[intent]), done=[], results={}, events=[], trace=[], current=None)
        if intent in ("analyze_resume", "improve_resume_for_job") and (state.get("job_id") or state.get("job_description")):
            update["intent"] = "improve_resume_for_job"
        return update

    @staticmethod
    def _llm_intent(message: str) -> str | None:
        system = ("Classify the user's career request into exactly one intent from: "
                  + ", ".join(sorted(ALLOWED_INTENTS - {"resume_uploaded", "skills_updated", "scheduled_scan"}))
                  + '. Return JSON {"intent": "<one of them>"}')
        data = llm.json(system, wrap_untrusted("MESSAGE", message, 1000), max_tokens=60)
        intent = data.get("intent") if isinstance(data, dict) else None
        return intent if intent in ALLOWED_INTENTS else None

    def _dispatch(self, state: AgentState) -> dict:
        plan, done, results = list(state.get("plan", [])), state.get("done", []), state.get("results", {})
        events = list(state.get("events", []))
        jd = results.get("job_discovery")
        # adaptive re-planning: weak job matches -> make sure a learning plan is produced
        if (jd and jd.get("top_score", 100) < 50 and "skill_gap" in done
                and "planner" not in plan and "planner" not in done):
            plan.insert(0, "planner")
            events.append("replan: top job match < 50%, adding roadmap step")
        # nothing to analyse without a resume: skip downstream resume-dependent notification noise
        nxt = plan.pop(0) if plan else None
        return {"plan": plan, "current": nxt, "events": events}

    def _respond(self, state: AgentState) -> dict:
        draft = compose_response(state)
        results = state.get("results", {})
        if (llm.available and draft and state.get("intent") not in ("interview",) and "knowledge" not in results):
            polished = llm.chat(
                "You are CareerCompass, a friendly, concise career coach. Rewrite the DRAFT as a clear reply (max ~180 words). "
                "Keep every number, role, skill and job name EXACTLY as in the draft. Do not add facts.",
                f"DRAFT:\n{draft}", temperature=0.4, max_tokens=500)
            if polished:
                draft = polished
        return {"response": draft}

    # ------------------------------------------------------------------ public API
    def handle(self, user_id: int, trigger: str = "chat", message: str = "", **options) -> dict:
        t0 = time.perf_counter()
        init: AgentState = {
            "user_id": user_id, "trigger": trigger, "message": message,
            "target_role": options.pop("target_role", None), "known_skills": options.pop("known_skills", []),
            "job_id": options.pop("job_id", None), "job_description": options.pop("job_description", None),
            "options": options,
        }
        final = self.graph.invoke(init, {"recursion_limit": 40})
        latency = int((time.perf_counter() - t0) * 1000)
        trace = final.get("trace", [])
        run = AgentRun(user_id=user_id, trigger=trigger, message=(message or "")[:2000], intent=final.get("intent"),
                       plan=INTENT_PLANS.get(final.get("intent", ""), []), steps=trace,
                       success=all(s.get("ok") for s in trace), flagged_injection=bool(final.get("flagged_injection")),
                       latency_ms=latency, created_at=utcnow())
        self.db.add(run)
        self.db.commit()
        return {"run_id": run.id, "intent": final.get("intent"), "response": final.get("response", ""),
                "steps": trace, "events": final.get("events", []), "results": final.get("results", {}),
                "latency_ms": latency, "flagged_injection": bool(final.get("flagged_injection"))}


# ---------------------------------------------------------------------- response composition (deterministic)
def compose_response(state: AgentState) -> str:
    r = state.get("results", {})
    parts: list[str] = []
    if state.get("flagged_injection"):
        parts.append("Note: I ignored instruction-like text in your message and treated it as plain content.")

    pu = r.get("profile_update")
    if pu and not pu.get("error"):
        bits = []
        if pu.get("target_role"):
            bits.append(f"target role set to {pu['target_role']}")
        if pu.get("declared_skills"):
            bits.append(f"noted that you know {', '.join(pu['declared_skills'])}")
        if bits:
            parts.append("Profile updated: " + "; ".join(bits) + ".")

    rs = r.get("resume")
    if rs:
        if rs.get("status") == "no_resume":
            parts.append(rs["message"])
        elif rs.get("status") == "ok":
            tag = f"for {rs['job_title']}" if rs.get("targeted") and rs.get("job_title") else (f"for {rs['role']}" if rs.get("role") else "")
            probs = [p["issue"] for p in rs["analysis"]["problems"][:3]]
            parts.append(f"Your resume scores {rs['ats_score']}/100 {tag}.".replace(" .", ".")
                         + (" Top issues: " + "; ".join(probs) + "." if probs else ""))

    gap = r.get("skill_gap")
    if gap and not gap.get("error"):
        strong = ", ".join(s["skill"] for s in gap["strong"][:5]) or "none yet"
        miss = ", ".join(m["skill"] for m in gap["missing"][:5]) or "none"
        parts.append(f"Your profile matches about {gap['overall_match_pct']}% of typical {gap['target_role']} requirements. "
                     f"Strong: {strong}. Priority gaps: {miss}."
                     + (" " + " ".join(gap["insights"][:2]) if gap.get("insights") else "")
                     + (f" {gap['note']}" if gap.get("note") else ""))

    jd = r.get("job_discovery")
    if jd and jd.get("jobs"):
        top = "; ".join(f"{j['title']} at {j['company'] or 'n/a'} ({j['match']}%)" for j in jd["jobs"][:3])
        parts.append(f"Top job matches: {top}.")
    elif jd is not None and not jd.get("error"):
        parts.append("I couldn't find matching jobs yet. Try setting a target role or enabling more job sources.")

    pl = r.get("planner")
    if pl and pl.get("status") == "ok":
        rm = pl["roadmap"]
        weeks = "; ".join(f"Week {m['weeks']}: {m['focus']}" for m in rm["milestones"][:4])
        parts.append(f"I built a {rm['total_weeks']}-week {rm['target_role']} roadmap (v{pl['version']}). {weeks}...")
    elif pl and pl.get("status") == "no_gaps":
        parts.append(pl["message"])

    iv = r.get("interview")
    if iv and iv.get("first_question"):
        q = iv["first_question"]
        parts.append(f"Mock interview ready ({iv['total_questions']} questions, session {iv['session_id']}). "
                     f"Round 1 - {q['round']}: {q['question']}")

    tr = r.get("tracker")
    if tr:
        parts.append(" ".join(tr["insights"]) if tr.get("insights") else "No applications tracked yet.")

    kn = r.get("knowledge")
    if kn:
        parts.append(kn["answer"])

    for name, out in r.items():
        if isinstance(out, dict) and out.get("error") and name != "skill_gap":
            parts.append(f"(The {name.replace('_', ' ')} step hit a problem and was skipped.)")
    return "\n\n".join(parts) if parts else "I'm not sure how to help with that yet. Try asking about your resume, jobs, skill gaps, roadmap or interview practice."
