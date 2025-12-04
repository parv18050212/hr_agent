# 🚀 Autonomous AI Recruitment Manager — Backend (FastAPI + LangGraph + Gemini)

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)  
[![LangChain](https://img.shields.io/badge/LangGraph%2FLangChain-000000?style=flat)](https://langchain.com)  
[![Gemini](https://img.shields.io/badge/Google%20Gemini-4285F4?style=flat&logo=google)](https://ai.google/)  
[![Postgres](https://img.shields.io/badge/Postgres%20%2B%20pgvector-336791?style=flat&logo=postgresql)](https://www.postgresql.org)  

> **Autonomous backend system** that semantically evaluates resumes, identifies top candidates, proposes interviews, sends them for HR approval, and—only after approval—automatically schedules Google Calendar meetings and emails candidates.

This backend powers the full product.  
**Frontend repo:** https://github.com/parv18050212/ai-recruiter-app

---

# 📌 TL;DR — Run in 30 seconds

```bash
git clone https://github.com/parv18050212/hr_agent
cd hr_agent

python3 -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env       # Add DATABASE_URL, keys, etc.

# Add Google OAuth credentials.json in root
python get_token.py        # Creates token.json after browser auth

uvicorn hr_agent.app.main:app --reload
```

Open → **http://127.0.0.1:8000/docs**

---

# 🎯 What This Backend Does

### **1. Resume Understanding**
- Upload PDF
- Text extracted + embedded using **Google Gemini**
- Stored inside Postgres **pgvector**
- Compared against job vectors → similarity score

### **2. AI-Driven Candidate Ranking**
- LangGraph pipeline interprets candidate-job match
- If strong match → create `PENDING` interview record

### **3. Human‑in‑the‑Loop Safety**
Agent cannot book interviews automatically.  
HR must **approve** via `/pending-interviews/{id}/approve`.

### **4. Autonomous Interview Booking**
After approval:
- Google Calendar booking
- Meet link creation
- Automated Gmail email to candidate

### **5. Candidate Portal**
```
/my-applications/{email}
```

### **6. Feedback Loop**
HR feedback stored for future model improvements.

---

# 🧠 System Architecture

```
              ┌───────────────────────────────┐
              │           React UI             │
              │ (candidate + HR dashboards)    │
              └──────────────┬────────────────┘
                             │
                             ▼
                   ┌───────────────────┐
                   │     FastAPI       │
                   │ REST + Handlers   │
                   └───────┬───────────┘
                           │
     ┌─────────────────────┼─────────────────────┐
     ▼                     ▼                     ▼
[Resume Parser]   [Gemini Embeddings]   [LangGraph Agent]
 Extract text      Store vectors in     Decide fit → propose
 in Python         Postgres(pgvector)   interview

                   ┌───────────────────┐
                   │  HR Approval UI   │
                   └─────────┬─────────┘
                             ▼
                   [Google Calendar API]
                   [Gmail Automated Emails]
```

---

# 🛠️ Tech Stack

### **Core**
- **FastAPI** (REST API)
- **LangChain + LangGraph** (agent workflow)
- **Gemini Embeddings**
- **PostgreSQL + pgvector**
- **Google Calendar API**
- **Gmail API**

### **Utilities**
- Python 3.10+
- Uvicorn
- Pydantic
- SQLAlchemy

---

# ⚙️ Setup / Environment Variables

`.env.example` includes:

```env
DATABASE_URL="postgresql://user:pass@host/db"
GOOGLE_API_KEY="AIza..."
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="lsv2_..."

GOOGLE_OAUTH_CREDENTIALS="credentials.json"
```

### Enable pgvector extension
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

# 🔑 Google OAuth Setup

### Steps
1. Google Cloud Console → Create Project  
2. Enable:
   - **Google Calendar API**
   - **Gmail API**
3. OAuth → External → Add test users  
4. Create Desktop OAuth Client → download **credentials.json**  
5. Place file in project root  
6. Run:
```bash
python get_token.py
```

Generates `token.json`.

---

# 📡 API Examples

### Create Job
```bash
curl -X POST "http://127.0.0.1:8000/jobs" -H "Content-Type: application/json" -d '{"title":"Backend Engineer","description":"Python + FastAPI","location":"Remote"}'
```

### Upload Resume
```bash
curl -X POST "http://127.0.0.1:8000/jobs/1/candidates" -F "name=Parv" -F "email=parv@example.com" -F "resume=@/path/resume.pdf"
```

### Get Pending Interviews
```bash
curl http://127.0.0.1:8000/pending-interviews
```

### Approve Interview
```bash
curl -X POST http://127.0.0.1:8000/pending-interviews/42/approve
```

### Candidate View
```bash
curl http://127.0.0.1:8000/my-applications/parv@example.com
```

---

# 🧩 Design Notes

- **Agent never books without HR approval**
- **Google token.json required only once**
- **Vector dims depend on embedding model**
- **Minimal PII stored**
- **Embeddings cached where possible**

---

# 📅 Roadmap

- ATS integrations (Greenhouse / Lever)
- Better UI for HR review
- Full audit logging
- Explainability layer for ranking
- Multi-round interview planning

---

# 📄 License
MIT License.  
Feel free to fork, extend, or deploy.
