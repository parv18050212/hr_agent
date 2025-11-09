from sqlalchemy import (
    Column, Integer, String, Text, DateTime, 
    ForeignKey, JSON, Numeric, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector # <-- ADD THIS
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import relationship
# Create a new Base here for models
Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    
    job_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description_text = Column(Text, nullable=False)
    requirements_structured = Column(JSON) 
    embedding = Column(Vector(768))  # <-- UPDATED to 768
    status = Column(String(50), nullable=False, default='open') 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    candidates = relationship("Candidate", back_populates="job")

class Candidate(Base):
    __tablename__ = "candidates"
    
    candidate_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.job_id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    resume_raw_text = Column(Text) 
    skills_parsed = Column(JSON) 
    embedding = Column(Vector(768))  # <-- UPDATED to 768
    fit_score = Column(Numeric(5, 4)) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    job = relationship("Job", back_populates="candidates")
    logs = relationship("AuditLog", back_populates="candidate")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    log_id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), index=True)
    job_id = Column(Integer, ForeignKey("jobs.job_id"), index=True)
    action = Column(String(255), nullable=False) 
    details = Column(JSON) 
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship("Candidate", back_populates="logs")
    job = relationship("Job")

class PendingInterview(Base):
    __tablename__ = "pending_interviews"
    
    interview_id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), index=True)
    job_id = Column(Integer, ForeignKey("jobs.job_id"), index=True)
    
    # The data the agent proposes
    summary = Column(String(255), nullable=False)
    proposed_start_time = Column(DateTime(timezone=True), nullable=False)
    proposed_end_time = Column(DateTime(timezone=True), nullable=False)
    
    # 'pending', 'approved', 'rejected'
    status = Column(String(50), nullable=False, default='pending') 
    meet_link = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    candidate = relationship("Candidate")
    job = relationship("Job")

class Feedback(Base):
    __tablename__ = "feedback"
    
    feedback_id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.job_id"), index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), index=True)
    
    # The score the agent gave
    agent_score = Column(Numeric(5, 4))
    
    # HR's decision, e.g., "Approved" (agreed) or "Rejected" (disagreed)
    hr_decision = Column(String(50), nullable=False)
    
    # The "why" from HR
    hr_comments = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    candidate = relationship("Candidate")
    job = relationship("Job")