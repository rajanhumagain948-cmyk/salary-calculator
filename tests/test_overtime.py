import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.break_record import BreakRecord
from models.work_record import WorkRecord
from services.overtime_service import classify_record

def test_overtime_night_holiday_and_multiple_breaks():
    record = WorkRecord("1", date(2026, 8, 1), 9*60, 23*60, False, breaks=[BreakRecord(12*60, 13*60), BreakRecord(18*60, 18*60+30)])
    result = classify_record(record, 480)
    assert result.regular_minutes == 480 and result.overtime_minutes == 270
    assert result.overtime_night_minutes == 60
    holiday = classify_record(WorkRecord("1", date.today(), 22*60, 5*60, True, 0), 480)
    assert holiday.holiday_minutes == 420 and holiday.holiday_night_minutes == 420
