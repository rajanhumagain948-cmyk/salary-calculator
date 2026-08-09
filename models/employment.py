"""Employment terms, deliberately separate from personnel master data."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

@dataclass(slots=True)
class EmploymentTerms:
    employee_id: str
    standard_daily_minutes: int = 480
    standard_weekly_minutes: int = 2400
    monthly_hourly_divisor: Decimal = Decimal("0")
    overtime_method: Literal["実残業時間方式", "固定残業代方式"] = "実残業時間方式"
    fixed_overtime_amount: Decimal = Decimal("0")
    fixed_overtime_minutes: int = 0
    housing_company_burden: Decimal = Decimal("0")
    company_housing_employee_burden: Decimal = Decimal("0")
