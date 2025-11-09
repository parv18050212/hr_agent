# 🚀 Autonomous AI Recruitment Manager

[![FastAPI](https://img.shields.io/badge/FastAPI-000000?style=flat&logo=fastapi)](https://fastapi.tiangolo.com) [![LangChain](https://img.shields.io/badge/LangChain-000000?style=flat)](https://langchain.com) [![Gemini](https://img.shields.io/badge/Gemini-000000?style=flat)](https://ai.google/) [![Postgres](https://img.shields.io/badge/Postgres-336791?style=flat&logo=postgresql)]

> **Autonomous pipeline** that scores resumes semantically, proposes interviews, flows through HR approval, then autonomously books Google Calendar events and emails candidates. Human-in-the-loop for safe, auditable automation.

---

## TL;DR

1. Clone repo  
2. Create `.env` from `.env.example` and populate keys (DATABASE_URL, GOOGLE_API_KEY, Google OAuth `credentials.json`)  
3. `pip install -r requirements.txt`  
4. `python get_token.py` → authorize once (creates `token.json`)  
5. `uvicorn hr_agent.app.main:app --reload` → open `http://127.0.0.1:8000/docs`  

---

## What this does (short)

- Ingests PDF resumes and scores them against job descriptions using **Gemini** embeddings + **pgvector**.
- Triggers a LangGraph/LangChain agent for high-fit candidates.
- Agent proposes an interview (creates `Pending` interview in DB).
- HR approves via `/pending-interviews/{id}/approve` — only then agent books GCal & sends Gmail.
- Candidate-facing endpoint `/my-applications/{email}` shows status + meet link.
- HR feedback endpoint to capture labeling data for future improvements.

---

## Quick Features

- Semantic resume scoring (Gemini + pgvector)
- LangGraph agent orchestration
- Google Calendar & Gmail integration (real bookings & invites)
- Human-in-the-loop safety gate
- Candidate self-service endpoint
- Feedback loop for continuous learning

---

## Architecture (at-a-glance)

```
[React UI] -> [FastAPI] -> [Resume Parser + Embeddings] -> [pgvector / Postgres]
                                          |
                                          v
                                     [Agent via LangGraph]
                                          |
                       proposes interview -> DB (status=PENDING)
                                          |
                      HR approves -> agent books GCal + sends Gmail
```

---

## Quickstart (developer)

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

# venv
python3 -m venv .venv
source .venv/bin/activate   # or .\.venv\Scripts\activate (Windows)

pip install -r requirements.txt
cp .env.example .env        # edit .env
# put credentials.json (Google OAuth) in project root
python get_token.py         # authorize once -> token.json
uvicorn hr_agent.app.main:app --reload --host 127.0.0.1 --port 8000
```

Docs: `http://127.0.0.1:8000/docs`

---

## Environment Variables (`.env` example)

```env
DATABASE_URL="postgresql://user:pass@host/dbname"   # Neon / Postgres w/ pgvector
GOOGLE_API_KEY="AIza..."                            # Gemini / Google AI Studio key
GOOGLE_OAUTH_CREDENTIALS="credentials.json"         # path if needed elsewhere
# Optional tracing / debug
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="lsv2_..."
```

**Database:** enable `vector` extension:  
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Google OAuth (Calendar & Gmail)

1. Google Cloud Console → Create Project  
2. Enable **Google Calendar API** & **Gmail API**  
3. OAuth consent: External, add scopes:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/gmail.send`
4. Add Test User(s) (your email)
5. Create OAuth client -> Desktop app -> download `credentials.json`
6. Run `python get_token.py` → follow prompts; creates `token.json`

---

## Endpoints — Examples

Create job:
```bash
curl -X POST "http://127.0.0.1:8000/jobs" -H "Content-Type: application/json" -d '{
  "title": "Backend Engineer",
  "description": "2+ years Python, FastAPI, cloud",
  "location": "Remote"
}'
```

Upload candidate resume (triggers scoring & agent if high-fit):
```bash
curl -X POST "http://127.0.0.1:8000/jobs/1/candidates"   -F "name=Parv"   -F "email=parv@example.com"   -F "resume=@/path/to/resume.pdf"
```

Get pending interviews (HR):
```bash
curl "http://127.0.0.1:8000/pending-interviews"
```

Approve a pending interview:
```bash
curl -X POST "http://127.0.0.1:8000/pending-interviews/42/approve"
```

Candidate view:
```bash
curl "http://127.0.0.1:8000/my-applications/parv@example.com"
```

Submit feedback:
```bash
curl -X POST "http://127.0.0.1:8000/jobs/1/candidates/1/feedback"   -H "Content-Type: application/json"   -d '{"score": 3, "notes": "Candidate is strong but lacks domain experience."}'
```

---

## Design Notes

- **Auth + tokens:** `token.json` created once. Rotate credentials? Re-run `get_token.py`.
- **Gemini quotas:** Use dev keys for testing.
- **Vector dimensions:** Match your embedding model; recreate index if model changes.
- **HITL safety:** Agent never books interviews without approval.
- **Privacy:** Store minimal resume data; secure DB access.

---

## Roadmap

- ATS Integrations (Greenhouse / Workable)
- Fine-tuned model from HR feedback
- Web dashboard for HR
- Audit logs & explainability

---

## License

MIT — see `LICENSE`.
