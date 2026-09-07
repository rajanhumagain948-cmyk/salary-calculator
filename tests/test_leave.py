from datetime import date
from decimal import Decimal

from models.leave_grant import LeaveGrant
from services.storage_service import PayrollRepository


def test_leave_grant_is_saved_and_loaded(tmp_path):
    repo = PayrollRepository(tmp_path / "payroll.sqlite3")

    grant = repo.save_leave_grant(
        LeaveGrant(
            employee_id="E1",
            grant_date=date(2026, 7, 1),
            granted_days=Decimal("10"),
            expires_on=date(2028, 6, 30),
        )
    )

    assert grant.grant_id is not None

    grants = repo.leave_grants("E1")

    assert len(grants) == 1
    assert grants[0].employee_id == "E1"
    assert grants[0].grant_date == date(2026, 7, 1)
    assert grants[0].granted_days == Decimal("10")
    assert grants[0].expires_on == date(2028, 6, 30)


def test_leave_balance_subtracts_only_approved_requests(tmp_path):
    from models.leave_request import LeaveRequest
    from services.leave_service import calculate_leave_balance

    repo = PayrollRepository(tmp_path / "payroll.sqlite3")

    repo.save_leave_grant(
        LeaveGrant(
            employee_id="E1",
            grant_date=date(2026, 7, 1),
            granted_days=Decimal("10"),
            expires_on=date(2028, 6, 30),
        )
    )

    for leave_date, status in (
        (date(2026, 9, 10), "承認"),
        (date(2026, 9, 11), "承認"),
        (date(2026, 9, 12), "申請中"),
    ):
        repo.save_leave_request(
            LeaveRequest(
                employee_id="E1",
                leave_date=leave_date,
                status=status,
            )
        )

    balance = calculate_leave_balance(
        repo,
        "E1",
        date(2026, 9, 30),
    )

    assert balance.granted_days == Decimal("10")
    assert balance.used_days == Decimal("2")
    assert balance.pending_days == Decimal("1")
    assert balance.remaining_days == Decimal("8")


def test_expired_leave_grant_is_not_in_current_balance(tmp_path):
    from services.leave_service import calculate_leave_balance

    repo = PayrollRepository(tmp_path / "payroll.sqlite3")

    repo.save_leave_grant(
        LeaveGrant(
            employee_id="E1",
            grant_date=date(2024, 7, 1),
            granted_days=Decimal("10"),
            expires_on=date(2026, 6, 30),
        )
    )

    repo.save_leave_grant(
        LeaveGrant(
            employee_id="E1",
            grant_date=date(2026, 7, 1),
            granted_days=Decimal("11"),
            expires_on=date(2028, 6, 30),
        )
    )

    balance = calculate_leave_balance(
        repo,
        "E1",
        date(2026, 9, 30),
    )

    assert balance.granted_days == Decimal("11")
    assert balance.remaining_days == Decimal("11")


def test_standard_paid_leave_entitlement_days():
    from services.leave_service import standard_entitlement_days

    assert standard_entitlement_days(6) == Decimal("10")
    assert standard_entitlement_days(18) == Decimal("11")
    assert standard_entitlement_days(30) == Decimal("12")
    assert standard_entitlement_days(42) == Decimal("14")
    assert standard_entitlement_days(54) == Decimal("16")
    assert standard_entitlement_days(66) == Decimal("18")
    assert standard_entitlement_days(78) == Decimal("20")
    assert standard_entitlement_days(120) == Decimal("20")


def test_proportional_paid_leave_entitlement_days():
    from services.leave_service import proportional_entitlement_days

    # 継続勤務6か月
    assert proportional_entitlement_days(4, 6) == Decimal("7")
    assert proportional_entitlement_days(3, 6) == Decimal("5")
    assert proportional_entitlement_days(2, 6) == Decimal("3")
    assert proportional_entitlement_days(1, 6) == Decimal("1")

    # 継続勤務1年6か月
    assert proportional_entitlement_days(4, 18) == Decimal("8")
    assert proportional_entitlement_days(3, 18) == Decimal("6")
    assert proportional_entitlement_days(2, 18) == Decimal("4")
    assert proportional_entitlement_days(1, 18) == Decimal("2")

    # 6年6か月以上
    assert proportional_entitlement_days(4, 78) == Decimal("15")
    assert proportional_entitlement_days(3, 78) == Decimal("11")
    assert proportional_entitlement_days(2, 78) == Decimal("7")
    assert proportional_entitlement_days(1, 78) == Decimal("3")


def test_employee_paid_leave_entitlement_selects_correct_schedule():
    from models.employee import Employee
    from services.leave_service import employee_entitlement_days

    base = dict(
        employee_id="E1",
        name="有給テスト",
        employment_type="パート",
        hire_date=date(2026, 1, 1),
        pay_type="時給",
        hourly_rate=Decimal("1200"),
    )

    # 週4日かつ30時間未満 → 比例付与
    proportional = Employee(
        **base,
        weekly_days=4,
        weekly_hours=Decimal("29"),
    )
    assert employee_entitlement_days(proportional, 6) == Decimal("7")

    # 週4日でも30時間以上 → 通常付与
    thirty_hours = Employee(
        **base,
        weekly_days=4,
        weekly_hours=Decimal("30"),
    )
    assert employee_entitlement_days(thirty_hours, 6) == Decimal("10")

    # 週5日 → 通常付与
    five_days = Employee(
        **base,
        weekly_days=5,
        weekly_hours=Decimal("20"),
    )
    assert employee_entitlement_days(five_days, 6) == Decimal("10")
