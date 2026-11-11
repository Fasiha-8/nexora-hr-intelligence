
from pathlib import Path
from datetime import datetime
import shutil
import pandas as pd

# ==========================================================
# NEXORA TECHNOLOGIES - FINAL LEAVE BALANCE FINALIZATION
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "generated"

BALANCE_FILE = DATA_DIR / "leave_balances.csv"
REQUEST_FILE = DATA_DIR / "leave_requests.csv"
POLICY_FILE = DATA_DIR / "leave_policies.csv"
EMPLOYEE_FILE = DATA_DIR / "employees.csv"

BACKUP_FILE = DATA_DIR / (
    f"leave_balances_backup_{datetime.now():%Y%m%d_%H%M%S}.csv"
)

REPORT_FILE = DATA_DIR / "final_leave_reconciliation_report.csv"

# ----------------------------------------------------------
# 1. Check files
# ----------------------------------------------------------

for file in [
    BALANCE_FILE,
    REQUEST_FILE,
    POLICY_FILE,
    EMPLOYEE_FILE
]:
    if not file.exists():
        raise FileNotFoundError(f"Missing file: {file}")

print("=" * 65)
print("NEXORA TECHNOLOGIES - LEAVE DATA FINALIZATION")
print("=" * 65)

# ----------------------------------------------------------
# 2. Load datasets
# ----------------------------------------------------------

balances = pd.read_csv(BALANCE_FILE)
requests = pd.read_csv(REQUEST_FILE)
policies = pd.read_csv(POLICY_FILE)
employees = pd.read_csv(EMPLOYEE_FILE)

for df in [balances, requests, policies, employees]:
    df.columns = df.columns.str.strip().str.lower()

today = pd.Timestamp.today().normalize()

requests["request_status"] = (
    requests["request_status"]
    .astype(str)
    .str.strip()
    .str.upper()
)

requests["start_date"] = pd.to_datetime(
    requests["start_date"], errors="coerce"
)

requests["end_date"] = pd.to_datetime(
    requests["end_date"], errors="coerce"
)

requests["requested_days"] = pd.to_numeric(
    requests["requested_days"], errors="coerce"
)

balances["leave_year"] = pd.to_numeric(
    balances["leave_year"], errors="coerce"
)

# ----------------------------------------------------------
# 3. Validate input structure
# ----------------------------------------------------------

balance_columns = [
    "employee_id",
    "leave_type",
    "leave_year",
    "entitled_days",
    "used_days",
    "pending_days",
    "available_days"
]

request_columns = [
    "employee_id",
    "leave_type",
    "start_date",
    "end_date",
    "requested_days",
    "request_status"
]

for column in balance_columns:
    if column not in balances.columns:
        raise ValueError(f"Missing balance column: {column}")

for column in request_columns:
    if column not in requests.columns:
        raise ValueError(f"Missing request column: {column}")

if balances.duplicated(
    ["employee_id", "leave_type", "leave_year"]
).any():
    raise ValueError("Duplicate balance records detected.")

if requests[
    ["start_date", "end_date", "requested_days"]
].isna().any().any():
    raise ValueError("Invalid request dates or requested days found.")

if not requests["employee_id"].isin(
    employees["employee_id"]
).all():
    raise ValueError("Requests contain unknown employee IDs.")

if requests["requested_days"].lt(0).any():
    raise ValueError("Negative leave days detected.")

# ----------------------------------------------------------
# 4. Verify original policy dataset
# ----------------------------------------------------------

print("\nOriginal policy records:", len(policies))

# We preserve the original policy file and its rules.
# Entitlements are taken from existing balance templates.

# ----------------------------------------------------------
# 5. Assign requests to leave years
# ----------------------------------------------------------

requests["leave_year"] = requests["start_date"].dt.year

approved = requests[
    requests["request_status"] == "APPROVED"
].copy()

pending = requests[
    requests["request_status"] == "PENDING"
].copy()

rejected = requests[
    requests["request_status"] == "REJECTED"
].copy()

cancelled = requests[
    requests["request_status"] == "CANCELLED"
].copy()

# ----------------------------------------------------------
# 6. Classify approved leave
# ----------------------------------------------------------

completed = approved[
    approved["end_date"] < today
].copy()

ongoing = approved[
    (approved["start_date"] <= today)
    & (approved["end_date"] >= today)
].copy()

future = approved[
    approved["start_date"] > today
].copy()

# Completed leave: full requested days are used.
completed["calculated_used"] = completed["requested_days"]

# Ongoing leave: count business days elapsed.
ongoing["calculated_used"] = ongoing.apply(
    lambda row: len(
        pd.bdate_range(
            start=row["start_date"],
            end=min(row["end_date"], today)
        )
    ),
    axis=1
)

# Remaining days in ongoing approved requests are reserved.
ongoing["calculated_reserved"] = (
    ongoing["requested_days"] - ongoing["calculated_used"]
).clip(lower=0)

# Future approved leave is fully reserved.
future["calculated_reserved"] = future["requested_days"]

# ----------------------------------------------------------
# 7. Aggregate leave accounting
# ----------------------------------------------------------

group_columns = [
    "employee_id",
    "leave_type",
    "leave_year"
]

used_data = pd.concat(
    [completed, ongoing],
    ignore_index=True
)

used_totals = (
    used_data.groupby(group_columns)["calculated_used"]
    .sum()
    .reset_index(name="calculated_used")
)

pending_totals = (
    pending.groupby(group_columns)["requested_days"]
    .sum()
    .reset_index(name="calculated_pending")
)

reserved_data = pd.concat(
    [future, ongoing],
    ignore_index=True
)

reserved_totals = (
    reserved_data.groupby(group_columns)["calculated_reserved"]
    .sum()
    .reset_index(name="calculated_reserved")
)

# ----------------------------------------------------------
# 8. Add balance rows for missing request years
# ----------------------------------------------------------

existing_keys = set(
    zip(
        balances["employee_id"],
        balances["leave_type"],
        balances["leave_year"]
    )
)

new_rows = []

for _, request in requests.iterrows():

    key = (
        request["employee_id"],
        request["leave_type"],
        request["leave_year"]
    )

    if key in existing_keys:
        continue

    templates = balances[
        (balances["employee_id"] == request["employee_id"])
        & (balances["leave_type"] == request["leave_type"])
    ]

    if templates.empty:
        raise ValueError(
            f"No entitlement template for {key}. "
            "Cannot safely create this balance record."
        )

    template = templates.sort_values(
        "leave_year"
    ).iloc[-1].copy()

    template["leave_year"] = request["leave_year"]
    template["used_days"] = 0
    template["pending_days"] = 0
    template["available_days"] = template["entitled_days"]

    if "reserved_days" in template.index:
        template["reserved_days"] = 0

    new_rows.append(template)
    existing_keys.add(key)

if new_rows:
    balances = pd.concat(
        [balances, pd.DataFrame(new_rows)],
        ignore_index=True
    )

# ----------------------------------------------------------
# 9. Merge calculated totals
# ----------------------------------------------------------

for totals, value_column in [
    (used_totals, "calculated_used"),
    (pending_totals, "calculated_pending"),
    (reserved_totals, "calculated_reserved")
]:
    balances = balances.merge(
        totals,
        on=group_columns,
        how="left"
    )

    balances[value_column] = (
        balances[value_column].fillna(0)
    )

balances["used_days"] = balances["calculated_used"]
balances["pending_days"] = balances["calculated_pending"]
balances["reserved_days"] = balances["calculated_reserved"]

# ----------------------------------------------------------
# 10. Recalculate available leave
# ----------------------------------------------------------

balances["available_days"] = (
    balances["entitled_days"]
    - balances["used_days"]
    - balances["pending_days"]
    - balances["reserved_days"]
)

balances["insufficient_balance"] = (
    balances["available_days"] < 0
)

balances["accounting_status"] = balances[
    "insufficient_balance"
].map({
    True: "INSUFFICIENT_BALANCE",
    False: "RECONCILED"
})

# ----------------------------------------------------------
# 11. Clean calculated columns
# ----------------------------------------------------------

balances.drop(
    columns=[
        "calculated_used",
        "calculated_pending",
        "calculated_reserved"
    ],
    inplace=True
)

numeric_columns = [
    "entitled_days",
    "used_days",
    "pending_days",
    "reserved_days",
    "available_days"
]

for column in numeric_columns:
    balances[column] = balances[column].round(2)

balances = balances.sort_values(
    ["employee_id", "leave_year", "leave_type"]
).reset_index(drop=True)

# ----------------------------------------------------------
# 12. Final integrity checks
# ----------------------------------------------------------

if balances.duplicated(group_columns).any():
    raise ValueError("Duplicate balance records after processing.")

if balances[numeric_columns].isna().any().any():
    raise ValueError("Missing numeric balance values detected.")

# Verify the accounting formula.
expected_available = (
    balances["entitled_days"]
    - balances["used_days"]
    - balances["pending_days"]
    - balances["reserved_days"]
)

if not (
    balances["available_days"].round(2)
    == expected_available.round(2)
).all():
    raise ValueError("Leave accounting formula validation failed.")

# ----------------------------------------------------------
# 13. Backup original file
# ----------------------------------------------------------

shutil.copy2(BALANCE_FILE, BACKUP_FILE)

# ----------------------------------------------------------
# 14. Save finalized data and report
# ----------------------------------------------------------

balances.to_csv(BALANCE_FILE, index=False)

balances.to_csv(REPORT_FILE, index=False)

# ----------------------------------------------------------
# 15. Print final report
# ----------------------------------------------------------

print("\n" + "=" * 65)
print("FINAL LEAVE RECONCILIATION SUMMARY")
print("=" * 65)

print("Employees:", balances["employee_id"].nunique())
print("Balance records:", len(balances))
print("Leave requests:", len(requests))

print("\nRequest classification:")
print("Completed approved:", len(completed))
print("Ongoing approved:", len(ongoing))
print("Future approved:", len(future))
print("Pending:", len(pending))
print("Rejected:", len(rejected))
print("Cancelled:", len(cancelled))

print("\nBalance results:")
print(
    "Reconciled records:",
    int((balances["accounting_status"] == "RECONCILED").sum())
)

print(
    "Insufficient balance records:",
    int(balances["insufficient_balance"].sum())
)

print("\nYears represented:")
print(sorted(balances["leave_year"].dropna().unique().tolist()))

print("\nBackup created:", BACKUP_FILE.name)
print("Final report created:", REPORT_FILE.name)

print("\nOriginal leave policies and requests were not modified.")
print("Leave balance finalization completed successfully.")
