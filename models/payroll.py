from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal

@dataclass(slots=True)
class TimeClassification:
    regular_minutes: int = 0
    overtime_minutes: int = 0
    night_minutes: int = 0
    regular_night_minutes: int = 0
    holiday_minutes: int = 0
    overtime_night_minutes: int = 0
    holiday_night_minutes: int = 0
    overtime_over_60_minutes: int = 0

@dataclass(slots=True)
class InsuranceResult:
    health: Decimal = Decimal("0")
    nursing: Decimal = Decimal("0")
    pension: Decimal = Decimal("0")
    employment: Decimal = Decimal("0")
    health_enrolled: bool = False
    pension_enrolled: bool = False
    employment_enrolled: bool = False

@dataclass(slots=True)
class PayrollResult:
    employee_id: str
    year_month: str
    classification: TimeClassification
    payments: dict[str, Decimal] = field(default_factory=dict)
    deductions: dict[str, Decimal] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)
    finalized: bool = False
    company_name: str = ""

    @property
    def gross_pay(self) -> Decimal:
        return sum(self.payments.values(), Decimal("0"))
    @property
    def total_deductions(self) -> Decimal:
        return sum(self.deductions.values(), Decimal("0"))
    @property
    def net_pay(self) -> Decimal:
        return self.gross_pay - self.total_deductions
