
import pandas as pd
from pathlib import Path
from datetime import date, timedelta

# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "generated"

OUTPUT_FILE = DATA_DIR / "organizational_relationships.csv"
EMPLOYEE_FILE = DATA_DIR / "employees.csv"
MANAGER_FILE = DATA_DIR / "managers.csv"

# Prevent accidental overwriting of an existing dataset
if OUTPUT_FILE.exists():
    raise FileExistsError(
        "Organizational relationships already exist. "
        "Delete the existing file only if you intend to "
        "regenerate the scenario."
    )

# --------------------------------------------------
# 2. Load existing datasets
# --------------------------------------------------

employees = pd.read_csv(EMPLOYEE_FILE)
managers = pd.read_csv(MANAGER_FILE)

# --------------------------------------------------
# 3. Define the transfer scenario
# --------------------------------------------------

TRANSFER_EMPLOYEE_ID = "EMP0001"
TARGET_DEPARTMENT_ID = "DEPT003"

employee_record = employees[
    employees["employee_id"] == TRANSFER_EMPLOYEE_ID
]

if len(employee_record) != 1:
    raise ValueError("Transfer employee not found or duplicated.")

employee_record = employee_record.iloc[0]

if employee_record["role"] == "MANAGER":
    raise ValueError("The selected transfer employee is a manager.")

if employee_record["employment_status"] != "Active":
    raise ValueError("Transfer employee must be active.")

old_department_id = employee_record["department_id"]
old_manager_id = employee_record["manager_id"]

if old_department_id == TARGET_DEPARTMENT_ID:
    raise ValueError("Employee is already in the target department.")

# Find a valid manager in the target department
target_managers = managers[
    (managers["department_id"] == TARGET_DEPARTMENT_ID)
    & (managers["is_active"] == True)
]

if target_managers.empty:
    raise ValueError("No active manager found in target department.")

new_manager_id = target_managers.iloc[0]["manager_id"]

# --------------------------------------------------
# 4. Calculate transfer date
# --------------------------------------------------

hire_date = pd.to_datetime(employee_record["hire_date"]).date()
today = date.today()

if hire_date >= today:
    raise ValueError("Employee must have a past hire date.")

# Use a reproducible midpoint between hire date and today
transfer_date = hire_date + (today - hire_date) // 2

previous_relationship_end = transfer_date - timedelta(days=1)

# --------------------------------------------------
# 5. Generate organizational relationships
# --------------------------------------------------

relationships = []

for _, employee in employees.iterrows():

    employee_id = employee["employee_id"]

    hire_date = pd.to_datetime(employee["hire_date"]).date()

    if employee_id == TRANSFER_EMPLOYEE_ID:

        # Historical relationship
        relationships.append({
            "relationship_id": "REL0001",
            "employee_id": employee_id,
            "department_id": old_department_id,
            "manager_id": old_manager_id,
            "valid_from": hire_date.isoformat(),
            "valid_to": previous_relationship_end.isoformat(),
            "is_current": False,
            "change_reason": "INITIAL_ASSIGNMENT"
        })

        # New current relationship
        relationships.append({
            "relationship_id": "REL0002",
            "employee_id": employee_id,
            "department_id": TARGET_DEPARTMENT_ID,
            "manager_id": new_manager_id,
            "valid_from": transfer_date.isoformat(),
            "valid_to": None,
            "is_current": True,
            "change_reason": "DEPARTMENT_TRANSFER"
        })

    else:

        relationships.append({
            "relationship_id": f"REL{len(relationships) + 1:04d}",
            "employee_id": employee_id,
            "department_id": employee["department_id"],
            "manager_id": employee["manager_id"],
            "valid_from": hire_date.isoformat(),
            "valid_to": None,
            "is_current": True,
            "change_reason": "INITIAL_ASSIGNMENT"
        })

relationships_df = pd.DataFrame(relationships)

# --------------------------------------------------
# 6. Update employee's current record
# --------------------------------------------------

employees.loc[
    employees["employee_id"] == TRANSFER_EMPLOYEE_ID,
    "department_id"
] = TARGET_DEPARTMENT_ID

employees.loc[
    employees["employee_id"] == TRANSFER_EMPLOYEE_ID,
    "manager_id"
] = new_manager_id

# --------------------------------------------------
# 7. Data validation
# --------------------------------------------------

assert relationships_df["relationship_id"].is_unique

assert relationships_df["employee_id"].isin(
    employees["employee_id"]
).all()

# Every employee must have exactly one current relationship
current_relationships = relationships_df[
    relationships_df["is_current"] == True
]

assert len(current_relationships) == len(employees)

assert current_relationships["employee_id"].is_unique

# Current organizational relationships must match employee records
for _, employee in employees.iterrows():

    current_record = current_relationships[
        current_relationships["employee_id"] == employee["employee_id"]
    ].iloc[0]

    assert (
    current_record["department_id"]
    == employee["department_id"]
)

current_manager = current_record["manager_id"]
employee_manager = employee["manager_id"]

if pd.isna(current_manager) and pd.isna(employee_manager):
    pass
else:
    assert current_manager == employee_manager, (
        f"Manager mismatch for {employee['employee_id']}"
    )

# Historical relationship must end before the new one starts
old_record = relationships_df[
    relationships_df["relationship_id"] == "REL0001"
].iloc[0]

new_record = relationships_df[
    relationships_df["relationship_id"] == "REL0002"
].iloc[0]

assert old_record["valid_to"] < new_record["valid_from"]

# --------------------------------------------------
# 8. Save datasets
# --------------------------------------------------

relationships_df.to_csv(OUTPUT_FILE, index=False)
employees.to_csv(EMPLOYEE_FILE, index=False)

# --------------------------------------------------
# 9. Display results
# --------------------------------------------------

print("Organizational relationship dataset generated!")
print(f"Total relationships: {len(relationships_df)}")
print(f"Total employees: {len(employees)}")

print("\nDepartment transfer scenario:")
print(f"Employee: {TRANSFER_EMPLOYEE_ID}")
print(f"Previous department: {old_department_id}")
print(f"Previous manager: {old_manager_id}")
print(f"New department: {TARGET_DEPARTMENT_ID}")
print(f"New manager: {new_manager_id}")
print(f"Transfer effective date: {transfer_date}")

print("\nEmployee relationship history:")
print(
    relationships_df[
        relationships_df["employee_id"] == TRANSFER_EMPLOYEE_ID
    ].to_string(index=False)
)

print("\nAll organizational relationship validations passed!")
