from __future__ import annotations

from datetime import date
from typing import Any

from models.employment import EmploymentTerms
from models.shifts import Shift
from models.work_record import WorkRecord
from services.attendance_service import attendance_days
from services.overtime_service import classify_records


def build_overtime_forecast(
    *,
    records: list[WorkRecord],
    terms: EmploymentTerms,
    as_of: date,
    shifts: list[Shift] | None = None,
) -> dict[str, Any]:
    actual_records = [
        record
        for record in records
        if record.work_date <= as_of
    ]
    classification = classify_records(
        actual_records,
        terms.standard_daily_minutes,
        terms.standard_weekly_minutes,
    )

    worked_days = attendance_days(actual_records)
    future_confirmed_shift_days = sum(
        1
        for shift in (shifts or [])
        if shift.confirmed and shift.shift_date > as_of
    )

    average_overtime_minutes = (
        classification.overtime_minutes / worked_days
        if worked_days
        else 0
    )
    forecast_overtime_minutes = round(
        classification.overtime_minutes
        + average_overtime_minutes * future_confirmed_shift_days
    )

    return {
        "actual_overtime_minutes": classification.overtime_minutes,
        "future_confirmed_shift_days": future_confirmed_shift_days,
        "forecast_overtime_minutes": forecast_overtime_minutes,
    }
