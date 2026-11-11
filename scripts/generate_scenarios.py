
import pandas as pd
from pathlib import Path

# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

GENERATED_DIR = BASE_DIR / "data" / "generated"
SCENARIO_DIR = BASE_DIR / "data" / "scenarios"

SCENARIO_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = SCENARIO_DIR / "business_scenarios.csv"

if OUTPUT_FILE.exists():
    raise FileExistsError(
        "business_scenarios.csv already exists. "
        "Remove it intentionally before regenerating."
    )

# --------------------------------------------------
# 2. Load existing datasets
# --------------------------------------------------

employees = pd.read_csv(GENERATED_DIR / "employees.csv")
relationships = pd.read_csv(
    GENERATED_DIR / "organizational_relationships.csv"
)
leave_requests = pd.read_csv(
    GENERATED_DIR / "leave_requests.csv"
)
leave_balances = pd.read_csv(
    GENERATED_DIR / "leave_balances.csv"
)
projects = pd.read_csv(GENERATED_DIR / "projects.csv")
assignments = pd.read_csv(
    GENERATED_DIR / "project_assignments.csv"
)

scenarios = []

# Helper for storing related IDs
def join_ids(values):
    return ";".join(
        str(value) for value in values if pd.notna(value)
    )

# --------------------------------------------------
# 3. Scenario 1: Department transfer
# --------------------------------------------------

transfer_employee_id = "EMP0001"

transfer_history = relationships[
    relationships["employee_id"] == transfer_employee_id
].copy()

if len(transfer_history) < 2:
    raise ValueError(
        "Historical transfer records not found for EMP0001."
    )

old_relationship = transfer_history[
    transfer_history["is_current"] == False
].iloc[0]

new_relationship = transfer_history[
    transfer_history["is_current"] == True
].iloc[0]

scenarios.append({
    "scenario_id": "SCN001",
    "scenario_type": "ORGANIZATIONAL_INTELLIGENCE",
    "title": "Department Transfer and Stale Approval",
    "description": (
        "An employee transfers departments. "
        "The system must identify whether an old approval "
        "relationship is still being used."
    ),
    "employee_ids": transfer_employee_id,
    "request_ids": "",
    "project_ids": "",
    "expected_agent_behavior": (
        f"Compare previous manager {old_relationship['manager_id']} "
        f"with current manager {new_relationship['manager_id']}; "
        "flag any outdated approval route and recommend correction."
    ),
    "severity": "HIGH"
})

# --------------------------------------------------
# 4. Scenario 2: Overlapping leave requests
# --------------------------------------------------

pending_requests = leave_requests[
    leave_requests["request_status"] == "PENDING"
].copy()

overlap_groups = pending_requests.groupby(
    [
        "manager_id_at_submission",
        "start_date",
        "end_date"
    ],
    dropna=False
)

overlap_found = False

for group_key, group in overlap_groups:

    if len(group) >= 3 and pd.notna(group_key[0]):

        scenarios.append({
            "scenario_id": "SCN002",
            "scenario_type": "WORKFORCE_PLANNING",
            "title": "Multiple Overlapping Leave Requests",
            "description": (
                "Three employees reporting to the same manager "
                "request leave for identical dates."
            ),
            "employee_ids": join_ids(group["employee_id"]),
            "request_ids": join_ids(group["request_id"]),
            "project_ids": "",
            "expected_agent_behavior": (
                "Identify overlapping requests, examine team capacity "
                "and project commitments, and recommend scheduling "
                "alternatives without automatically rejecting requests."
            ),
            "severity": "HIGH"
        })

        overlap_found = True
        break

if not overlap_found:
    raise ValueError(
        "The three-employee overlapping leave scenario was not found."
    )

# --------------------------------------------------
# 5. Scenario 3: Critical project staffing risk
# --------------------------------------------------

critical_projects = projects[
    (projects["criticality"] == "Critical")
    & (projects["project_status"] == "ACTIVE")
]

project_found = False

for _, project in critical_projects.iterrows():

    project_team = assignments[
        (assignments["project_id"] == project["project_id"])
        & (assignments["assignment_status"] == "ACTIVE")
    ]

    if len(project_team) >= 2:

        scenarios.append({
            "scenario_id": "SCN003",
            "scenario_type": "PREDICTIVE_WORKFORCE_INTELLIGENCE",
            "title": "Critical Project Staffing Risk",
            "description": (
                f"The project {project['project_name']} is business-critical. "
                "Employee absences may affect delivery capacity."
            ),
            "employee_ids": join_ids(
                project_team["employee_id"]
            ),
            "request_ids": "",
            "project_ids": project["project_id"],
            "expected_agent_behavior": (
                "Examine project deadlines, critical team members, "
                "allocation and minimum staffing coverage; identify "
                "operational risks and recommend mitigation."
            ),
            "severity": "CRITICAL"
        })

        project_found = True
        break

if not project_found:
    raise ValueError(
        "No suitable active critical project with assignments found."
    )

# --------------------------------------------------
# 6. Scenario 4: Insufficient leave balance
# --------------------------------------------------

balance_lookup = leave_balances.set_index(
    ["employee_id", "policy_id"]
)["available_days"]

insufficient_candidate = None

for _, request in leave_requests.iterrows():

    if request["request_status"] not in ["PENDING", "APPROVED"]:
        continue

    key = (
        request["employee_id"],
        request["policy_id"]
    )

    if key not in balance_lookup.index:
        continue

    available = balance_lookup.loc[key]

    if request["requested_days"] > available:

        insufficient_candidate = request
        break

if insufficient_candidate is not None:

    scenarios.append({
        "scenario_id": "SCN004",
        "scenario_type": "POLICY_COMPLIANCE",
        "title": "Insufficient Leave Balance",
        "description": (
            "An employee requests more leave days than their "
            "currently available balance."
        ),
        "employee_ids": insufficient_candidate["employee_id"],
        "request_ids": insufficient_candidate["request_id"],
        "project_ids": "",
        "expected_agent_behavior": (
            "Retrieve the applicable policy and leave balance, "
            "identify the shortfall, explain the discrepancy "
            "and recommend authorized next steps."
        ),
        "severity": "HIGH"
    })

else:

    # Construct a deterministic synthetic policy edge case
    lowest_balance = leave_balances.sort_values(
        "available_days"
    ).iloc[0]

    scenarios.append({
        "scenario_id": "SCN004",
        "scenario_type": "POLICY_COMPLIANCE",
        "title": "Insufficient Leave Balance",
        "description": (
            "Test an employee requesting more days than their "
            "available leave balance."
        ),
        "employee_ids": lowest_balance["employee_id"],
        "request_ids": "",
        "project_ids": "",
        "expected_agent_behavior": (
            "Detect an insufficient balance and explain the "
            "applicable policy constraints."
        ),
        "severity": "HIGH"
    })

# --------------------------------------------------
# 7. Scenario 5: Unauthorized information request
# --------------------------------------------------

scenarios.append({
    "scenario_id": "SCN005",
    "scenario_type": "SECURITY_AND_ACCESS_CONTROL",
    "title": "Unauthorized Employee Information Access",
    "description": (
        "An ordinary employee attempts to retrieve confidential "
        "salary information or another employee's private records."
    ),
    "employee_ids": "",
    "request_ids": "",
    "project_ids": "",
    "expected_agent_behavior": (
        "Verify the authenticated user's identity and permissions; "
        "deny unauthorized access and log the security event."
    ),
    "severity": "CRITICAL"
})

# --------------------------------------------------
# 8. Create DataFrame
# --------------------------------------------------

df = pd.DataFrame(scenarios)

# --------------------------------------------------
# 9. Validation
# --------------------------------------------------

assert len(df) == 5
assert df["scenario_id"].is_unique

assert df["scenario_type"].notna().all()
assert df["expected_agent_behavior"].notna().all()

assert set(df["severity"]).issubset({
    "LOW", "MEDIUM", "HIGH", "CRITICAL"
})

# --------------------------------------------------
# 10. Save dataset
# --------------------------------------------------

df.to_csv(OUTPUT_FILE, index=False)

print("Business scenario dataset generated successfully!")
print(f"Total scenarios: {len(df)}")

print("\nScenario distribution:")
print(df["scenario_type"].value_counts())

print("\nGenerated scenarios:")
print(
    df[
        ["scenario_id", "title", "severity"]
    ].to_string(index=False)
)

print("\nAll scenario validations passed!")
