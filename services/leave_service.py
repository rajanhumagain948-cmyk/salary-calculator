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
    available_days: Decimal = Decimal("0")


def leave_request_days(request) -> Decimal:
    """有給申請1件が消化する日数を返す。"""
    if request.leave_unit == "全日":
        return Decimal("1")

    if request.leave_unit == "半日":
        return Decimal("0.5")

    raise ValueError(
        "時間単位有給の日数換算設定が未登録です。"
    )


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
            leave_request_days(request)
            for request in requests
            if request.status == "承認"
            and request.leave_date <= as_of
        ),
        Decimal("0"),
    )

    pending_days = sum(
        (
            leave_request_days(request)
            for request in requests
            if request.status == "申請中"
            and request.leave_date <= as_of
        ),
        Decimal("0"),
    )

    remaining_days = max(
        Decimal("0"),
        granted_days - used_days,
    )

    available_days = max(
        Decimal("0"),
        remaining_days - pending_days,
    )

    return LeaveBalance(
        granted_days=granted_days,
        used_days=used_days,
        pending_days=pending_days,
        remaining_days=remaining_days,
        available_days=available_days,
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


def has_overlapping_leave_request(
    requests,
    leave_date: date,
    leave_unit: str,
    half_day_period: str | None = None,
) -> bool:
    """申請中・承認済みの有給と取得範囲が重複するか判定する。"""
    for existing in requests:
        if existing.status == "却下":
            continue

        if existing.leave_date != leave_date:
            continue

        if existing.leave_unit == "全日" or leave_unit == "全日":
            return True

        if (
            existing.leave_unit == "半日"
            and leave_unit == "半日"
            and existing.half_day_period == half_day_period
        ):
            return True

    return False


def next_leave_grant(
    employee,
    as_of: date,
) -> LeaveGrantCandidate:
    """基準日時点の次回法定付与予定を返す。"""
    grant_index = 0

    while True:
        scheduled_date = leave_grant_date(
            employee.hire_date,
            grant_index,
        )

        if scheduled_date >= as_of:
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


def hourly_leave_hours_per_day(
    standard_daily_minutes: int,
) -> int:
    """時間単位年休における1日相当の時間数を返す。"""
    if standard_daily_minutes <= 0:
        raise ValueError(
            "1日の所定労働時間を0分より大きく設定してください。"
        )

    hours, remainder = divmod(
        standard_daily_minutes,
        60,
    )

    return hours + (1 if remainder else 0)


def hourly_leave_annual_limit_hours(
    standard_daily_minutes: int,
) -> int:
    """時間単位年休の年間上限5日分を時間数で返す。"""
    return hourly_leave_hours_per_day(
        standard_daily_minutes
    ) * 5


def hourly_leave_duration_hours(
    start_minute: int,
    end_minute: int,
    *,
    unit_hours: int,
) -> int:
    """時間単位年休の時間帯を検証し、取得時間数を返す。"""
    if unit_hours <= 0:
        raise ValueError("取得単位は1時間以上で設定してください。")

    if not (0 <= start_minute < 24 * 60):
        raise ValueError("開始時刻が不正です。")

    if not (0 < end_minute <= 24 * 60):
        raise ValueError("終了時刻が不正です。")

    if end_minute <= start_minute:
        raise ValueError("終了時刻は開始時刻より後にしてください。")

    duration_minutes = end_minute - start_minute

    # 時間単位年休なので分単位の端数は許可しない。
    if duration_minutes % 60 != 0:
        raise ValueError("時間単位年休は1時間単位で指定してください。")

    duration_hours = duration_minutes // 60

    if duration_hours % unit_hours != 0:
        raise ValueError(
            f"時間単位年休は{unit_hours}時間単位で指定してください。"
        )

    return duration_hours


def validate_hourly_leave_request(
    *,
    start_minute: int,
    end_minute: int,
    unit_hours: int,
    standard_daily_minutes: int,
) -> int:
    """時間単位年休1回分を検証し、取得時間数を返す。"""
    duration_hours = hourly_leave_duration_hours(
        start_minute,
        end_minute,
        unit_hours=unit_hours,
    )

    hours_per_day = hourly_leave_hours_per_day(
        standard_daily_minutes
    )

    if duration_hours > hours_per_day:
        raise ValueError(
            "1回の時間単位年休が1日相当時間数を超えています。"
        )

    return duration_hours


def hourly_leave_period(
    as_of: date,
    *,
    start_month: int,
    start_day: int,
) -> tuple[date, date]:
    """時間単位年休の年度開始日・終了日を返す。"""
    from datetime import timedelta

    if not 1 <= start_month <= 12:
        raise ValueError("年度開始月が不正です。")

    try:
        this_start = date(as_of.year, start_month, start_day)
    except ValueError as error:
        raise ValueError("年度開始日が不正です。") from error

    if as_of < this_start:
        start = date(as_of.year - 1, start_month, start_day)
    else:
        start = this_start

    try:
        next_start = date(start.year + 1, start_month, start_day)
    except ValueError as error:
        raise ValueError("年度開始日が不正です。") from error

    return start, next_start - timedelta(days=1)


def hourly_leave_used_hours(
    requests,
    *,
    period_start: date,
    period_end: date,
    include_pending: bool = True,
) -> int:
    total = 0

    statuses = {"承認"}
    if include_pending:
        statuses.add("申請中")

    for request in requests:
        if request.leave_unit != "時間":
            continue
        if request.status not in statuses:
            continue
        if not period_start <= request.leave_date <= period_end:
            continue
        if request.start_minute is None or request.end_minute is None:
            continue

        total += (request.end_minute - request.start_minute) // 60

    return total


def validate_hourly_annual_limit(
    requests,
    *,
    requested_hours: int,
    standard_daily_minutes: int,
    as_of: date,
    year_start_month: int,
    year_start_day: int,
) -> None:
    period_start, period_end = hourly_leave_period(
        as_of,
        start_month=year_start_month,
        start_day=year_start_day,
    )

    used = hourly_leave_used_hours(
        requests,
        period_start=period_start,
        period_end=period_end,
        include_pending=True,
    )

    limit = hourly_leave_annual_limit_hours(
        standard_daily_minutes
    )

    if used + requested_hours > limit:
        raise ValueError(
            "時間単位年休は1年間に5日相当を超えて取得できません。"
        )


def hourly_leave_days(
    hours: int,
    standard_daily_minutes: int,
) -> Decimal:
    hours_per_day = hourly_leave_hours_per_day(
        standard_daily_minutes
    )

    return Decimal(hours) / Decimal(hours_per_day)
