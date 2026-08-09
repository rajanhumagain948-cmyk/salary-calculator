"""Source-tax calculation driven by an imported official monthly table, not a hard-coded rate."""
from __future__ import annotations
from decimal import Decimal
from pathlib import Path
import csv

def calculate_income_tax(taxable_after_social: Decimal, dependents: int, category: str, table_path: Path) -> Decimal:
    """Look up the 2026 NTA monthly table exported as CSV.

    CSV columns: lower,upper,category,dependents,tax.  This intentionally has no
    fallback percentage: the official annual table must be imported before use.
    """
    if not table_path.exists():
        raise FileNotFoundError("国税庁の源泉徴収税額表CSVを rules/2026 に取り込んでください。")
    amount = int(taxable_after_social)
    with table_path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if (row["category"] == category and int(row["dependents"]) == dependents
                    and int(row["lower"]) <= amount < int(row["upper"])):
                return Decimal(row["tax"])
    raise ValueError("所得税表に該当する行がありません。")
