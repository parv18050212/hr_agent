import os
from typing import List, Optional, Dict

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from .config import settings # Use our project's config

# --- MODELS (from Nirmaan.HR/resume_matching.py) ---
# We define the Pydantic models the prompt will output
class EducationInfo(BaseModel):
    degree: Optional[str] = Field(description="Degree")
    completion_year: Optional[str] = Field(description="Year of degree completion")
    percentage: Optional[str] = Field(description="Percentage obtained")

class SkillInfo(BaseModel):
    name: Optional[str] = Field(description="Name of the skill.")
    category: Optional[str] = Field(description="Category (e.g., Programming Language)")

class ExperienceInfo(BaseModel):
    organization: Optional[str] = Field(description="Name of the company.")
    title: Optional[str] = Field(description="Title of the job role.")
    years: Optional[str] = Field(description="Years of experience in the job role")

class ResumeMatchingInfo(BaseModel):
    role: Optional[str] = Field(description="Role specified in the job description.")
    candidate: Optional[str] = Field(description="Name of the candidate from the resume.")
    location: Optional[str] = Field(description="Location specified in the job description")
    education: Optional[List[EducationInfo]] = Field(description="List of education qualifications.")
    similar_skills: Optional[List[SkillInfo]] = Field(description="Matched skills")
    missing_skills: Optional[List[SkillInfo]] = Field(description="Missing skills")
    preferable_skills: Optional[List[SkillInfo]] = Field(description="Matched preferable skills")
    experiences: Optional[List[ExperienceInfo]] = Field(description="Relevant job experiences")
    validation: Optional[str] = Field(description="Validation on score. Total breakdown of point allocation and sum of scoring.")
    score: Optional[str] = Field(description="Matching score (0% to 100%).")
    recommendation: Optional[str] = Field(description="Hiring recommendation summary.")

class ListResumeMatchingInfo(BaseModel):
    jds_report: List[ResumeMatchingInfo] = Field(description="List of resume matching reports.")

# --- PROMPT (from Nirmaan.HR/resume_matching.py) ---
# This is the detailed scoring rubric
resume_template = """
Background:
You are an experienced technical recruiter. Your objective is to meticulously compare the skills in the job description with the candidate's resume, categorize them, and calculate a matching score from 0-100.

Instructions:
1.  **Skills Matching:**
    -   Compare "skills_required" from the JOB_DESCRIPTION with the RESUME.
    -   Categorize into "similar_skills" (matches) and "missing_skills" (gaps).
    -   Match "skills_preferable" from the JOB_DESCRIPTION and list them under "preferable_skills".

2.  **Experience Matching:**
    -   Extract relevant experiences from the RESUME that align with the JOB_DESCRIPTION.

3.  **Matching Score Calculation (Total 100 points):**

    **A. Skills (Max 50 points):**
    -   **Required Skills (Max 44 points):** 4 points for each highly relevant skill, 2 points for moderately relevant. Cap at 44.
    -   **Preferable Skills (Max 6 points):** 1 point for each preferable skill found. Cap at 6.
    -   *Total Skill Points = (Points from Required) + (Points from Preferable)*

    **B. Experience Alignment (Max 50 points):**
    -   **Base Points:** Award 25 points if the candidate meets the minimum years of experience from the JOB_DESCRIPTION.
    -   **Bonus Points:** Award 2 points for *each* additional year of relevant experience beyond the minimum.
    -   **Cap:** The total for Experience Alignment cannot exceed 50 points.
    -   *Total Experience Points = (Base Points) + (Bonus Points)*

    **Total Score = Total Skill Points + Total Experience Points**

4.  **Validation:** Provide a brief, one-sentence breakdown of the score.
    *Example: "Score: 85/100 (40/50 from skills + 45/50 from 5 years experience)."*

5.  **Recommendation:** Write a 3-4 line hiring recommendation summary.

-----------------------------------------------------------------
RESUME:
{resume}

JOB_DESCRIPTION:
{job_description}

OUTPUT_INSTRUCTIONS:
{format_instructions}

ANSWER:
"""

# --- PARSER (from Nirmaan.HR/resume_matching.py) ---
parser = PydanticOutputParser(pydantic_object=ListResumeMatchingInfo)

prompt = PromptTemplate(
    template=resume_template,
    input_variables=["job_description", "resume"],
    partial_variables={
        "format_instructions": parser.get_format_instructions()},
)

# --- MAIN FUNCTION ---
def get_detailed_analysis(resume_text: str, job_description_text: str) -> Optional[Dict]:
    """
    Runs the detailed Nirmaan.HR scoring logic on a single resume and JD.
    """
    try:
        model = ChatOpenAI(
            temperature=0, 
            model="gpt-4", # Use a fast, cheap model first. Can upgrade to gpt-4
            api_key=settings.OPENAI_API_KEY.get_secret_value()
        )
        chain = prompt | model | parser
        
        # We wrap this in ListResumeMatchingInfo just to match the parser
        # The prompt is designed to return a list with one item.
        response = chain.invoke({
            "job_description": job_description_text, 
            "resume": resume_text
        })
        
        if response.jds_report:
            # This returns the FULL object (skills, exp, score, etc.)
            return response.jds_report[0].dict()
        else:
            return None
    except Exception as e:
        print(f"Error in Nirmaan Scorer: {e}")
        return None