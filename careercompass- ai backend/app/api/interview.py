from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.interview_agent import InterviewAgent
from app.core.deps import get_current_user
from app.db.models import InterviewSession, User
from app.db.session import get_db
from app.schemas import AnswerIn, InterviewStartIn

router = APIRouter(prefix="/interview", tags=["interview"])


def _session_or_404(agent: InterviewAgent, user: User, session_id: int) -> InterviewSession:
    s = agent.get(user.id, session_id)
    if not s:
        raise HTTPException(404, "Interview session not found")
    return s


@router.post("/start", status_code=201)
def start(body: InterviewStartIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = InterviewAgent(db)
    s = agent.start_session(user.id, body.target_role, body.job_id, body.n_questions)
    return {"session_id": s.id, "target_role": s.target_role, "total_questions": len(s.questions),
            "first_question": agent.public_question(s, 0)}


@router.post("/{session_id}/answer")
def answer(session_id: int, body: AnswerIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = InterviewAgent(db)
    s = _session_or_404(agent, user, session_id)
    if s.status != "active":
        raise HTTPException(409, "This session is already finished")
    return agent.submit_answer(s, body.answer)


@router.post("/{session_id}/finish")
def finish(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = InterviewAgent(db)
    s = _session_or_404(agent, user, session_id)
    result = agent.finish(s)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/{session_id}")
def get_session(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _session_or_404(InterviewAgent(db), user, session_id)
    return {"id": s.id, "target_role": s.target_role, "status": s.status, "questions": s.questions,
            "answers": s.answers, "overall": s.overall, "created_at": s.created_at.isoformat()}


@router.get("")
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(InterviewSession).where(InterviewSession.user_id == user.id)
                      .order_by(InterviewSession.id.desc())).all()
    return [{"id": s.id, "target_role": s.target_role, "status": s.status,
             "overall": (s.overall or {}).get("overall"), "created_at": s.created_at.isoformat()} for s in rows]
