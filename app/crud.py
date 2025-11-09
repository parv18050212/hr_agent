from sqlalchemy.orm import Session
from sqlalchemy import func, text
from . import models, schemas
from .parsing import get_job_parser_chain, get_resume_parser_chain
from langchain_google_genai import GoogleGenerativeAIEmbeddings # <-- Use Google
import numpy as np
from .config import settings

# Load the embedding model ONCE when the app starts
embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=settings.GOOGLE_API_KEY.get_secret_value()  # <--- 2. ADD THIS LINE
)

def _create_embedding(text: str) -> list[float]:
    """Helper function to create an embedding from text."""
    return embedding_model.embed_query(text)

# ==================
# Job CRUD
# ==================

def get_job(db: Session, job_id: int):
    return db.query(models.Job).filter(models.Job.job_id == job_id).first()

def get_jobs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Job).offset(skip).limit(limit).all()

def create_job(db: Session, job: schemas.JobCreate):
    """
    Create a new job, parse it, and create its embedding.
    """
    # 1. Parse the job description text
    parser_chain = get_job_parser_chain()
    parsed_data = parser_chain.invoke({"text": job.description_text})
    
    # 2. Create the embedding
    embedding = _create_embedding(job.description_text)
    
    db_job = models.Job(
        title=job.title,
        description_text=job.description_text,
        requirements_structured=parsed_data.dict(), # <-- Save the parsed JSON
        embedding=embedding                         # <-- Save the vector
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

# ==================
# Candidate CRUD
# ==================

def get_candidates_for_job(db: Session, job_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Candidate)\
             .filter(models.Candidate.job_id == job_id)\
             .offset(skip)\
             .limit(limit)\
             .all()

def create_candidate(db: Session, candidate: schemas.CandidateCreate, resume_text: str):
    """
    Create a new candidate, parse resume, create embedding, and calculate fit_score.
    """
    # 1. Get the job we're applying for
    db_job = get_job(db, job_id=candidate.job_id)
    if not db_job or db_job.embedding is None:
        return None # Job or job embedding not found

    # 2. Parse the resume text
    parser_chain = get_resume_parser_chain()
    parsed_data = parser_chain.invoke({"text": resume_text})
    
    # 3. Create the resume embedding
    embedding = _create_embedding(resume_text)
    
    # 4. Calculate the fit_score (Cosine Similarity)
    job_embedding = np.array(db_job.embedding)
    candidate_embedding = np.array(embedding)
    
    # Handle potential zero vectors to avoid division by zero
    norm_job = np.linalg.norm(job_embedding)
    norm_cand = np.linalg.norm(candidate_embedding)
    
    if norm_job == 0 or norm_cand == 0:
        fit_score = 0.0
    else:
        cos_sim = np.dot(job_embedding, candidate_embedding) / (norm_job * norm_cand)
        fit_score = float(cos_sim)

    db_candidate = models.Candidate(
        job_id=candidate.job_id,
        name=candidate.name,
        email=candidate.email,
        resume_raw_text=resume_text,
        skills_parsed=parsed_data.dict(), # <-- Save the parsed JSON
        embedding=embedding,              # <-- Save the vector
        fit_score=fit_score               # <-- Save the score
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate

def get_shortlisted_candidates(db: Session, job_id: int, min_score: float = 0.7):
    """
    Get candidates for a job, ordered by fit_score descending.
    """
    return db.query(models.Candidate)\
             .filter(models.Candidate.job_id == job_id)\
             .filter(models.Candidate.fit_score >= min_score)\
             .order_by(models.Candidate.fit_score.desc())\
             .all()

def create_pending_interview(db: Session, interview: schemas.PendingInterviewCreate):
    db_interview = models.PendingInterview(
        candidate_id=interview.candidate_id,
        job_id=interview.job_id,
        summary=interview.summary,
        proposed_start_time=interview.proposed_start_time,
        proposed_end_time=interview.proposed_end_time,
        status='pending'
    )
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    return db_interview

def get_pending_interviews(db: Session):
    return db.query(models.PendingInterview)\
             .filter(models.PendingInterview.status == 'pending')\
             .all()

def get_pending_interview(db: Session, interview_id: int):
    return db.query(models.PendingInterview)\
             .filter(models.PendingInterview.interview_id == interview_id)\
             .first()

def update_interview_status(db: Session, interview_id: int, status: str):
    db_interview = get_pending_interview(db, interview_id)
    if db_interview:
        db_interview.status = status
        db.commit()
        db.refresh(db_interview)
    return db_interview

def update_interview_schedule_details(db: Session, interview_id: int, meet_link: str, status: str = "scheduled"):
    db_interview = get_pending_interview(db, interview_id)
    if db_interview:
        db_interview.status = status
        db_interview.meet_link = meet_link
        db.commit()
        db.refresh(db_interview)
    return db_interview

def get_candidate(db: Session, candidate_id: int):
    return db.query(models.Candidate).filter(models.Candidate.candidate_id == candidate_id).first()


def create_feedback(db: Session, feedback: schemas.FeedbackCreate):
    db_feedback = models.Feedback(
        job_id=feedback.job_id,
        candidate_id=feedback.candidate_id,
        agent_score=feedback.agent_score,
        hr_decision=feedback.hr_decision,
        hr_comments=feedback.hr_comments
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback