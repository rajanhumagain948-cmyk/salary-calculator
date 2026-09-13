from fastapi.testclient import TestClient

import webapp.main as main
from models.user import User
from services.storage_service import PayrollRepository


def test_employee_cannot_view_overtime_predictions(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="employee",
            password_hash="unused",
            role="employee",
            employee_id="E001",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/overtime",
        params={
            "year_month": "2026-09",
            "as_of": "2026-09-10",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "admin only"


def test_overtime_predictions_reject_invalid_year_month(tmp_path, monkeypatch):
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

    response = client.get(
        "/predictions/overtime",
        params={
            "year_month": "2026-9",
            "as_of": "2026-09-10",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "year_month must be YYYY-MM"


def test_overtime_predictions_reject_invalid_as_of(tmp_path, monkeypatch):
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

    response = client.get(
        "/predictions/overtime",
        params={
            "year_month": "2026-09",
            "as_of": "not-a-date",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "as_of must be YYYY-MM-DD"


def test_overtime_predictions_reject_as_of_outside_target_month(
    tmp_path,
    monkeypatch,
):
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

    response = client.get(
        "/predictions/overtime",
        params={
            "year_month": "2026-09",
            "as_of": "2026-10-01",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "as_of must be within year_month"
