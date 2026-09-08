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


def standard_entitlement_days(
    service_months: int,
) -> Decimal:
    """継続勤務月数から通常の年次有給休暇の法定付与日数を返す。"""
    if service_months < 6:
        return Decimal("0")
    if service_months < 18:
        return Decimal("10")
    if service_months < 30:
        return Decimal("11")
    if service_months < 42:
        return Decimal("12")
    if service_months < 54:
        return Decimal("14")
    if service_months < 66:
        return Decimal("16")
    if service_months < 78:
        return Decimal("18")

    return Decimal("20")


def proportional_entitlement_days(
    weekly_days: int,
    service_months: int,
) -> Decimal:
    """週所定労働日数1〜4日の短時間労働者向け比例付与日数。"""
    if weekly_days not in (1, 2, 3, 4):
        raise ValueError("weekly_days must be between 1 and 4")

    if service_months < 6:
        return Decimal("0")

    schedules = {
        4: (7, 8, 9, 10, 12, 13, 15),
        3: (5, 6, 6, 8, 9, 10, 11),
        2: (3, 4, 4, 5, 6, 6, 7),
        1: (1, 2, 2, 2, 3, 3, 3),
    }

    thresholds = (6, 18, 30, 42, 54, 66, 78)

    index = 0
    for i, threshold in enumerate(thresholds):
        if service_months >= threshold:
            index = i

    return Decimal(schedules[weekly_days][index])


def employee_entitlement_days(
    employee,
    service_months: int,
) -> Decimal:
    """従業員の週所定労働日数・時間から法定付与日数表を選択する。"""
    weekly_days = employee.weekly_days
    weekly_hours = employee.weekly_hours

    if weekly_days >= 5 or weekly_hours >= Decimal("30"):
        return standard_entitlement_days(service_months)

    if weekly_days in (1, 2, 3, 4):
        return proportional_entitlement_days(
            weekly_days,
            service_months,
        )

    raise ValueError(
        "有給付与には週所定労働日数を1日以上設定してください。"
    )


def leave_grant_date(
    hire_date: date,
    grant_index: int,
) -> date:
    """初回6か月後、以後12か月ごとの法定付与予定日を返す。"""
    import calendar

    if grant_index < 0:
        raise ValueError("grant_index must be 0 or greater")

    months_to_add = 6 + (grant_index * 12)

    month_index = (
        hire_date.year * 12
        + (hire_date.month - 1)
        + months_to_add
    )

    year = month_index // 12
    month = month_index % 12 + 1

    last_day = calendar.monthrange(year, month)[1]
    day = min(hire_date.day, last_day)

    return date(year, month, day)


@dataclass(slots=True)
class LeaveGrantCandidate:
    grant_date: date
    days: Decimal
    service_months: int


def due_leave_grant(
    repo: PayrollRepository,
    employee,
    as_of: date,
) -> LeaveGrantCandidate | None:
    """到来済みで、まだ登録されていない最も古い付与候補を返す。"""
    existing_dates = {
        grant.grant_date
        for grant in repo.leave_grants(employee.employee_id)
    }

    grant_index = 0

    while True:
        scheduled_date = leave_grant_date(
            employee.hire_date,
            grant_index,
        )

        if scheduled_date > as_of:
            return None

        if scheduled_date not in existing_dates:
            service_months = 6 + grant_index * 12

            return LeaveGrantCandidate(
                grant_date=scheduled_date,
                days=employee_entitlement_days(
                    employee,
                    service_months,
                ),
                service_months=service_months,
            )

        grant_index += 1


def leave_grant_expiry_date(
    grant_date: date,
) -> date:
    """付与された年次有給休暇を日単位で管理するための最終有効日を返す。"""
    from datetime import timedelta

    try:
        two_years_later = grant_date.replace(
            year=grant_date.year + 2,
        )
    except ValueError:
        # 2月29日 → 2年後が平年の場合は2月28日
        two_years_later = grant_date.replace(
            year=grant_date.year + 2,
            day=28,
        )

    return two_years_later - timedelta(days=1)
