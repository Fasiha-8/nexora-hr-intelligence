
import pandas as pd
import random
from pathlib import Path
from datetime import date

# Reproducible synthetic data
random.seed(42)

# Project paths
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "generated"

# Load existing datasets
employees = pd.read_csv(DATA_DIR / "employees.csv")
policies = pd.read_csv(DATA_DIR / "leave_policies.csv")

LEAVE_YEAR = 2026
TODAY = date.today()

# Generate balances for ordinary leave categories
supported_leave_types = [
    "Annual Leave",
    "Sick Leave",
    "Casual Leave"
]

selected_policies = policies[
    policies["leave_type"].isin(supported_leave_types)
]

leave_balances = []

balance_counter = 1

for _, employee in employees.iterrows():

    employee_id = employee["employee_id"]
    hire_date = pd.to_datetime(employee["hire_date"]).date()

    service_days = (TODAY - hire_date).days

    for _, policy in selected_policies.iterrows():

        policy_id = policy["policy_id"]
        leave_type = policy["leave_type"]

        entitlement = int(policy["annual_entitlement_days"])
        minimum_service = int(policy["minimum_service_days"])

        is_eligible = service_days >= minimum_service

        # Ineligible employees receive zero available entitlement
        effective_entitlement = entitlement if is_eligible else 0

        # Generate realistic usage only for eligible employees
        if is_eligible:

            used_days = random.randint(
                0,
                min(10, effective_entitlement)
            )

            remaining_after_usage = (
                effective_entitlement - used_days
            )

            pending_days = random.randint(
                0,
                min(3, remaining_after_usage)
            )

        else:
            used_days = 0
            pending_days = 0

        available_days = (
            effective_entitlement
            - used_days
            - pending_days
        )

        leave_balances.append({
            "balance_id": f"BAL{balance_counter:05d}",
            "employee_id": employee_id,
            "policy_id": policy_id,
            "leave_type": leave_type,
            "leave_year": LEAVE_YEAR,
            "entitled_days": effective_entitlement,
            "used_days": used_days,
            "pending_days": pending_days,
            "available_days": available_days,
            "eligibility_status": (
                "ELIGIBLE" if is_eligible else "NOT_ELIGIBLE"
            )
        })

        balance_counter += 1

# Convert to DataFrame
df = pd.DataFrame(leave_balances)

# ------------------------------------------
# Data quality validations
# ------------------------------------------

assert df["balance_id"].is_unique

assert df["employee_id"].isin(
    employees["employee_id"]
).all()

assert df["policy_id"].isin(
    policies["policy_id"]
).all()

assert (df["available_days"] >= 0).all()

assert (
    df["entitled_days"]
    == df["used_days"]
    + df["pending_days"]
    + df["available_days"]
).all()

assert not df.duplicated(
    subset=["employee_id", "policy_id", "leave_year"]
).any()

# Save dataset
output_file = DATA_DIR / "leave_balances.csv"
df.to_csv(output_file, index=False)

# ------------------------------------------
# Display results
# ------------------------------------------

print("Leave balance dataset generated successfully!")

print(f"Total balance records: {len(df)}")
print(f"Total employees: {employees['employee_id'].nunique()}")
print(f"Leave categories: {df['leave_type'].nunique()}")

print("\nEligibility distribution:")
print(df.groupby(
    ["leave_type", "eligibility_status"]
).size())

print("\nSample leave balances:")
print(df.head(10).to_string(index=False))

print("\nAll leave balance validations passed!")
