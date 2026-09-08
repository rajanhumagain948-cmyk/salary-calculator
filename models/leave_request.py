"""Paid leave request model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal


LeaveStatus = Literal["申請中", "承認", "却下"]
LeaveUnit = Literal["全日", "半日", "時間"]
HalfDayPeriod = Literal["午前", "午後"]


@dataclass(slots=True)
class LeaveRequest:
    employee_id: str
    leave_date: date
    reason: str = ""
    status: LeaveStatus = "申請中"
    leave_unit: LeaveUnit = "全日"
    half_day_period: HalfDayPeriod | None = None
    request_id: int | None = None
    created_at: datetime | None = None