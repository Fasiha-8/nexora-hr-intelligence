
import pandas as pd
from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "generated"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Fictional Nexora Technologies leave policies
policies = [
    {
        "policy_id": "POL001",
        "leave_type": "Annual Leave",
        "annual_entitlement_days": 20,
        "max_consecutive_days": 15,
        "minimum_service_days": 90,
        "requires_documentation": False,
        "manager_approval_required": True,
        "hr_approval_required": False,
        "carry_forward_allowed": True,
        "description": "Paid annual vacation leave."
    },
    {
        "policy_id": "POL002",
        "leave_type": "Sick Leave",
        "annual_entitlement_days": 10,
        "max_consecutive_days": 10,
        "minimum_service_days": 0,
        "requires_documentation": True,
        "manager_approval_required": True,
        "hr_approval_required": False,
        "carry_forward_allowed": False,
        "description": "Leave for personal illness or medical recovery."
    },
    {
        "policy_id": "POL003",
        "leave_type": "Casual Leave",
        "annual_entitlement_days": 7,
        "max_consecutive_days": 3,
        "minimum_service_days": 90,
        "requires_documentation": False,
        "manager_approval_required": True,
        "hr_approval_required": False,
        "carry_forward_allowed": False,
        "description": "Short-duration personal leave."
    },
    {
        "policy_id": "POL004",
        "leave_type": "Maternity Leave",
        "annual_entitlement_days": 90,
        "max_consecutive_days": 90,
        "minimum_service_days": 180,
        "requires_documentation": True,
        "manager_approval_required": True,
        "hr_approval_required": True,
        "carry_forward_allowed": False,
        "description": "Maternity leave subject to HR eligibility review."
    },
    {
        "policy_id": "POL005",
        "leave_type": "Paternity Leave",
        "annual_entitlement_days": 14,
        "max_consecutive_days": 14,
        "minimum_service_days": 180,
        "requires_documentation": True,
        "manager_approval_required": True,
        "hr_approval_required": True,
        "carry_forward_allowed": False,
        "description": "Paternity leave subject to HR eligibility review."
    },
    {
        "policy_id": "POL006",
        "leave_type": "Unpaid Leave",
        "annual_entitlement_days": 0,
        "max_consecutive_days": 30,
        "minimum_service_days": 90,
        "requires_documentation": False,
        "manager_approval_required": True,
        "hr_approval_required": True,
        "carry_forward_allowed": False,
        "description": "Unpaid leave requiring manager and HR review."
    }
]

df = pd.DataFrame(policies)

# Data validation
assert df["policy_id"].is_unique
assert df["leave_type"].is_unique
assert (df["annual_entitlement_days"] >= 0).all()
assert (df["max_consecutive_days"] > 0).all()

# Save dataset
output_file = DATA_DIR / "leave_policies.csv"
df.to_csv(output_file, index=False)

print("Leave policy dataset generated successfully!")
print(f"Total policies: {len(df)}")

print("\nLeave policies:")
print(df[
    ["policy_id", "leave_type", "annual_entitlement_days",
     "max_consecutive_days", "manager_approval_required",
     "hr_approval_required"]
].to_string(index=False))

print("\nAll leave policy validations passed!")
