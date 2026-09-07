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


def test_employee_can_view_own_finalized_payroll(tmp_path, monkeypatch):
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
            finalized=True,
            company_name="テスト株式会社",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get("/payroll/2026-08/E1")

    assert response.status_code == 200

    data = response.json()
    assert data["employee_id"] == "E1"
    assert data["year_month"] == "2026-08"
    assert data["finalized"] is True
    assert data["payments"]["基本給"] == "200000"
    assert data["deductions"]["所得税"] == "3270"
    assert data["gross_pay"] == "200000"
    assert data["net_pay"] == "196730"
    assert data["company_name"] == "テスト株式会社"


def test_employee_can_download_own_finalized_payroll_pdf(
    tmp_path,
    monkeypatch,
):
    from datetime import date

    from models.employee import Employee

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

    test_repo.save_employee(
        Employee(
            employee_id="E1",
            name="給与明細テスト",
            employment_type="正社員",
            hire_date=date(2026, 1, 1),
            pay_type="月給",
            monthly_salary=Decimal("200000"),
        )
    )

    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E1",
            year_month="2026-08",
            classification=TimeClassification(),
            payments={"基本給": Decimal("200000")},
            deductions={"所得税": Decimal("3270")},
            finalized=True,
            company_name="テスト株式会社",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get("/payroll/2026-08/E1/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 0


def test_employee_cannot_download_another_employees_payroll_pdf(
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
            finalized=True,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get("/payroll/2026-08/E2/pdf")

    assert response.status_code == 403


def test_employee_cannot_download_own_unfinalized_payroll_pdf(
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
            employee_id="E1",
            year_month="2026-08",
            classification=TimeClassification(),
            payments={"基本給": Decimal("200000")},
            finalized=False,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get("/payroll/2026-08/E1/pdf")

    assert response.status_code == 404


def test_admin_can_calculate_all_employees_payroll(tmp_path, monkeypatch):
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
            name="社員1",
            employment_type="正社員",
            hire_date=date(2026, 1, 1),
            pay_type="月給",
            monthly_salary=Decimal("200000"),
            weekly_hours=Decimal("40"),
            weekly_days=5,
            workplace_size=100,
            dependents=0,
            tax_category="甲",
            standard_monthly_remuneration=Decimal("200000"),
        )
    )

    test_repo.save_employee(
        Employee(
            employee_id="E2",
            name="社員2",
            employment_type="正社員",
            hire_date=date(2026, 1, 1),
            pay_type="月給",
            monthly_salary=Decimal("250000"),
            weekly_hours=Decimal("40"),
            weekly_days=5,
            workplace_size=100,
            dependents=0,
            tax_category="甲",
            standard_monthly_remuneration=Decimal("250000"),
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/payroll/calculate-all",
        data={"year_month": "2026-09"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["year_month"] == "2026-09"
    assert len(data["results"]) == 2
    assert [item["employee_id"] for item in data["results"]] == ["E1", "E2"]

    assert test_repo.payroll_result("E1", "2026-09") is not None
    assert test_repo.payroll_result("E2", "2026-09") is not None


def test_batch_payroll_does_not_recalculate_finalized_payroll(
    tmp_path,
    monkeypatch,
):
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

    # 現在の従業員情報は300,000円。
    test_repo.save_employee(
        Employee(
            employee_id="E1",
            name="確定済み社員",
            employment_type="正社員",
            hire_date=date(2026, 1, 1),
            pay_type="月給",
            monthly_salary=Decimal("300000"),
            weekly_hours=Decimal("40"),
            weekly_days=5,
            workplace_size=100,
            standard_monthly_remuneration=Decimal("300000"),
        )
    )

    # しかし2026-09給与は200,000円で既に確定済み。
    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E1",
            year_month="2026-09",
            classification=TimeClassification(),
            payments={"基本給": Decimal("200000")},
            deductions={"所得税": Decimal("3270")},
            finalized=True,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/payroll/calculate-all",
        data={"year_month": "2026-09"},
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "確定済"

    saved = test_repo.payroll_result("E1", "2026-09")
    assert saved is not None
    assert saved.finalized is True
    assert saved.payments["基本給"] == Decimal("200000")
    assert saved.deductions["所得税"] == Decimal("3270")


def test_batch_payroll_marks_warning_as_needs_review(
    tmp_path,
    monkeypatch,
):
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
            name="要確認社員",
            employment_type="パート",
            hire_date=date(2026, 1, 1),
            pay_type="時給",
            hourly_rate=Decimal("1200"),
            weekly_hours=Decimal("20"),
            workplace_size=20,
            standard_monthly_remuneration=Decimal("0"),
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/payroll/calculate-all",
        data={"year_month": "2026-09"},
    )

    assert response.status_code == 200

    item = response.json()["results"][0]

    assert item["employee_id"] == "E1"
    assert item["status"] == "要確認"
    assert item["payroll"] is not None
    assert (
        "標準報酬月額が未登録のため、今月の総支給額を暫定使用しています。"
        in item["payroll"]["warnings"]
    )


def test_batch_payroll_marks_calculation_error_as_unavailable(
    tmp_path,
    monkeypatch,
):
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

    # 正常に計算できる社員
    test_repo.save_employee(
        Employee(
            employee_id="E1",
            name="正常社員",
            employment_type="正社員",
            hire_date=date(2026, 1, 1),
            pay_type="月給",
            monthly_salary=Decimal("200000"),
            weekly_hours=Decimal("40"),
            weekly_days=5,
            workplace_size=100,
            standard_monthly_remuneration=Decimal("200000"),
        )
    )

    # 給与額が不正で計算できない社員
    test_repo.save_employee(
        Employee(
            employee_id="E2",
            name="計算不可社員",
            employment_type="正社員",
            hire_date=date(2026, 1, 1),
            pay_type="月給",
            monthly_salary=Decimal("-1"),
            weekly_hours=Decimal("40"),
            weekly_days=5,
            workplace_size=100,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/payroll/calculate-all",
        data={"year_month": "2026-09"},
    )

    assert response.status_code == 200

    results = {
        item["employee_id"]: item
        for item in response.json()["results"]
    }

    assert results["E1"]["status"] in ("正常", "要確認")
    assert results["E1"]["payroll"] is not None

    assert results["E2"]["status"] == "計算不可"
    assert results["E2"]["payroll"] is None
    assert "時給・月給は0円以上で入力してください。" in results["E2"]["error"]

    # E2の失敗で一括処理全体が止まらず、E1は保存される。
    assert test_repo.payroll_result("E1", "2026-09") is not None
    assert test_repo.payroll_result("E2", "2026-09") is None


def test_app_lifespan_runs_automatic_payroll_check(monkeypatch):
    calls = []

    def fake_auto_check(repo):
        calls.append(repo)
        return None

    monkeypatch.setattr(main, "run_payroll_auto_check", fake_auto_check)

    with TestClient(main.app):
        pass

    assert calls == [main.repo]


def test_admin_can_list_payroll_results_for_month(tmp_path, monkeypatch):
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
            year_month="2026-09",
            classification=TimeClassification(),
            payments={"基本給": Decimal("200000")},
            deductions={"所得税": Decimal("3270")},
            finalized=False,
        )
    )

    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E2",
            year_month="2026-09",
            classification=TimeClassification(),
            payments={"基本給": Decimal("250000")},
            deductions={"所得税": Decimal("5000")},
            finalized=True,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get("/payroll-results/2026-09")

    assert response.status_code == 200

    data = response.json()

    assert data["year_month"] == "2026-09"
    assert len(data["results"]) == 2
    assert data["results"][0]["employee_id"] == "E1"
    assert data["results"][0]["finalized"] is False
    assert data["results"][1]["employee_id"] == "E2"
    assert data["results"][1]["finalized"] is True


def test_employee_cannot_list_all_payroll_results(tmp_path, monkeypatch):
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

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get("/payroll-results/2026-09")

    assert response.status_code == 403
