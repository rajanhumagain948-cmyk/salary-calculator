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


def test_overtime_forecast_projects_average_overtime_over_future_confirmed_shifts():
    from models.shifts import Shift

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
    shifts = [
        Shift(
            employee_id="E001",
            shift_date=date(2026, 9, 2),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_minutes=60,
            confirmed=True,
        ),
        Shift(
            employee_id="E001",
            shift_date=date(2026, 9, 3),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_minutes=60,
            confirmed=True,
        ),
    ]

    forecast = build_overtime_forecast(
        records=records,
        terms=terms,
        shifts=shifts,
        as_of=date(2026, 9, 1),
    )

    assert forecast["actual_overtime_minutes"] == 60
    assert forecast["future_confirmed_shift_days"] == 2
    assert forecast["forecast_overtime_minutes"] == 180


def test_overtime_forecast_ignores_unconfirmed_future_shifts():
    from models.shifts import Shift

    terms = EmploymentTerms("E001")
    records = [
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=19 * 60,
            break_total_minutes=60,
        )
    ]
    shifts = [
        Shift(
            employee_id="E001",
            shift_date=date(2026, 9, 2),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_minutes=60,
            confirmed=False,
        )
    ]

    forecast = build_overtime_forecast(
        records=records,
        terms=terms,
        shifts=shifts,
        as_of=date(2026, 9, 1),
    )

    assert forecast["future_confirmed_shift_days"] == 0
    assert forecast["forecast_overtime_minutes"] == 60


def test_overtime_forecast_ignores_work_records_after_as_of():
    terms = EmploymentTerms("E001")
    records = [
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=19 * 60,
            break_total_minutes=60,
        ),
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 20),
            start_minute=9 * 60,
            end_minute=21 * 60,
            break_total_minutes=60,
        ),
    ]

    forecast = build_overtime_forecast(
        records=records,
        terms=terms,
        as_of=date(2026, 9, 10),
    )

    assert forecast["actual_overtime_minutes"] == 60
    assert forecast["forecast_overtime_minutes"] == 60
