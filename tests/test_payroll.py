import sys
from pathlib import Path
from datetime import date
from decimal import Decimal
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.allowance import Allowance
from models.employee import Employee
from models.employment import EmploymentTerms
from models.transportation import Transportation
from models.work_record import WorkRecord
from services.payroll_service import calculate_payroll

def employee():
    return Employee("E1", "テスト", "パート", date(2026, 1, 1), "時給", Decimal("1200"), weekly_hours=Decimal("20"), workplace_size=20)

def test_fixed_overtime_transport_and_allowance():
    records = [WorkRecord("E1", date(2026, 8, 3), 9*60, 19*60, break_total_minutes=60)]
    result = calculate_payroll(employee(), EmploymentTerms("E1", overtime_method="固定残業代方式", fixed_overtime_amount=Decimal("30000"), fixed_overtime_minutes=60), records, [Allowance("スキル手当", Decimal("5000"))], Transportation("日額", Decimal("600"), 20), [], "2026-08")
    assert result.payments["固定残業代"] == 30000
    assert result.payments["交通費"] == 12000
    assert result.payments["スキル手当"] == 5000

def test_fixed_overtime_excess():
    records = [WorkRecord("E1", date(2026, 8, 3), 9*60, 21*60, break_total_minutes=60)]
    result = calculate_payroll(employee(), EmploymentTerms("E1", overtime_method="固定残業代方式", fixed_overtime_amount=Decimal("30000"), fixed_overtime_minutes=60), records, [], Transportation(), [], "2026-08")
    assert result.payments["固定残業超過分"] > 0


def test_payroll_uses_2026_official_monthly_income_tax_table():
    emp = Employee(
        employee_id="E-TAX",
        name="所得税テスト",
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

    result = calculate_payroll(
        emp,
        EmploymentTerms(
            "E-TAX",
            monthly_hourly_divisor=Decimal("160"),
        ),
        [],
        [],
        Transportation(),
        [],
        "2026-08",
    )

    # 社会保険料等控除後 170,850円
    # 令和8年分月額表 169,000円以上171,000円未満・甲欄0人
    assert result.deductions["所得税"] == Decimal("3270")
    assert not result.blocking_issues
