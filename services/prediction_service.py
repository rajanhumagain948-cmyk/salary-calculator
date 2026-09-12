from __future__ import annotations

from datetime import date
from typing import Any

from models.employment import EmploymentTerms
from models.work_record import WorkRecord
from services.overtime_service import classify_records


def build_overtime_forecast(
    *,
    records: list[WorkRecord],
    terms: EmploymentTerms,
    as_of: date,
) -> dict[str, Any]:
    classification = classify_records(
        records,
        terms.standard_daily_minutes,
        terms.standard_weekly_minutes,
    )

    return {
        "actual_overtime_minutes": classification.overtime_minutes,
    }
