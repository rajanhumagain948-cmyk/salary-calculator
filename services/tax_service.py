"""Source-tax calculation driven by an imported official monthly table, not a hard-coded rate."""
from __future__ import annotations
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
import csv

# 国税庁「令和8年分 給与所得の源泉徴収税額表（月額表）」の
# 740,000円以上の甲欄基準税額（扶養親族等 0～7人）。
MONTHLY_DEPENDENT_EXCESS_DEDUCTION = Decimal("1610")
MONTHLY_OTSU_LOW_RATE = Decimal("0.03063")

# 国税庁「令和8年分 給与所得の源泉徴収税額表（月額表）」乙欄。
MONTHLY_OTSU_HIGH_BASE_740 = Decimal("259200")
MONTHLY_OTSU_HIGH_BASE_1710 = Decimal("655400")
MONTHLY_OTSU_RATE_740_TO_1710 = Decimal("0.4084")
MONTHLY_OTSU_RATE_OVER_1710 = Decimal("0.45945")

HIGH_INCOME_BASES = {
    740000: (71680, 65210, 58750, 52290, 45810, 39350, 32890, 26410),
    790000: (81890, 75420, 68960, 62500, 56020, 49560, 43100, 36620),
    960000: (121820, 115340, 108880, 102420, 95940, 89480, 83020, 76540),
    1710000: (374520, 368040, 361580, 355120, 348640, 342180, 335720, 329240),
    2130000: (549440, 542970, 536500, 530040, 523570, 517110, 510640, 504170),
    2170000: (571220, 564750, 558280, 551820, 545350, 538880, 532420, 525950),
    2210000: (593000, 586520, 580060, 573600, 567120, 560660, 554200, 547730),
    2250000: (614770, 608300, 601840, 595380, 588900, 582440, 575980, 569500),
    3500000: (1125270, 1118800, 1112340, 1105880, 1099400, 1092940, 1086480, 1080000),
}


# (下限, 上限, 加算率)
# 上限 None は上限なし。
HIGH_INCOME_RATES = (
    (740000, 790000, Decimal("0.2042")),
    (790000, 960000, Decimal("0.23483")),
    (960000, 1710000, Decimal("0.33693")),
    (1710000, 2130000, Decimal("0.4084")),
    (2130000, 2170000, Decimal("0.4084")),
    (2170000, 2210000, Decimal("0.4084")),
    (2210000, 2250000, Decimal("0.4084")),
    (2250000, 3500000, Decimal("0.4084")),
    (3500000, None, Decimal("0.45945")),
)




def _truncate_yen(value: Decimal) -> Decimal:
    """1円未満を切り捨てる。"""
    return value.quantize(Decimal("1"), rounding=ROUND_DOWN)



def _calculate_otsu_low_income(amount: int) -> Decimal:
    """令和8年分月額表・乙欄の105,000円未満を計算する。"""
    if amount < 0:
        raise ValueError("社会保険料等控除後の給与等の金額は0円以上で指定してください。")

    return _truncate_yen(
        Decimal(amount) * MONTHLY_OTSU_LOW_RATE
    )



def _calculate_high_income_otsu(amount: int) -> Decimal:
    """令和8年分月額表・乙欄の740,000円以上を計算する。"""
    if amount < 740000:
        raise ValueError("乙欄高額給与の計算範囲に該当しません。")

    if amount < 1710000:
        tax = (
            MONTHLY_OTSU_HIGH_BASE_740
            + (Decimal(amount) - Decimal("740000"))
            * MONTHLY_OTSU_RATE_740_TO_1710
        )
        return _truncate_yen(tax)

    tax = (
        MONTHLY_OTSU_HIGH_BASE_1710
        + (Decimal(amount) - Decimal("1710000"))
        * MONTHLY_OTSU_RATE_OVER_1710
    )
    return _truncate_yen(tax)


def _calculate_high_income_ko(amount: int, dependents: int) -> Decimal:
    """令和8年分月額表・甲欄の740,000円以上を計算する。"""
    if not 0 <= dependents <= 7:
        raise ValueError("扶養親族等の数は0～7人で指定してください。")

    for lower, upper, rate in HIGH_INCOME_RATES:
        if amount >= lower and (upper is None or amount < upper):
            base_tax = Decimal(HIGH_INCOME_BASES[lower][dependents])
            additional = (Decimal(amount) - Decimal(lower)) * rate
            return _truncate_yen(base_tax + additional)

    raise ValueError("高額給与の所得税計算範囲に該当しません。")



def _apply_excess_dependents(tax_for_seven: Decimal, dependents: int) -> Decimal:
    """月額表甲欄で扶養親族等が7人を超える場合の控除を適用する。"""
    if dependents <= 7:
        return tax_for_seven

    deduction = (
        Decimal(dependents - 7)
        * MONTHLY_DEPENDENT_EXCESS_DEDUCTION
    )
    return max(Decimal("0"), tax_for_seven - deduction)


def calculate_income_tax(taxable_after_social: Decimal, dependents: int, category: str, table_path: Path) -> Decimal:
    """Look up the 2026 NTA monthly table exported as CSV.

    CSV columns: lower,upper,category,dependents,tax.  This intentionally has no
    fallback percentage: the official annual table must be imported before use.
    """
    if not table_path.exists():
        raise FileNotFoundError("国税庁の源泉徴収税額表CSVを rules/2026 に取り込んでください。")

    if category not in ("甲", "乙"):
        raise ValueError("税額表の区分は「甲」または「乙」で指定してください。")

    amount = int(taxable_after_social)

    if amount < 0:
        raise ValueError("社会保険料等控除後の給与等の金額は0円以上で指定してください。")

    if dependents < 0:
        raise ValueError("扶養親族等の数は0人以上で指定してください。")

    # 甲欄は扶養親族等の数で列を選択する。
    # 乙欄には扶養人数別の列がないためCSV上は常に0を使用する。
    # 「従たる給与についての扶養控除等申告書」による1人1,610円控除は
    # 申告書フラグをモデルへ追加する際に別途対応する。
    lookup_dependents = min(dependents, 7) if category == "甲" else 0

    if category == "乙" and amount < 105000:
        return _calculate_otsu_low_income(amount)

    if category == "乙" and amount >= 740000:
        return _calculate_high_income_otsu(amount)

    if category == "甲" and amount >= 740000:
        tax = _calculate_high_income_ko(amount, lookup_dependents)
        return _apply_excess_dependents(tax, dependents)

    with table_path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if (row["category"] == category and int(row["dependents"]) == lookup_dependents
                    and int(row["lower"]) <= amount < int(row["upper"])):
                tax = Decimal(row["tax"])
                if category == "甲":
                    return _apply_excess_dependents(tax, dependents)
                return tax
    raise ValueError("所得税表に該当する行がありません。")
