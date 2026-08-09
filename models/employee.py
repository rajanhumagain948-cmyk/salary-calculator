"""Employee master data."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

EmploymentType = Literal["正社員", "契約社員", "パート", "アルバイト"]
PayType = Literal["時給", "月給"]
TaxCategory = Literal["甲", "乙"]

@dataclass(slots=True)
class Employee:
    employee_id: str
    name: str
    employment_type: EmploymentType
    hire_date: date
    pay_type: PayType
    hourly_rate: Decimal = Decimal("0")
    monthly_salary: Decimal = Decimal("0")
    weekly_hours: Decimal = Decimal("0")
    weekly_days: int = 0
    contract_months: int | None = None
    workplace_size: int = 0
    is_student: bool = False
    dependents: int = 0
    tax_category: TaxCategory = "甲"
    birth_date: date | None = None
    termination_date: date | None = None
    prefecture: str = "東京都"
    resident_tax_monthly: Decimal = Decimal("0")
    resident_tax_method: Literal["特別徴収", "普通徴収"] = "特別徴収"
    standard_monthly_remuneration: Decimal = Decimal("0")
