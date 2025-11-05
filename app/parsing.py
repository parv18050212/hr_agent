from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from .config import settings

# 1. Define the structure we want to extract
class ParsedJobRequirements(BaseModel):
    """Structured data extracted from a job description."""
    required_skills: List[str] = Field(..., description="A list of essential technical skills (e.g., 'Python', 'FastAPI', 'AWS').")
    preferred_skills: List[str] = Field(..., description="A list of 'nice-to-have' skills.")
    required_years_experience: Optional[int] = Field(None, description="Minimum years of experience required.")

class ParsedResume(BaseModel):
    """Structured data extracted from a candidate's resume."""
    skills: List[str] = Field(..., description="A list of all technical skills found in the resume.")
    years_experience: Optional[int] = Field(None, description="The candidate's total years of professional experience.")
    education: Optional[str] = Field(None, description="The candidate's highest level of education or degree.")


# 2. Setup the LLM and Prompt
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    google_api_key=settings.GOOGLE_API_KEY.get_secret_value(),
    convert_system_message_to_human=True
)

JOB_PROMPT_TEMPLATE = """
You are an expert HR assistant. Your task is to extract key requirements from the provided job description text.
Only extract the information explicitly requested in the output format.

Job Description:
{text}
"""

RESUME_PROMPT_TEMPLATE = """
You are an expert resume parser. Your task is to extract key information from the provided resume text.
Only extract the information explicitly requested in the output format.

Resume Text:
{text}
"""

# 3. Create the extraction "chains"
def get_job_parser_chain():
    """Returns a LangChain chain that parses job descriptions."""
    prompt = PromptTemplate(
        template=JOB_PROMPT_TEMPLATE,
        input_variables=["text"]
    )
    # Gemini's .with_structured_output is simpler
    structured_llm = llm.with_structured_output(ParsedJobRequirements)
    return prompt | structured_llm

def get_resume_parser_chain():
    """Returns a LangChain chain that parses resumes."""
    prompt = PromptTemplate(
        template=RESUME_PROMPT_TEMPLATE,
        input_variables=["text"]
    )
    structured_llm = llm.with_structured_output(ParsedResume)
    return prompt | structured_llm