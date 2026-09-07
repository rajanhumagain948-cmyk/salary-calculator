from decimal import Decimal

from fastapi.testclient import TestClient

import webapp.main as main
from models.payroll import PayrollResult, TimeClassification
from models.user import User
from services.storage_service import PayrollRepository


def test_admin_can_finalize_payroll_without_blocking_issues(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="admin",
            password_hash="unused",
            role="admin",
        )
    )

    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E1",
            year_month="2026-08",
            classification=TimeClassification(),
            payments={"基本給": Decimal("200000")},
            deductions={"所得税": Decimal("3270")},
            blocking_issues=[],
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/payroll/finalize",
        data={
            "employee_id": "E1",
            "year_month": "2026-08",
        },
    )

    assert response.status_code == 200

    saved = test_repo.payroll_result("E1", "2026-08")
    assert saved is not None
    assert saved.finalized is True
    assert saved.payments["基本給"] == Decimal("200000")
    assert saved.deductions["所得税"] == Decimal("3270")


def test_admin_cannot_finalize_payroll_with_blocking_issues(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="admin",
            password_hash="unused",
            role="admin",
        )
    )

    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E1",
            year_month="2026-08",
            classification=TimeClassification(),
            payments={"基本給": Decimal("200000")},
            deductions={"所得税": Decimal("3270")},
            blocking_issues=["勤怠に未確認の問題があります。"],
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/payroll/finalize",
        data={
            "employee_id": "E1",
            "year_month": "2026-08",
        },
    )

    assert response.status_code == 409

    saved = test_repo.payroll_result("E1", "2026-08")
    assert saved is not None
    assert saved.finalized is False
    assert saved.blocking_issues == ["勤怠に未確認の問題があります。"]


def test_employee_cannot_finalize_payroll(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="employee",
            password_hash="unused",
            role="employee",
            employee_id="E1",
        )
    )

    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E1",
            year_month="2026-08",
            classification=TimeClassification(),
            payments={"基本給": Decimal("200000")},
            deductions={"所得税": Decimal("3270")},
            blocking_issues=[],
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/payroll/finalize",
        data={
            "employee_id": "E1",
            "year_month": "2026-08",
        },
    )

    assert response.status_code == 403

    saved = test_repo.payroll_result("E1", "2026-08")
    assert saved is not None
    assert saved.finalized is False


def test_cannot_finalize_payroll_before_calculation(tmp_path, monkeypatch):
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

    response = client.post(
        "/payroll/finalize",
        data={
            "employee_id": "E-NOT-CALCULATED",
            "year_month": "2026-08",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "先に給与を計算してください。"
    assert test_repo.payroll_result(
        "E-NOT-CALCULATED",
        "2026-08",
    ) is None


def test_finalized_payroll_cannot_be_recalculated(tmp_path, monkeypatch):
    from datetime import date

    from models.employee import Employee

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="admin",
            password_hash="unused",
            role="admin",
        )
    )

    test_repo.save_employee(
        Employee(
            employee_id="E1",
            name="確定済みテスト",
            employment_type="正社員",
            hire_date=date(2026, 1, 1),
            pay_type="月給",
            monthly_salary=Decimal("999999"),
        )
    )

    # 確定時点では基本給200,000円だった、というスナップショット。
    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E1",
            year_month="2026-08",
            classification=TimeClassification(),
            payments={"基本給": Decimal("200000")},
            deductions={"所得税": Decimal("3270")},
            blocking_issues=[],
            finalized=True,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/payroll/calculate",
        data={
            "employee_id": "E1",
            "year_month": "2026-08",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "確定済みの給与は再計算できません。"

    saved = test_repo.payroll_result("E1", "2026-08")
    assert saved is not None
    assert saved.finalized is True
    assert saved.payments["基本給"] == Decimal("200000")
    assert saved.deductions["所得税"] == Decimal("3270")


def test_employee_cannot_view_own_unfinalized_payroll(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="employee",
            password_hash="unused",
            role="employee",
            employee_id="E1",
        )
    )

    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E1",
            year_month="2026-08",
            classification=TimeClassification(),
            payments={"基本給": Decimal("200000")},
            deductions={"所得税": Decimal("3270")},
            finalized=False,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get("/payroll/2026-08/E1")

    assert response.status_code == 404


def test_employee_cannot_view_another_employees_finalized_payroll(
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
            employee_id="E1",
        )
    )

    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E2",
            year_month="2026-08",
            classification=TimeClassification(),
            payments={"基本給": Decimal("300000")},
            deductions={"所得税": Decimal("5000")},
            finalized=True,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get("/payroll/2026-08/E2")

    assert response.status_code == 403
