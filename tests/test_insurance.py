import sys
from pathlib import Path
from datetime import date
from decimal import Decimal
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.employee import Employee
from services.insurance_service import calculate_insurance
from services.rule_service import load_rule

def test_social_insurance_condition_based():
    rule = load_rule(2026, "insurance")
    covered = Employee("1", "A", "アルバイト", date.today(), "時給", weekly_hours=Decimal("30"))
    not_covered = Employee("2", "B", "正社員", date.today(), "月給", weekly_hours=Decimal("10"), workplace_size=1)
    assert calculate_insurance(covered, Decimal("200000"), rule).health_enrolled
    assert not calculate_insurance(not_covered, Decimal("200000"), rule).health_enrolled
