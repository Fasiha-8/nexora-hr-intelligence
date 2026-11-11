
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field

from app.database import get_db

# LangGraph is now the primary orchestration engine.
from app.graph_orchestrator import ask_nexora_graph

# Original Groq orchestrator retained as fallback.
from app.orchestrator import ask_nexora

from app.services.organizational_intelligence import (
    run_organizational_audit,
    run_approval_routing_audit,
)


app = FastAPI(
    title="Nexora Technologies - Workforce Intelligence",
    description=(
        "AI-powered HR intelligence, workforce analysis "
        "and approval routing using LangGraph and Groq."
    ),
    version="2.0.0",
)


# =====================================================
# REQUEST MODELS
# =====================================================

class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=2000,
        description="Ask Nexora an HR or workforce-related question."
    )


# =====================================================
# HOME AND HEALTH ENDPOINTS
# =====================================================

@app.get("/")
def home():
    return {
        "message": "Welcome to Nexora Workforce Intelligence Agent",
        "status": "running",
        "ai_engine": "Groq",
        "orchestration": "LangGraph",
        "version": "2.0.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "Nexora",
        "orchestration": "LangGraph",
        "llm_provider": "Groq",
    }


@app.get("/health/database")
def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "connected",
            "database": "nexora_hr",
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(error)}"
        )


# =====================================================
# EMPLOYEE ENDPOINTS
# =====================================================

@app.get("/employees")
def get_employees(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 200."
        )

    result = db.execute(
        text("""
            SELECT *
            FROM employees
            ORDER BY employee_id
            LIMIT :limit
        """),
        {"limit": limit}
    )

    employees = result.mappings().all()

    return {
        "count": len(employees),
        "employees": [
            dict(row) for row in employees
        ]
    }


@app.get("/employees/{employee_id}")
def get_employee(
    employee_id: str,
    db: Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT *
            FROM employees
            WHERE employee_id = :employee_id
        """),
        {"employee_id": employee_id}
    )

    employee = result.mappings().first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found."
        )

    return dict(employee)


# =====================================================
# ORGANIZATIONAL INTELLIGENCE
# =====================================================

@app.get("/intelligence/organizational-audit")
def organizational_audit(
    db: Session = Depends(get_db)
):
    try:
        return run_organizational_audit(db)

    except Exception as error:
        print("Organizational audit error:", str(error))

        raise HTTPException(
            status_code=500,
            detail="Organizational audit failed."
        )


@app.get("/intelligence/approval-routing-audit")
def approval_routing_audit(
    db: Session = Depends(get_db)
):
    try:
        return run_approval_routing_audit(db)

    except Exception as error:
        print("Approval routing audit error:", str(error))

        raise HTTPException(
            status_code=500,
            detail="Approval routing audit failed."
        )


# =====================================================
# NEXORA AI CHAT - LANGGRAPH
# =====================================================

@app.post("/assistant/chat")
def chat_with_nexora(request: ChatRequest):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please enter a question."
        )

    try:
        # Primary: LangGraph orchestration.
        answer = ask_nexora_graph(question)

        return {
            "agent": "Nexora HR Intelligence Agent",
            "model": "Groq",
            "orchestration": "LangGraph",
            "question": question,
            "answer": answer,
        }

    except Exception as error:

        print("LangGraph execution error:", str(error))

        # Fallback to the original Groq orchestrator.
        try:
            answer = ask_nexora(question)

            return {
                "agent": "Nexora HR Intelligence Agent",
                "model": "Groq",
                "orchestration": "Original Groq Fallback",
                "question": question,
                "answer": answer,
            }

        except Exception as fallback_error:

            print(
                "Original orchestrator error:",
                str(fallback_error)
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Nexora could not process the question "
                    "through either orchestration engine."
                )
            )
