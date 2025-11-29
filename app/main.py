from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import EmailStr
import pypdf
import io
from typing import List, Any , Dict
from datetime import datetime, timezone, timedelta
import pytz 

from . import crud, models, schemas
from .database import SessionLocal, engine, get_db, create_db_and_tables
from . import chat

from .agent import app as agent_app
from .agent import run_approval_workflow
from langchain_core.messages import HumanMessage

create_db_and_tables()

app = FastAPI(
    title="AI Recruitment Manager API",
    description="Grand Project: 2-Stage Scoring",
    version="1.0.0"
)

# --- ADD CORS MIDDLEWARE ---
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_current_hr_user():
    # This is a placeholder. We will replace this with real Supabase auth.
    print("--- WARNING: Bypassing auth for /hr/chat-analytics ---")
    return {"user_id": "hr_admin_user", "role": "hr_admin"}

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Recruitment Manager API"}

# ==================
# Job Endpoints
# ==================

@app.post("/jobs", response_model=schemas.Job, status_code=201)
def create_new_job(job: schemas.JobCreate, db: Session = Depends(get_db)):
    return crud.create_job(db=db, job=job)

@app.get("/jobs", response_model=List[schemas.Job])
def read_all_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_jobs(db, skip=skip, limit=limit)

@app.get("/jobs/{job_id}", response_model=schemas.Job)
def read_one_job(job_id: int, db: Session = Depends(get_db)):
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job

# ==================
# Candidate Endpoints
# ==================

@app.post("/jobs/{job_id}/candidates", response_model=schemas.Candidate, status_code=201)
def upload_candidate_resume(
    job_id: int,
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    email: EmailStr = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Check job
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # 2. Check PDF
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDFs are accepted.")

    # 3. Read PDF
    try:
        resume_bytes = resume.file.read()
        pdf_reader = pypdf.PdfReader(io.BytesIO(resume_bytes))
        raw_text = ""
        for page in pdf_reader.pages:
            raw_text += page.extract_text()
        if not raw_text:
             raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

    # 4. Create candidate (this runs the FAST vector score)
    candidate_data = schemas.CandidateCreate(job_id=job_id, name=name, email=email)
    db_candidate = crud.create_candidate(
        db=db, 
        candidate=candidate_data, 
        resume_text=raw_text
    )
    
    if db_candidate is None:
        raise HTTPException(status_code=500, detail="Could not create candidate.")
        
    # 5. --- TRIGGER THE AGENT & DEEP ANALYSIS ---
    MIN_FIT_SCORE = 0.7 
    if db_candidate.fit_score and db_candidate.fit_score >= MIN_FIT_SCORE:
        print(f"Candidate {db_candidate.candidate_id} scored {db_candidate.fit_score}. Triggering agent...")
        
        # --- Time Zone Fix ---
        HR_TIMEZONE = pytz.timezone("Asia/Kolkata")
        now_in_hr_tz = datetime.now(HR_TIMEZONE)
        tomorrow_in_hr_tz = (now_in_hr_tz + timedelta(days=1))
        start_search_dt_in_hr_tz = tomorrow_in_hr_tz.replace(hour=9, minute=30, second=0, microsecond=0)
        start_search_utc = start_search_dt_in_hr_tz.astimezone(timezone.utc)
        start_search_iso = start_search_utc.isoformat()

        initial_state = {
            "messages": [
                HumanMessage(
                    content=f"New high-fit candidate detected: {db_candidate.name}. "
                            f"Start the interview proposal workflow. "
                            f"You must search for a 60-minute slot. "
                            f"The HR manager is in India (IST / UTC+5:30). "
                            f"You MUST start your calendar search no earlier than this exact UTC timestamp: {start_search_iso}"
                )
            ],
            "job_id": db_job.job_id,
            "candidate_id": db_candidate.candidate_id,
            "candidate_name": db_candidate.name,
            "candidate_email": db_candidate.email,
        }
        
        # --- ADD BOTH TASKS TO BACKGROUND ---
        # Task 1: The Agent (for scheduling)
        background_tasks.add_task(agent_app.invoke, initial_state)
        
        # Task 2: The Deep Analysis (for detailed scoring)
        background_tasks.add_task(crud.run_deep_analysis_task, db_candidate.candidate_id, db_job.job_id)

    return db_candidate

@app.get("/jobs/{job_id}/candidates", response_model=List[schemas.Candidate])
def read_job_candidates(job_id: int, db: Session = Depends(get_db)):
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    candidates = crud.get_candidates_for_job(db, job_id=job_id)
    return candidates

# --- NEW ENDPOINT FOR FRONTEND ---
@app.get("/candidates/{candidate_id}/analysis", response_model=schemas.CandidateAnalysis)
def get_candidate_analysis(candidate_id: int, db: Session = Depends(get_db)):
    """
    FOR HR DASHBOARD: Get the detailed Nirmaan.HR analysis for a single candidate.
    """
    db_candidate = crud.get_candidate(db, candidate_id=candidate_id)
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    return {
        "status": db_candidate.deep_analysis_status,
        "detailed_score": db_candidate.detailed_score,
        "detailed_validation": db_candidate.detailed_validation,
        "detailed_recommendation": db_candidate.detailed_recommendation
    }
    
# ==================
# Shortlist Endpoint
# ==================
@app.get("/jobs/{job_id}/shortlist", response_model=List[schemas.Candidate])
def get_job_shortlist(job_id: int, min_score: float = 0.7, db: Session = Depends(get_db)):
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    candidates = crud.get_shortlisted_candidates(db, job_id=job_id, min_score=min_score)
    return candidates

# ==================
# HITL Endpoints
# ==================
@app.get("/pending-interviews", response_model=List[schemas.PendingInterview])
def list_pending_interviews(db: Session = Depends(get_db)):
    return crud.get_pending_interviews(db)

@app.post("/pending-interviews/{interview_id}/approve", response_model=schemas.PendingInterview)
def approve_interview(
    interview_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    db_interview = crud.get_pending_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    if db_interview.status != 'pending':
        raise HTTPException(status_code=400, detail="Interview not in pending state")

    db_interview = crud.update_interview_status(db, interview_id, "approved")
    background_tasks.add_task(run_approval_workflow, interview_id)
    return db_interview

# ==================
# Feedback Endpoint
# ==================
@app.post("/jobs/{job_id}/candidates/{candidate_id}/feedback", response_model=schemas.Feedback)
def submit_feedback(
    job_id: int,
    candidate_id: int,
    feedback_data: schemas.FeedbackBase,
    db: Session = Depends(get_db)
):
    db_candidate = crud.get_candidate(db, candidate_id=candidate_id)
    if not db_candidate or db_candidate.job_id != job_id:
        raise HTTPException(status_code=404, detail="Candidate not found for this job")

    feedback_to_create = schemas.FeedbackCreate(
        job_id=job_id,
        candidate_id=candidate_id,
        agent_score=db_candidate.fit_score,
        hr_decision=feedback_data.hr_decision,
        hr_comments=feedback_data.hr_comments
    )
    return crud.create_feedback(db=db, feedback=feedback_to_create)

@app.post("/hr/chat-analytics", response_model=schemas.ChatResponse)
def chat_with_database(
    chat_request: schemas.ChatRequest, 
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_hr_user) # <-- SECURE
):
    """
    FOR HR DASHBOARD: Allows HR to ask natural language questions
    about the database.
    """
    
    # We are now secure and know this is an HR admin
    print(f"Chat request from user: {current_user['user_id']}")
    
    try:
        answer = chat.run_chat_analytics(
            question=chat_request.question,
            chat_history_dicts=[msg.dict() for msg in chat_request.chat_history]
        )
        return {"answer": answer}
        
    except Exception as e:
        print(f"Error in chat analytics endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/exam/{token}", response_model=schemas.CandidateExamData)
def get_exam_for_candidate(token: str, db: Session = Depends(get_db)):
    """
    FOR CANDIDATE: Fetch the exam questions using a unique token.
    """
    db_exam = crud.get_candidate_exam_by_token(db, token)
    
    if not db_exam or db_exam.status != 'pending':
        raise HTTPException(status_code=404, detail="Exam not found or already completed")
    
    # Get the master exam questions
    master_exam = crud.get_exam(db, db_exam.exam_id)
    if not master_exam:
        raise HTTPException(status_code=500, detail="Exam data missing")
        
    # Get the job title
    job = crud.get_job(db, master_exam.job_id)

    return {
        "candidate_exam_id": db_exam.candidate_exam_id,
        "status": db_exam.status,
        "job_title": job.title if job else "Test",
        "questions": master_exam.questions.get("questions", [])
    }

@app.post("/exam/{token}/submit")
def submit_exam_answers(
    token: str, 
    answers: schemas.CandidateExamAnswers,
    db: Session = Depends(get_db)
):
    """
    FOR CANDIDATE: Submit their answers to the exam.
    """
    db_exam = crud.submit_candidate_exam(db, token, answers.answers)
    
    if not db_exam:
        raise HTTPException(status_code=404, detail="Exam not found or already submitted")
        
    return {"message": "Exam submitted successfully!"}


@app.get("/hr/candidate-exams/{candidate_id}", response_model=List[schemas.CandidateExamResult])
def get_candidate_exam_results(
    candidate_id: int, 
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_hr_user) # Secure this
):
    """
    FOR HR: Get all completed exam results for a candidate.
    """
    results = crud.get_candidate_exam_results(db, candidate_id)
    
    processed_results = []
    for result in results:
        # Get master questions and job title for context
        master_exam = crud.get_exam(db, result.exam_id)
        job = crud.get_job(db, master_exam.job_id) if master_exam else None
        
        processed_results.append({
            "submitted_at": result.submitted_at,
            "job_title": job.title if job else "N/A",
            "questions": master_exam.questions.get("questions", []) if master_exam else [],
            "answers": result.answers
        })
        
    return processed_results

@app.get("/analytics/dashboard", response_model=schemas.DashboardMetrics)
def get_analytics_dashboard(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_hr_user)
):
    """
    FOR HR DASHBOARD: Get aggregated metrics for the analytics dashboard.
    """
    pipeline = crud.get_pipeline_metrics(db)
    score_dist = crud.get_score_distribution(db)
    job_metrics = crud.get_job_metrics(db)
    
    return {
        "pipeline": pipeline,
        "score_distribution": score_dist,
        "job_metrics": job_metrics # <-- FIXED: Changed key from "jobs" to "job_metrics"
    }