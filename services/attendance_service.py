from __future__ import annotations
from .time_service import minimum_break_minutes
from models.work_record import WorkRecord

def validate_work_record(record: WorkRecord) -> list[str]:
    if record.actual_break_minutes < 0 or record.actual_break_minutes > record.span_minutes:
        raise ValueError("休憩時間は勤務時間の範囲内で入力してください。")
    for item in record.breaks:
        if item.minutes <= 0:
            raise ValueError("休憩の開始・終了時刻を確認してください。")
    warnings: list[str] = []
    actual = record.span_minutes - record.actual_break_minutes
    required = minimum_break_minutes(actual)
    if record.actual_break_minutes < required:
        warnings.append(f"休憩が法定目安より{required - record.actual_break_minutes}分不足しています。")
    return warnings

def attendance_days(records: list[WorkRecord]) -> int:
    return sum(1 for record in records if record.span_minutes > record.actual_break_minutes)
