"""Notification Agent: turns system events into in-app notifications and Telegram messages."""
from datetime import timedelta

from sqlalchemy import select

from app.agents.base import BaseAgent
from app.core.timeutil import utcnow
from app.db.models import Application, Notification, User
from app.tools.telegram import send_fcm, send_telegram

NEW_JOB_THRESHOLD = 85
ICONS = {"new_job": "🔔", "skill_alert": "🎯", "deadline": "⏰", "interview": "🎤", "resume_feedback": "📄",
         "roadmap_ready": "🗺️", "info": "ℹ️"}


class NotificationAgent(BaseAgent):
    name = "notification"

    # ---------------------------------------------------------------- core
    def notify(self, user_id: int, kind: str, title: str, body: str, payload: dict | None = None,
               dedupe_key: str | None = None) -> Notification | None:
        if dedupe_key:
            dup = self.db.scalar(select(Notification.id).where(Notification.user_id == user_id,
                                                               Notification.dedupe_key == dedupe_key))
            if dup:
                return None
        user = self.db.get(User, user_id)
        n = Notification(user_id=user_id, kind=kind, title=title, body=body, payload=payload or {},
                         dedupe_key=dedupe_key, channel="in_app")
        text = f"{ICONS.get(kind, '')} {title}\n{body}".strip()
        sent = send_telegram(user.telegram_chat_id, text) if user else False
        sent = send_fcm(user.fcm_token, title, body) or sent if user else sent
        n.delivered = bool(sent)
        if sent:
            n.channel = "telegram"
        self.db.add(n)
        self.db.commit()
        return n

    # ---------------------------------------------------------------- from orchestrator results
    def run(self, state) -> dict:
        uid = state["user_id"]
        res = state.get("results") or {}
        created = []

        resume = res.get("resume")
        if resume and resume.get("status") == "ok" and not resume.get("targeted"):
            top = (resume["analysis"].get("problems") or [{}])[0].get("issue", "Looks solid.")
            n = self.notify(uid, "resume_feedback", f"Resume analysed: ATS {resume['ats_score']}/100",
                            f"Top issue: {top}", {"resume_id": resume["resume_id"]},
                            dedupe_key=f"resume:{resume['resume_id']}")
            created.append(n)

        jobs = (res.get("job_discovery") or {}).get("jobs", [])
        for j in jobs:
            if j["match"] >= NEW_JOB_THRESHOLD:
                n = self.notify(uid, "new_job", "New high-match job",
                                f"{j['title']} at {j['company'] or 'a company'} matches your profile at {j['match']}%.",
                                {"job_id": j["job_id"], "match": j["match"]}, dedupe_key=f"job:{j['job_id']}")
                created.append(n)

        gap = res.get("skill_gap") or {}
        for m in (gap.get("missing") or [])[:2]:
            if m["market_frequency_pct"] >= 60:
                n = self.notify(uid, "skill_alert", "Skill gap alert",
                                f"{m['skill']} appears in {m['market_frequency_pct']}% of your reference jobs.",
                                {"skill": m["skill"]}, dedupe_key=f"skill:{m['skill']}:{utcnow().date()}")
                created.append(n)

        plan = res.get("planner") or {}
        if plan.get("status") == "ok":
            rm = plan["roadmap"]
            n = self.notify(uid, "roadmap_ready", "Your roadmap is ready",
                            f"{rm['total_weeks']}-week plan for {rm['target_role']}: {', '.join(rm['skills_covered'][:4])}...",
                            {"roadmap_id": plan["roadmap_id"]}, dedupe_key=f"roadmap:{plan['roadmap_id']}")
            created.append(n)

        created = [c for c in created if c]
        return {"created": len(created), "delivered_external": sum(1 for c in created if c.delivered),
                "kinds": [c.kind for c in created]}

    # ---------------------------------------------------------------- scheduled reminders
    def deadline_and_interview_reminders(self) -> int:
        now = utcnow()
        horizon = now + timedelta(hours=24)
        count = 0
        apps = self.db.scalars(select(Application).where(Application.status.notin_(["offer", "rejected", "withdrawn"]))).all()
        for a in apps:
            if a.deadline and now <= a.deadline <= horizon and a.status in ("saved", "applied"):
                if self.notify(a.user_id, "deadline", "Application reminder",
                               f"Your application deadline for {a.company} ({a.role}) is within 24 hours.",
                               {"application_id": a.id}, dedupe_key=f"deadline:{a.id}:{a.deadline.date()}"):
                    count += 1
            if a.interview_at and now <= a.interview_at <= horizon:
                when = a.interview_at.strftime("%d %b %H:%M UTC")
                if self.notify(a.user_id, "interview", "Interview reminder",
                               f"Your interview with {a.company} is at {when}.",
                               {"application_id": a.id}, dedupe_key=f"interview:{a.id}:{a.interview_at.isoformat()}"):
                    count += 1
        return count
