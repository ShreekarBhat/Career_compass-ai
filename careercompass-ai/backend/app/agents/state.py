from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # inputs
    user_id: int
    trigger: str                  # chat | resume_uploaded | goal_set | skills_updated | scheduled_scan | api
    message: str
    options: dict                 # weeks, hours_per_week, refresh, job_id, job_description ...
    # understanding
    intent: str
    target_role: str | None
    known_skills: list
    job_id: int | None
    job_description: str | None
    flagged_injection: bool
    # execution
    plan: list
    current: str | None
    done: list
    results: dict
    events: list
    trace: list
    # output
    response: str
