from __future__ import annotations
from decimal import Decimal
from models.allowance import Allowance

def validate_allowances(items: list[Allowance]) -> list[str]:
    warnings: list[str] = []
    for item in items:
        if item.amount < Decimal("0"):
            raise ValueError(f"{item.name}は0円以上で入力してください。")
        if item.amount == 0:
            warnings.append(f"{item.name}が0円です。")
    return warnings
