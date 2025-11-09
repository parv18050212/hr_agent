from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import EmailStr
import pypdf
import io
from typing import List
from datetime import datetime, timezone # <-- This import is used for the fix
from typing import List, Optional
# --- Import all project components ---
from . import crud, models, schemas
from .database import SessionLocal, engine, get_db, create_db_and_tables
from fastapi.middleware.cors import CORSMiddleware
# --- Import Agent & Workflows ---
from .agent import app as agent_app
from .agent import run_approval_workflow
from langchain_core.messages import HumanMessage

# Create all database tables on startup
# (This will add the new PendingInterview table)
create_db_and_tables()

app = FastAPI(
    title="AI Recruitment Manager API",
    description="Phase 4: Full Agentic Loop with HITL",
    version="0.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (or specify Lovable domain)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Recruitment Manager API"}

# ==================
# Job Endpoints
# ==================

@app.post("/jobs", response_model=schemas.Job, status_code=201)
def create_new_job(job: schemas.JobCreate, db: Session = Depends(get_db)):
    """
    Create a new job posting.
    This automatically parses requirements and creates an embedding.
    """
    return crud.create_job(db=db, job=job)

@app.get("/jobs", response_model=List[schemas.Job])
def read_all_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all job postings.
    """
    jobs = crud.get_jobs(db, skip=skip, limit=limit)
    return jobs

@app.get("/jobs/{job_id}", response_model=schemas.Job)
def read_one_job(job_id: int, db: Session = Depends(get_db)):
    """
    Get details for a single job posting.
    """
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
    background_tasks: BackgroundTasks, # <-- ADDED for agent
    name: str = Form(...),
    email: EmailStr = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a new candidate. This now automatically:
    1. Parses the resume text.
    2. Creates an embedding.
    3. Calculates and saves a 'fit_score'.
    4. IF score is high, triggers agent in background.
    """
    # 1. Check if job exists
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # 2. Check if file is a PDF
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDFs are accepted.")

    # 3. Read and extract text from PDF
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

    # 4. Create the candidate in the database (this also scores them)
    candidate_data = schemas.CandidateCreate(job_id=job_id, name=name, email=email)
    
    db_candidate = crud.create_candidate(
        db=db, 
        candidate=candidate_data, 
        resume_text=raw_text
    )
    
    if db_candidate is None:
        raise HTTPException(status_code=500, detail="Could not create candidate. Check if job exists.")
        
    # 5. --- TRIGGER THE AGENT (Phase 4) ---
    MIN_FIT_SCORE = 0.7 # Set your threshold
    if db_candidate.fit_score and db_candidate.fit_score >= MIN_FIT_SCORE:
        print(f"Candidate {db_candidate.candidate_id} scored {db_candidate.fit_score}. Triggering agent...")
        
        # --- START OF FIX ---
        # Get the current date to "ground" the LLM
        today_iso = datetime.now(timezone.utc).isoformat()
        
        # Define the starting "memory" for our agent
        initial_state = {
            "messages": [
                HumanMessage(
                    content=f"New high-fit candidate detected: {db_candidate.name}. "
                        f"Start the interview proposal workflow. "
                        f"Today's date is {today_iso}. "  # <-- FIX: Ground the agent
                        f"Search for a 60-minute slot starting from tomorrow."
                )
            ],
            "job_id": db_job.job_id,
            "candidate_id": db_candidate.candidate_id,
            "candidate_name": db_candidate.name,
            "candidate_email": db_candidate.email,
        }
        # --- END OF FIX ---
        
        # Add the agent's run to the background queue
        background_tasks.add_task(agent_app.invoke, initial_state)

    # Return immediately to the user
    return db_candidate

@app.get("/jobs/{job_id}/candidates", response_model=List[schemas.Candidate])
def read_job_candidates(job_id: int, db: Session = Depends(get_db)):
    """
    List all candidates who have applied for a specific job.
    """
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    candidates = crud.get_candidates_for_job(db, job_id=job_id)
    return candidates
    
# ==================
# Shortlist Endpoint
# ==================

@app.get("/jobs/{job_id}/shortlist", response_model=List[schemas.Candidate])
def get_job_shortlist(job_id: int, min_score: float = 0.7, db: Session = Depends(get_db)):
    """
    Get a ranked list of the best candidates for a job,
    filtered by a minimum fit_score.
    """
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
        
    candidates = crud.get_shortlisted_candidates(db, job_id=job_id, min_score=min_score)
    return candidates

# ==================
# HITL Endpoints (NEW FOR PHASE 4)
# ==================

@app.get("/pending-interviews", response_model=List[schemas.PendingInterview])
def list_pending_interviews(db: Session = Depends(get_db)):
    """
    FOR HR: Get a list of all interviews needing approval.
    """
    return crud.get_pending_interviews(db)

@app.post("/pending-interviews/{interview_id}/approve", response_model=schemas.PendingInterview)
def approve_interview(
    interview_id: int, 
    background_tasks: BackgroundTasks, # <-- ADDED for workflow
    db: Session = Depends(get_db)
):
    """
    FOR HR: Approve a pending interview.
    This triggers a background task to send the calendar invite
    and email the candidate.
    """
    db_interview = crud.get_pending_interview(db, interview_id)
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    if db_interview.status != 'pending':
        raise HTTPException(status_code=400, detail="Interview not in pending state")

    # 1. Update status to 'approved' so it can't be double-triggered
    db_interview = crud.update_interview_status(db, interview_id, "approved")
    
    # 2. --- TRIGGER THE APPROVAL WORKFLOW ---
    # Run the "hands" in the background
    background_tasks.add_task(run_approval_workflow, interview_id)
    
    return db_interview

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


class ApplicationDetails(schemas.Candidate):
    job: schemas.Job
    interview: Optional[schemas.PendingInterview] = None

@app.get("/my-applications/{email}", response_model=List[ApplicationDetails])
def get_my_applications(email: EmailStr, db: Session = Depends(get_db)):
    """
    Get all applications (candidates) submitted by a specific email,
    and join related job and interview details.
    """
    
    # This query joins all three tables: Candidate, Job, and PendingInterview
    applications = db.query(models.Candidate, models.Job, models.PendingInterview)\
        .join(models.Job, models.Candidate.job_id == models.Job.job_id)\
        .outerjoin(models.PendingInterview, 
                 models.Candidate.candidate_id == models.PendingInterview.candidate_id)\
        .filter(models.Candidate.email == email)\
        .order_by(models.Candidate.created_at.desc())\
        .all()

    if not applications:
        return [] # Return empty list, not 404
    
    # Format the data into the Pydantic response model
    results = []
    for candidate, job, interview in applications:
        # We need to manually construct the response model
        app_details_data = candidate.__dict__
        app_details_data["job"] = job
        app_details_data["interview"] = interview
        
        app_details = ApplicationDetails(**app_details_data)
        results.append(app_details)
        
    return results

@app.post("/jobs/{job_id}/candidates/{candidate_id}/feedback", response_model=schemas.Feedback)
def submit_feedback(
    job_id: int,
    candidate_id: int,
    feedback_data: schemas.FeedbackBase, # Body of the request
    db: Session = Depends(get_db)
):
    """
    FOR HR: Submit feedback on an agent's scoring.
    HR can use this to "correct" the agent, e.g., rejecting a
    candidate the agent approved, or vice-versa.
    """
    # 1. Get the candidate to verify they exist
    db_candidate = crud.get_candidate(db, candidate_id=candidate_id)
    if not db_candidate or db_candidate.job_id != job_id:
        raise HTTPException(status_code=404, detail="Candidate not found for this job")

    # 2. Create the full feedback object
    feedback_to_create = schemas.FeedbackCreate(
        job_id=job_id,
        candidate_id=candidate_id,
        agent_score=db_candidate.fit_score, # Log the score the agent gave
        hr_decision=feedback_data.hr_decision,
        hr_comments=feedback_data.hr_comments
    )
    
    # 3. Save to database
    return crud.create_feedback(db=db, feedback=feedback_to_create)