from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def build_ai_monthly_summary(
    *,
    year_month: str,
    employee_count: int,
    payrolls: Iterable[Any],
    leave_requests: Iterable[Any],
) -> dict[str, int | str]:
    payrolls = list(payrolls)
    leave_requests = list(leave_requests)

    return {
        "year_month": year_month,
        "employee_count": employee_count,
        "calculated_payroll_count": len(payrolls),
        "finalized_payroll_count": sum(
            1 for item in payrolls if item.finalized
        ),
        "blocked_payroll_count": sum(
            1 for item in payrolls if item.blocking_issues
        ),
        "pending_leave_count": sum(
            1
            for item in leave_requests
            if item.status == "申請中"
            and item.leave_date.strftime("%Y-%m") == year_month
        ),
    }
