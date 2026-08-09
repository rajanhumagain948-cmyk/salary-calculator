from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

@dataclass(slots=True)
class Allowance:
    name: str
    amount: Decimal
    taxable: bool = True
