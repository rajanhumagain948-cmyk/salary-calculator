"""Application user account."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


UserRole = Literal["admin", "employee"]


@dataclass(slots=True)
class User:
    username: str
    password_hash: str
    role: UserRole
    employee_id: str | None = None
    active: bool = True