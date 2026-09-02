"""Shift (schedule) record."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class Shift:
    employee_id: str
    shift_date: date
    start_minute: int
    end_minute: int
    break_minutes: int = 0
    note: str = ""
    confirmed: bool = False
    shift_id: int | None = None