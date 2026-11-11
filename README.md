# Nexora — AI-Powered HR Intelligence

Nexora is an AI-powered HR intelligence application that helps organizations analyze workforce data, understand organizational structures, identify approval-routing issues, review HR workflows, and assess workforce risks.

## Features

- Organizational Intelligence
- Approval Routing Intelligence
- Workforce Intelligence
- Context-Aware HR Workflow Intelligence
- Predictive Workforce Intelligence
- Conversational AI assistant with tool calling

## Technology Stack

- Backend: Python, FastAPI
- Frontend: React.js, Vite, Node.js
- AI Orchestration: LangGraph
- LLM Provider: Groq
- Database: PostgreSQL
- ORM: SQLAlchemy

## Architecture

The React frontend communicates with the FastAPI backend through REST APIs. LangGraph orchestrates the AI assistant and tool execution. The assistant uses Groq to interpret questions and select from registered HR tools. Python services execute business logic and retrieve information from PostgreSQL.

## Project Structure

- app/ — Backend application and AI orchestration
- app/services/ — HR intelligence and business logic
- frontend/ — React chatbot interface
- scripts/ — Database initialization and data preparation scripts
- data/generated/ — Source CSV datasets
- data/scenarios/ — Business scenario datasets

## Setup

### 1. Clone the repository

\\\ash
git clone YOUR_GITHUB_REPOSITORY_URL
cd workforce-intelligence-agent
\\\

### 2. Create a Python environment

\\\ash
python -m venv venv
\\\

Activate it on Windows:

\\\powershell
.\\venv\\Scripts\\Activate.ps1
\\\

### 3. Install backend dependencies

\\\ash
pip install -r requirements.txt
\\\

### 4. Configure environment variables

Copy the example file:

\\\powershell
Copy-Item .env.example .env
\\\

Add your own Groq API key and PostgreSQL connection details to .env.

### 5. Initialize the database

Configure DATABASE_URL to point to an empty, disposable development database before running:

\\\ash
python scripts/init_database.py
\\\

WARNING: The initialization script drops and recreates its target tables. Never run it against an existing or production database containing data you need to preserve.

### 6. Start the backend

\\\ash
uvicorn app.main:app --reload
\\\

Backend: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

### 7. Start the frontend

Open another terminal:

\\\ash
cd frontend
npm install
npm run dev
\\\

Frontend: http://localhost:5173

## Current Limitations

- The current LangGraph workflow uses one assistant node and one tool execution node, not five independent agents.
- Predictive workforce intelligence uses rule-based scoring, not a trained machine-learning model.
- Authentication and role-based access control are not yet implemented.
- Leave workflows perform preliminary checks; they do not submit or approve leave requests.
- Chat history is maintained in frontend memory and is not persisted across page reloads.

## Development Notes

See DEVELOPMENT_TROUBLESHOOTING.md for implementation issues, debugging decisions, and fixes encountered during development.
