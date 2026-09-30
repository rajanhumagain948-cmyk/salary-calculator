from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

import webapp.main as main
from models.employee import Employee


def test_get_employees_uses_postgres_when_database_url_is_configured(monkeypatch):
    class Admin:
        role = "admin"

    class PostgresEmployeeRepository:
        def employees(self):
            return [
                Employee(
                    employee_id="PG1",
                    name="PostgreSQL Employee",
                    employment_type="正社員",
                    hire_date=date(2026, 1, 1),
                    pay_type="月給",
                    monthly_salary=Decimal("200000"),
                )
            ]

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@db.example.com/payroll",
    )
    monkeypatch.setattr(main, "auth_repo", PostgresEmployeeRepository())
    monkeypatch.setattr(main, "require_user", lambda request: Admin())

    client = TestClient(main.app)
    response = client.get("/employees")

    assert response.status_code == 200
    assert response.json() == [
        {
            "employee_id": "PG1",
            "name": "PostgreSQL Employee",
        }
    ]
