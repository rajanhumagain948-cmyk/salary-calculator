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


def test_completed_payroll_month_is_previous_month():
    from services.payroll_batch_service import completed_payroll_month

    assert completed_payroll_month(date(2026, 10, 1)) == "2026-09"
    assert completed_payroll_month(date(2026, 9, 30)) == "2026-08"
    assert completed_payroll_month(date(2026, 1, 1)) == "2025-12"


def test_due_payroll_batch_calculates_previous_month_without_finalizing(
    tmp_path,
):
    from services.payroll_batch_service import run_due_payroll_batch

    repo = PayrollRepository(tmp_path / "payroll.sqlite3")

    repo.save_employee(
        Employee(
            employee_id="E1",
            name="月末自動計算テスト",
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

    results = run_due_payroll_batch(
        repo,
        date(2026, 10, 1),
    )

    assert results is not None
    assert len(results) == 1

    saved = repo.payroll_result("E1", "2026-09")

    assert saved is not None
    assert saved.finalized is False
    assert repo.auto_payroll_processed_month() == "2026-09"


def test_due_payroll_batch_runs_only_once_for_same_month(tmp_path):
    from services.payroll_batch_service import run_due_payroll_batch

    repo = PayrollRepository(tmp_path / "payroll.sqlite3")

    repo.save_employee(
        Employee(
            employee_id="E1",
            name="二重実行防止テスト",
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

    first = run_due_payroll_batch(
        repo,
        date(2026, 10, 1),
    )

    assert first is not None
    assert repo.auto_payroll_processed_month() == "2026-09"

    saved_before = repo.payroll_result("E1", "2026-09")
    assert saved_before is not None

    second = run_due_payroll_batch(
        repo,
        date(2026, 10, 15),
    )

    assert second is None

    saved_after = repo.payroll_result("E1", "2026-09")
    assert saved_after is not None
    assert saved_after.payments == saved_before.payments
    assert saved_after.deductions == saved_before.deductions
    assert saved_after.finalized is False
