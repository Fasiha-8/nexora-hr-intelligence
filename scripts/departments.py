
import pandas as pd
from pathlib import Path

# Project root directory
BASE_DIR = Path(__file__).resolve().parents[1]

# Output directory
OUTPUT_DIR = BASE_DIR / "data" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Synthetic organization departments
departments = [
    {
        "department_id": "DEPT001",
        "department_name": "Human Resources",
        "department_code": "HR",
        "description": "Employee management, recruitment and HR operations"
    },
    {
        "department_id": "DEPT002",
        "department_name": "Engineering",
        "department_code": "ENG",
        "description": "Software development and engineering"
    },
    {
        "department_id": "DEPT003",
        "department_name": "Finance",
        "department_code": "FIN",
        "description": "Financial planning, accounting and payroll"
    },
    {
        "department_id": "DEPT004",
        "department_name": "Marketing",
        "department_code": "MKT",
        "description": "Marketing strategy and brand management"
    },
    {
        "department_id": "DEPT005",
        "department_name": "Sales",
        "department_code": "SAL",
        "description": "Business development and sales operations"
    },
    {
        "department_id": "DEPT006",
        "department_name": "Operations",
        "department_code": "OPS",
        "description": "Business operations and process management"
    },
    {
        "department_id": "DEPT007",
        "department_name": "Customer Support",
        "department_code": "CS",
        "description": "Customer service and support operations"
    },
    {
        "department_id": "DEPT008",
        "department_name": "Information Technology",
        "department_code": "IT",
        "description": "IT infrastructure, security and technical support"
    }
]

# Convert to DataFrame
df = pd.DataFrame(departments)

# Validate department IDs
assert df["department_id"].is_unique

# Save dataset
output_file = OUTPUT_DIR / "departments.csv"
df.to_csv(output_file, index=False)

print("Department dataset generated successfully!")
print(f"Total departments: {len(df)}")
print(f"Saved to: {output_file}")

print("\nDepartment records:")
print(df.to_string(index=False))
