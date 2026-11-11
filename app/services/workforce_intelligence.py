
from sqlalchemy import text
from sqlalchemy.orm import Session


def run_project_staffing_analysis(db: Session):
    """
    Compare active project staffing against required team sizes.
    """

    query = text("""
        SELECT
            p.project_id,
            p.project_name,
            p.department_id,
            p.priority,
            p.criticality,
            p.required_team_size,
            COUNT(DISTINCT CASE
                WHEN UPPER(pa.assignment_status) = 'ACTIVE'
                THEN pa.employee_id
            END) AS assigned_team_size

        FROM projects p

        LEFT JOIN project_assignments pa
            ON p.project_id = pa.project_id

        WHERE UPPER(p.project_status) = 'ACTIVE'

        GROUP BY
            p.project_id,
            p.project_name,
            p.department_id,
            p.priority,
            p.criticality,
            p.required_team_size

        ORDER BY p.project_id
    """)

    rows = db.execute(query).mappings().all()

    projects = []
    understaffed = []

    for row in rows:
        required = float(row["required_team_size"] or 0)
        assigned = int(row["assigned_team_size"] or 0)

        shortage = max(0, required - assigned)

        result = {
            "project_id": row["project_id"],
            "project_name": row["project_name"],
            "department_id": row["department_id"],
            "priority": row["priority"],
            "criticality": row["criticality"],
            "required_team_size": required,
            "assigned_team_size": assigned,
            "staffing_shortage": shortage,
            "staffing_status": (
                "Understaffed" if shortage > 0 else "Adequately staffed"
            )
        }

        projects.append(result)

        if shortage > 0:
            understaffed.append(result)

    return {
        "analysis": "Project staffing analysis completed.",
        "active_projects_analyzed": len(projects),
        "understaffed_projects": len(understaffed),
        "projects": projects,
        "staffing_risks": understaffed
    }


def run_employee_workload_analysis(db: Session):
    """
    Analyze active employee assignments and allocation percentages.
    """

    query = text("""
        SELECT
            e.employee_id,
            e.first_name,
            e.last_name,
            e.job_title,
            e.department_id,
            e.employment_status,

            COUNT(DISTINCT CASE
                WHEN UPPER(pa.assignment_status) = 'ACTIVE'
                THEN pa.project_id
            END) AS active_project_count,

            COALESCE(SUM(
                CASE
                    WHEN UPPER(pa.assignment_status) = 'ACTIVE'
                    THEN pa.allocation_percentage
                    ELSE 0
                END
            ), 0) AS total_allocation

        FROM employees e

        LEFT JOIN project_assignments pa
            ON e.employee_id = pa.employee_id

        WHERE LOWER(e.employment_status) = 'active'

        GROUP BY
            e.employee_id,
            e.first_name,
            e.last_name,
            e.job_title,
            e.department_id,
            e.employment_status

        ORDER BY total_allocation DESC
    """)

    rows = db.execute(query).mappings().all()

    employees = []
    overallocated = []
    multiple_projects = []

    for row in rows:
        allocation = float(row["total_allocation"] or 0)
        project_count = int(row["active_project_count"] or 0)

        employee = {
            "employee_id": row["employee_id"],
            "employee_name": (
                f'{row["first_name"] or ""} {row["last_name"] or ""}'.strip()
            ),
            "job_title": row["job_title"],
            "department_id": row["department_id"],
            "active_project_count": project_count,
            "total_allocation_percentage": round(allocation, 2),
            "workload_status": (
                "Overallocated" if allocation > 100
                else "Within allocation limit"
            )
        }

        employees.append(employee)

        if allocation > 100:
            overallocated.append(employee)

        if project_count > 1:
            multiple_projects.append(employee)

    return {
        "analysis": "Employee workload analysis completed.",
        "active_employees_analyzed": len(employees),
        "overallocated_employees": len(overallocated),
        "employees_on_multiple_projects": len(multiple_projects),
        "overallocated": overallocated,
        "multiple_project_assignments": multiple_projects
    }


def run_critical_resource_analysis(db: Session):
    """
    Identify critical employees assigned to active projects.
    """

    query = text("""
        SELECT
            e.employee_id,
            e.first_name,
            e.last_name,
            e.job_title,

            p.project_id,
            p.project_name,
            p.priority,
            p.criticality,

            pa.role_in_project,
            pa.allocation_percentage,
            pa.is_critical_member

        FROM project_assignments pa

        JOIN employees e
            ON pa.employee_id = e.employee_id

        JOIN projects p
            ON pa.project_id = p.project_id

        WHERE UPPER(pa.assignment_status) = 'ACTIVE'
          AND UPPER(p.project_status) = 'ACTIVE'
          AND pa.is_critical_member = TRUE
          AND LOWER(e.employment_status) = 'active'

        ORDER BY
            p.criticality DESC,
            p.priority DESC,
            e.employee_id
    """)

    rows = db.execute(query).mappings().all()

    resources = []

    for row in rows:
        resources.append({
            "employee_id": row["employee_id"],
            "employee_name": (
                f'{row["first_name"] or ""} {row["last_name"] or ""}'.strip()
            ),
            "job_title": row["job_title"],
            "project_id": row["project_id"],
            "project_name": row["project_name"],
            "priority": row["priority"],
            "criticality": row["criticality"],
            "role_in_project": row["role_in_project"],
            "allocation_percentage": float(
                row["allocation_percentage"] or 0
            )
        })

    unique_employees = len({
        resource["employee_id"] for resource in resources
    })

    return {
        "analysis": "Critical workforce resource analysis completed.",
        "critical_assignments": len(resources),
        "unique_critical_employees": unique_employees,
        "resources": resources
    }


def run_workforce_intelligence(db: Session):
    """
    Run all three workforce intelligence analyses.
    """

    staffing = run_project_staffing_analysis(db)
    workload = run_employee_workload_analysis(db)
    critical = run_critical_resource_analysis(db)

    return {
        "analysis": "Workforce intelligence analysis completed.",
        "project_staffing": staffing,
        "employee_workload": workload,
        "critical_resources": critical
    }
