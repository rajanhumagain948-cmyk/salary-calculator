from __future__ import annotations
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from models.employee import Employee
from models.payroll import InsuranceResult

def yen(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

def eligible_for_social_insurance(employee: Employee, rules: dict) -> bool:
    condition = rules["social_eligibility"]
    regular_ratio = Decimal(str(condition["weekly_hours_ratio"]))
    regular_hours = Decimal(str(condition["regular_weekly_hours"]))
    short_worker = (employee.weekly_hours >= Decimal(str(condition["short_worker_weekly_hours"]))
                    and employee.workplace_size >= condition["minimum_workplace_size"]
                    and not employee.is_student)
    return employee.weekly_hours >= regular_hours * regular_ratio or short_worker

def eligible_for_employment(employee: Employee, rules: dict) -> bool:
    return (employee.weekly_hours >= Decimal(str(rules["employment_eligibility"]["weekly_hours"]))
            and (employee.contract_months is None or employee.contract_months >= rules["employment_eligibility"]["contract_months"]))

def calculate_insurance(employee: Employee, standard_monthly: Decimal, rules: dict,
                        as_of: date | None = None) -> InsuranceResult:
    social = eligible_for_social_insurance(employee, rules)
    employment = eligible_for_employment(employee, rules)
    result = InsuranceResult(health_enrolled=social, pension_enrolled=social, employment_enrolled=employment)
    if social:
        health_rate = Decimal(str(rules["health_rate_by_prefecture"].get(employee.prefecture, rules["health_rate_by_prefecture"]["東京都"])))
        result.health = yen(standard_monthly * health_rate / 2)
        target = as_of or date.today()
        age = None if employee.birth_date is None else target.year - employee.birth_date.year - ((target.month, target.day) < (employee.birth_date.month, employee.birth_date.day))
        if age is not None and rules["nursing_age_min"] <= age < rules["nursing_age_max"]:
            result.nursing = yen(standard_monthly * Decimal(str(rules["nursing_rate"])) / 2)
        result.pension = yen(standard_monthly * Decimal(str(rules["pension_rate"])) / 2)
    if employment:
        result.employment = yen(standard_monthly * Decimal(str(rules["employment_employee_rate"])))
    return result
