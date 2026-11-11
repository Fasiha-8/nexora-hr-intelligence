
from pathlib import Path
import os
import re
import sys

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.types import (
    Integer,
    Float,
    Boolean,
    Date,
    DateTime,
    Text
)

# =====================================================
# NEXORA TECHNOLOGIES - DATABASE INITIALIZATION
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "generated"
SCENARIO_DIR = BASE_DIR / "data" / "scenarios"

load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL missing from .env file.")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# CSV filename -> PostgreSQL table name
DATASETS = {
    "departments": (DATA_DIR / "departments.csv", "departments"),
    "employees": (DATA_DIR / "employees.csv", "employees"),
    "managers": (DATA_DIR / "managers.csv", "managers"),
    "organizational_relationships": (
        DATA_DIR / "organizational_relationships.csv",
        "organizational_relationships"
    ),
    "leave_policies": (DATA_DIR / "leave_policies.csv", "leave_policies"),
    "leave_balances": (DATA_DIR / "leave_balances.csv", "leave_balances"),
    "leave_requests": (DATA_DIR / "leave_requests.csv", "leave_requests"),
    "projects": (DATA_DIR / "projects.csv", "projects"),
    "project_assignments": (
        DATA_DIR / "project_assignments.csv",
        "project_assignments"
    ),
    "business_scenarios": (
        SCENARIO_DIR / "business_scenarios.csv",
        "business_scenarios"
    )
}


# -----------------------------------------------------
# Infer safe PostgreSQL data types
# -----------------------------------------------------

def infer_sql_type(series):

    name = series.name.lower()

    if name in {
        "is_current",
        "is_active",
        "is_critical_member",
        "insufficient_balance"
    }:
        return Boolean()

    if "date" in name and "datetime" not in name:
        return Date()

    if "timestamp" in name or "datetime" in name:
        return DateTime()

    if (
        name.endswith("_days")
        or name.endswith("_percentage")
        or name in {
            "leave_year",
            "requested_days",
            "required_team_size",
            "minimum_coverage"
        }
    ):
        return Float()

    if pd.api.types.is_bool_dtype(series):
        return Boolean()

    if pd.api.types.is_integer_dtype(series):
        return Integer()

    if pd.api.types.is_float_dtype(series):
        return Float()

    return Text()


# -----------------------------------------------------
# Validate and prepare CSV
# -----------------------------------------------------

def prepare_dataframe(file_path):

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {file_path}"
        )

    df = pd.read_csv(file_path)

    df.columns = [
        re.sub(r"[^a-zA-Z0-9_]", "_", str(col).strip()).lower()
        for col in df.columns
    ]

    if df.columns.duplicated().any():
        raise ValueError(
            f"Duplicate column names after normalization: {file_path.name}"
        )

    # Parse date columns
    for column in df.columns:
        if "date" in column:
            parsed = pd.to_datetime(
                df[column], errors="coerce"
            )

            if df[column].notna().sum() == parsed.notna().sum():
                df[column] = parsed.dt.date

    # Preserve missing values as SQL NULL
    df = df.astype(object).where(pd.notna(df), None)

    return df


# -----------------------------------------------------
# Connect to PostgreSQL
# -----------------------------------------------------

print("=" * 60)
print("NEXORA TECHNOLOGIES - DATABASE INITIALIZATION")
print("=" * 60)

with engine.connect() as connection:
    connection.execute(text("SELECT 1"))
    print("\nPostgreSQL connection successful.")

# -----------------------------------------------------
# Import datasets in dependency order
# -----------------------------------------------------

import_order = [
    "departments",
    "employees",
    "managers",
    "organizational_relationships",
    "leave_policies",
    "leave_balances",
    "leave_requests",
    "projects",
    "project_assignments",
    "business_scenarios"
]

imported_counts = {}

for table_name in import_order:

    file_path, _ = DATASETS[table_name]

    print(f"\nImporting {table_name}...")

    df = prepare_dataframe(file_path)

    dtype_mapping = {
        column: infer_sql_type(df[column])
        for column in df.columns
    }

    # Replace only this prototype table's contents.
    # Existing CSV source files are never modified.
    with engine.begin() as connection:

        connection.execute(
            text(
                f'DROP TABLE IF EXISTS "{table_name}" CASCADE'
            )
        )

        df.to_sql(
            name=table_name,
            con=connection,
            if_exists="replace",
            index=False,
            dtype=dtype_mapping,
            method="multi",
            chunksize=500
        )

    imported_counts[table_name] = len(df)

    print(
        f"Imported {len(df)} records into {table_name}."
    )


# -----------------------------------------------------
# Verify database record counts
# -----------------------------------------------------

print("\n" + "=" * 60)
print("DATABASE IMPORT VERIFICATION")
print("=" * 60)

verification_errors = []

with engine.connect() as connection:

    for table_name, expected_count in imported_counts.items():

        actual_count = connection.execute(
            text(f'SELECT COUNT(*) FROM "{table_name}"')
        ).scalar_one()

        print(
            f"{table_name}: {actual_count} records"
        )

        if actual_count != expected_count:
            verification_errors.append(table_name)

if verification_errors:
    print("\nImport verification failed:")
    print(verification_errors)
    sys.exit(1)

print("\nAll 10 datasets imported and verified successfully.")

engine.dispose()
