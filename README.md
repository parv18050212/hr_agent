🤖 Autonomous AI Recruitment Manager

An end-to-end AI-driven recruitment automation system — not just a chatbot, but a fully autonomous agentic platform with perception, reasoning, and action capabilities.
This system autonomously handles the entire recruitment pipeline — from candidate application to resume scoring, interview scheduling, and real-world actions like sending emails and booking meetings.

🧠 Overview

The Autonomous AI Recruitment Manager streamlines hiring by combining AI intelligence with automation tools.
It perceives events (“eyes”), takes real-world actions (“hands”), and communicates (“voice”), while keeping humans in control through a Human-in-the-Loop (HITL) approval system.

⚙️ Core Features
🧩 API & Backend

Built on FastAPI — a scalable, async-ready RESTful backend.

Manages jobs, candidates, and interviews with clean API endpoints.

🧠 Semantic Resume Scoring

Parses and scores PDF resumes using Gemini embeddings and pgvector cosine similarity.

Matches candidates to job descriptions semantically, not just by keywords.

🤖 Autonomous Agent

Powered by LangGraph + LangChain for intelligent decision-making.

Automatically proposes interviews for top-matching candidates.

🧰 Agentic Tools
Capability	Description
👁️ Eyes	Searches real Google Calendar for open slots
✋ Hands	Books Google Calendar meetings with Meet links
🗣️ Voice	Sends personalized, formatted emails via Gmail
👩‍💼 Human-in-the-Loop (HITL)

The agent only proposes actions — HR must explicitly approve them.

Approval triggers autonomous scheduling and email dispatch.

👨‍💻 Candidate Experience

Endpoint (/my-applications/{email}) lets candidates check their status, scheduled meetings, and links in real-time.

🔁 Feedback Loop

HR can submit feedback (/feedback) on AI scoring, enabling data collection for model improvement.

🧭 System Workflow
graph TD
    subgraph "Step 1 & 2: Candidate Applies"
        A[Candidate applies via React UI]
        A --> B(FastAPI Backend: Scores Resume & Triggers Agent)
    end

    subgraph "Step 3: AI Agent (Brain)"
        B --> C(Agent checks GCal & creates 'Pending' Interview in DB)
    end

    subgraph "Step 4: Human-in-the-Loop"
        C --> D[HR Manager approves via Dashboard]
    end

    subgraph "Step 5: Agent Acts"
        D --> E(Books Google Calendar event & sends Gmail invite)
    end

    subgraph "Step 6: Loop Closed"
        E --> F[Candidate receives email & sees updated status]
    end

🧱 Tech Stack
Component	Technology
Backend	FastAPI, Uvicorn
AI Orchestration	LangGraph, LangChain
LLM & Embeddings	Google Gemini (2.5 Flash, text-embedding-004)
Database	PostgreSQL + pgvector (NeonDB recommended)
ORM	SQLAlchemy
Agent Tools	Google Calendar API, Gmail API
File Parsing	pypdf
Other	Pydantic, python-multipart
🚀 Setup & Installation
1️⃣ Clone the Repository
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

2️⃣ Create a Virtual Environment
# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.\.venv\Scripts\activate

3️⃣ Install Dependencies
pip install -r requirements.txt

🗄️ Database Setup (NeonDB + pgvector)

Sign up at NeonDB
.

Create a new PostgreSQL project.

In SQL Editor, run:

CREATE EXTENSION IF NOT EXISTS vector;


Copy your connection string (e.g. postgresql://user:pass@host/dbname).

⚙️ Environment Variables

Create a .env file from .env.example:

DATABASE_URL="postgresql://user:pass@host/dbname"
GOOGLE_API_KEY="AIza..."  # From Google AI Studio

# Optional: LangSmith tracing
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="lsv2_..."

🔑 Google Authentication (Calendar + Gmail)
Step 1: Create Google Cloud Project

Go to Google Cloud Console
.

Create a new project.

Enable:

Google Calendar API

Gmail API

Step 2: OAuth Consent Screen

Configure as External app.

Add scopes:

https://www.googleapis.com/auth/calendar

https://www.googleapis.com/auth/gmail.send

Add your email as a Test User.

Step 3: Create OAuth Credentials

Go to APIs & Services → Credentials → Create Credentials → OAuth Client ID.

Choose Desktop App.

Download the JSON and rename it to:

credentials.json


Place it in your project root.

Step 4: Authorize the App

Run once to generate token.json:

python get_token.py


Then:

Log in using your Test User account.

Approve access → Done.
token.json is now saved locally.

🧩 Running the Server
uvicorn hr_agent.app.main:app --reload --host 127.0.0.1 --port 8000


Your backend will start, auto-create tables, and serve documentation at:

👉 http://127.0.0.1:8000/docs

🔗 API Endpoints Summary
Endpoint	Method	Description
/jobs	POST	Create a new job posting
/jobs/{job_id}/candidates	POST	Upload a candidate resume (triggers AI agent)
/pending-interviews	GET	Fetch all pending interviews for HR review
/pending-interviews/{id}/approve	POST	Approve an interview proposal (triggers action)
/my-applications/{email}	GET	Candidate view: status & meeting info
/jobs/{job_id}/candidates/{candidate_id}/feedback	POST	Submit HR feedback for learning loop
🧠 Summary

This project showcases a fully autonomous recruitment workflow integrating:

✅ AI reasoning via LangGraph + Gemini
✅ Real-world action with Google APIs
✅ Transparent oversight through Human-in-the-Loop approval
✅ Continuous improvement via feedback-driven learning

🧩 Future Improvements

Integration with ATS (Greenhouse, Workable, Lever)

Fine-tuning with HR feedback data

Web dashboard for HR and candidate management

Enhanced prompt memory via LangGraph persistence

💡 Author

Parv Agarwal
AI & DevOps Engineer | Full-Stack Developer
🔗 LinkedIn
 • GitHub
