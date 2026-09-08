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


def test_paid_leave_grant_date_schedule_handles_month_end():
    from services.leave_service import leave_grant_date

    # 通常ケース
    assert leave_grant_date(date(2026, 1, 1), 0) == date(2026, 7, 1)
    assert leave_grant_date(date(2026, 1, 1), 1) == date(2027, 7, 1)

    # 月末入社でも存在しない日付にならない
    assert leave_grant_date(date(2026, 8, 31), 0) == date(2027, 2, 28)
    assert leave_grant_date(date(2027, 8, 31), 0) == date(2028, 2, 29)


def test_due_leave_grant_candidate_is_not_returned_twice(tmp_path):
    from models.employee import Employee
    from services.leave_service import due_leave_grant

    repo = PayrollRepository(tmp_path / "payroll.sqlite3")

    employee = Employee(
        employee_id="E1",
        name="付与候補テスト",
        employment_type="正社員",
        hire_date=date(2026, 3, 1),
        pay_type="月給",
        monthly_salary=Decimal("200000"),
        weekly_hours=Decimal("40"),
        weekly_days=5,
    )

    candidate = due_leave_grant(
        repo,
        employee,
        date(2026, 9, 7),
    )

    assert candidate is not None
    assert candidate.grant_date == date(2026, 9, 1)
    assert candidate.days == Decimal("10")
    assert candidate.service_months == 6

    repo.save_leave_grant(
        LeaveGrant(
            employee_id="E1",
            grant_date=candidate.grant_date,
            granted_days=candidate.days,
            expires_on=date(2028, 8, 31),
        )
    )

    assert due_leave_grant(
        repo,
        employee,
        date(2026, 9, 7),
    ) is None


def test_leave_grant_expiry_date():
    from services.leave_service import leave_grant_expiry_date

    assert leave_grant_expiry_date(
        date(2026, 9, 1)
    ) == date(2028, 8, 31)

    # うるう日の付与も扱える
    assert leave_grant_expiry_date(
        date(2028, 2, 29)
    ) == date(2030, 2, 27)


def test_half_day_leave_request_is_saved_and_loaded(tmp_path):
    from models.leave_request import LeaveRequest

    repo = PayrollRepository(tmp_path / "payroll.sqlite3")

    repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 15),
            reason="午前休",
            leave_unit="半日",
            half_day_period="午前",
        )
    )

    saved = repo.leave_requests("E1")

    assert len(saved) == 1
    assert saved[0].leave_unit == "半日"
    assert saved[0].half_day_period == "午前"


def test_half_day_leave_uses_half_a_day_from_balance(tmp_path):
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

    repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 15),
            status="承認",
            leave_unit="半日",
            half_day_period="午前",
        )
    )

    balance = calculate_leave_balance(
        repo,
        "E1",
        date(2026, 9, 30),
    )

    assert balance.used_days == Decimal("0.5")
    assert balance.remaining_days == Decimal("9.5")


def test_leave_balance_never_returns_negative_remaining_days(tmp_path):
    from models.leave_request import LeaveRequest
    from services.leave_service import calculate_leave_balance

    repo = PayrollRepository(tmp_path / "payroll.sqlite3")

    # 旧データなどで、付与がないのに承認済み申請が存在するケース。
    repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 8, 25),
            status="承認",
        )
    )

    balance = calculate_leave_balance(
        repo,
        "E1",
        date(2026, 9, 30),
    )

    assert balance.granted_days == Decimal("0")
    assert balance.used_days == Decimal("1")
    assert balance.remaining_days == Decimal("0")


def test_next_leave_grant_for_employee_before_first_grant():
    from models.employee import Employee
    from services.leave_service import next_leave_grant

    employee = Employee(
        employee_id="W250651",
        name="テスト",
        employment_type="正社員",
        hire_date=date(2026, 6, 1),
        pay_type="月給",
        monthly_salary=Decimal("200000"),
        weekly_hours=Decimal("40"),
        weekly_days=5,
    )

    candidate = next_leave_grant(
        employee,
        date(2026, 9, 8),
    )

    assert candidate.grant_date == date(2026, 12, 1)
    assert candidate.days == Decimal("10")
    assert candidate.service_months == 6


def test_leave_balance_reports_available_days_after_pending_requests(
    tmp_path,
):
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

    repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 10),
            status="承認",
        )
    )

    for day in (20, 21, 22):
        repo.save_leave_request(
            LeaveRequest(
                employee_id="E1",
                leave_date=date(2026, 9, day),
                status="申請中",
            )
        )

    balance = calculate_leave_balance(
        repo,
        "E1",
        date(2026, 9, 30),
    )

    assert balance.remaining_days == Decimal("9")
    assert balance.pending_days == Decimal("3")
    assert balance.available_days == Decimal("6")


def test_hourly_leave_hours_per_day_rounds_up_partial_hour():
    from services.leave_service import hourly_leave_hours_per_day

    assert hourly_leave_hours_per_day(480) == 8
    assert hourly_leave_hours_per_day(450) == 8
    assert hourly_leave_hours_per_day(420) == 7


def test_hourly_paid_leave_annual_limit_is_five_days():
    from services.leave_service import hourly_leave_annual_limit_hours

    # 1日8時間相当 → 年40時間
    assert hourly_leave_annual_limit_hours(480) == 40

    # 7時間30分は1日8時間相当 → 年40時間
    assert hourly_leave_annual_limit_hours(450) == 40

    # 1日7時間相当 → 年35時間
    assert hourly_leave_annual_limit_hours(420) == 35
