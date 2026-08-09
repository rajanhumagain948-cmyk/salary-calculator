"""Minute-by-minute classifier keeps cross-midnight and overlapping premiums exact."""
from __future__ import annotations
from models.payroll import TimeClassification
from models.work_record import WorkRecord

def classify_record(record: WorkRecord, standard_daily_minutes: int) -> TimeClassification:
    break_minutes: set[int] = set()
    for item in record.breaks:
        end = item.end_minute + (1440 if item.end_minute <= item.start_minute else 0)
        break_minutes.update(range(item.start_minute, end))
    if not record.breaks:
        # When only a total is entered, allocate it at the end; classification stays conservative.
        end = record.start_minute + record.span_minutes
        break_minutes.update(range(end - record.break_total_minutes, end))
    result = TimeClassification()
    worked_today = 0
    end = record.start_minute + record.span_minutes
    for absolute_minute in range(record.start_minute, end):
        if absolute_minute in break_minutes:
            continue
        clock = absolute_minute % 1440
        night = clock >= 1320 or clock < 300
        if record.is_holiday:
            result.holiday_minutes += 1
            if night:
                result.holiday_night_minutes += 1
        elif worked_today < standard_daily_minutes:
            result.regular_minutes += 1
            if night:
                result.night_minutes += 1
                result.regular_night_minutes += 1
        else:
            result.overtime_minutes += 1
            if night:
                result.overtime_night_minutes += 1
        worked_today += 1
    return result

def combine(items: list[TimeClassification]) -> TimeClassification:
    result = TimeClassification()
    for item in items:
        for name in result.__dataclass_fields__:
            setattr(result, name, getattr(result, name) + getattr(item, name))
    return result

def classify_records(records: list[WorkRecord], standard_daily_minutes: int,
                     standard_weekly_minutes: int) -> TimeClassification:
    """Apply daily then weekly statutory thresholds without rounding minutes."""
    indexed = [(record, classify_record(record, standard_daily_minutes)) for record in sorted(records, key=lambda r: (r.work_date, r.start_minute))]
    weekly: dict[tuple[int, int], list[TimeClassification]] = {}
    for record, item in indexed:
        if not record.is_holiday:
            weekly.setdefault(record.work_date.isocalendar()[:2], []).append(item)
    for items in weekly.values():
        excess = max(0, sum(item.regular_minutes for item in items) - standard_weekly_minutes)
        for item in reversed(items):
            if not excess:
                break
            move_night = min(excess, item.regular_night_minutes)
            item.regular_night_minutes -= move_night
            item.night_minutes -= move_night
            item.overtime_night_minutes += move_night
            item.regular_minutes -= move_night
            item.overtime_minutes += move_night
            excess -= move_night
            move_day = min(excess, item.regular_minutes)
            item.regular_minutes -= move_day
            item.overtime_minutes += move_day
            excess -= move_day
    result = combine([item for _, item in indexed])
    # Legal monthly threshold is evaluated after daily/weekly overtime classification.
    result.overtime_over_60_minutes = max(0, result.overtime_minutes - 3600)
    return result
