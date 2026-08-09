from __future__ import annotations
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from models.allowance import Allowance
from models.deduction import OtherDeduction
from models.employee import Employee
from models.employment import EmploymentTerms
from models.payroll import PayrollResult
from models.transportation import Transportation
from models.work_record import WorkRecord
from services.allowance_service import validate_allowances
from services.attendance_service import validate_work_record
from services.insurance_service import calculate_insurance
from services.overtime_service import classify_records
from services.rule_service import load_rule
from services.tax_service import calculate_income_tax

def yen(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

def _money_for_minutes(rate: Decimal, minutes: int, premium: Decimal) -> Decimal:
    return yen(rate * Decimal(minutes) / Decimal(60) * premium)

def calculate_payroll(employee: Employee, terms: EmploymentTerms, records: list[WorkRecord],
                      allowances: list[Allowance], transport: Transportation,
                      other_deductions: list[OtherDeduction], year_month: str) -> PayrollResult:
    if employee.hourly_rate < 0 or employee.monthly_salary < 0:
        raise ValueError("時給・月給は0円以上で入力してください。")
    if employee.resident_tax_monthly < 0:
        raise ValueError("住民税は0円以上で入力してください。")
    year = int(year_month[:4])
    labor = load_rule(year, "labor")
    insurance_rules = load_rule(year, "insurance")
    warnings = [warning for record in records for warning in validate_work_record(record)]
    warnings.extend(validate_allowances(allowances))
    classes = classify_records(records, terms.standard_daily_minutes, terms.standard_weekly_minutes)
    result = PayrollResult(employee.employee_id, year_month, classes, warnings=warnings)
    if terms.overtime_method == "固定残業代方式":
        if terms.fixed_overtime_amount <= 0 or terms.fixed_overtime_minutes <= 0:
            result.blocking_issues.append("固定残業代方式では、固定残業代と固定残業時間の両方を0より大きく設定してください。")
    rate = employee.hourly_rate
    if employee.pay_type == "時給":
        result.payments["基本給"] = _money_for_minutes(rate, classes.regular_minutes, Decimal("1"))
    else:
        result.payments["基本給"] = yen(employee.monthly_salary)
        if terms.monthly_hourly_divisor <= 0:
            result.blocking_issues.append("月給者の時間単価の基礎となる月平均所定労働時間を設定してください。")
        else:
            rate = employee.monthly_salary / terms.monthly_hourly_divisor
    ot_premium = Decimal(str(labor["premiums"]["overtime"]))
    night_extra = Decimal(str(labor["premiums"]["night_extra"]))
    holiday_premium = Decimal(str(labor["premiums"]["holiday"]))
    over_60_extra = Decimal(str(labor["premiums"].get("overtime_over_60_extra", 0)))
    normal_night = classes.regular_night_minutes
    overtime_total = classes.overtime_minutes
    overtime_night = classes.overtime_night_minutes
    if terms.overtime_method == "固定残業代方式":
        result.payments["固定残業代"] = yen(terms.fixed_overtime_amount)
        total = overtime_total
        excess = max(0, total - terms.fixed_overtime_minutes)
        # Fixed amount is assumed to cover ordinary overtime only; night premium is always added.
        fixed_remaining_after_day = max(0, terms.fixed_overtime_minutes - (overtime_total - overtime_night))
        covered_night = min(overtime_night, fixed_remaining_after_day)
        excess_night = overtime_night - covered_night
        excess_day = max(0, excess - excess_night)
        if excess_day:
            result.payments["固定残業超過分"] = _money_for_minutes(rate, excess_day, ot_premium)
        if covered_night:
            result.payments["固定残業内深夜加算"] = _money_for_minutes(rate, covered_night, night_extra)
        if excess_night:
            result.payments["固定残業超過深夜分"] = _money_for_minutes(rate, excess_night, ot_premium + night_extra)
    else:
        result.payments["時間外手当"] = _money_for_minutes(rate, overtime_total - overtime_night, ot_premium)
        result.payments["時間外＋深夜手当"] = _money_for_minutes(rate, overtime_night, ot_premium + night_extra)
    result.payments["深夜手当"] = _money_for_minutes(rate, normal_night, night_extra)
    result.payments["休日手当"] = _money_for_minutes(rate, classes.holiday_minutes, holiday_premium)
    result.payments["休日＋深夜手当"] = _money_for_minutes(rate, classes.holiday_night_minutes, night_extra)
    if classes.overtime_over_60_minutes:
        result.payments["月60時間超加算"] = _money_for_minutes(rate, classes.overtime_over_60_minutes, over_60_extra)
    for allowance in allowances:
        result.payments[allowance.name] = result.payments.get(allowance.name, Decimal("0")) + yen(allowance.amount)
    result.payments["交通費"] = yen(transport.amount)
    standard = employee.standard_monthly_remuneration
    if standard <= 0:
        standard = result.gross_pay
        result.warnings.append("標準報酬月額が未登録のため、今月の総支給額を暫定使用しています。")
    year_value, month_value = (int(part) for part in year_month.split("-"))
    ins = calculate_insurance(employee, standard, insurance_rules, date(year_value, month_value, 1))
    result.deductions.update({"健康保険": ins.health, "介護保険": ins.nursing, "厚生年金": ins.pension, "雇用保険": ins.employment})
    taxable = result.gross_pay - sum((ins.health, ins.nursing, ins.pension, ins.employment), Decimal("0"))
    if not transport.taxable:
        taxable -= transport.amount
    taxable -= sum((item.amount for item in allowances if not item.taxable), Decimal("0"))
    try:
        table = Path(__file__).resolve().parent.parent / "rules" / str(year) / "monthly_tax_table.csv"
        result.deductions["所得税"] = calculate_income_tax(taxable, employee.dependents, employee.tax_category, table)
    except (FileNotFoundError, ValueError) as error:
        result.deductions["所得税"] = Decimal("0")
        result.warnings.append(f"所得税は未計算: {error}")
        result.blocking_issues.append("国税庁の月額表CSVを登録し、所得税を計算してください。")
    if employee.resident_tax_method == "特別徴収":
        result.deductions["住民税"] = yen(employee.resident_tax_monthly)
    for item in other_deductions:
        if item.amount < 0:
            raise ValueError(f"{item.name}は0円以上で入力してください。")
        result.deductions[item.name] = result.deductions.get(item.name, Decimal("0")) + yen(item.amount)
    return result
