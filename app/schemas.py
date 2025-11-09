from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Any
from datetime import datetime

# ==================
# Job Schemas
# ==================

class JobBase(BaseModel):
    title: str
    description_text: str

class JobCreate(JobBase):
    pass

class Job(JobBase):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    status: str
    created_at: datetime
    requirements_structured: Optional[dict[str, Any]] = None
    
# ==================
# Candidate Schemas
# ==================

class CandidateBase(BaseModel):
    name: str
    email: EmailStr

class CandidateCreate(CandidateBase):
    # This is used internally by crud.py
    job_id: int

class Candidate(CandidateBase):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: int
    job_id: int
    fit_score: Optional[float] = None
    created_at: datetime
    resume_raw_text: Optional[str] = None
    skills_parsed: Optional[dict[str, Any]] = None

class PendingInterviewBase(BaseModel):
    summary: str
    proposed_start_time: datetime
    proposed_end_time: datetime

class PendingInterviewCreate(PendingInterviewBase):
    candidate_id: int
    job_id: int

class PendingInterview(PendingInterviewBase):
    model_config = ConfigDict(from_attributes=True)
    
    interview_id: int
    candidate_id: int
    job_id: int
    status: str
    meet_link: Optional[str] = None
    created_at: datetime

class FeedbackBase(BaseModel):
    hr_decision: str  # e.g., "Approved" or "Rejected"
    hr_comments: Optional[str] = None

class FeedbackCreate(FeedbackBase):
    job_id: int
    candidate_id: int
    agent_score: Optional[float] = None

class Feedback(FeedbackBase):
    model_config = ConfigDict(from_attributes=True)
    
    feedback_id: int
    job_id: int
    candidate_id: int
    agent_score: Optional[float] = None
    created_at: datetime