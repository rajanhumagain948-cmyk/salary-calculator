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
