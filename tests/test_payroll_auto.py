from datetime import date
from decimal import Decimal

from models.employee import Employee
from services.payroll_auto_service import run_payroll_auto_check
from services.storage_service import PayrollRepository


def test_auto_check_calculates_previous_month_but_does_not_finalize(tmp_path):
    repo = PayrollRepository(tmp_path / "payroll.sqlite3")

    repo.save_employee(
        Employee(
            employee_id="E1",
            name="自動給与テスト",
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

    results = run_payroll_auto_check(
        repo,
        date(2026, 10, 1),
    )

    assert results is not None

    saved = repo.payroll_result("E1", "2026-09")

    assert saved is not None
    assert saved.finalized is False
    assert repo.auto_payroll_processed_month() == "2026-09"
