from fastapi.testclient import TestClient

import webapp.main as main
from models.user import User
from services.storage_service import PayrollRepository


def test_admin_can_save_hourly_paid_leave_settings(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="admin",
            password_hash="unused",
            role="admin",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.put(
        "/company",
        data={
            "name": "テスト株式会社",
            "address": "",
            "representative": "",
            "hourly_paid_leave_enabled": "1",
            "hourly_paid_leave_unit_hours": "1",
            "hourly_paid_leave_year_start_month": "7",
            "hourly_paid_leave_year_start_day": "15",
        },
    )

    assert response.status_code == 200

    company = test_repo.company()

    assert company.hourly_paid_leave_enabled is True
    assert company.hourly_paid_leave_unit_hours == 1
    assert company.hourly_paid_leave_year_start_month == 7
    assert company.hourly_paid_leave_year_start_day == 15

    get_response = client.get("/company")

    assert get_response.status_code == 200
    assert get_response.json()["hourly_paid_leave_enabled"] is True
    assert get_response.json()["hourly_paid_leave_unit_hours"] == 1
    assert get_response.json()["hourly_paid_leave_year_start_month"] == 7
    assert get_response.json()["hourly_paid_leave_year_start_day"] == 15


def test_get_company_uses_postgres_repository_when_database_url_is_configured(
    monkeypatch,
):
    from models.company import Company

    class PostgresCompanyRepository:
        def company(self):
            return Company(
                name="PostgreSQL株式会社",
                address="Tokyo",
                representative="Taro",
            )

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@db.example.com/payroll",
    )
    monkeypatch.setattr(main, "auth_repo", PostgresCompanyRepository())
    monkeypatch.setattr(main, "require_user", lambda request: object())

    client = TestClient(main.app)
    response = client.get("/company")

    assert response.status_code == 200
    assert response.json()["name"] == "PostgreSQL株式会社"
