
from sqlalchemy import text
from sqlalchemy.orm import Session


def run_organizational_audit(db: Session):
    """
    Identify organizational structure inconsistencies,
    reporting relationship problems, and manager assignment risks.
    """

    query = text("""
        WITH relationship_counts AS (
            SELECT
                employee_id,
                COUNT(*) AS current_relationship_count
            FROM organizational_relationships
            WHERE is_current = TRUE
            GROUP BY employee_id
        )

        SELECT
            e.employee_id,
            e.department_id AS employee_department,
            e.manager_id AS employee_manager,

            m.department_id AS manager_department,
            m.is_active AS manager_active,

            r.department_id AS relationship_department,
            r.manager_id AS relationship_manager,

            COALESCE(rc.current_relationship_count, 0)
                AS current_relationship_count

        FROM employees e

        LEFT JOIN managers m
            ON e.manager_id = m.manager_id

        LEFT JOIN relationship_counts rc
            ON e.employee_id = rc.employee_id

        LEFT JOIN LATERAL (
            SELECT
                department_id,
                manager_id
            FROM organizational_relationships
            WHERE employee_id = e.employee_id
              AND is_current = TRUE
            ORDER BY valid_from DESC
            LIMIT 1
        ) r ON TRUE

        ORDER BY e.employee_id
    """)

    rows = db.execute(query).mappings().all()

    issues = []

    for row in rows:

        employee_id = row["employee_id"]

        relationship_count = row["current_relationship_count"]

        if relationship_count == 0:
            issues.append({
                "employee_id": employee_id,
                "issue": "Missing current organizational relationship",
                "severity": "High"
            })

        elif relationship_count > 1:
            issues.append({
                "employee_id": employee_id,
                "issue": "Multiple current organizational relationships",
                "severity": "High"
            })

        if not row["employee_manager"]:
            issues.append({
                "employee_id": employee_id,
                "issue": "Missing assigned manager",
                "severity": "High"
            })

        elif row["manager_active"] is None:
            issues.append({
                "employee_id": employee_id,
                "manager_id": row["employee_manager"],
                "issue": "Assigned manager does not exist in managers table",
                "severity": "High"
            })

        elif row["manager_active"] is False:
            issues.append({
                "employee_id": employee_id,
                "manager_id": row["employee_manager"],
                "issue": "Assigned manager is inactive",
                "severity": "High"
            })

        if (
            row["relationship_manager"] is not None
            and row["employee_manager"] is not None
            and str(row["relationship_manager"])
            != str(row["employee_manager"])
        ):
            issues.append({
                "employee_id": employee_id,
                "assigned_manager": row["employee_manager"],
                "expected_manager": row["relationship_manager"],
                "issue": "Manager mismatch between employee and organizational relationship",
                "severity": "High"
            })

        if (
            row["relationship_department"] is not None
            and row["employee_department"] is not None
            and str(row["relationship_department"])
            != str(row["employee_department"])
        ):
            issues.append({
                "employee_id": employee_id,
                "employee_department": row["employee_department"],
                "expected_department": row["relationship_department"],
                "issue": "Department mismatch",
                "severity": "Medium"
            })

    severity_summary = {
        "high": sum(
            1 for issue in issues
            if issue["severity"] == "High"
        ),
        "medium": sum(
            1 for issue in issues
            if issue["severity"] == "Medium"
        ),
        "low": sum(
            1 for issue in issues
            if issue["severity"] == "Low"
        )
    }

    return {
        "analysis": "Organizational structure audit completed.",
        "employees_analyzed": len(rows),
        "total_issues": len(issues),
        "severity_summary": severity_summary,
        "issues": issues
    }


def run_approval_routing_audit(db: Session):
    """
    Identify leave approval routing problems,
    missing managers, inactive managers, and historical mismatches.
    """

    query = text("""
        SELECT
            lr.request_id,
            lr.employee_id,
            lr.request_status,
            lr.submitted_date,
            lr.manager_id_at_submission,

            e.manager_id AS current_manager_id,

            m.is_active AS assigned_manager_active,

            historical.manager_id AS expected_manager_id

        FROM leave_requests lr

        LEFT JOIN employees e
            ON lr.employee_id = e.employee_id

        LEFT JOIN managers m
            ON lr.manager_id_at_submission = m.manager_id

        LEFT JOIN LATERAL (
            SELECT
                r.manager_id

            FROM organizational_relationships r

            WHERE r.employee_id = lr.employee_id

              AND r.valid_from::date <= lr.submitted_date::date

              AND (
                  r.valid_to IS NULL
                  OR r.valid_to::date >= lr.submitted_date::date
              )

            ORDER BY r.valid_from::date DESC

            LIMIT 1

        ) historical ON TRUE

        ORDER BY lr.request_id
    """)

    rows = db.execute(query).mappings().all()

    issues = []

    analyzed_requests = 0

    for row in rows:

        status = (
            row["request_status"] or ""
        ).strip().upper()

        if status not in (
            "PENDING",
            "PENDING APPROVAL",
            "APPROVED"
        ):
            continue

        analyzed_requests += 1

        manager_id = row["manager_id_at_submission"]
        expected_manager = row["expected_manager_id"]

        if not manager_id:
            issues.append({
                "request_id": row["request_id"],
                "employee_id": row["employee_id"],
                "issue": "Missing approval manager",
                "severity": "High"
            })

            continue

        if row["assigned_manager_active"] is None:
            issues.append({
                "request_id": row["request_id"],
                "employee_id": row["employee_id"],
                "manager_id": manager_id,
                "issue": "Assigned approval manager not found",
                "severity": "High"
            })

        elif row["assigned_manager_active"] is False:
            issues.append({
                "request_id": row["request_id"],
                "employee_id": row["employee_id"],
                "manager_id": manager_id,
                "issue": "Assigned approval manager is inactive",
                "severity": "High"
            })

        if (
            expected_manager is not None
            and str(manager_id) != str(expected_manager)
        ):
            issues.append({
                "request_id": row["request_id"],
                "employee_id": row["employee_id"],
                "assigned_manager": manager_id,
                "expected_manager": expected_manager,
                "issue": "Historical approval manager mismatch",
                "severity": "High"
            })

    return {
        "analysis": "Leave approval routing audit completed.",
        "requests_analyzed": analyzed_requests,
        "total_issues": len(issues),
        "issues": issues
    }
