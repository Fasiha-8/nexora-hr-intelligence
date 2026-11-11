
import pandas as pd
import random
from faker import Faker
from pathlib import Path

fake = Faker()
Faker.seed(42)
random.seed(42)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "generated"

departments = pd.read_csv(DATA_DIR / "departments.csv")

# Department-specific job titles
job_titles = {
    "DEPT001": ["HR Specialist", "HR Business Partner", "Recruiter", "HR Coordinator"],
    "DEPT002": ["Software Engineer", "Senior Developer", "QA Engineer", "Tech Lead"],
    "DEPT003": ["Accountant", "Financial Analyst", "Finance Manager"],
    "DEPT004": ["Marketing Specialist", "Brand Manager", "Content Strategist"],
    "DEPT005": ["Sales Executive", "Account Manager", "Sales Analyst"],
    "DEPT006": ["Operations Analyst", "Operations Manager", "Process Specialist"],
    "DEPT007": ["Support Specialist", "Customer Success Manager"],
    "DEPT008": ["IT Support Engineer", "System Administrator", "Security Analyst"]
}

locations = ["Islamabad", "Karachi", "Lahore", "London", "Dubai", "New York"]

employment_types = ["Full-time", "Part-time", "Contract"]

employees = []

for i in range(1, 201):

    department_id = random.choice(departments["department_id"].tolist())

    first_name = fake.first_name()
    last_name = fake.last_name()

    employee = {
        "employee_id": f"EMP{i:04d}",
        "first_name": first_name,
        "last_name": last_name,
        "email": f"{first_name.lower()}.{last_name.lower()}{i}@example.com",
        "department_id": department_id,
        "job_title": random.choice(job_titles[department_id]),
        "employment_type": random.choice(employment_types),
        "employment_status": random.choices(
            ["Active", "On Leave", "Inactive"],
            weights=[85, 10, 5]
        )[0],
        "hire_date": fake.date_between(
            start_date="-8y",
            end_date="today"
        ).isoformat(),
        "location": random.choice(locations),
        "salary_grade": random.choice(["G1", "G2", "G3", "G4", "G5", "G6"]),
        "manager_id": None
    }

    employees.append(employee)

df = pd.DataFrame(employees)

# Validation
assert df["employee_id"].is_unique
assert df["department_id"].isin(
    departments["department_id"]
).all()

output_file = DATA_DIR / "employees.csv"
df.to_csv(output_file, index=False)

print("Employee dataset generated successfully!")
print(f"Total employees: {len(df)}")
print(f"Unique employee IDs: {df['employee_id'].nunique()}")
print(f"Departments represented: {df['department_id'].nunique()}")

print("\nSample employee records:")
print(df.head(10).to_string(index=False))
