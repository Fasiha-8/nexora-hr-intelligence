
from pathlib import Path
import pandas as pd

# --------------------------------------------------
# 1. Define project paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "generated"

BALANCES_FILE = DATA_DIR / "leave_balances.csv"
REQUESTS_FILE = DATA_DIR / "leave_requests.csv"

REPORT_FILE = DATA_DIR / "leave_reconciliation_report.csv"


# --------------------------------------------------
# 2. Load datasets
# --------------------------------------------------

balances = pd.read_csv(BALANCES_FILE)
requests = pd.read_csv(REQUESTS_FILE)

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

requests["request_status"] = (
    requests["request_status"].str.strip().str.upper()
)

print("Leave balance and request datasets loaded.")
print(f"Balance records: {len(balances)}")
print(f"Request records: {len(requests)}")


# --------------------------------------------------
# 3. Assign each request to its leave year
# --------------------------------------------------

requests["leave_year"] = requests["start_date"].dt.year

today = pd.Timestamp.today().normalize()

# Separate approved and pending requests

approved_requests = requests[
    requests["request_status"] == "APPROVED"
].copy()

pending_requests = requests[
    requests["request_status"] == "PENDING"
].copy()


# --------------------------------------------------
# 4. Classify approved leave
# --------------------------------------------------

# Approved leave that has already ended

completed_leave = approved_requests[
    approved_requests["end_date"] < today
]

# Approved leave scheduled for a future date

future_approved_leave = approved_requests[
    approved_requests["start_date"] > today
]

# Approved leave currently in progress

ongoing_approved_leave = approved_requests[
    (approved_requests["start_date"] <= today)
    & (approved_requests["end_date"] >= today)
]


# --------------------------------------------------
# 5. Calculate expected leave usage
# --------------------------------------------------

group_columns = [
    "employee_id",
    "leave_type",
    "leave_year"
]

expected_used = (
    completed_leave.groupby(group_columns)["requested_days"]
    .sum()
    .reset_index(name="expected_used")
)

expected_pending = (
    pending_requests.groupby(group_columns)["requested_days"]
    .sum()
    .reset_index(name="expected_pending")
)

expected_future = (
    future_approved_leave.groupby(group_columns)["requested_days"]
    .sum()
    .reset_index(name="approved_future_days")
)

expected_ongoing = (
    ongoing_approved_leave.groupby(group_columns)["requested_days"]
    .sum()
    .reset_index(name="approved_ongoing_days")
)


# --------------------------------------------------
# 6. Compare expected and recorded balances
# --------------------------------------------------

report = balances.merge(
    expected_used,
    on=group_columns,
    how="left"
)

report = report.merge(
    expected_pending,
    on=group_columns,
    how="left"
)

report = report.merge(
    expected_future,
    on=group_columns,
    how="left"
)

report = report.merge(
    expected_ongoing,
    on=group_columns,
    how="left"
)

# Replace missing values with zero

calculated_columns = [
    "expected_used",
    "expected_pending",
    "approved_future_days",
    "approved_ongoing_days"
]

for column in calculated_columns:
    report[column] = report[column].fillna(0)

# Compare recorded and expected values

report["used_difference"] = (
    report["used_days"] - report["expected_used"]
)

report["pending_difference"] = (
    report["pending_days"] - report["expected_pending"]
)

report["used_matches"] = (
    report["used_difference"] == 0
)

report["pending_matches"] = (
    report["pending_difference"] == 0
)

report["reconciliation_status"] = report.apply(
    lambda row: (
        "MATCHED"
        if row["used_matches"] and row["pending_matches"]
        else "DISCREPANCY"
    ),
    axis=1
)


# --------------------------------------------------
# 7. Generate summary
# --------------------------------------------------

total_records = len(report)

matched_records = (
    report["reconciliation_status"] == "MATCHED"
).sum()

discrepancy_records = (
    report["reconciliation_status"] == "DISCREPANCY"
).sum()

print("\n" + "=" * 60)
print("NEXORA TECHNOLOGIES - LEAVE RECONCILIATION REPORT")
print("=" * 60)

print(f"Total balance records: {total_records}")
print(f"Matched records: {matched_records}")
print(f"Records with discrepancies: {discrepancy_records}")

if total_records:
    print(
        f"Match rate: "
        f"{(matched_records / total_records) * 100:.2f}%"
    )

print("\nLeave request classification:")

print(f"Completed approved requests: {len(completed_leave)}")
print(f"Future approved requests: {len(future_approved_leave)}")
print(f"Ongoing approved requests: {len(ongoing_approved_leave)}")
print(f"Pending requests: {len(pending_requests)}")

print("\nDiscrepancy breakdown:")

print(
    "Used-day mismatches:",
    (~report["used_matches"]).sum()
)

print(
    "Pending-day mismatches:",
    (~report["pending_matches"]).sum()
)


# --------------------------------------------------
# 8. Save detailed report
# --------------------------------------------------

report.to_csv(REPORT_FILE, index=False)

print("\nDetailed reconciliation report saved to:")
print(REPORT_FILE)


# --------------------------------------------------
# 9. Display sample discrepancies
# --------------------------------------------------

discrepancies = report[
    report["reconciliation_status"] == "DISCREPANCY"
]

if not discrepancies.empty:

    print("\nSample discrepancies:")

    display_columns = [
        "employee_id",
        "leave_type",
        "leave_year",
        "used_days",
        "expected_used",
        "pending_days",
        "expected_pending",
        "approved_future_days",
        "approved_ongoing_days",
        "reconciliation_status"
    ]

    print(
        discrepancies[display_columns]
        .head(10)
        .to_string(index=False)
    )

else:
    print("\nAll leave balances match their request records.")

print("\nOriginal datasets were not modified.")
