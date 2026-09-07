"""Paid annual leave grant."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(slots=True)
class LeaveGrant:
    employee_id: str
    grant_date: date
    granted_days: Decimal
    expires_on: date
    grant_id: int | None = None
