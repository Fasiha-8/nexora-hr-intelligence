
import pandas as pd
import random
from pathlib import Path

random.seed(42)

# Project paths
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "generated"

# Load existing employee records
employees = pd.read_csv(DATA_DIR / "employees.csv")
departments = pd.read_csv(DATA_DIR / "departments.csv")

# Number of managers per department
manager_allocation = {
    "DEPT001": 2,
    "DEPT002": 4,
    "DEPT003": 2,
    "DEPT004": 2,
    "DEPT005": 3,
    "DEPT006": 2,
    "DEPT007": 2,
    "DEPT008": 3
}

# Manager job titles
manager_titles = {
    "DEPT001": "HR Manager",
    "DEPT002": "Engineering Manager",
    "DEPT003": "Finance Manager",
    "DEPT004": "Marketing Manager",
    "DEPT005": "Sales Manager",
    "DEPT006": "Operations Manager",
    "DEPT007": "Customer Support Manager",
    "DEPT008": "IT Manager"
}

# Initialize reporting relationships
employees["manager_id"] = None
employees["role"] = "EMPLOYEE"

manager_records = []

for department_id, manager_count in manager_allocation.items():

    department_employees = employees[
    (employees["department_id"] == department_id)
    & (employees["employment_status"] == "Active")
    & (employees["employment_type"] == "Full-time")

    ]

    if len(department_employees) <= manager_count:
        raise ValueError(
            f"Not enough employees in department {department_id}"
        )

    # Select managers from existing employees
    selected_managers = department_employees.sample(
        n=manager_count,
        random_state=42
    )

    manager_ids = selected_managers["employee_id"].tolist()

    # Update manager records
    for manager_id in manager_ids:

        employees.loc[
            employees["employee_id"] == manager_id,
            "role"
        ] = "MANAGER"

        employees.loc[
            employees["employee_id"] == manager_id,
            "job_title"
        ] = manager_titles[department_id]

        manager_records.append({
            "manager_id": manager_id,
            "department_id": department_id,
            "manager_title": manager_titles[department_id],
            "management_level": "DEPARTMENT_MANAGER",
            "is_active": True
        })

    # Assign remaining employees to managers
    non_managers = department_employees[
        ~department_employees["employee_id"].isin(manager_ids)
    ]

    for index, employee_id in enumerate(
        non_managers["employee_id"].tolist()
    ):

        assigned_manager = manager_ids[
            index % len(manager_ids)
        ]

        employees.loc[
            employees["employee_id"] == employee_id,
            "manager_id"
        ] = assigned_manager

# Create managers dataframe
managers_df = pd.DataFrame(manager_records)

# Validation checks
assert len(managers_df) == 20
assert managers_df["manager_id"].is_unique

# Every employee's manager must exist
valid_manager_ids = set(managers_df["manager_id"])

assigned_manager_ids = set(
    employees["manager_id"].dropna()
)

assert assigned_manager_ids.issubset(valid_manager_ids)

# Employees must not report to themselves
assert not (
    employees["employee_id"] == employees["manager_id"]
).any()

# Managers must belong to the same department as their reports
manager_departments = managers_df.set_index(
    "manager_id"
)["department_id"]

for _, employee in employees.dropna(
    subset=["manager_id"]
).iterrows():

    assert (
        employee["department_id"]
        == manager_departments[employee["manager_id"]]
    )

# Save updated datasets
managers_df.to_csv(
    DATA_DIR / "managers.csv",
    index=False
)

employees.to_csv(
    DATA_DIR / "employees.csv",
    index=False
)

print("Manager dataset generated successfully!")
print(f"Total managers: {len(managers_df)}")
print(f"Total employees: {len(employees)}")

print("\nManagers by department:")
print(
    managers_df.groupby("department_id").size()
)

print("\nSample manager records:")
print(managers_df.head(10).to_string(index=False))

print("\nSample employee reporting relationships:")
print(
    employees[
        ["employee_id", "department_id", "role", "manager_id"]
    ].head(15).to_string(index=False)
)

print("\nAll organizational hierarchy validations passed!")
