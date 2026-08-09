import sys
from pathlib import Path
from datetime import date
from decimal import Decimal
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.employee import Employee
from models.employment import EmploymentTerms
from models.work_record import WorkRecord
from services.payroll_service import calculate_payroll

def test_resident_tax_special_and_ordinary():
    base = dict(employee_id="E", name="A", employment_type="パート", hire_date=date.today(), pay_type="時給", hourly_rate=Decimal("1000"), resident_tax_monthly=Decimal("5000"))
    special = Employee(**base, resident_tax_method="特別徴収")
    ordinary = Employee(**base, resident_tax_method="普通徴収")
    work = [WorkRecord("E", date(2026, 8, 1), 9*60, 18*60, break_total_minutes=60)]
    assert calculate_payroll(special, EmploymentTerms("E"), work, [], __import__('models.transportation', fromlist=['Transportation']).Transportation(), [], "2026-08").deductions["住民税"] == 5000
    assert "住民税" not in calculate_payroll(ordinary, EmploymentTerms("E"), work, [], __import__('models.transportation', fromlist=['Transportation']).Transportation(), [], "2026-08").deductions
