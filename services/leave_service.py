"""Paid annual leave calculations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from services.storage_service import PayrollRepository


@dataclass(slots=True)
class LeaveBalance:
    granted_days: Decimal = Decimal("0")
    used_days: Decimal = Decimal("0")
    pending_days: Decimal = Decimal("0")
    remaining_days: Decimal = Decimal("0")


def calculate_leave_balance(
    repo: PayrollRepository,
    employee_id: str,
    as_of: date,
) -> LeaveBalance:
    grants = repo.leave_grants(employee_id)

    granted_days = sum(
        (
            grant.granted_days
            for grant in grants
            if grant.grant_date <= as_of <= grant.expires_on
        ),
        Decimal("0"),
    )

    requests = repo.leave_requests(employee_id)

    used_days = sum(
        (
            Decimal("1")
            for request in requests
            if request.status == "承認"
            and request.leave_date <= as_of
        ),
        Decimal("0"),
    )

    pending_days = sum(
        (
            Decimal("1")
            for request in requests
            if request.status == "申請中"
            and request.leave_date <= as_of
        ),
        Decimal("0"),
    )

    return LeaveBalance(
        granted_days=granted_days,
        used_days=used_days,
        pending_days=pending_days,
        remaining_days=granted_days - used_days,
    )
