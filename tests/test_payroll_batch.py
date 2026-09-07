from datetime import date
from decimal import Decimal

from models.employee import Employee
from services.payroll_batch_service import calculate_monthly_payrolls
from services.storage_service import PayrollRepository


def test_batch_calculation_never_finalizes_payroll(tmp_path):
    repo = PayrollRepository(tmp_path / "payroll.sqlite3")

    repo.save_employee(
        Employee(
            employee_id="E1",
            name="自動計算テスト",
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

    results = calculate_monthly_payrolls(repo, "2026-09")

    assert len(results) == 1
    assert results[0].payroll is not None
    assert results[0].payroll.finalized is False

    saved = repo.payroll_result("E1", "2026-09")

    assert saved is not None
    assert saved.finalized is False
