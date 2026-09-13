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


def test_admin_can_view_employee_overtime_prediction(tmp_path, monkeypatch):
    from datetime import date

    from models.employee import Employee
    from models.employment import EmploymentTerms
    from models.shifts import Shift
    from models.work_record import WorkRecord

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(username="admin", password_hash="unused", role="admin")
    )
    test_repo.save_employee(
        Employee(
            employee_id="E001",
            name="山田太郎",
            employment_type="正社員",
            hire_date=date(2025, 1, 1),
            pay_type="月給",
        )
    )
    test_repo.save_terms(
        EmploymentTerms(
            "E001",
            standard_daily_minutes=480,
            standard_weekly_minutes=2400,
        )
    )
    test_repo.save_work_record(
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=19 * 60,
            break_total_minutes=60,
        )
    )
    test_repo.save_shift(
        Shift(
            employee_id="E001",
            shift_date=date(2026, 9, 2),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_minutes=60,
            confirmed=True,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/overtime",
        params={
            "year_month": "2026-09",
            "as_of": "2026-09-01",
        },
    )

    assert response.status_code == 200
    assert response.json()["reference_only"] is True
    assert response.json()["used_for_payroll"] is False
    assert response.json()["method"] == (
        "実績勤務日1日あたりの平均残業時間を、"
        "基準日より後の確定シフト日数へ外挿"
    )
    assert response.json()["items"] == [
        {
            "employee_id": "E001",
            "employee_name": "山田太郎",
            "actual_overtime_minutes": 60,
            "future_confirmed_shift_days": 1,
            "forecast_overtime_minutes": 120,
        }
    ]


def test_employee_cannot_view_attendance_review_predictions(
    tmp_path,
    monkeypatch,
):
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
        "/predictions/attendance-review",
        params={"year_month": "2026-09"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "admin only"


def test_attendance_review_rejects_invalid_year_month(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(username="admin", password_hash="unused", role="admin")
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/attendance-review",
        params={"year_month": "2026-9"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "year_month must be YYYY-MM"


def test_admin_can_view_attendance_review_items(tmp_path, monkeypatch):
    from datetime import date

    from models.employee import Employee
    from models.work_record import WorkRecord

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(username="admin", password_hash="unused", role="admin")
    )
    test_repo.save_employee(
        Employee(
            employee_id="E001",
            name="山田太郎",
            employment_type="正社員",
            hire_date=date(2025, 1, 1),
            pay_type="月給",
        )
    )
    test_repo.save_work_record(
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_total_minutes=0,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/attendance-review",
        params={"year_month": "2026-09"},
    )

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "employee_id": "E001",
            "employee_name": "山田太郎",
            "warning_count": 1,
            "warnings": [
                {
                    "work_date": "2026-09-01",
                    "messages": ["休憩が法定目安より60分不足しています。"],
                }
            ],
        }
    ]
