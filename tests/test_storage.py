import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.employee import Employee
from services.storage_service import PayrollRepository


def test_legacy_string_number_values_are_normalized_on_read():
    with TemporaryDirectory() as folder:
        repo = PayrollRepository(Path(folder) / "payroll.sqlite3")
        repo.save_employee(Employee("E", "A", "正社員", date.today(), "月給", monthly_salary=Decimal("208000")))
        employee = repo.employees()[0]
        assert employee.standard_monthly_remuneration == Decimal("0")


def test_finalized_payroll_result_is_saved_as_snapshot():
    from models.payroll import PayrollResult, TimeClassification

    with TemporaryDirectory() as folder:
        repo = PayrollRepository(Path(folder) / "payroll.sqlite3")

        result = PayrollResult(
            employee_id="E1",
            year_month="2026-08",
            classification=TimeClassification(
                regular_minutes=9600,
                overtime_minutes=300,
            ),
            payments={
                "基本給": Decimal("200000"),
                "残業代": Decimal("10000"),
                "交通費": Decimal("12000"),
            },
            deductions={
                "健康保険": Decimal("9850"),
                "厚生年金": Decimal("18300"),
                "雇用保険": Decimal("1000"),
                "所得税": Decimal("3270"),
                "住民税": Decimal("5000"),
            },
            warnings=[],
            blocking_issues=[],
            finalized=True,
            company_name="テスト株式会社",
        )

        repo.save_payroll_result(result)

        # 保存後にメモリ上の元データを変更しても、
        # DBに保存した確定給与は変化しない。
        result.payments["基本給"] = Decimal("999999")
        result.deductions["所得税"] = Decimal("99999")

        saved = repo.payroll_result("E1", "2026-08")

        assert saved is not None
        assert saved.finalized is True
        assert saved.payments["基本給"] == Decimal("200000")
        assert saved.deductions["所得税"] == Decimal("3270")
        assert saved.gross_pay == Decimal("222000")
        assert saved.total_deductions == Decimal("37420")
        assert saved.net_pay == Decimal("184580")
