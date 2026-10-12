from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class ProfileUpdateIn(BaseModel):
    target_role: str | None = Field(default=None, max_length=120)
    career_goal: str | None = Field(default=None, max_length=1000)
    preferred_roles: list[str] | None = None
    preferred_locations: list[str] | None = None
    experience_level: str | None = None
    salary_preference: str | None = Field(default=None, max_length=64)


class SkillsIn(BaseModel):
    skills: list[str] = Field(min_length=1, max_length=40)


class TailorIn(BaseModel):
    job_id: int | None = None
    job_description: str | None = Field(default=None, max_length=8000)


class DiscoverIn(BaseModel):
    refresh: bool = True
    limit: int = Field(default=10, ge=1, le=30)
    min_score: int = Field(default=0, ge=0, le=100)


class JobIn(BaseModel):
    title: str = Field(max_length=255)
    company: str = Field(default="", max_length=255)
    location: str = Field(default="", max_length=255)
    remote: bool = False
    description: str = Field(max_length=10000)
    url: str | None = None


class RoadmapIn(BaseModel):
    target_role: str | None = None
    weeks: int = Field(default=12, ge=4, le=26)
    hours_per_week: int = Field(default=10, ge=3, le=60)


class RoadmapAdjustIn(BaseModel):
    known_skills: list[str] = Field(min_length=1, max_length=40)
    weeks: int = Field(default=12, ge=4, le=26)
    hours_per_week: int = Field(default=10, ge=3, le=60)


class InterviewStartIn(BaseModel):
    target_role: str | None = None
    job_id: int | None = None
    n_questions: int = Field(default=6, ge=3, le=12)


class AnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)


class ApplicationIn(BaseModel):
    company: str = Field(max_length=255)
    role: str = Field(max_length=255)
    job_id: int | None = None
    url: str | None = None
    match_score: int | None = Field(default=None, ge=0, le=100)
    status: str = "saved"
    applied_on: date | None = None
    deadline: datetime | None = None
    interview_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)


class ApplicationUpdateIn(BaseModel):
    company: str | None = None
    role: str | None = None
    url: str | None = None
    match_score: int | None = Field(default=None, ge=0, le=100)
    status: str | None = None
    applied_on: date | None = None
    deadline: datetime | None = None
    interview_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)


class TelegramIn(BaseModel):
    chat_id: str = Field(min_length=1, max_length=64)


class AgentChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    job_id: int | None = None
    job_description: str | None = Field(default=None, max_length=8000)
