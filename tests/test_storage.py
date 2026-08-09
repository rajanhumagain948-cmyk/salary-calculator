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
