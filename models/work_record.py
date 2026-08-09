from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from .break_record import BreakRecord

@dataclass(slots=True)
class WorkRecord:
    employee_id: str
    work_date: date
    start_minute: int
    end_minute: int
    is_holiday: bool = False
    break_total_minutes: int = 0
    breaks: list[BreakRecord] = field(default_factory=list)
    record_id: int | None = None

    @property
    def span_minutes(self) -> int:
        end = self.end_minute + (1440 if self.end_minute <= self.start_minute else 0)
        return end - self.start_minute

    @property
    def actual_break_minutes(self) -> int:
        return sum(item.minutes for item in self.breaks) if self.breaks else self.break_total_minutes
