
import pandas as pd
import random
from pathlib import Path

random.seed(42)

# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "generated"

EMPLOYEE_FILE = DATA_DIR / "employees.csv"
PROJECT_FILE = DATA_DIR / "projects.csv"
OUTPUT_FILE = DATA_DIR / "project_assignments.csv"

if OUTPUT_FILE.exists():
    raise FileExistsError(
        "project_assignments.csv already exists. "
        "Remove it intentionally before regenerating."
    )

# --------------------------------------------------
# 2. Load existing datasets
# --------------------------------------------------

employees = pd.read_csv(EMPLOYEE_FILE)
projects = pd.read_csv(PROJECT_FILE)

# Select active employees
active_employees = employees[
    employees["employment_status"] == "Active"
].copy()

# --------------------------------------------------
# 3. Prepare project lookup
# --------------------------------------------------

project_lookup = {}

for _, project in projects.iterrows():

    department_id = project["department_id"]

    if department_id not in project_lookup:
        project_lookup[department_id] = []

    project_lookup[department_id].append(project)

# --------------------------------------------------
# 4. Define project responsibilities
# --------------------------------------------------

project_roles = [
    "Technical Lead",
    "Software Engineer",
    "Backend Developer",
    "Frontend Developer",
    "QA Engineer",
    "Business Analyst",
    "Project Coordinator",
    "Data Analyst",
    "Operations Specialist",
    "Support Specialist",
    "Security Engineer",
    "Project Manager"
]

assignments = []
assignment_counter = 1

# Track employee allocation across projects
employee_allocations = {}

# --------------------------------------------------
# 5. Generate employee-project assignments
# --------------------------------------------------

for _, employee in active_employees.iterrows():

    employee_id = employee["employee_id"]
    department_id = employee["department_id"]

    available_projects = project_lookup.get(
        department_id, []
    )

    if not available_projects:
        raise ValueError(
            f"No project found for department {department_id}"
        )

    # Every active employee receives at least one assignment
    selected_projects = [
        random.choice(available_projects)
    ]

    # Some employees participate in a second project
    if len(available_projects) > 1 and random.random() < 0.25:

        remaining_projects = [
            p for p in available_projects
            if p["project_id"] != selected_projects[0]["project_id"]
        ]

        selected_projects.append(
            random.choice(remaining_projects)
        )

    employee_allocations[employee_id] = 0

    for project in selected_projects:

        project_id = project["project_id"]

        # Allocation must never exceed 100%
        remaining_allocation = (
            100 - employee_allocations[employee_id]
        )

        if remaining_allocation < 15:
            continue

        allocation = min(
            random.choice([20, 25, 30, 40, 50, 60]),
            remaining_allocation
        )

        employee_allocations[employee_id] += allocation

        # Project responsibility
        role = random.choice(project_roles)

        # Project leads receive their leadership role
        if employee_id == project["project_lead_id"]:
            role = "Project Lead"

        # Critical project membership
        is_critical = (
            project["criticality"] == "Critical"
            and (
                role in [
                    "Project Lead",
                    "Technical Lead",
                    "Security Engineer"
                ]
                or random.random() < 0.30
            )
        )

        assignments.append({
            "assignment_id": f"ASG{assignment_counter:05d}",
            "employee_id": employee_id,
            "project_id": project_id,
            "department_id": department_id,
            "role_in_project": role,
            "allocation_percentage": allocation,
            "assignment_start_date": project["start_date"],
            "assignment_end_date": project["deadline"],
            "is_critical_member": is_critical,
            "assignment_status": (
                "ACTIVE"
                if project["project_status"] == "ACTIVE"
                else project["project_status"]
            )
        })

        assignment_counter += 1

# --------------------------------------------------
# 6. Create DataFrame
# --------------------------------------------------

df = pd.DataFrame(assignments)

# --------------------------------------------------
# 7. Data quality validations
# --------------------------------------------------

assert df["assignment_id"].is_unique

assert df["employee_id"].isin(
    employees["employee_id"]
).all()

assert df["project_id"].isin(
    projects["project_id"]
).all()

# Department consistency
employee_department = employees.set_index(
    "employee_id"
)["department_id"]

project_department = projects.set_index(
    "project_id"
)["department_id"]

for _, assignment in df.iterrows():

    assert (
        assignment["department_id"]
        == employee_department[assignment["employee_id"]]
    )

    assert (
        assignment["department_id"]
        == project_department[assignment["project_id"]]
    )

# Allocation cannot exceed 100% per employee
total_allocations = df.groupby(
    "employee_id"
)["allocation_percentage"].sum()

assert (total_allocations <= 100).all()

assert (df["allocation_percentage"] > 0).all()

assert (df["allocation_percentage"] <= 100).all()

# Every active employee must have at least one assignment
assigned_employees = set(df["employee_id"])

assert set(active_employees["employee_id"]).issubset(
    assigned_employees
)

# --------------------------------------------------
# 8. Save dataset
# --------------------------------------------------

df.to_csv(OUTPUT_FILE, index=False)

# --------------------------------------------------
# 9. Display results
# --------------------------------------------------

print("Project assignment dataset generated successfully!")

print(f"Total assignments: {len(df)}")
print(f"Unique employees assigned: {df['employee_id'].nunique()}")
print(f"Projects represented: {df['project_id'].nunique()}")

print("\nAssignment roles:")
print(df["role_in_project"].value_counts())

print("\nCritical project members:")
print(df["is_critical_member"].value_counts())

print("\nEmployee allocation summary:")
print(total_allocations.describe())

print("\nSample project assignments:")
print(df.head(10).to_string(index=False))

print("\nAll project assignment validations passed!")
