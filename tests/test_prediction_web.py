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


def test_employee_cannot_view_payroll_estimates(tmp_path, monkeypatch):
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
        "/predictions/payroll-estimate",
        params={
            "year_month": "2026-09",
            "as_of": "2026-09-10",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "admin only"


def test_payroll_estimates_reject_invalid_year_month(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(username="admin", password_hash="unused", role="admin")
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/payroll-estimate",
        params={
            "year_month": "2026-9",
            "as_of": "2026-09-10",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "year_month must be YYYY-MM"


def test_payroll_estimates_reject_invalid_as_of(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(username="admin", password_hash="unused", role="admin")
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/payroll-estimate",
        params={
            "year_month": "2026-09",
            "as_of": "not-a-date",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "as_of must be YYYY-MM-DD"


def test_payroll_estimates_reject_as_of_outside_target_month(
    tmp_path,
    monkeypatch,
):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(username="admin", password_hash="unused", role="admin")
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/payroll-estimate",
        params={
            "year_month": "2026-09",
            "as_of": "2026-10-01",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "as_of must be within year_month"


def test_admin_can_view_payroll_estimate(tmp_path, monkeypatch):
    from datetime import date
    from decimal import Decimal

    from models.employee import Employee
    from models.employment import EmploymentTerms

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
            monthly_salary=Decimal("200000"),
        )
    )
    test_repo.save_terms(
        EmploymentTerms(
            "E001",
            monthly_hourly_divisor=Decimal("160"),
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/payroll-estimate",
        params={
            "year_month": "2026-09",
            "as_of": "2026-09-10",
        },
    )

    assert response.status_code == 200
    assert response.json()["reference_only"] is True
    assert response.json()["used_for_payroll"] is False
    assert response.json()["includes_future_work"] is False
    assert response.json()["method"] == (
        "基準日までの実績勤怠と現在入力済みの給与条件による参考試算"
    )
    assert response.json()["items"][0]["employee_id"] == "E001"
    assert response.json()["items"][0]["employee_name"] == "山田太郎"
    assert response.json()["items"][0]["forecastable"] is True
    assert response.json()["items"][0]["gross_pay"] == "200000"
    assert response.json()["summary"] == {
        "gross_pay_reference_total": "200000",
        "included_count": 1,
        "excluded_count": 0,
    }
    assert test_repo.payroll_result("E001", "2026-09") is None


def test_payroll_estimate_preserves_finalized_payroll(tmp_path, monkeypatch):
    from datetime import date
    from decimal import Decimal

    from models.employee import Employee
    from models.payroll import PayrollResult, TimeClassification

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
            monthly_salary=Decimal("999999"),
        )
    )
    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E001",
            year_month="2026-09",
            classification=TimeClassification(),
            payments={"基本給": Decimal("200000")},
            deductions={"所得税": Decimal("5000")},
            finalized=True,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/payroll-estimate",
        params={
            "year_month": "2026-09",
            "as_of": "2026-09-10",
        },
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["status"] == "確定済"
    assert item["gross_pay"] == "200000"
    assert item["total_deductions"] == "5000"
    assert item["net_pay"] == "195000"


def test_payroll_estimate_reports_employee_calculation_error(
    tmp_path,
    monkeypatch,
):
    from datetime import date
    from decimal import Decimal

    from models.employee import Employee

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
            monthly_salary=Decimal("-1"),
        )
    )

    client = TestClient(main.app, raise_server_exceptions=False)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/payroll-estimate",
        params={
            "year_month": "2026-09",
            "as_of": "2026-09-10",
        },
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["employee_id"] == "E001"
    assert item["employee_name"] == "山田太郎"
    assert item["status"] == "計算不可"
    assert item["error"] == "時給・月給は0円以上で入力してください。"
    assert response.json()["summary"] == {
        "gross_pay_reference_total": "0",
        "included_count": 0,
        "excluded_count": 1,
    }


def test_employee_cannot_view_leave_trends(tmp_path, monkeypatch):
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
        "/predictions/leave-trend",
        params={"year": "2026"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "admin only"


def test_leave_trends_reject_invalid_year(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(username="admin", password_hash="unused", role="admin")
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/leave-trend",
        params={"year": "26"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "year must be YYYY"


def test_admin_can_view_leave_trend_items(tmp_path, monkeypatch):
    from datetime import date
    from decimal import Decimal

    from models.employee import Employee
    from models.employment import EmploymentTerms
    from models.leave_request import LeaveRequest

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
        )
    )
    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E001",
            leave_date=date(2026, 2, 10),
            status="承認",
            leave_unit="全日",
        )
    )
    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E001",
            leave_date=date(2026, 7, 15),
            status="承認",
            leave_unit="半日",
            half_day_period="午前",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/leave-trend",
        params={"year": "2026"},
    )

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "employee_id": "E001",
            "employee_name": "山田太郎",
            "approved_request_count": 2,
            "approved_days": "1.5",
            "monthly_approved_days": {
                "2026-02": "1",
                "2026-07": "0.5",
            },
        }
    ]


def test_employee_cannot_view_payroll_processing_risks(
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
        "/predictions/payroll-risk",
        params={"year_month": "2026-09"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "admin only"


def test_payroll_risks_reject_invalid_year_month(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(username="admin", password_hash="unused", role="admin")
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/payroll-risk",
        params={"year_month": "2026-9"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "year_month must be YYYY-MM"


def test_admin_can_view_payroll_processing_risks(tmp_path, monkeypatch):
    from decimal import Decimal

    from models.employee import Employee
    from models.payroll import PayrollResult, TimeClassification

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(username="admin", password_hash="unused", role="admin")
    )

    for employee_id, name in (
        ("E001", "要確認A"),
        ("E002", "要確認B"),
        ("E003", "問題なし"),
    ):
        test_repo.save_employee(
            Employee(
                employee_id=employee_id,
                name=name,
                employment_type="正社員",
                hire_date=__import__("datetime").date(2025, 1, 1),
                pay_type="月給",
                monthly_salary=Decimal("200000"),
            )
        )

    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E001",
            year_month="2026-09",
            classification=TimeClassification(),
            warnings=["警告A"],
            blocking_issues=["ブロッキングA"],
        )
    )
    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E002",
            year_month="2026-09",
            classification=TimeClassification(),
            warnings=["警告B"],
        )
    )
    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E003",
            year_month="2026-09",
            classification=TimeClassification(),
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/predictions/payroll-risk",
        params={"year_month": "2026-09"},
    )

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "employee_id": "E001",
            "employee_name": "要確認A",
            "level": "high",
            "reasons": ["ブロッキングA", "警告A"],
        },
        {
            "employee_id": "E002",
            "employee_name": "要確認B",
            "level": "medium",
            "reasons": ["警告B"],
        },
    ]
