# Autonomous AI Recruitment Manager

This project is a complete, full-stack application demonstrating an **autonomous AI agent** that manages the recruitment pipeline. It's not just a chatbot; it's an agentic system with "eyes," "hands," and a "voice" to perceive events, make decisions, and take real-world actions.

The system automates the entire flow: from a candidate applying, to the AI scoring their resume, proposing an interview, getting human (HR) approval, and then autonomously booking the Google Calendar invite and emailing the candidate.

## Core Features

* **RESTful API:** A robust backend built with **FastAPI** to manage jobs, candidates, and interviews.
* **Semantic Resume Scoring:** Automatically parses PDF resumes and scores them against job descriptions using **Gemini embeddings** and **pgvector** cosine similarity.
* **Autonomous Agent:** A **LangGraph**-powered agent that activates for high-fit candidates.
* **Agentic Tools (Real-World Actions):**
    * **"Eyes":** Can search a real Google Calendar for available slots.
    * **"Hands":** Can book a real Google Calendar event with a Meet link.
    * **"Voice":** Can send a personalized, formatted email to the candidate via Gmail.
* **Human-in-the-Loop (HITL):** The agent doesn't act without permission. It proposes an interview, which must be approved by an HR manager via a simple API endpoint (`/approve`).
* **Candidate-Facing Endpoint:** Includes an endpoint (`/my-applications/{email}`) that joins data from candidates, jobs, and interviews to show a candidate their application status and scheduled meeting link.
* **Feedback Loop:** An HR manager can submit feedback (`/feedback`) on an agent's score, creating data for future fine-tuning.

## How It Works: The Autonomous Workflow

This diagram shows the complete, end-to-end loop that makes this system autonomous.

```mermaid
graph TD
    subgraph "Step 1 & 2: Candidate Applies"
        A[Candidate applies via React UI]
        A --> B(FastAPI Backend: Scores Resume & Triggers Agent)
    end

    subgraph "Step 3: AI Agent (Brain)"
        B --> C(Agent checks GCal & creates 'Pending' Interview in DB)
    end

    subgraph "Step 4: Human-in-the-Loop (HITL)"
        C --> D[HR Manager: Approves in HR Dashboard]
    end

    subgraph "Step 5: AI Agent (Hands & Voice)"
        D -- Triggers Workflow --> E(Agent books 'Real' GCal Event & Sends Gmail)
    end

    subgraph "Step 6: Loop Closed"
        E --> F[Candidate: Receives Email & Sees 'Scheduled' Status]
    end


## Tech Stack

  * **Backend:** FastAPI, Uvicorn
  * **AI Orchestration:** LangGraph, LangChain
  * **LLM & Embeddings:** Google Gemini (Gemini 2.5 Flash, text-embedding-004)
  * **Database:** PostgreSQL with `pgvector` extension (NeonDB recommended)
  * **ORM:** SQLAlchemy
  * **Agent Tools:** Google Calendar API, Gmail API
  * **File Handling:** `pypdf` for resume parsing
  * **Other:** Pydantic, python-multipart

-----

## 🚀 Setup and Installation

### 1\. Clone the Repository

```bash
git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
cd your-repo-name
```

### 2\. Set Up Virtual Environment

```bash
# For macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

# For Windows
python -m venv .venv
.\.venv\Scripts\activate
```

### 3\. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4\. Database Setup (NeonDB + pgvector)

This project requires a PostgreSQL database with the `pgvector` extension. The easiest way to get one is with [NeonDB](https://neon.tech/):

1.  Create a free NeonDB account.
2.  Create a new project.
3.  Go to the **SQL Editor** and run `CREATE EXTENSION IF NOT EXISTS vector;` to enable pgvector.
4.  Find your **Connection String** (it will look like `postgresql://user:pass@host/dbname`) and copy it.

### 5\. Environment Variables

Rename `.env.example` (you should create this from `.env`) to `.env` and fill in the required variables:

```.env
# 1. Your NeonDB connection string
DATABASE_URL="postgresql://user:pass@host/dbname"

# 2. Your Google API Key (for Gemini)
# Go to Google AI Studio to generate this
GOOGLE_API_KEY="AIza..."

# 3. (Optional) LangSmith Tracing
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_ENDPOINT="[https://api.smith.langchain.com](https://api.smith.langchain.com)"
LANGCHAIN_API_KEY="lsv2_..."
```

### 6\. Google Auth (For Calendar & Gmail)

This is the most important step for letting the agent use its "hands" and "voice."

1.  **Google Cloud Project:**

      * Go to the [Google Cloud Console](https://console.cloud.google.com/).
      * Create a new project.
      * Go to "APIs & Services" \> "Library."
      * Search for and **Enable** the **Google Calendar API** and **Gmail API**.

2.  **OAuth Consent Screen:**

      * Go to "APIs & Services" \> "OAuth consent screen."
      * Select **External** and create an app.
      * Fill in the required fields (app name, user support email).
      * **Add Scopes:** Add the following scopes:
          * `https://www.googleapis.com/auth/calendar`
          * `https://www.googleapis.com/auth/gmail.send`
      * **Add Test Users:** Add your own Google email address as a test user.

3.  **Get Credentials:**

      * Go to "APIs & Services" \> "Credentials."
      * Click "Create Credentials" \> "OAuth client ID."
      * Select **Desktop app** as the application type.
      * Click "Create."
      * A modal will pop up. Click **DOWNLOAD JSON**.
      * Rename this file to `credentials.json` and place it in the root of your project directory.

4.  **Authorize the Application:**

      * Run the `get_token.py` script *once* from your terminal:

    <!-- end list -->

    ```bash
    python get_token.py
    ```

      * This will open a browser window.
      * Log in with the **Test User** email you added in Step 2.
      * You will see a "Google hasn't verified this app" screen. Click **Advanced** \> **"Go to (unsafe)..."**.
      * Grant the permissions.
      * The script will complete, and a new `token.json` file will be created. This file stores your authorization.

### 7\. Run the Application

You are now ready to start the server\!

```bash
uvicorn hr_agent.app.main:app --reload --host 127.0.0.1 --port 8000
```

The server will start, automatically connect to your database, and create all the tables.

Your API is now live at `http://127.0.0.1:8000/docs`.

## Key API Endpoints

  * `POST /jobs`: Create a new job posting.
  * `POST /jobs/{job_id}/candidates`: Upload a candidate's resume (this triggers the AI agent if the score is high).
  * `GET /pending-interviews`: **(For HR)** Get the "To-Do" list of interviews the AI has proposed.
  * `POST /pending-interviews/{interview_id}/approve`: **(For HR)** The "Approve" button. This triggers the agent's action workflow.
  * `GET /my-applications/{email}`: **(For Candidates)** A single endpoint to see the status of all their applications, including scheduled interview times and Meet links.
  * `POST /jobs/{job_id}/candidates/{candidate_id}/feedback`: **(For HR)** Endpoint to submit feedback on the agent's scoring to close the learning loop.

<!-- end list -->

```
```
