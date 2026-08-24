"""Paid leave request model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal


LeaveStatus = Literal["申請中", "承認", "却下"]


@dataclass(slots=True)
class LeaveRequest:
    employee_id: str
    leave_date: date
    reason: str = ""
    status: LeaveStatus = "申請中"
    request_id: int | None = None
    created_at: datetime | None = None