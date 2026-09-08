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
        },
    )

    assert response.status_code == 200

    company = test_repo.company()

    assert company.hourly_paid_leave_enabled is True
    assert company.hourly_paid_leave_unit_hours == 1

    get_response = client.get("/company")

    assert get_response.status_code == 200
    assert get_response.json()["hourly_paid_leave_enabled"] is True
    assert get_response.json()["hourly_paid_leave_unit_hours"] == 1
