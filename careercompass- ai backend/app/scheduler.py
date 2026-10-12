"""Background jobs (APScheduler). Enable with SCHEDULER_ENABLED=true."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.agents.notification_agent import NotificationAgent
from app.agents.orchestrator import Orchestrator
from app.db.models import CareerProfile
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def reminder_job() -> None:
    with SessionLocal() as db:
        n = NotificationAgent(db).deadline_and_interview_reminders()
        if n:
            logger.info("Sent %s reminders", n)


def job_scan() -> None:
    """Daily: re-scan jobs for every user with a target role and alert on high matches."""
    with SessionLocal() as db:
        user_ids = db.scalars(select(CareerProfile.user_id).where(CareerProfile.target_role.is_not(None))).all()
        for uid in user_ids:
            try:
                Orchestrator(db).handle(uid, "scheduled_scan")
            except Exception:
                logger.exception("Scheduled scan failed for user %s", uid)


def start() -> None:
    global _scheduler
    if _scheduler:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(reminder_job, "interval", minutes=15, id="reminders", max_instances=1, coalesce=True)
    _scheduler.add_job(job_scan, "cron", hour=3, minute=30, id="job_scan", max_instances=1, coalesce=True)
    _scheduler.start()
    logger.info("Scheduler started")


def stop() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
