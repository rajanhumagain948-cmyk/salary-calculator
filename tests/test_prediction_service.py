from datetime import date

from models.employment import EmploymentTerms
from models.work_record import WorkRecord
from services.prediction_service import build_overtime_forecast


def test_overtime_forecast_uses_existing_overtime_classification():
    terms = EmploymentTerms(
        "E001",
        standard_daily_minutes=480,
        standard_weekly_minutes=2400,
    )
    records = [
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=19 * 60,
            break_total_minutes=60,
        )
    ]

    forecast = build_overtime_forecast(
        records=records,
        terms=terms,
        as_of=date(2026, 9, 1),
    )

    assert forecast["actual_overtime_minutes"] == 60
