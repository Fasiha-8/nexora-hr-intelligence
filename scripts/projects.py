
import pandas as pd
import random
from pathlib import Path
from datetime import date, timedelta

random.seed(42)

# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "generated"

EMPLOYEE_FILE = DATA_DIR / "employees.csv"
MANAGER_FILE = DATA_DIR / "managers.csv"
OUTPUT_FILE = DATA_DIR / "projects.csv"

if OUTPUT_FILE.exists():
    raise FileExistsError(
        "projects.csv already exists. "
        "Remove it intentionally before regenerating."
    )

# --------------------------------------------------
# 2. Load existing datasets
# --------------------------------------------------

employees = pd.read_csv(EMPLOYEE_FILE)
managers = pd.read_csv(MANAGER_FILE)

# Only active employees can lead projects
active_employees = employees[
    employees["employment_status"] == "Active"
]

# --------------------------------------------------
# 3. Define synthetic projects
# --------------------------------------------------

project_definitions = [
    ("Enterprise HR Platform", "DEPT001", "Critical"),
    ("Employee Experience Initiative", "DEPT001", "High"),
    ("Cloud Infrastructure Migration", "DEPT002", "Critical"),
    ("AI Automation Platform", "DEPT002", "Critical"),
    ("Financial Reporting System", "DEPT003", "High"),
    ("Annual Budget Optimization", "DEPT003", "Medium"),
    ("Global Marketing Campaign", "DEPT004", "High"),
    ("Brand Transformation", "DEPT004", "Medium"),
    ("Enterprise Sales Expansion", "DEPT005", "High"),
    ("Customer Operations Optimization", "DEPT006", "Critical"),
    ("Customer Support Automation", "DEPT007", "High"),
    ("Cybersecurity Enhancement", "DEPT008", "Critical")
]

priorities = ["Low", "Medium", "High", "Critical"]

projects = []

today = date.today()

# --------------------------------------------------
# 4. Generate project records
# --------------------------------------------------

for i, (name, department_id, criticality) in enumerate(
    project_definitions, start=1
):

    # Find active managers in the project department
    department_managers = managers[
        (managers["department_id"] == department_id)
        & (managers["is_active"] == True)
    ]

    if department_managers.empty:
        raise ValueError(
            f"No active manager found for {department_id}"
        )

    project_lead_id = random.choice(
        department_managers["manager_id"].tolist()
    )

    # Generate project timeline
    start_date = today - timedelta(
        days=random.randint(15, 180)
    )

    deadline = today + timedelta(
        days=random.randint(10, 120)
    )

    required_team_size = random.randint(5, 15)

    minimum_coverage = random.randint(
        2, max(2, required_team_size - 1)
    )

    # Generate project status
    project_status = random.choices(
        ["ACTIVE", "PLANNING", "COMPLETED"],
        weights=[75, 15, 10]
    )[0]

    projects.append({
        "project_id": f"PROJ{i:03d}",
        "project_name": name,
        "department_id": department_id,
        "project_lead_id": project_lead_id,
        "start_date": start_date.isoformat(),
        "deadline": deadline.isoformat(),
        "priority": criticality,
        "criticality": criticality,
        "project_status": project_status,
        "required_team_size": required_team_size,
        "minimum_coverage": minimum_coverage
    })

# --------------------------------------------------
# 5. Create DataFrame
# --------------------------------------------------

df = pd.DataFrame(projects)

# --------------------------------------------------
# 6. Data validation
# --------------------------------------------------

assert len(df) == 12

assert df["project_id"].is_unique

assert df["department_id"].isin(
    employees["department_id"]
).all()

assert df["project_lead_id"].isin(
    employees["employee_id"]
).all()

assert (df["deadline"] > df["start_date"]).all()

assert (
    df["minimum_coverage"] <= df["required_team_size"]
).all()

assert df["project_status"].isin(
    ["ACTIVE", "PLANNING", "COMPLETED"]
).all()

# Project leads must be active managers
active_manager_ids = set(
    managers.loc[
        managers["is_active"] == True,
        "manager_id"
    ]
)

assert set(df["project_lead_id"]).issubset(
    active_manager_ids
)

# --------------------------------------------------
# 7. Save dataset
# --------------------------------------------------

df.to_csv(OUTPUT_FILE, index=False)

# --------------------------------------------------
# 8. Display results
# --------------------------------------------------

print("Project dataset generated successfully!")

print(f"Total projects: {len(df)}")
print(f"Departments represented: {df['department_id'].nunique()}")

print("\nProject criticality distribution:")
print(df["criticality"].value_counts())

print("\nGenerated projects:")
print(df.to_string(index=False))

print("\nAll project validations passed!")
