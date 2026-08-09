import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.time_service import format_minutes, parse_date, parse_time

def test_parse_compact_date_and_time():
    assert str(parse_date("20260807")) == "2026-08-07"
    assert parse_time("09:37") == 577
    assert format_minutes(517) == "8時間37分"
