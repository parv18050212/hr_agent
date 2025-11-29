# app/tools/exam_tool.py
import json
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app import crud
from app.database import SessionLocal
from app.config import settings

class ExamToolArgs(BaseModel):
    """Input schema for the GenerateExamTool."""
    candidate_id: int = Field(..., description="The ID of the candidate.")
    job_id: int = Field(..., description="The ID of the job.")

# --- NEW: Pydantic model for the exam questions ---
class Question(BaseModel):
    question_text: str = Field(description="The full text of the question")
    question_type: str = Field(description="Type of question, e.g., 'multiple-choice', 'short-answer', 'coding'")
    options: Optional[List[str]] = Field(None, description="A list of options for multiple-choice questions")

class ExamQuestions(BaseModel):
    questions: List[Question] = Field(description="A list of 10 exam questions")


class GenerateExamTool(BaseTool):
    """
    A tool to generate a custom technical exam, save it to the database,
    and return the new exam's ID.
    """
    name: str = "generate_and_save_exam"
    description: str = (
        "Use this tool to generate a list of 10 technical questions as JSON, "
        "save them to the database, and get the exam_id. "
        "Input is 'candidate_id' and 'job_id'."
    )
    args_schema: Type[BaseModel] = ExamToolArgs

    def _get_data(self, candidate_id: int, job_id: int) -> Optional[Dict[str, Any]]:
        """Helper to get resume and JD text from our database."""
        db = SessionLocal()
        try:
            candidate = crud.get_candidate(db, candidate_id)
            job = crud.get_job(db, job_id)
            
            if not candidate or not job:
                return None
                
            return {
                "resume_info": candidate.resume_raw_text,
                "jd_info": job.description_text
            }
        finally:
            db.close()

    def _save_exam(self, job_id: int, questions_json: Dict) -> int:
        """Saves the generated exam to the 'exams' table."""
        db = SessionLocal()
        try:
            db_exam = crud.create_exam(db, job_id, questions_json)
            return db_exam.exam_id
        finally:
            db.close()

    def _run(self, candidate_id: int, job_id: int) -> str:
        """Use the tool."""
        print(f"--- [Tool] Running GenerateExamTool for C:{candidate_id}, J:{job_id} ---")
        
        data = self._get_data(candidate_id, job_id)
        if not data:
            return json.dumps({"error": "Could not find candidate or job in database."})

        # This prompt is adapted from Nirmaan.HR/exam.py
        # It now asks for JSON output.
        parser = JsonOutputParser(pydantic_object=ExamQuestions)
        
        prompt_template = PromptTemplate(
            input_variables=["resume_info", "jd_info"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
            template=(
                "You are an expert technical interviewer. Generate a technical assessment exam based on the following resume and job description.\n"
                "Provide exactly 10 questions with a mix of 'multiple-choice', 'short-answer', and 1-2 'coding' questions.\n"
                "The questions should be relevant to the skills in the job description and the candidate's experience.\n"
                "Do NOT ask questions *about* the candidate's resume (e.g., 'What was your project...'). Ask questions that *test* their skills (e.g., 'In FastAPI, what is Pydantic for?').\n"
                "Return ONLY the JSON requested in the format instructions. Do not include any other text.\n\n"
                "RESUME:\n{resume_info}\n\n"
                "JOB DESCRIPTION:\n{jd_info}\n\n"
                "{format_instructions}"
            ),
        )
        
        try:
            llm = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY.get_secret_value(), 
                model="gpt-4o"
            )
            
            chain = prompt_template | llm | parser
            exam_json = chain.invoke(data)
            
            # Save the exam to the DB
            exam_id = self._save_exam(job_id, exam_json)
            print(f"--- [Tool] Exam generated and saved with exam_id: {exam_id} ---")
            
            return json.dumps({"exam_id": exam_id, "success": True})
            
        except Exception as e:
            print(f"!!! Error in GenerateExamTool: {e} !!!")
            return json.dumps({"error": f"Error generating exam: {e}", "success": False})