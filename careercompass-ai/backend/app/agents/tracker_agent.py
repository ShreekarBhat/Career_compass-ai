from app.agents.base import BaseAgent
from app.tools import tracker


class TrackerAgent(BaseAgent):
    name = "tracker"

    def run(self, state) -> dict:
        return tracker.analytics(self.db, state["user_id"])
