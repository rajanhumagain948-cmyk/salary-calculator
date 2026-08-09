from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

@dataclass(slots=True)
class Transportation:
    method: Literal["なし", "月額固定", "日額", "実費"] = "なし"
    unit_amount: Decimal = Decimal("0")
    attendance_days: int = 0
    taxable: bool = False

    @property
    def amount(self) -> Decimal:
        if self.method == "日額":
            return self.unit_amount * self.attendance_days
        return self.unit_amount if self.method != "なし" else Decimal("0")
