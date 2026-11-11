
from pathlib import Path
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

# =====================================================
# NEXORA HR - DATABASE CONSTRAINTS
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL missing from .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# -----------------------------------------------------
# 1. Define primary keys
# -----------------------------------------------------

PRIMARY_KEYS = {
    "departments": ["department_id"],
    "employees": ["employee_id"],
    "managers": ["manager_id"],
    "organizational_relationships": ["relationship_id"],
    "leave_policies": ["policy_id"],
    "leave_balances": ["balance_id"],
    "leave_requests": ["request_id"],
    "projects": ["project_id"],
    "project_assignments": ["assignment_id"],
    "business_scenarios": ["scenario_id"]
}

# -----------------------------------------------------
# 2. Define foreign keys
# -----------------------------------------------------

FOREIGN_KEYS = [
    ("employees", "department_id", "departments", "department_id"),
    ("employees", "manager_id", "managers", "manager_id"),

    ("managers", "manager_id", "employees", "employee_id"),
    ("managers", "department_id", "departments", "department_id"),

    ("organizational_relationships", "employee_id", "employees", "employee_id"),
    ("organizational_relationships", "department_id", "departments", "department_id"),

    ("leave_balances", "employee_id", "employees", "employee_id"),
    ("leave_balances", "policy_id", "leave_policies", "policy_id"),

    ("leave_requests", "employee_id", "employees", "employee_id"),
    ("leave_requests", "policy_id", "leave_policies", "policy_id"),

    ("projects", "department_id", "departments", "department_id"),
    ("projects", "project_lead_id", "managers", "manager_id"),

    ("project_assignments", "employee_id", "employees", "employee_id"),
    ("project_assignments", "project_id", "projects", "project_id")
]

# -----------------------------------------------------
# 3. Define unique constraints
# -----------------------------------------------------

UNIQUE_CONSTRAINTS = {
    "leave_balances": [
        ("employee_id", "policy_id", "leave_year")
    ]
}

# -----------------------------------------------------
# 4. Apply constraints
# -----------------------------------------------------

def quote_identifier(name):
    if not name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe SQL identifier: {name}")
    return f'"{name}"'


with engine.begin() as connection:

    inspector = inspect(connection)

    print("Checking database tables...")

    existing_tables = set(inspector.get_table_names())

    for table in PRIMARY_KEYS:
        if table not in existing_tables:
            raise ValueError(f"Missing database table: {table}")

    print("All required tables exist.")

    # Primary keys
    for table, columns in PRIMARY_KEYS.items():

        current_pks = inspector.get_pk_constraint(table)
        if current_pks.get("constrained_columns"):
            print(f"Primary key already exists: {table}")
            continue

        column_sql = ", ".join(
            quote_identifier(col) for col in columns
        )

        connection.execute(text(
            f"ALTER TABLE {quote_identifier(table)} "
            f"ADD CONSTRAINT {quote_identifier('pk_' + table)} "
            f"PRIMARY KEY ({column_sql})"
        ))

        print(f"Primary key added: {table}")

    # Unique constraints
    inspector = inspect(connection)

    for table, constraints in UNIQUE_CONSTRAINTS.items():

        existing = {
            tuple(item["column_names"])
            for item in inspector.get_unique_constraints(table)
        }

        for columns in constraints:

            if tuple(columns) in existing:
                print(f"Unique constraint already exists: {table}")
                continue

            column_sql = ", ".join(
                quote_identifier(col) for col in columns
            )

            constraint_name = "uq_" + table + "_" + "_".join(columns)

            connection.execute(text(
                f"ALTER TABLE {quote_identifier(table)} "
                f"ADD CONSTRAINT {quote_identifier(constraint_name)} "
                f"UNIQUE ({column_sql})"
            ))

            print(f"Unique constraint added: {table}")

    # Foreign keys
    inspector = inspect(connection)

    existing_fks = {
        (
            fk["constrained_table"],
            tuple(fk["constrained_columns"]),
            fk["referred_table"],
            tuple(fk["referred_columns"])
        )
        for table in existing_tables
        for fk in inspector.get_foreign_keys(table)
    }

    for child, child_col, parent, parent_col in FOREIGN_KEYS:

        key = (
            child,
            (child_col,),
            parent,
            (parent_col,)
        )

        if key in existing_fks:
            print(f"Foreign key already exists: {child}.{child_col}")
            continue

        constraint_name = f"fk_{child}_{child_col}"

        connection.execute(text(
            f"ALTER TABLE {quote_identifier(child)} "
            f"ADD CONSTRAINT {quote_identifier(constraint_name)} "
            f"FOREIGN KEY ({quote_identifier(child_col)}) "
            f"REFERENCES {quote_identifier(parent)} "
            f"({quote_identifier(parent_col)})"
        ))

        print(f"Foreign key added: {child}.{child_col}")

    # Indexes for common joins and lookups
    index_columns = {
        "employees": ["department_id", "manager_id"],
        "organizational_relationships": ["employee_id"],
        "leave_balances": ["employee_id", "policy_id"],
        "leave_requests": ["employee_id", "request_status"],
        "projects": ["department_id"],
        "project_assignments": ["employee_id", "project_id"]
    }

    inspector = inspect(connection)

    for table, columns in index_columns.items():

        existing_indexes = {
            index["name"]
            for index in inspector.get_indexes(table)
        }

        for column in columns:

            index_name = f"idx_{table}_{column}"

            if index_name in existing_indexes:
                continue

            connection.execute(text(
                f"CREATE INDEX {quote_identifier(index_name)} "
                f"ON {quote_identifier(table)} "
                f"({quote_identifier(column)})"
            ))

            print(f"Index created: {index_name}")

print("\nAll database constraints applied successfully.")

engine.dispose()
