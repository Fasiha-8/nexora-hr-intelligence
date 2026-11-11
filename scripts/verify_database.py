
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

# =====================================================
# NEXORA HR - DATABASE RELATIONSHIP VERIFICATION
# Read-only: does not modify database records.
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL missing from .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
inspector = inspect(engine)

EXPECTED_TABLES = [
    "departments",
    "employees",
    "managers",
    "organizational_relationships",
    "leave_policies",
    "leave_balances",
    "leave_requests",
    "projects",
    "project_assignments",
    "business_scenarios",
]

# Child table, child column, parent table, parent column
RELATIONSHIPS = [
    ("employees", "department_id", "departments", "department_id"),
    ("employees", "manager_id", "managers", "manager_id"),
    ("managers", "manager_id", "employees", "employee_id"),
    ("organizational_relationships", "employee_id", "employees", "employee_id"),
    ("organizational_relationships", "department_id", "departments", "department_id"),
    ("organizational_relationships", "manager_id", "managers", "manager_id"),
    ("leave_balances", "employee_id", "employees", "employee_id"),
    ("leave_balances", "policy_id", "leave_policies", "policy_id"),
    ("leave_requests", "employee_id", "employees", "employee_id"),
    ("leave_requests", "policy_id", "leave_policies", "policy_id"),
    ("leave_requests", "manager_id_at_submission", "managers", "manager_id"),
    ("projects", "department_id", "departments", "department_id"),
    ("projects", "project_lead_id", "managers", "manager_id"),
    ("project_assignments", "employee_id", "employees", "employee_id"),
    ("project_assignments", "project_id", "projects", "project_id"),
]

errors = []
warnings = []

print("=" * 60)
print("NEXORA TECHNOLOGIES - DATABASE VERIFICATION")
print("=" * 60)

try:
    existing_tables = set(inspector.get_table_names())

    # -------------------------------------------------
    # 1. Table existence and record counts
    # -------------------------------------------------

    print("\n1. TABLE VERIFICATION")

    for table in EXPECTED_TABLES:
        if table not in existing_tables:
            errors.append(f"Missing table: {table}")
            print(f"MISSING: {table}")
        else:
            with engine.connect() as connection:
                count = connection.execute(
                    text(f'SELECT COUNT(*) FROM "{table}"')
                ).scalar_one()

            print(f"OK: {table} - {count} records")

    # -------------------------------------------------
    # 2. Primary key verification
    # -------------------------------------------------

    print("\n2. PRIMARY KEY VERIFICATION")

    for table in EXPECTED_TABLES:
        if table not in existing_tables:
            continue

        primary_key = inspector.get_pk_constraint(table)
        columns = primary_key.get("constrained_columns") or []

        if not columns:
            errors.append(f"Missing primary key: {table}")
            print(f"MISSING: {table}")
        else:
            print(f"OK: {table} - {columns}")

    # -------------------------------------------------
    # 3. Foreign key verification
    # -------------------------------------------------

    print("\n3. FOREIGN KEY VERIFICATION")

    for table in EXPECTED_TABLES:
        if table not in existing_tables:
            continue

        foreign_keys = inspector.get_foreign_keys(table)

        for fk in foreign_keys:
            print(
                f"OK: {table}.{fk['constrained_columns']} "
                f"-> {fk['referred_table']}.{fk['referred_columns']}"
            )

    # -------------------------------------------------
    # 4. Relationship and orphan checks
    # -------------------------------------------------

    print("\n4. RELATIONSHIP INTEGRITY CHECKS")

    with engine.connect() as connection:

        for child, child_col, parent, parent_col in RELATIONSHIPS:

            if child not in existing_tables or parent not in existing_tables:
                continue

            child_columns = {
                column["name"]
                for column in inspector.get_columns(child)
            }

            parent_columns = {
                column["name"]
                for column in inspector.get_columns(parent)
            }

            if child_col not in child_columns:
                warnings.append(
                    f"Column not found: {child}.{child_col}"
                )
                continue

            if parent_col not in parent_columns:
                warnings.append(
                    f"Column not found: {parent}.{parent_col}"
                )
                continue

            query = text(f"""
                SELECT COUNT(*)
                FROM "{child}" c
                LEFT JOIN "{parent}" p
                    ON c."{child_col}" = p."{parent_col}"
                WHERE c."{child_col}" IS NOT NULL
                  AND p."{parent_col}" IS NULL
            """)

            orphan_count = connection.execute(query).scalar_one()

            if orphan_count:
                errors.append(
                    f"{child}.{child_col}: {orphan_count} orphan records"
                )
                print(
                    f"ERROR: {child}.{child_col} - "
                    f"{orphan_count} orphan records"
                )
            else:
                print(
                    f"OK: {child}.{child_col} -> "
                    f"{parent}.{parent_col}"
                )

    # -------------------------------------------------
    # 5. Final report
    # -------------------------------------------------

    print("\n" + "=" * 60)
    print("FINAL DATABASE VERIFICATION REPORT")
    print("=" * 60)

    print("Expected tables:", len(EXPECTED_TABLES))
    print("Existing tables:", len(EXPECTED_TABLES) - sum(
        1 for table in EXPECTED_TABLES
        if table not in existing_tables
    ))

    print("Errors:", len(errors))
    print("Warnings:", len(warnings))

    if errors:
        print("\nERRORS:")
        for error in errors:
            print("-", error)

    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print("-", warning)

    if not errors:
        print("\nSUCCESS: Database verification passed.")
    else:
        print("\nDATABASE VERIFICATION FAILED.")

finally:
    engine.dispose()
