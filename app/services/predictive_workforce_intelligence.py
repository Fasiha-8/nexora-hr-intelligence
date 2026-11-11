
from sqlalchemy import text
from sqlalchemy.orm import Session


# =====================================================
# PROJECT WORKFORCE RISK
# =====================================================

def predict_project_workforce_risks(db: Session):
    query = text("""
        SELECT
            p.project_id,
            p.project_name,
            p.department_id,
            p.priority,
            p.criticality,
            p.required_team_size,
            p.minimum_coverage,

            COUNT(DISTINCT CASE
                WHEN UPPER(pa.assignment_status) = 'ACTIVE'
                THEN pa.employee_id
            END) AS assigned_employees,

            COUNT(DISTINCT CASE
                WHEN UPPER(pa.assignment_status) = 'ACTIVE'
                 AND pa.is_critical_member = TRUE
                THEN pa.employee_id
            END) AS critical_employees

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
            p.required_team_size,
            p.minimum_coverage

        ORDER BY p.project_id
    """)

    rows = db.execute(query).mappings().all()
    predictions = []

    for row in rows:
        required = float(row["required_team_size"] or 0)
        assigned = int(row["assigned_employees"] or 0)
        critical = int(row["critical_employees"] or 0)
        minimum = float(row["minimum_coverage"] or 0)

        coverage = (
            assigned / required * 100
            if required > 0 else 100
        )

        score = 0
        factors = []

        if required > 0 and assigned < required:
            score += 35
            factors.append({
                "factor": "Staffing shortage",
                "points": 35,
                "triggered": True
            })

        if required > 0 and coverage < minimum:
            score += 25
            factors.append({
                "factor": "Below minimum coverage",
                "points": 25,
                "triggered": True
            })

        if critical == 1:
            score += 15
            factors.append({
                "factor": "Single critical employee dependency",
                "points": 15,
                "triggered": True
            })
        elif critical == 0:
            score += 10
            factors.append({
                "factor": "No active critical employee",
                "points": 10,
                "triggered": True
            })

        priority = str(row["priority"] or "").upper()
        criticality = str(row["criticality"] or "").upper()

        if priority in ("HIGH", "CRITICAL", "URGENT"):
            score += 10
            factors.append({
                "factor": "High project priority",
                "points": 10,
                "triggered": True
            })

        if criticality in ("HIGH", "CRITICAL"):
            score += 15
            factors.append({
                "factor": "High operational criticality",
                "points": 15,
                "triggered": True
            })

        score = min(score, 100)

        if score >= 70:
            risk_level = "HIGH"
        elif score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        recommendations = []

        if assigned < required:
            recommendations.append(
                "Allocate additional qualified employees "
                "to meet the required team size."
            )

        if coverage < minimum:
            recommendations.append(
                f"Improve staffing coverage to at least "
                f"{minimum}%."
            )

        if critical <= 1:
            recommendations.append(
                "Review critical-role backup and succession coverage."
            )

        if not recommendations:
            recommendations.append(
                "Continue monitoring staffing and resource allocation."
            )

        predictions.append({
            "project_id": row["project_id"],
            "project_name": row["project_name"],
            "department_id": row["department_id"],
            "priority": row["priority"],
            "criticality": row["criticality"],
            "required_team_size": required,
            "assigned_employees": assigned,
            "staffing_coverage_percentage": round(coverage, 2),
            "minimum_coverage_percentage": minimum,
            "critical_employees": critical,
            "staffing_gap": max(0, int(required - assigned)),
            "risk_score": score,
            "risk_level": risk_level,
            "risk_factors": factors,
            "risk_reasons": [
                factor["factor"]
                for factor in factors
            ],
            "recommendations": recommendations
        })

    return {
        "analysis": "Project workforce risk assessment completed.",
        "projects_analyzed": len(predictions),
        "high_risk_projects": sum(
            p["risk_level"] == "HIGH" for p in predictions
        ),
        "medium_risk_projects": sum(
            p["risk_level"] == "MEDIUM" for p in predictions
        ),
        "low_risk_projects": sum(
            p["risk_level"] == "LOW" for p in predictions
        ),
        "scoring_rules": {
            "staffing_shortage": 35,
            "below_minimum_coverage": 25,
            "single_critical_employee": 15,
            "no_critical_employee": 10,
            "high_priority": 10,
            "high_criticality": 15,
            "high_risk_threshold": 70,
            "medium_risk_threshold": 40
        },
        "predictions": predictions,
        "methodology": (
            "Explainable rule-based scoring using current staffing, "
            "minimum coverage, priority and criticality. "
            "Not a statistically trained forecasting model."
        )
    }


# =====================================================
# EMPLOYEE WORKFORCE RISK
# =====================================================

def predict_employee_workforce_risks(db: Session):
    query = text("""
        SELECT
            e.employee_id,
            e.first_name,
            e.last_name,
            e.job_title,
            e.department_id,

            COUNT(DISTINCT CASE
                WHEN UPPER(pa.assignment_status) = 'ACTIVE'
                THEN pa.project_id
            END) AS active_projects,

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
            e.department_id

        ORDER BY total_allocation DESC
    """)

    rows = db.execute(query).mappings().all()
    employees = []

    for row in rows:
        allocation = float(row["total_allocation"] or 0)
        project_count = int(row["active_projects"] or 0)

        score = 0
        reasons = []

        if allocation > 100:
            score += 60
            reasons.append(
                "Total active project allocation exceeds 100%."
            )

        elif allocation >= 90:
            score += 30
            reasons.append(
                "Employee allocation is close to full capacity."
            )

        if project_count >= 4:
            score += 25
            reasons.append(
                "Employee is assigned to four or more active projects."
            )

        elif project_count >= 3:
            score += 15
            reasons.append(
                "Employee is assigned to multiple active projects."
            )

        score = min(score, 100)

        if score >= 70:
            risk_level = "HIGH"
        elif score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # This is a separate utilization indicator,
        # not an additional risk-score factor.
        if project_count == 0:
            utilization_status = "UNASSIGNED"
        elif allocation > 100:
            utilization_status = "OVERALLOCATED"
        elif allocation >= 90:
            utilization_status = "NEAR_CAPACITY"
        else:
            utilization_status = "WITHIN_CAPACITY"

        employees.append({
            "employee_id": row["employee_id"],
            "employee_name": (
                f'{row["first_name"] or ""} '
                f'{row["last_name"] or ""}'.strip()
            ),
            "job_title": row["job_title"],
            "department_id": row["department_id"],
            "active_project_count": project_count,
            "total_allocation_percentage": round(allocation, 2),
            "utilization_status": utilization_status,
            "risk_score": score,
            "risk_level": risk_level,
            "risk_reasons": reasons
        })

    return {
        "analysis": "Employee workforce risk assessment completed.",
        "employees_analyzed": len(employees),
        "high_risk_employees": sum(
            e["risk_level"] == "HIGH" for e in employees
        ),
        "medium_risk_employees": sum(
            e["risk_level"] == "MEDIUM" for e in employees
        ),
        "low_risk_employees": sum(
            e["risk_level"] == "LOW" for e in employees
        ),
        "unassigned_employees": sum(
            e["utilization_status"] == "UNASSIGNED"
            for e in employees
        ),
        "overallocated_employees": sum(
            e["utilization_status"] == "OVERALLOCATED"
            for e in employees
        ),
        "scoring_rules": {
            "allocation_above_100_percent": 60,
            "allocation_90_to_100_percent": 30,
            "four_or_more_projects": 25,
            "three_projects": 15,
            "high_risk_threshold": 70,
            "medium_risk_threshold": 40
        },
        "employees": employees,
        "methodology": (
            "Explainable rule-based workload scoring using active "
            "project allocation and project count. "
            "Unassigned status is reported separately and does not "
            "automatically increase the risk score."
        )
    }


# =====================================================
# COMPLETE PREDICTIVE ANALYSIS
# =====================================================

def run_predictive_workforce_analysis(db: Session):
    project_risks = predict_project_workforce_risks(db)
    employee_risks = predict_employee_workforce_risks(db)

    return {
        "analysis": "Predictive workforce intelligence completed.",
        "project_risk_analysis": project_risks,
        "employee_risk_analysis": employee_risks,
        "overall_methodology": (
            "Explainable workforce risk scoring based on current "
            "database indicators. Not a trained forecasting model."
        )
    }
