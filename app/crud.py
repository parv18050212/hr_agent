from sqlalchemy.orm import Session
from sqlalchemy import func, text
from . import models, schemas
from .parsing import get_job_parser_chain, get_resume_parser_chain
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import numpy as np
from .config import settings
from .database import SessionLocal # <-- IMPORT FOR BACKGROUND TASK
import secrets
# --- IMPORT THE NEW NIRMAAN SCORER ---
from .nirmaan_scorer import get_detailed_analysis
from typing import Optional, Any, List, Dict
# Load embedding model
embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=settings.GOOGLE_API_KEY.get_secret_value()
)

def _create_embedding(text: str) -> list[float]:
    return embedding_model.embed_query(text)

# ==================
# Job CRUD
# ==================

def get_job(db: Session, job_id: int):
    return db.query(models.Job).filter(models.Job.job_id == job_id).first()

def get_jobs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Job).offset(skip).limit(limit).all()

def create_job(db: Session, job: schemas.JobCreate):
    parser_chain = get_job_parser_chain()
    parsed_data = parser_chain.invoke({"text": job.description_text})
    embedding = _create_embedding(job.description_text)
    
    db_job = models.Job(
        title=job.title,
        description_text=job.description_text,
        requirements_structured=parsed_data.dict(),
        embedding=embedding
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

# ==================
# Candidate CRUD
# ==================

def get_candidate(db: Session, candidate_id: int):
    return db.query(models.Candidate).filter(models.Candidate.candidate_id == candidate_id).first()

def get_candidates_for_job(db: Session, job_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Candidate)\
             .filter(models.Candidate.job_id == job_id)\
             .offset(skip)\
             .limit(limit)\
             .all()

def create_candidate(db: Session, candidate: schemas.CandidateCreate, resume_text: str):
    # 1. Get job
    db_job = get_job(db, job_id=candidate.job_id)
    if not db_job or db_job.embedding is None:
        return None 

    # 2. Parse resume
    parser_chain = get_resume_parser_chain()
    parsed_data = parser_chain.invoke({"text": resume_text})
    
    # 3. Create resume embedding
    embedding = _create_embedding(resume_text)
    
    # 4. Calculate FAST vector fit_score
    job_embedding = np.array(db_job.embedding)
    candidate_embedding = np.array(embedding)
    
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
        skills_parsed=parsed_data.dict(),
        embedding=embedding,
        fit_score=fit_score,
        deep_analysis_status='pending' # Set status for new task
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate

def get_shortlisted_candidates(db: Session, job_id: int, min_score: float = 0.7):
    return db.query(models.Candidate)\
             .filter(models.Candidate.job_id == job_id)\
             .filter(models.Candidate.fit_score >= min_score)\
             .order_by(models.Candidate.fit_score.desc())\
             .all()

# --- NEW FUNCTION FOR DEEP ANALYSIS ---
def run_deep_analysis_task(candidate_id: int, job_id: int):
    """
    BACKGROUND TASK: Runs the slow, detailed Nirmaan.HR scorer.
    """
    print(f"--- [Task] Starting Deep Analysis for Candidate {candidate_id} ---")
    db = SessionLocal()
    try:
        # 1. Get data from DB
        db_candidate = get_candidate(db, candidate_id)
        db_job = get_job(db, job_id)
        
        if not db_candidate or not db_job:
            raise Exception("Candidate or Job not found")

        # 2. Run Nirmaan's detailed scoring logic
        # This is the slow, expensive GPT-4 call
        analysis = get_detailed_analysis(
            resume_text=db_candidate.resume_raw_text,
            job_description_text=db_job.description_text # Send raw text
        )
        
        # 3. Save the detailed results to our database
        if analysis:
            db_candidate.detailed_score = analysis.get('score')
            db_candidate.detailed_validation = analysis.get('validation')
            db_candidate.detailed_recommendation = analysis.get('recommendation')
            db_candidate.deep_analysis_status = 'complete'
            print(f"--- [Task] Deep Analysis for {candidate_id} complete. Score: {analysis.get('score')} ---")
        else:
            db_candidate.deep_analysis_status = 'failed'
            print(f"--- [Task] Deep Analysis for {candidate_id} failed. ---")

        db.commit()
    except Exception as e:
        db_candidate.deep_analysis_status = 'failed'
        db.commit()
        print(f"!!! [Task] Error in deep analysis: {e} !!!")
    finally:
        db.close()

# ==================
# Pending Interview CRUD
# ==================
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

# ==================
# Feedback CRUD
# ==================
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


def create_exam(db: Session, job_id: int, questions: Dict) -> models.Exam:
    """Saves a new set of exam questions."""
    db_exam = models.Exam(job_id=job_id, questions=questions)
    db.add(db_exam)
    db.commit()
    db.refresh(db_exam)
    return db_exam

def get_exam(db: Session, exam_id: int):
    return db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()

def create_candidate_exam(db: Session, candidate_id: int, exam_id: int) -> models.CandidateExam:
    """Creates a unique, secure link for a candidate to take an exam."""
    token = secrets.token_urlsafe(32)
    db_candidate_exam = models.CandidateExam(
        candidate_id=candidate_id,
        exam_id=exam_id,
        access_token=token,
        status='pending'
    )
    db.add(db_candidate_exam)
    db.commit()
    db.refresh(db_candidate_exam)
    return db_candidate_exam

def get_candidate_exam_by_token(db: Session, token: str) -> Optional[models.CandidateExam]:
    """Get an exam by its secure access token."""
    return db.query(models.CandidateExam).filter(models.CandidateExam.access_token == token).first()

def submit_candidate_exam(db: Session, token: str, answers: Dict) -> Optional[models.CandidateExam]:
    """Submits a candidate's answers."""
    db_exam = get_candidate_exam_by_token(db, token)
    if db_exam and db_exam.status == 'pending':
        db_exam.answers = answers
        db_exam.status = 'completed'
        db_exam.submitted_at = func.now()
        db.commit()
        db.refresh(db_exam)
        return db_exam
    return None
# ==================
# Candidate CRUD
# ==================

def get_candidate(db: Session, candidate_id: int):
    return db.query(models.Candidate).filter(models.Candidate.candidate_id == candidate_id).first()

def get_candidates_for_job(db: Session, job_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Candidate)\
             .filter(models.Candidate.job_id == job_id)\
             .offset(skip)\
             .limit(limit)\
             .all()

def create_candidate(db: Session, candidate: schemas.CandidateCreate, resume_text: str):
    # 1. Get job
    db_job = get_job(db, job_id=candidate.job_id)
    if not db_job or db_job.embedding is None:
        return None 

    # 2. Parse resume
    parser_chain = get_resume_parser_chain()
    parsed_data = parser_chain.invoke({"text": resume_text})
    
    # 3. Create resume embedding
    embedding = _create_embedding(resume_text)
    
    # 4. Calculate FAST vector fit_score
    job_embedding = np.array(db_job.embedding)
    candidate_embedding = np.array(embedding)
    
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
        skills_parsed=parsed_data.dict(),
        embedding=embedding,
        fit_score=fit_score,
        deep_analysis_status='pending' # Set status for new task
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate

def get_shortlisted_candidates(db: Session, job_id: int, min_score: float = 0.7):
    return db.query(models.Candidate)\
             .filter(models.Candidate.job_id == job_id)\
             .filter(models.Candidate.fit_score >= min_score)\
             .order_by(models.Candidate.fit_score.desc())\
             .all()

# --- NEW FUNCTION FOR DEEP ANALYSIS ---
def run_deep_analysis_task(candidate_id: int, job_id: int):
    """
    BACKGROUND TASK: Runs the slow, detailed Nirmaan.HR scorer.
    """
    print(f"--- [Task] Starting Deep Analysis for Candidate {candidate_id} ---")
    db = SessionLocal()
    try:
        # 1. Get data from DB
        db_candidate = get_candidate(db, candidate_id)
        db_job = get_job(db, job_id)
        
        if not db_candidate or not db_job:
            raise Exception("Candidate or Job not found")

        # 2. Run Nirmaan's detailed scoring logic
        # This is the slow, expensive GPT-4 call
        analysis = get_detailed_analysis(
            resume_text=db_candidate.resume_raw_text,
            job_description_text=db_job.description_text # Send raw text
        )
        
        # 3. Save the detailed results to our database
        if analysis:
            db_candidate.detailed_score = analysis.get('score')
            db_candidate.detailed_validation = analysis.get('validation')
            db_candidate.detailed_recommendation = analysis.get('recommendation')
            db_candidate.deep_analysis_status = 'complete'
            print(f"--- [Task] Deep Analysis for {candidate_id} complete. Score: {analysis.get('score')} ---")
        else:
            db_candidate.deep_analysis_status = 'failed'
            print(f"--- [Task] Deep Analysis for {candidate_id} failed. ---")

        db.commit()
    except Exception as e:
        db_candidate.deep_analysis_status = 'failed'
        db.commit()
        print(f"!!! [Task] Error in deep analysis: {e} !!!")
    finally:
        db.close()

# ==================
# Pending Interview CRUD
# ==================
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

# ==================
# Feedback CRUD
# ==================
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


def create_exam(db: Session, job_id: int, questions: Dict) -> models.Exam:
    """Saves a new set of exam questions."""
    db_exam = models.Exam(job_id=job_id, questions=questions)
    db.add(db_exam)
    db.commit()
    db.refresh(db_exam)
    return db_exam

def get_exam(db: Session, exam_id: int):
    return db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()

def create_candidate_exam(db: Session, candidate_id: int, exam_id: int) -> models.CandidateExam:
    """Creates a unique, secure link for a candidate to take an exam."""
    token = secrets.token_urlsafe(32)
    db_candidate_exam = models.CandidateExam(
        candidate_id=candidate_id,
        exam_id=exam_id,
        access_token=token,
        status='pending'
    )
    db.add(db_candidate_exam)
    db.commit()
    db.refresh(db_candidate_exam)
    return db_candidate_exam

def get_candidate_exam_by_token(db: Session, token: str) -> Optional[models.CandidateExam]:
    """Get an exam by its secure access token."""
    return db.query(models.CandidateExam).filter(models.CandidateExam.access_token == token).first()

def submit_candidate_exam(db: Session, token: str, answers: Dict) -> Optional[models.CandidateExam]:
    """Submits a candidate's answers."""
    db_exam = get_candidate_exam_by_token(db, token)
    if db_exam and db_exam.status == 'pending':
        db_exam.answers = answers
        db_exam.status = 'completed'
        db_exam.submitted_at = func.now()
        db.commit()
        db.refresh(db_exam)
        return db_exam
    return None

def get_candidate_exam_results(db: Session, candidate_id: int) -> List[models.CandidateExam]:
    """Get all exam results for a specific candidate."""
    return db.query(models.CandidateExam)\
             .filter(models.CandidateExam.candidate_id == candidate_id)\
             .filter(models.CandidateExam.status == 'completed')\
             .all()

# ==================
# Analytics CRUD
# ==================

def get_pipeline_metrics(db: Session) -> schemas.PipelineMetrics:
    total_candidates = db.query(models.Candidate).count()
    
    # Simple logic: 
    # - Screened: fit_score calculated (>0)
    # - Shortlisted: fit_score >= 0.7
    # - Interview Pending: In pending_interviews table (status='pending')
    # - Interview Scheduled: In pending_interviews table (status='scheduled')
    # - Offer Sent: (Placeholder, we don't have this status yet, assume 0)
    # - Rejected: fit_score < 0.7 (approx)
    
    screened = db.query(models.Candidate).filter(models.Candidate.fit_score > 0).count()
    shortlisted = db.query(models.Candidate).filter(models.Candidate.fit_score >= 0.7).count()
    rejected = db.query(models.Candidate).filter(models.Candidate.fit_score < 0.7).count()
    
    interview_pending = db.query(models.PendingInterview).filter(models.PendingInterview.status == 'pending').count()
    interview_scheduled = db.query(models.PendingInterview).filter(models.PendingInterview.status == 'scheduled').count()
    
    return schemas.PipelineMetrics(
        total_candidates=total_candidates,
        screened=screened,
        shortlisted=shortlisted,
        interview_pending=interview_pending,
        interview_scheduled=interview_scheduled,
        offer_sent=0, # Placeholder
        rejected=rejected
    )

def get_score_distribution(db: Session) -> schemas.ScoreDistribution:
    # Buckets
    range_0_20 = db.query(models.Candidate).filter(models.Candidate.fit_score >= 0.0, models.Candidate.fit_score < 0.2).count()
    range_20_40 = db.query(models.Candidate).filter(models.Candidate.fit_score >= 0.2, models.Candidate.fit_score < 0.4).count()
    range_40_60 = db.query(models.Candidate).filter(models.Candidate.fit_score >= 0.4, models.Candidate.fit_score < 0.6).count()
    range_60_80 = db.query(models.Candidate).filter(models.Candidate.fit_score >= 0.6, models.Candidate.fit_score < 0.8).count()
    range_80_100 = db.query(models.Candidate).filter(models.Candidate.fit_score >= 0.8).count()
    
    return schemas.ScoreDistribution(
        range_0_20=range_0_20,
        range_20_40=range_20_40,
        range_40_60=range_40_60,
        range_60_80=range_60_80,
        range_80_100=range_80_100
    )

def get_job_metrics(db: Session) -> schemas.JobMetrics:
    total_jobs = db.query(models.Job).count()
    open_jobs = db.query(models.Job).filter(models.Job.status == 'open').count()
    closed_jobs = db.query(models.Job).filter(models.Job.status == 'closed').count()
    
    total_candidates = db.query(models.Candidate).count()
    avg_candidates = total_candidates / total_jobs if total_jobs > 0 else 0.0
    
    return schemas.JobMetrics(
        total_jobs=total_jobs,
        open_jobs=open_jobs,
        closed_jobs=closed_jobs,
        avg_candidates_per_job=round(avg_candidates, 1)
    )