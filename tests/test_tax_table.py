from decimal import Decimal
from pathlib import Path

from services.tax_service import calculate_income_tax


TABLE = (
    Path(__file__).resolve().parents[1]
    / "rules"
    / "2026"
    / "monthly_tax_table.csv"
)


def tax(amount: int, dependents: int = 0, category: str = "甲"):
    return calculate_income_tax(
        Decimal(amount),
        dependents,
        category,
        TABLE,
    )


def test_2026_monthly_table_first_boundaries():
    assert tax(0) == Decimal("0")
    assert tax(104999) == Decimal("0")

    assert tax(105000) == Decimal("170")
    assert tax(106999) == Decimal("170")

    assert tax(107000) == Decimal("280")
    assert tax(108999) == Decimal("280")


def test_2026_monthly_table_dependents():
    assert tax(105000, 1) == Decimal("0")
    assert tax(107000, 1) == Decimal("0")


def test_2026_high_income_ko_official_base_values():
    from services.tax_service import _calculate_high_income_ko

    expected = {
        740000: 71680,
        790000: 81890,
        960000: 121820,
        1710000: 374520,
        2130000: 549440,
        2170000: 571220,
        2210000: 593000,
        2250000: 614770,
        3500000: 1125270,
    }

    for amount, expected_tax in expected.items():
        assert _calculate_high_income_ko(
            amount,
            0,
        ) == Decimal(expected_tax)


def test_2026_ko_more_than_seven_dependents():
    # 500,000円は月額表7人欄4,830円。
    # 8人の場合は1人超過なので1,610円を控除。
    assert tax(500000, 8, "甲") == Decimal("3220")

    # 740,000円は7人欄26,410円。
    assert tax(740000, 8, "甲") == Decimal("24800")


def test_2026_otsu_official_values():
    # 国税庁「令和8年分 源泉徴収税額表」月額表・乙欄
    expected = {
        80750: 2473,
        105000: 3800,
        195000: 18300,
        739999: 257700,
        740000: 259200,
        1710000: 655400,
    }

    for amount, expected_tax in expected.items():
        assert tax(
            amount,
            0,
            "乙",
        ) == Decimal(expected_tax)
