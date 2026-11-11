
from pathlib import Path
import os
import shutil
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# =====================================================
# NEXORA HR - FIX DUPLICATE LEAVE BALANCE IDs
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "generated"

CSV_FILE = DATA_DIR / "leave_balances.csv"

BACKUP_FILE = DATA_DIR / (
    f"leave_balances_pre_id_fix_{datetime.now():%Y%m%d_%H%M%S}.csv"
)

# -----------------------------------------------------
# 1. Load database configuration
# -----------------------------------------------------

load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL missing from .env")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# -----------------------------------------------------
# 2. Load and validate CSV
# -----------------------------------------------------

balances = pd.read_csv(CSV_FILE)

required_columns = {
    "balance_id",
    "employee_id",
    "policy_id",
    "leave_year"
}

if not required_columns.issubset(balances.columns):
    raise ValueError("Required balance columns are missing.")

if balances["balance_id"].isna().any():
    raise ValueError("Missing balance IDs detected.")

if balances.duplicated(
    ["employee_id", "policy_id", "leave_year"]
).any():
    raise ValueError("Duplicate employee-policy-year records found.")

duplicate_mask = balances["balance_id"].duplicated(
    keep="first"
)

duplicate_rows = balances[duplicate_mask].copy()

print("Original balance records:", len(balances))
print("Duplicate ID rows:", len(duplicate_rows))

# -----------------------------------------------------
# 3. Generate new unique IDs
# -----------------------------------------------------

def get_id_number(value):
    digits = "".join(
        character for character in str(value)
        if character.isdigit()
    )
    return int(digits) if digits else 0


existing_numbers = [
    get_id_number(value)
    for value in balances["balance_id"]
]

next_id = max(existing_numbers, default=0) + 1

# The duplicated IDs should belong to the new 2027 records.
# Keep the original 2026 IDs and replace the 2027 IDs.

for index in duplicate_rows.index:

    year = int(balances.at[index, "leave_year"])

    if year != 2027:
        raise ValueError(
            f"Unexpected duplicate ID outside 2027: "
            f"{balances.at[index, 'balance_id']}"
        )

    balances.at[index, "balance_id"] = (
        f"BAL{next_id:05d}"
    )

    next_id += 1

# -----------------------------------------------------
# 4. Verify uniqueness before saving
# -----------------------------------------------------

if balances["balance_id"].duplicated().any():
    raise ValueError(
        "Duplicate IDs remain. No files were updated."
    )

if len(balances) != 651:
    raise ValueError(
        f"Unexpected record count: {len(balances)}"
    )

# -----------------------------------------------------
# 5. Update PostgreSQL and save CSV
# -----------------------------------------------------

# Create backup before making changes.
shutil.copy2(CSV_FILE, BACKUP_FILE)

try:

    with engine.begin() as connection:

        # Verify database table exists.
        connection.execute(
            text('SELECT 1 FROM "leave_balances" LIMIT 1')
        )

        # Update only the IDs using their unique business keys.
        for _, row in duplicate_rows.iterrows():

            updated_id = balances.at[
                row.name, "balance_id"
            ]

            result = connection.execute(
                text("""
                    UPDATE leave_balances
                    SET balance_id = :new_id
                    WHERE employee_id = :employee_id
                      AND policy_id = :policy_id
                      AND leave_year = :leave_year
                """),
                {
                    "new_id": updated_id,
                    "employee_id": row["employee_id"],
                    "policy_id": row["policy_id"],
                    "leave_year": row["leave_year"]
                }
            )

            if result.rowcount != 1:
                raise ValueError(
                    f"Expected one database row for "
                    f"{row['employee_id']}, "
                    f"{row['policy_id']}, "
                    f"{row['leave_year']}; "
                    f"updated {result.rowcount}."
                )

    # Save corrected CSV after successful database transaction.
    balances.to_csv(CSV_FILE, index=False)

except Exception:
    shutil.copy2(BACKUP_FILE, CSV_FILE)
    raise

# -----------------------------------------------------
# 6. Final verification
# -----------------------------------------------------

with engine.connect() as connection:

    database_count = connection.execute(
        text('SELECT COUNT(*) FROM "leave_balances"')
    ).scalar_one()

    duplicate_count = connection.execute(
        text("""
            SELECT COUNT(*)
            FROM (
                SELECT balance_id
                FROM leave_balances
                GROUP BY balance_id
                HAVING COUNT(*) > 1
            ) duplicates
        """)
    ).scalar_one()

print("\n" + "=" * 55)
print("LEAVE BALANCE ID CORRECTION REPORT")
print("=" * 55)

print("CSV records:", len(balances))
print("Database records:", database_count)
print("IDs corrected:", len(duplicate_rows))
print("Remaining duplicate database IDs:", duplicate_count)
print("Unique CSV IDs:", balances["balance_id"].nunique())
print("Backup:", BACKUP_FILE.name)

if (
    database_count == 651
    and duplicate_count == 0
    and balances["balance_id"].nunique() == 651
):
    print("\nSUCCESS: All leave balance IDs are unique.")
else:
    raise ValueError("Final verification failed.")

engine.dispose()
