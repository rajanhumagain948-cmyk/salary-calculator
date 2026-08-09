import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.allowance import Allowance
from models.employee import Employee
from models.employment import EmploymentTerms
from models.transportation import Transportation
from models.work_record import WorkRecord
from services.payroll_service import calculate_payroll
from services.storage_service import PayrollRepository


def _employee() -> Employee:
    return Employee("E", "テスト", "パート", date(2026, 1, 1), "時給", Decimal("1000"), weekly_hours=Decimal("20"), workplace_size=20)


def test_same_named_allowances_are_aggregated_and_non_taxable_excluded():
    result = calculate_payroll(
        _employee(), EmploymentTerms("E"),
        [WorkRecord("E", date(2026, 8, 1), 9 * 60, 18 * 60, break_total_minutes=60)],
        [Allowance("その他", Decimal("100")), Allowance("その他", Decimal("200"), False)],
        Transportation(), [], "2026-08",
    )
    assert result.payments["その他"] == 300


def test_weekly_overtime_and_holiday_night_do_not_double_pay():
    records = [WorkRecord("E", date(2026, 8, 3) + timedelta(days=i), 9 * 60, 19 * 60) for i in range(5)]
    weekly = calculate_payroll(_employee(), EmploymentTerms("E", standard_daily_minutes=600), records, [], Transportation(), [], "2026-08")
    assert weekly.classification.overtime_minutes == 600
    holiday = calculate_payroll(_employee(), EmploymentTerms("E"), [WorkRecord("E", date(2026, 8, 2), 22 * 60, 5 * 60, True)], [], Transportation(), [], "2026-08")
    assert holiday.payments["休日手当"] == 9450
    assert holiday.payments["休日＋深夜手当"] == 1750


def test_monthly_inputs_preserve_unlimited_allowances():
    with TemporaryDirectory() as folder:
        repo = PayrollRepository(Path(folder) / "payroll.sqlite3")
        allowances = [Allowance("その他", Decimal(index), index % 2 == 0) for index in range(1, 21)]
        repo.save_monthly_inputs("E", "2026-08", allowances, [], Transportation("日額", Decimal("600"), 20))
        saved, deductions, transport = repo.monthly_inputs("E", "2026-08")
        assert len(saved) == 20 and not deductions and transport.amount == 12000


def test_fixed_overtime_requires_amount_and_hours():
    result = calculate_payroll(
        _employee(), EmploymentTerms("E", overtime_method="固定残業代方式", fixed_overtime_amount=Decimal("30000")),
        [], [], Transportation(), [], "2026-08",
    )
    assert result.blocking_issues
