
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_employee_hr_context(db: Session, employee_id: str):
    """Retrieve employee profile, manager, leave balances and requests."""

    employee_query = text("""
        SELECT
            e.employee_id,
            e.first_name,
            e.last_name,
            e.department_id,
            e.job_title,
            e.employment_type,
            e.employment_status,
            e.hire_date,
            e.location,
            e.manager_id,
            e.role,
            m.is_active AS manager_active,
            m.manager_title,
            m.management_level
        FROM employees e
        LEFT JOIN managers m ON e.manager_id = m.manager_id
        WHERE e.employee_id = :employee_id
    """)

    employee = db.execute(
        employee_query,
        {"employee_id": employee_id}
    ).mappings().first()

    if not employee:
        return {
            "found": False,
            "message": f"No employee found with ID {employee_id}."
        }

    balance_query = text("""
        SELECT
            lb.leave_type,
            lb.leave_year,
            lb.entitled_days,
            lb.used_days,
            lb.pending_days,
            lb.available_days,
            lb.eligibility_status,
            lb.reserved_days,
            lb.insufficient_balance,
            lb.accounting_status,
            lp.description AS policy_description
        FROM leave_balances lb
        LEFT JOIN leave_policies lp
            ON lb.policy_id = lp.policy_id
        WHERE lb.employee_id = :employee_id
        ORDER BY lb.leave_year DESC, lb.leave_type
    """)

    balances = db.execute(
        balance_query,
        {"employee_id": employee_id}
    ).mappings().all()

    requests_query = text("""
        SELECT
            request_id,
            leave_type,
            start_date,
            end_date,
            requested_days,
            request_status,
            manager_id_at_submission,
            submitted_date,
            approval_date,
            rejection_reason
        FROM leave_requests
        WHERE employee_id = :employee_id
        ORDER BY submitted_date DESC
        LIMIT 20
    """)

    requests = db.execute(
        requests_query,
        {"employee_id": employee_id}
    ).mappings().all()

    return {
        "found": True,
        "employee": dict(employee),
        "leave_balances": [dict(row) for row in balances],
        "leave_requests": [dict(row) for row in requests]
    }


def review_leave_workflow(
    db: Session,
    employee_id: str,
    leave_type: str,
    requested_days: float,
    start_date: str = None,
    end_date: str = None
):
    """
    Validate leave balance, eligibility, policy, date conflicts
    and approval readiness.

    Does not submit or approve leave.
    """

    if requested_days <= 0:
        return {
            "error": "Requested leave days must be greater than zero."
        }

    if not leave_type or not leave_type.strip():
        return {
            "error": "Leave type must be provided."
        }

    # DATE VALIDATION

    parsed_start_date = None
    parsed_end_date = None

    if (start_date is None) != (end_date is None):
        return {
            "error": "Both start_date and end_date must be provided."
        }

    if start_date is not None:
        try:
            parsed_start_date = date.fromisoformat(str(start_date))
            parsed_end_date = date.fromisoformat(str(end_date))
        except (ValueError, TypeError):
            return {
                "error": "Dates must use YYYY-MM-DD format."
            }

        if parsed_end_date < parsed_start_date:
            return {
                "error": "End date cannot be before start date."
            }

    # EMPLOYEE LOOKUP

    employee_query = text("""
        SELECT
            employee_id,
            first_name,
            last_name,
            department_id,
            job_title,
            employment_status,
            hire_date,
            manager_id
        FROM employees
        WHERE employee_id = :employee_id
    """)

    employee = db.execute(
        employee_query,
        {"employee_id": employee_id}
    ).mappings().first()

    if not employee:
        return {
            "found": False,
            "message": "Employee not found."
        }

    employee_name = (
        f'{employee["first_name"] or ""} '
        f'{employee["last_name"] or ""}'.strip()
    )

    if (employee["employment_status"] or "").strip().lower() != "active":
        return {
            "found": True,
            "workflow_status": "REQUIRES_HR_REVIEW",
            "employee_id": employee_id,
            "employee_name": employee_name,
            "reason": "Employee is not currently marked as active."
        }

    # LEAVE BALANCE LOOKUP

    balance_query = text("""
        SELECT *
        FROM leave_balances
        WHERE employee_id = :employee_id
          AND REGEXP_REPLACE(
                LOWER(TRIM(leave_type)),
                '\\s+leave$',
                ''
              ) =
              REGEXP_REPLACE(
                LOWER(TRIM(:leave_type)),
                '\\s+leave$',
                ''
              )
        ORDER BY leave_year DESC
        LIMIT 1
    """)

    balance = db.execute(
        balance_query,
        {
            "employee_id": employee_id,
            "leave_type": leave_type
        }
    ).mappings().first()

    # DATE-CONFLICT CHECK

    conflicting_requests = []

    if parsed_start_date and parsed_end_date:

        conflict_query = text("""
            SELECT
                request_id,
                leave_type,
                start_date,
                end_date,
                requested_days,
                request_status
            FROM leave_requests
            WHERE employee_id = :employee_id
              AND UPPER(TRIM(request_status))
                    IN ('PENDING', 'APPROVED')
              AND start_date IS NOT NULL
              AND end_date IS NOT NULL
              AND start_date <= :requested_end_date
              AND end_date >= :requested_start_date
            ORDER BY start_date
        """)

        conflict_rows = db.execute(
            conflict_query,
            {
                "employee_id": employee_id,
                "requested_start_date": parsed_start_date,
                "requested_end_date": parsed_end_date
            }
        ).mappings().all()

        conflicting_requests = [
            dict(row) for row in conflict_rows
        ]

    # MISSING BALANCE

    if not balance:

        reasons = ["No matching leave balance record was found."]

        if conflicting_requests:
            reasons.append(
                "Existing pending or approved leave requests "
                "overlap with the requested dates."
            )

        return {
            "found": True,
            "workflow_status": "REQUIRES_HR_REVIEW",
            "employee_id": employee_id,
            "employee_name": employee_name,
            "leave_type": leave_type,
            "requested_days": requested_days,
            "requested_start_date": parsed_start_date,
            "requested_end_date": parsed_end_date,
            "date_conflict_check_performed": (
                parsed_start_date is not None
            ),
            "has_date_conflicts": bool(conflicting_requests),
            "conflicting_requests": conflicting_requests,
            "reasons_for_review": reasons,
            "submission_ready": False,
            "decision": "Leave balance verification is required."
        }

    # POLICY LOOKUP

    policy_query = text("""
        SELECT *
        FROM leave_policies
        WHERE policy_id = :policy_id
    """)

    policy = db.execute(
        policy_query,
        {"policy_id": balance["policy_id"]}
    ).mappings().first()

    available_days = float(balance["available_days"] or 0)

    max_consecutive = (
        float(policy["max_consecutive_days"])
        if policy and policy["max_consecutive_days"] is not None
        else None
    )

    reasons = []
    next_steps = []

    # BALANCE AND ELIGIBILITY

    if balance["insufficient_balance"] is True:
        reasons.append(
            "The balance record flags insufficient leave balance."
        )

    if requested_days > available_days:
        reasons.append(
            "Requested days exceed recorded available leave balance."
        )

    if (
        max_consecutive is not None
        and requested_days > max_consecutive
    ):
        reasons.append(
            "Requested days exceed the policy's maximum consecutive days."
        )

    eligibility = (
        (balance["eligibility_status"] or "").strip().lower()
    )

    if eligibility not in ("eligible", "active", "approved"):
        reasons.append(
            "The recorded leave eligibility status requires verification."
        )

    # DATE CONFLICTS

    if conflicting_requests:
        reasons.append(
            "Existing pending or approved leave requests "
            "overlap with the requested dates."
        )

        next_steps.append(
            "Review the overlapping leave requests."
        )

    # APPROVAL REQUIREMENTS

    manager_approval_required = (
        policy is not None
        and str(policy["manager_approval_required"]).strip().lower()
        in ("yes", "true", "required")
    )

    hr_approval_required = (
        policy is not None
        and str(policy["hr_approval_required"]).strip().lower()
        in ("yes", "true", "required")
    )

    manager_assigned = bool(employee["manager_id"])

    approval_blocked = (
        manager_approval_required and not manager_assigned
    )

    if approval_blocked:
        next_steps.append(
            "An authorized manager must be assigned before "
            "approval routing can proceed."
        )

    if manager_approval_required and manager_assigned:
        next_steps.append(
            "Route the request to the assigned manager."
        )

    if hr_approval_required:
        next_steps.append(
            "Include HR approval in the workflow."
        )

    # DOCUMENTATION REQUIREMENTS

    if policy and str(
        policy["requires_documentation"]
    ).strip().lower() in ("yes", "true", "required"):
        next_steps.append(
            "Check whether required supporting documentation is provided."
        )

    # PRELIMINARY VALIDATION STATUS

    if reasons:
        validation_status = "REQUIRES_HR_REVIEW"
    else:
        validation_status = "PRELIMINARY_CHECK_PASSED"

    # FINAL WORKFLOW STATUS

    if reasons:
        workflow_status = "REQUIRES_HR_REVIEW"
    elif approval_blocked:
        workflow_status = "BLOCKED_MISSING_APPROVER"
    else:
        workflow_status = "PRELIMINARY_CHECK_PASSED"

    submission_ready = (
        not reasons
        and not approval_blocked
    )

    if not next_steps and submission_ready:
        next_steps.append(
            "The preliminary checks passed. Follow the official "
            "submission and approval process."
        )

    return {
        "found": True,
        "workflow_status": workflow_status,
        "validation_status": validation_status,
        "employee_id": employee_id,
        "employee_name": employee_name,
        "leave_type": leave_type,
        "requested_days": requested_days,
        "requested_start_date": parsed_start_date,
        "requested_end_date": parsed_end_date,
        "available_days": available_days,
        "eligibility_status": balance["eligibility_status"],
        "policy_id": balance["policy_id"],
        "policy_max_consecutive_days": max_consecutive,
        "date_conflict_check_performed": (
            parsed_start_date is not None
        ),
        "has_date_conflicts": bool(conflicting_requests),
        "conflicting_requests": conflicting_requests,
        "manager_id": employee["manager_id"],
        "manager_assigned": manager_assigned,
        "manager_approval_required": manager_approval_required,
        "hr_approval_required": hr_approval_required,
        "approval_blocked": approval_blocked,
        "submission_ready": submission_ready,
        "reasons_for_review": reasons,
        "recommended_next_steps": next_steps,
        "decision": (
            "Preliminary validation passed, but approval routing "
            "is blocked because no authorized manager is assigned."
            if approval_blocked and not reasons
            else
            "This is a preliminary workflow assessment, not a "
            "leave approval or submission."
        )
    }


def get_hr_business_scenarios(db: Session):
    """Retrieve predefined HR scenarios for workflow guidance."""

    result = db.execute(text("""
        SELECT
            scenario_id,
            scenario_type,
            title,
            description,
            employee_ids,
            request_ids,
            project_ids,
            expected_agent_behavior,
            severity
        FROM business_scenarios
        ORDER BY severity, scenario_id
    """))

    result_rows = result.mappings().all()

    return {
        "scenario_count": len(result_rows),
        "scenarios": [
            dict(row) for row in result_rows
        ]
    }
