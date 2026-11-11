
import pandas as pd
from pathlib import Path

# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "generated"
SCENARIO_DIR = BASE_DIR / "data" / "scenarios"


# --------------------------------------------------
# 2. Load datasets
# --------------------------------------------------

def load_dataset(filename, directory=DATA_DIR):

    file_path = directory / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"Required dataset not found: {file_path}"
        )

    return pd.read_csv(file_path)


departments = load_dataset("departments.csv")
employees = load_dataset("employees.csv")
managers = load_dataset("managers.csv")
relationships = load_dataset("organizational_relationships.csv")
policies = load_dataset("leave_policies.csv")
balances = load_dataset("leave_balances.csv")
requests = load_dataset("leave_requests.csv")
projects = load_dataset("projects.csv")
assignments = load_dataset("project_assignments.csv")

scenarios = load_dataset(
    "business_scenarios.csv",
    SCENARIO_DIR
)

errors = []
warnings = []


# --------------------------------------------------
# 3. Employee integrity
# --------------------------------------------------

if departments["department_id"].duplicated().any():
    errors.append("Duplicate department IDs found.")

if employees["employee_id"].duplicated().any():
    errors.append("Duplicate employee IDs found.")

if not employees["department_id"].isin(
    departments["department_id"]
).all():
    errors.append("Employees reference invalid departments.")

print("Employee integrity checked.")


# --------------------------------------------------
# 4. Manager integrity
# --------------------------------------------------

if managers["manager_id"].duplicated().any():
    errors.append("Duplicate manager IDs found.")

if not managers["manager_id"].isin(
    employees["employee_id"]
).all():
    errors.append("Manager records reference invalid employees.")

manager_ids = set(managers["manager_id"])
employee_ids = set(employees["employee_id"])

assigned_managers = set(
    employees["manager_id"].dropna()
)

if not assigned_managers.issubset(manager_ids):
    errors.append("Some employees reference nonexistent managers.")

manager_details = employees[
    employees["employee_id"].isin(manager_ids)
]

if not (
    (manager_details["employment_status"] == "Active")
    & (manager_details["employment_type"] == "Full-time")
).all():
    warnings.append(
        "Some managers are not active full-time employees."
    )

print("Manager integrity checked.")


# --------------------------------------------------
# 5. Organizational relationship integrity
# --------------------------------------------------

if relationships["relationship_id"].duplicated().any():
    errors.append("Duplicate organizational relationship IDs.")

if not relationships["employee_id"].isin(employee_ids).all():
    errors.append("Invalid employee IDs in organizational history.")

current_relationships = relationships[
    relationships["is_current"] == True
]

current_counts = current_relationships.groupby(
    "employee_id"
).size()

if not (current_counts == 1).all():
    errors.append(
        "Some employees have multiple current relationships."
    )

if set(current_relationships["employee_id"]) != employee_ids:
    errors.append(
        "Some employees are missing a current relationship."
    )

for _, row in current_relationships.iterrows():

    employee = employees[
        employees["employee_id"] == row["employee_id"]
    ].iloc[0]

    if row["department_id"] != employee["department_id"]:
        errors.append(
            f"Department mismatch: {row['employee_id']}"
        )

    current_manager = row["manager_id"]
    employee_manager = employee["manager_id"]

    if pd.isna(current_manager) and pd.isna(employee_manager):
        continue

    if current_manager != employee_manager:
        errors.append(
            f"Manager mismatch: {row['employee_id']}"
        )

print("Organizational integrity checked.")


# --------------------------------------------------
# 6. Leave policy and balance integrity
# --------------------------------------------------

if policies["policy_id"].duplicated().any():
    errors.append("Duplicate leave policy IDs.")

if not balances["employee_id"].isin(employee_ids).all():
    errors.append("Invalid employee IDs in leave balances.")

if not balances["policy_id"].isin(
    policies["policy_id"]
).all():
    errors.append("Invalid policy IDs in leave balances.")

if balances.duplicated(
    subset=["employee_id", "policy_id", "leave_year"]
).any():
    errors.append("Duplicate employee leave balance records.")

# Check required balance columns
balance_required_columns = [
    "entitled_days",
    "used_days",
    "pending_days",
    "reserved_days",
    "available_days"
]

for column in balance_required_columns:
    if column not in balances.columns:
        errors.append(
            f"Missing required leave balance column: {column}"
        )

# Perform calculations only if required columns exist
if all(
    column in balances.columns
    for column in balance_required_columns
):

    numeric_columns = balance_required_columns

    for column in numeric_columns:
        balances[column] = pd.to_numeric(
            balances[column], errors="coerce"
        )

    if balances[numeric_columns].isna().any().any():
        errors.append(
            "Missing or invalid numeric values in leave balances."
        )

    else:

        expected_available = (
            balances["entitled_days"]
            - balances["used_days"]
            - balances["pending_days"]
            - balances["reserved_days"]
        )

        if not (
            expected_available.round(2)
            == balances["available_days"].round(2)
        ).all():
            errors.append(
                "Incorrect leave balance calculations."
            )

        negative_balances = (
            balances["available_days"] < 0
        ).sum()

        if negative_balances > 0:
            warnings.append(
                f"{negative_balances} leave balance records "
                "have insufficient entitlement. "
                "Flagged for HR review."
            )

print("Leave balance integrity checked.")


# --------------------------------------------------
# 7. Leave request integrity
# --------------------------------------------------

if requests["request_id"].duplicated().any():
    errors.append("Duplicate leave request IDs.")

if not requests["employee_id"].isin(employee_ids).all():
    errors.append("Invalid employees in leave requests.")

if not requests["policy_id"].isin(
    policies["policy_id"]
).all():
    errors.append("Invalid policies in leave requests.")

valid_statuses = {
    "PENDING", "APPROVED", "REJECTED", "CANCELLED"
}

requests["request_status"] = (
    requests["request_status"].astype(str).str.strip().str.upper()
)

if not requests["request_status"].isin(valid_statuses).all():
    errors.append("Invalid leave request statuses.")

request_start = pd.to_datetime(
    requests["start_date"], errors="coerce"
)

request_end = pd.to_datetime(
    requests["end_date"], errors="coerce"
)

if request_start.isna().any() or request_end.isna().any():
    errors.append("Invalid or missing leave request dates.")

elif not (request_start <= request_end).all():
    errors.append("Invalid leave request date ranges.")

if (
    (requests["request_status"] == "PENDING")
    & requests["approval_date"].notna()
).any():
    errors.append(
        "Pending leave requests have approval dates."
    )

request_managers = set(
    requests["manager_id_at_submission"].dropna()
)

if not request_managers.issubset(manager_ids):
    warnings.append(
        "Some leave requests have invalid manager references."
    )

print("Leave request integrity checked.")


# --------------------------------------------------
# 8. Project integrity
# --------------------------------------------------

if projects["project_id"].duplicated().any():
    errors.append("Duplicate project IDs.")

if not projects["department_id"].isin(
    departments["department_id"]
).all():
    errors.append("Projects reference invalid departments.")

if not projects["project_lead_id"].isin(
    manager_ids
).all():
    errors.append("Invalid project leads.")

if assignments["assignment_id"].duplicated().any():
    errors.append("Duplicate assignment IDs.")

if not assignments["employee_id"].isin(employee_ids).all():
    errors.append("Invalid employees in project assignments.")

if not assignments["project_id"].isin(
    projects["project_id"]
).all():
    errors.append("Invalid project references in assignments.")

allocation_totals = assignments.groupby(
    "employee_id"
)["allocation_percentage"].sum()

if (allocation_totals > 100).any():
    errors.append("Employee project allocation exceeds 100%.")

print("Project integrity checked.")


# --------------------------------------------------
# 9. Business scenario integrity
# --------------------------------------------------

if scenarios["scenario_id"].duplicated().any():
    errors.append("Duplicate business scenario IDs.")

if scenarios["expected_agent_behavior"].isna().any():
    errors.append("Missing expected agent behavior.")

if len(scenarios) != 5:
    warnings.append(
        f"Expected 5 business scenarios; found {len(scenarios)}."
    )

print("Business scenario integrity checked.")


# --------------------------------------------------
# 10. Final validation report
# --------------------------------------------------

print("\n" + "=" * 55)
print("NEXORA TECHNOLOGIES - DATA QUALITY REPORT")
print("=" * 55)

print(f"Departments: {len(departments)}")
print(f"Employees: {len(employees)}")
print(f"Managers: {len(managers)}")
print(f"Organizational relationships: {len(relationships)}")
print(f"Leave policies: {len(policies)}")
print(f"Leave balances: {len(balances)}")
print(f"Leave requests: {len(requests)}")
print(f"Projects: {len(projects)}")
print(f"Project assignments: {len(assignments)}")
print(f"Business scenarios: {len(scenarios)}")

print(f"\nTotal errors: {len(errors)}")
print(f"Total warnings: {len(warnings)}")

if errors:
    print("\nERRORS:")
    for error in errors:
        print(f"- {error}")

if warnings:
    print("\nWARNINGS:")
    for warning in warnings:
        print(f"- {warning}")

if not errors:
    print("\nAll critical data integrity checks passed!")
else:
    print("\nData integrity validation failed.")
    raise SystemExit(1)
