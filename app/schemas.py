from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Any, List, Dict
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
    job_id: int

class Candidate(CandidateBase):
    model_config = ConfigDict(from_attributes=True)
    candidate_id: int
    job_id: int
    fit_score: Optional[float] = None
    created_at: datetime
    resume_raw_text: Optional[str] = None
    skills_parsed: Optional[dict[str, Any]] = None
    
    # --- NEW FIELDS ---
    deep_analysis_status: Optional[str] = None
    detailed_score: Optional[str] = None

# --- NEW SCHEMA FOR ANALYSIS MODAL ---
class CandidateAnalysis(BaseModel):
    status: Optional[str] = None
    detailed_score: Optional[str] = None
    detailed_validation: Optional[str] = None
    detailed_recommendation: Optional[str] = None
    
# ==================
# Pending Interview Schemas
# ==================
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
    created_at: datetime

# ==================
# Feedback Schemas
# ==================
class FeedbackBase(BaseModel):
    hr_decision: str
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


class ChatMessage(BaseModel):
    role: str # "human" or "ai"
    content: str

class ChatRequest(BaseModel):
    question: str
    chat_history: List[ChatMessage]

class ChatResponse(BaseModel):
    answer: str


class ExamQuestion(BaseModel):
    """A single question, scrubbed of answers."""
    question_text: str
    question_type: str
    options: Optional[List[str]] = None

class CandidateExamData(BaseModel):
    """The data sent to the candidate to take the exam."""
    candidate_exam_id: int
    status: str
    job_title: str
    questions: List[ExamQuestion]

class CandidateExamAnswers(BaseModel):
    """The structure the candidate sends back."""
    answers: Dict[str, Any] # e.g., {"question_1": "answer", "question_5": "option_c"}

class CandidateExamResult(BaseModel):
    """The data HR sees."""
    model_config = ConfigDict(from_attributes=True)
    
    submitted_at: datetime
    job_title: str
    questions: List[ExamQuestion] # The original questions
    answers: Dict[str, Any] # The candidate's answers

class SkillInfo(BaseModel):
    name: str
    category: Optional[str] = None

class ExperienceInfo(BaseModel):
    organization: Optional[str] = None
    title: Optional[str] = None
    years: Optional[str] = None

class EducationInfo(BaseModel):
    degree: Optional[str] = None
    completion_year: Optional[str] = None
    percentage: Optional[str] = None

class CandidateAnalysis(BaseModel):
    """The rich data structure for the Deep Dive modal."""
    status: str
    detailed_score: Optional[str] = None
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Any, List, Dict
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
    job_id: int

class Candidate(CandidateBase):
    model_config = ConfigDict(from_attributes=True)
    candidate_id: int
    job_id: int
    fit_score: Optional[float] = None
    created_at: datetime
    resume_raw_text: Optional[str] = None
    skills_parsed: Optional[dict[str, Any]] = None
    
    # --- NEW FIELDS ---
    deep_analysis_status: Optional[str] = None
    detailed_score: Optional[str] = None

# --- NEW SCHEMA FOR ANALYSIS MODAL ---
class CandidateAnalysis(BaseModel):
    status: Optional[str] = None
    detailed_score: Optional[str] = None
    detailed_validation: Optional[str] = None
    detailed_recommendation: Optional[str] = None
    
# ==================
# Pending Interview Schemas
# ==================
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
    created_at: datetime

# ==================
# Feedback Schemas
# ==================
class FeedbackBase(BaseModel):
    hr_decision: str
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


class ChatMessage(BaseModel):
    role: str # "human" or "ai"
    content: str

class ChatRequest(BaseModel):
    question: str
    chat_history: List[ChatMessage]

class ChatResponse(BaseModel):
    answer: str


class ExamQuestion(BaseModel):
    """A single question, scrubbed of answers."""
    question_text: str
    question_type: str
    options: Optional[List[str]] = None

class CandidateExamData(BaseModel):
    """The data sent to the candidate to take the exam."""
    candidate_exam_id: int
    status: str
    job_title: str
    questions: List[ExamQuestion]

class CandidateExamAnswers(BaseModel):
    """The structure the candidate sends back."""
    answers: Dict[str, Any] # e.g., {"question_1": "answer", "question_5": "option_c"}

class CandidateExamResult(BaseModel):
    """The data HR sees."""
    model_config = ConfigDict(from_attributes=True)
    
    submitted_at: datetime
    job_title: str
    questions: List[ExamQuestion] # The original questions
    answers: Dict[str, Any] # The candidate's answers

class SkillInfo(BaseModel):
    name: str
    category: Optional[str] = None

class ExperienceInfo(BaseModel):
    organization: Optional[str] = None
    title: Optional[str] = None
    years: Optional[str] = None

class EducationInfo(BaseModel):
    degree: Optional[str] = None
    completion_year: Optional[str] = None
    percentage: Optional[str] = None

class CandidateAnalysis(BaseModel):
    """The rich data structure for the Deep Dive modal."""
    status: str
    detailed_score: Optional[str] = None
    detailed_validation: Optional[str] = None
    detailed_recommendation: Optional[str] = None
    
    # These lists explain the "Why"
    similar_skills: List[SkillInfo] = []
    missing_skills: List[SkillInfo] = []
    experiences: List[ExperienceInfo] = []
    education: List[EducationInfo] = []

# ==================
# Analytics Schemas
# ==================

class PipelineMetrics(BaseModel):
    total_candidates: int
    screened: int
    shortlisted: int
    interview_pending: int
    interview_scheduled: int
    offer_sent: int
    rejected: int

class ScoreDistribution(BaseModel):
    range_0_20: int
    range_20_40: int
    range_40_60: int
    range_60_80: int
    range_80_100: int

class JobMetrics(BaseModel):
    total_jobs: int
    open_jobs: int
    closed_jobs: int
    avg_candidates_per_job: float

class DashboardMetrics(BaseModel):
    pipeline: PipelineMetrics
    score_distribution: ScoreDistribution
    job_metrics: JobMetrics