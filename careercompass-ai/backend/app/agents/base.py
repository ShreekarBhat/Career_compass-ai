from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CareerProfile, Resume, User
from app.profile import engine as profile_engine


class BaseAgent:
    name = "base"

    def __init__(self, db: Session):
        self.db = db

    def user(self, state) -> User:
        return self.db.get(User, state["user_id"])

    def profile(self, state) -> CareerProfile:
        return profile_engine.get_or_create(self.db, state["user_id"])

    def latest_resume(self, state) -> Resume | None:
        return self.db.scalar(select(Resume).where(Resume.user_id == state["user_id"], Resume.is_active.is_(True))
                              .order_by(Resume.id.desc()))

    def target_role(self, state, profile: CareerProfile | None = None) -> str | None:
        profile = profile or self.profile(state)
        return state.get("target_role") or profile.target_role

    def run(self, state) -> dict:  # pragma: no cover
        raise NotImplementedError
