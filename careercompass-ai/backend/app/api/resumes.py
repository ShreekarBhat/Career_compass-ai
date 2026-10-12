from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.core.deps import get_current_user
from app.db.models import Resume, User
from app.db.session import get_db
from app.schemas import TailorIn
from app.tools.resume_parser import extract_text

router = APIRouter(prefix="/resumes", tags=["resume"])


@router.post("", status_code=201)
async def upload_resume(file: UploadFile = File(...), user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Upload a PDF/DOCX/TXT resume. Fires the `resume_uploaded` event: the orchestrator then runs
    Resume -> Skill Gap -> Job Discovery -> Planner -> Notification agents."""
    data = await file.read()
    text = extract_text(file.filename or "resume", data)
    db.execute(update(Resume).where(Resume.user_id == user.id).values(is_active=False))
    resume = Resume(user_id=user.id, filename=(file.filename or "resume")[:255], text=text, is_active=True)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    run = Orchestrator(db).handle(user.id, "resume_uploaded")
    return {"resume_id": resume.id, "filename": resume.filename, "run_id": run["run_id"], "response": run["response"],
            "steps": run["steps"], "results": run["results"]}


@router.get("")
def list_resumes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.id.desc())).all()
    return [{"id": r.id, "filename": r.filename, "ats_score": r.ats_score, "is_active": r.is_active,
             "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/{resume_id}")
def get_resume(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.scalar(select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id))
    if not r:
        raise HTTPException(404, "Resume not found")
    return {"id": r.id, "filename": r.filename, "ats_score": r.ats_score, "analysis": r.analysis,
            "text": r.text, "is_active": r.is_active, "created_at": r.created_at.isoformat()}


@router.post("/analyze")
def reanalyze(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = Orchestrator(db).handle(user.id, "api", intent="analyze_resume")
    return run["results"].get("resume", {}) | {"run_id": run["run_id"]}


@router.post("/tailor")
def tailor_for_job(body: TailorIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """'Improve my resume for this particular job.'"""
    if not (body.job_id or body.job_description):
        raise HTTPException(422, "Provide job_id or job_description")
    run = Orchestrator(db).handle(user.id, "api", intent="improve_resume_for_job", job_id=body.job_id,
                                  job_description=body.job_description)
    return run["results"].get("resume", {}) | {"run_id": run["run_id"]}
