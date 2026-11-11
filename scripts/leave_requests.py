
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
POLICY_FILE = DATA_DIR / "leave_policies.csv"
RELATIONSHIP_FILE = DATA_DIR / "organizational_relationships.csv"
OUTPUT_FILE = DATA_DIR / "leave_requests.csv"

if OUTPUT_FILE.exists():
    raise FileExistsError(
        "leave_requests.csv already exists. "
        "Remove it intentionally before regenerating."
    )

# --------------------------------------------------
# 2. Load datasets
# --------------------------------------------------

employees = pd.read_csv(EMPLOYEE_FILE)
policies = pd.read_csv(POLICY_FILE)
relationships = pd.read_csv(RELATIONSHIP_FILE)

# Current organizational relationships
current_relationships = relationships[
    relationships["is_current"] == True
]

# Create employee-to-manager lookup
manager_lookup = current_relationships.set_index(
    "employee_id"
)["manager_id"].to_dict()

# Supported leave categories
supported_types = [
    "Annual Leave",
    "Sick Leave",
    "Casual Leave"
]

eligible_policies = policies[
    policies["leave_type"].isin(supported_types)
]

policy_lookup = eligible_policies.set_index(
    "leave_type"
)["policy_id"].to_dict()

# --------------------------------------------------
# 3. Select active employees
# --------------------------------------------------

active_employees = employees[
    employees["employment_status"] == "Active"
].copy()

# --------------------------------------------------
# 4. Helper function: working days
# --------------------------------------------------

def calculate_working_days(start_date, end_date):

    return len(
        pd.bdate_range(
            start=start_date,
            end=end_date
        )
    )

# --------------------------------------------------
# 5. Generate leave requests
# --------------------------------------------------

requests = []

today = date.today()

statuses = ["PENDING", "APPROVED", "REJECTED", "CANCELLED"]
status_weights = [35, 40, 15, 10]

for i in range(1, 121):

    employee = active_employees.sample(
        n=1,
        random_state=42 + i
    ).iloc[0]

    employee_id = employee["employee_id"]

    # Select leave type
    leave_type = random.choice(supported_types)
    policy_id = policy_lookup[leave_type]

    # Generate future or recent leave dates
    days_from_today = random.randint(-30, 150)

    start_date = today + timedelta(days=days_from_today)

    requested_duration = random.randint(1, 10)

    # Calculate an end date that excludes weekends
    working_dates = pd.bdate_range(
        start=start_date,
        periods=requested_duration
    )

    end_date = working_dates[-1].date()

    requested_days = calculate_working_days(
        start_date,
        end_date
    )

    # Submission date
    submitted_date = start_date - timedelta(
        days=random.randint(1, 20)
    )

    # Request status
    status = random.choices(
        statuses,
        weights=status_weights
    )[0]

    # Determine approval date
    if status in ["APPROVED", "REJECTED"]:
        approval_date = (
            submitted_date
            + timedelta(days=random.randint(1, 5))
        )
    else:
        approval_date = None

    # Rejection reason
    rejection_reason = None

    if status == "REJECTED":
        rejection_reason = random.choice([
            "Insufficient team coverage",
            "Insufficient leave balance",
            "Project delivery conflict",
            "Policy eligibility requirements not met"
        ])

    manager_id = manager_lookup.get(employee_id)

    requests.append({
        "request_id": f"LR{i:04d}",
        "employee_id": employee_id,
        "policy_id": policy_id,
        "leave_type": leave_type,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "requested_days": requested_days,
        "request_status": status,
        "manager_id_at_submission": manager_id,
        "submitted_date": submitted_date.isoformat(),
        "approval_date": (
            approval_date.isoformat()
            if approval_date else None
        ),
        "rejection_reason": rejection_reason
    })

# --------------------------------------------------
# 6. Create a reproducible leave conflict scenario
# --------------------------------------------------

# Select three active employees reporting to the same manager
employee_manager_data = current_relationships.merge(
    employees[["employee_id", "employment_status"]],
    on="employee_id"
)

team_candidates = employee_manager_data[
    employee_manager_data["employment_status"] == "Active"
].dropna(subset=["manager_id"])

team_sizes = team_candidates.groupby(
    "manager_id"
)["employee_id"].nunique()

suitable_managers = team_sizes[
    team_sizes >= 3
]

if suitable_managers.empty:
    raise ValueError(
        "No manager has three active direct reports."
    )

scenario_manager_id = suitable_managers.index[0]

scenario_employees = team_candidates[
    team_candidates["manager_id"] == scenario_manager_id
]["employee_id"].head(3).tolist()

scenario_start = today + timedelta(days=35)

scenario_dates = pd.bdate_range(
    start=scenario_start,
    periods=5
)

scenario_end = scenario_dates[-1].date()

for i, employee_id in enumerate(scenario_employees, start=121):

    requests.append({
        "request_id": f"LR{i:04d}",
        "employee_id": employee_id,
        "policy_id": policy_lookup["Annual Leave"],
        "leave_type": "Annual Leave",
        "start_date": scenario_start.isoformat(),
        "end_date": scenario_end.isoformat(),
        "requested_days": 5,
        "request_status": "PENDING",
        "manager_id_at_submission": scenario_manager_id,
        "submitted_date": today.isoformat(),
        "approval_date": None,
        "rejection_reason": None
    })

# --------------------------------------------------
# 7. Create DataFrame
# --------------------------------------------------

df = pd.DataFrame(requests)

# --------------------------------------------------
# 8. Data quality validation
# --------------------------------------------------

assert df["request_id"].is_unique

assert df["employee_id"].isin(
    employees["employee_id"]
).all()

assert df["policy_id"].isin(
    policies["policy_id"]
).all()

assert (df["requested_days"] > 0).all()

assert (
    pd.to_datetime(df["start_date"])
    <= pd.to_datetime(df["end_date"])
).all()

assert df["request_status"].isin(statuses).all()

assert not (
    df[
        df["request_status"] == "PENDING"
    ]["approval_date"].notna()
).any()

# --------------------------------------------------
# 9. Save dataset
# --------------------------------------------------

df.to_csv(OUTPUT_FILE, index=False)

# --------------------------------------------------
# 10. Display results
# --------------------------------------------------

print("Leave request dataset generated successfully!")

print(f"Total requests: {len(df)}")
print(f"Unique employees requesting leave: {df['employee_id'].nunique()}")

print("\nRequest status distribution:")
print(df["request_status"].value_counts())

print("\nLeave type distribution:")
print(df["leave_type"].value_counts())

print("\nDeliberate overlapping leave scenario:")
print(f"Manager: {scenario_manager_id}")
print(f"Employees: {scenario_employees}")
print(f"Start date: {scenario_start}")
print(f"End date: {scenario_end}")

print("\nSample leave requests:")
print(df.head(10).to_string(index=False))

print("\nAll leave request validations passed!")
