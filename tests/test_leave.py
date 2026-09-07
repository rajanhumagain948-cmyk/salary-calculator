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
