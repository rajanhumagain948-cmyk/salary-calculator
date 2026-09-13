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
    future_confirmed_shift_days = len(
        {
            shift.shift_date
            for shift in (shifts or [])
            if shift.confirmed and shift.shift_date > as_of
        }
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


def build_attendance_review(
    *,
    records: list[WorkRecord],
) -> dict[str, Any]:
    from services.attendance_service import validate_work_record

    warnings = []

    for record in records:
        messages = validate_work_record(record)
        if not messages:
            continue

        warnings.append(
            {
                "work_date": record.work_date.isoformat(),
                "messages": messages,
            }
        )

    return {
        "warning_count": len(warnings),
        "warnings": warnings,
    }


def build_payroll_estimate(
    *,
    employee,
    terms,
    records,
    allowances,
    transport,
    other_deductions,
    year_month: str,
    as_of: date | None = None,
) -> dict[str, Any]:
    from services.payroll_service import calculate_payroll

    estimate_records = (
        [
            record
            for record in records
            if record.work_date <= as_of
        ]
        if as_of is not None
        else records
    )

    result = calculate_payroll(
        employee=employee,
        terms=terms,
        records=estimate_records,
        allowances=allowances,
        transport=transport,
        other_deductions=other_deductions,
        year_month=year_month,
    )

    return {
        "reference_only": True,
        "used_for_payroll": False,
        "gross_pay": str(result.gross_pay),
    }
