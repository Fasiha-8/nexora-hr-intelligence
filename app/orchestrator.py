
import os
import json
from pathlib import Path
from collections import Counter

from dotenv import load_dotenv
from groq import Groq

from app.database import SessionLocal

from app.services.organizational_intelligence import (
    run_organizational_audit,
    run_approval_routing_audit,
)

from app.services.workforce_intelligence import (
    run_project_staffing_analysis,
    run_employee_workload_analysis,
    run_critical_resource_analysis,
    run_workforce_intelligence,
)

from app.services.hr_workflow_intelligence import (
    get_employee_hr_context,
    review_leave_workflow,
    get_hr_business_scenarios,
)

from app.services.predictive_workforce_intelligence import (
    predict_project_workforce_risks,
    predict_employee_workforce_risks,
    run_predictive_workforce_analysis,
)


# =====================================================
# CONFIGURATION
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

if not API_KEY:
    raise ValueError("GROQ_API_KEY is missing from .env")

client = Groq(api_key=API_KEY)


# =====================================================
# DATABASE TOOL FUNCTIONS
# =====================================================

def organizational_audit():
    db = SessionLocal()
    try:
        return run_organizational_audit(db)
    finally:
        db.close()


def approval_routing_audit():
    db = SessionLocal()
    try:
        return run_approval_routing_audit(db)
    finally:
        db.close()


def workforce_overview():
    from sqlalchemy import text

    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT
                d.department_name,
                COUNT(e.employee_id) AS employee_count
            FROM departments d
            LEFT JOIN employees e
                ON d.department_id = e.department_id
            GROUP BY d.department_id, d.department_name
            ORDER BY employee_count DESC
        """))

        return {
            "department_workforce": [
                dict(row) for row in result.mappings().all()
            ]
        }
    finally:
        db.close()


def project_staffing_analysis():
    db = SessionLocal()
    try:
        return run_project_staffing_analysis(db)
    finally:
        db.close()


def employee_workload_analysis():
    db = SessionLocal()
    try:
        return run_employee_workload_analysis(db)
    finally:
        db.close()


def critical_resource_analysis():
    db = SessionLocal()
    try:
        return run_critical_resource_analysis(db)
    finally:
        db.close()


def complete_workforce_analysis():
    db = SessionLocal()
    try:
        return run_workforce_intelligence(db)
    finally:
        db.close()


# =====================================================
# CONTEXT-AWARE HR WORKFLOW FUNCTIONS
# =====================================================

def employee_hr_context(employee_id: str):
    db = SessionLocal()
    try:
        return get_employee_hr_context(db, employee_id)
    finally:
        db.close()


def leave_workflow_review(
    employee_id: str,
    leave_type: str,
    requested_days: float,
    start_date: str = None,
    end_date: str = None
):
    db = SessionLocal()
    try:
        return review_leave_workflow(
            db,
            employee_id,
            leave_type,
            requested_days,
            start_date,
            end_date
        )
    finally:
        db.close()


def hr_business_scenarios():
    db = SessionLocal()
    try:
        return get_hr_business_scenarios(db)
    finally:
        db.close()


# =====================================================
# PREDICTIVE WORKFORCE INTELLIGENCE FUNCTIONS
# =====================================================

def project_workforce_risks():
    db = SessionLocal()
    try:
        return predict_project_workforce_risks(db)
    finally:
        db.close()


def employee_workforce_risks():
    db = SessionLocal()
    try:
        return predict_employee_workforce_risks(db)
    finally:
        db.close()


def complete_predictive_analysis():
    db = SessionLocal()
    try:
        return run_predictive_workforce_analysis(db)
    finally:
        db.close()


# =====================================================
# TOOL RESULT COMPRESSION
# =====================================================

def compact_tool_result(data, max_records=10):
    """
    Reduce large tool results before sending them to Groq.

    Preserves:
    - Total record counts
    - Risk-level counts
    - Highest-risk records
    - Other summary fields

    This does not modify the database or original service results.
    """

    if isinstance(data, dict):
        return {
            key: compact_tool_result(value, max_records)
            for key, value in data.items()
        }

    if isinstance(data, list):

        if len(data) <= max_records:
            return [
                compact_tool_result(item, max_records)
                for item in data
            ]

        risk_counts = Counter()
        risk_records = []

        for item in data:
            if isinstance(item, dict):
                level = item.get("risk_level")

                if level:
                    risk_counts[str(level).upper()] += 1

                risk_records.append(item)

        if risk_records:
            risk_records.sort(
                key=lambda item: float(
                    item.get("risk_score", item.get("score", 0)) or 0
                ),
                reverse=True
            )

        selected = risk_records[:max_records]

        return {
            "total_records": len(data),
            "records_sent_to_ai": len(selected),
            "records_omitted": len(data) - len(selected),
            "risk_level_counts": dict(risk_counts),
            "records": [
                compact_tool_result(item, max_records)
                for item in selected
            ],
            "note": (
                "Only the highest-scoring records are included. "
                "Risk-level counts represent the complete dataset."
            )
        }

    return data


# =====================================================
# GROQ TOOL DEFINITIONS
# =====================================================

def empty_parameters():
    return {
        "type": "object",
        "properties": {},
        "required": []
    }


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "organizational_audit",
            "description": (
                "Audit employee reporting relationships, missing "
                "managers and department inconsistencies."
            ),
            "parameters": empty_parameters()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "approval_routing_audit",
            "description": (
                "Audit leave approval routing and manager assignments."
            ),
            "parameters": empty_parameters()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "workforce_overview",
            "description": (
                "Retrieve employee headcount grouped by department."
            ),
            "parameters": empty_parameters()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "project_staffing_analysis",
            "description": (
                "Identify understaffed active projects."
            ),
            "parameters": empty_parameters()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "employee_workload_analysis",
            "description": (
                "Identify overallocated employees and multiple "
                "project assignments."
            ),
            "parameters": empty_parameters()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "critical_resource_analysis",
            "description": (
                "Identify critical employees assigned to active projects."
            ),
            "parameters": empty_parameters()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_workforce_analysis",
            "description": (
                "Run all workforce staffing, workload and critical "
                "resource analyses."
            ),
            "parameters": empty_parameters()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "employee_hr_context",
            "description": (
                "Retrieve employee profile, manager, leave balances "
                "and recent leave requests."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"}
                },
                "required": ["employee_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "leave_workflow_review",
            "description": (
                "Validate a proposed employee leave request against "
                "recorded leave balance, eligibility and policy. "
                "When the employee provides leave dates, pass start_date "
                "and end_date in YYYY-MM-DD format so existing PENDING "
                "and APPROVED requests can be checked for date overlaps "
                "across all leave types. Does not submit or approve leave."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string"
                    },
                    "leave_type": {
                        "type": "string"
                    },
                    "requested_days": {
                        "type": "number"
                    },
                    "start_date": {
                        "type": "string",
                        "description": (
                            "Optional leave start date in YYYY-MM-DD format."
                        )
                    },
                    "end_date": {
                        "type": "string",
                        "description": (
                            "Optional leave end date in YYYY-MM-DD format."
                        )
                    }
                },
                "required": [
                    "employee_id",
                    "leave_type",
                    "requested_days"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "hr_business_scenarios",
            "description": (
                "Retrieve predefined HR business scenarios "
                "and expected agent behavior."
            ),
            "parameters": empty_parameters()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "project_workforce_risks",
            "description": (
                "Assess active project staffing, minimum coverage "
                "and critical resource risks using explainable risk scoring."
            ),
            "parameters": empty_parameters()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "employee_workforce_risks",
            "description": (
                "Assess employee allocation and multi-project workload "
                "risks using explainable risk scoring."
            ),
            "parameters": empty_parameters()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_predictive_analysis",
            "description": (
                "Run the complete predictive workforce risk assessment "
                "for projects and employees."
            ),
            "parameters": empty_parameters()
        }
    }
]


AVAILABLE_FUNCTIONS = {
    "organizational_audit": organizational_audit,
    "approval_routing_audit": approval_routing_audit,
    "workforce_overview": workforce_overview,
    "project_staffing_analysis": project_staffing_analysis,
    "employee_workload_analysis": employee_workload_analysis,
    "critical_resource_analysis": critical_resource_analysis,
    "complete_workforce_analysis": complete_workforce_analysis,
    "employee_hr_context": employee_hr_context,
    "leave_workflow_review": leave_workflow_review,
    "hr_business_scenarios": hr_business_scenarios,
    "project_workforce_risks": project_workforce_risks,
    "employee_workforce_risks": employee_workforce_risks,
    "complete_predictive_analysis": complete_predictive_analysis,
}


# =====================================================
# CENTRAL NEXORA AI ORCHESTRATOR
# =====================================================

SYSTEM_PROMPT = """
You are Nexora, an AI Workforce Intelligence and HR Orchestration Agent.

You coordinate five capabilities:

1. Organizational Intelligence
2. Approval Routing Intelligence
3. Workforce Intelligence
4. Context-Aware HR Workflow Intelligence
5. Predictive Workforce Intelligence

PREDICTIVE INTELLIGENCE:
- Use project_workforce_risks for project risk questions.
- Use employee_workforce_risks for employee workload risk questions.
- Use complete_predictive_analysis for comprehensive workforce risk analysis.

IMPORTANT RULES:
- Retrieve actual database information using tools.
- Never invent employee records, statistics, scores or predictions.
- Use the exact risk scores and risk levels returned by the tools.
- Do not change or reinterpret the scoring methodology.
- Explain risk factors only when supported by tool results.
- Distinguish risk indicators from confirmed events.
- The predictive service uses explainable rule-based scoring, not a trained forecasting model.
- Do not claim that a project will fail or an employee will leave based only on risk indicators.
- Summarized tool results may contain only the highest-risk records.
- Respect total record counts and risk-level counts provided in summaries.
- Do not treat omitted records as zero-risk records.
- Recommend preventive actions based on verified findings.
- Recommend human review for sensitive HR decisions.

LEAVE WORKFLOW RULES:
- Use leave_workflow_review to check employee leave balance and policy eligibility.
- If the employee provides start and end dates, pass both exact dates to leave_workflow_review in YYYY-MM-DD format.
- Report date-conflict results only when the tool confirms that the date-conflict check was performed.
- Treat overlapping PENDING and APPROVED leave requests as conflicts.
- Do not treat REJECTED or CANCELLED requests as conflicts.
- If dates are not provided, explain that date-conflict validation has not been performed.
- Never claim a leave request has been submitted or approved unless a tool explicitly confirms that action.
- Never approve leave or modify employee records.
"""


def ask_nexora(question: str) -> str:

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]

    for _ in range(5):

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=1500,
            temperature=0
        )

        assistant_message = response.choices[0].message

        if not assistant_message.tool_calls:
            return assistant_message.content or "No response generated."

        messages.append(
            assistant_message.model_dump(exclude_none=True)
        )

        for tool_call in assistant_message.tool_calls:

            function_name = tool_call.function.name

            arguments = json.loads(
                tool_call.function.arguments or "{}"
            )

            if function_name not in AVAILABLE_FUNCTIONS:
                tool_result = {"error": "Unknown tool"}

            else:
                try:
                    raw_result = AVAILABLE_FUNCTIONS[
                        function_name
                    ](**arguments)

                    tool_result = compact_tool_result(raw_result)

                except Exception as error:
                    tool_result = {
                        "error": str(error),
                        "tool": function_name
                    }

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(
                    tool_result,
                    default=str
                )
            })

    return (
        "The agent reached its tool-call limit. "
        "Please try a more specific question."
    )
