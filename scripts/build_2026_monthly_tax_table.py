from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import pdfplumber


def numbers(text: str | None) -> list[int]:
    return [
        int(value.replace(",", ""))
        for value in re.findall(r"\d[\d,]*", text or "")
    ]


def tax_values(text: str | None) -> list[int]:
    return numbers(text)


def build_ranges(page_no: int, row: list[str | None]) -> list[tuple[int, int]]:
    if page_no == 0:
        lines = [
            line.strip()
            for line in (row[0] or "").splitlines()
            if line.strip() and line.strip() != "円 円"
        ]

        ranges: list[tuple[int, int]] = [(0, 105000)]

        for line in lines[1:]:
            values = numbers(line)
            if len(values) != 2:
                raise ValueError(
                    f"page 1 range parse error: {line!r}"
                )
            ranges.append((values[0], values[1]))

        return ranges

    if page_no in (1, 2, 3):
        lowers = numbers(row[0])
        uppers = numbers(row[1])

        if len(lowers) != len(uppers):
            raise ValueError(
                f"page {page_no + 1}: lower/upper count mismatch"
            )

        return list(zip(lowers, uppers))

    if page_no == 4:
        lines = [
            line.strip()
            for line in (row[0] or "").splitlines()
            if line.strip()
            and line.strip() != "円 円"
            and line.strip() != "740,000円"
        ]

        ranges = []

        for line in lines:
            values = numbers(line)
            if len(values) != 2:
                raise ValueError(
                    f"page 5 range parse error: {line!r}"
                )
            ranges.append((values[0], values[1]))

        return ranges

    raise ValueError(f"unsupported page: {page_no + 1}")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: build_2026_monthly_tax_table.py INPUT.pdf OUTPUT.csv"
        )

    pdf_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    rows: list[dict[str, int | str]] = []
    expected_counts = [46, 50, 50, 50, 36]

    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) < 6:
            raise ValueError("PDF must contain the cover and monthly table pages")

        # 令和8年分「源泉徴収税額表」全体版では、
        # PDF 1ページ目が表紙、2～6ページ目が月額表の固定表部分。
        for page_no in range(5):
            pdf_page_no = page_no + 1
            tables = pdf.pages[pdf_page_no].extract_tables()

            if len(tables) != 1:
                raise ValueError(
                    f"page {page_no + 1}: expected one table"
                )

            table = tables[0]
            data_row = table[4]
            ranges = build_ranges(page_no, data_row)

            if len(ranges) != expected_counts[page_no]:
                raise ValueError(
                    f"page {page_no + 1}: "
                    f"range count {len(ranges)} != "
                    f"{expected_counts[page_no]}"
                )

            for dependents in range(8):
                taxes = tax_values(data_row[2 + dependents])

                # 5ページ目の最後は740,000円ちょうどの基準税額。
                # 通常の固定区間には含めない。
                if page_no == 4:
                    taxes = taxes[:-1]

                if len(taxes) != len(ranges):
                    raise ValueError(
                        f"page {page_no + 1}, dependents {dependents}: "
                        f"tax count {len(taxes)} != range count {len(ranges)}"
                    )

                for (lower, upper), tax in zip(ranges, taxes):
                    rows.append(
                        {
                            "lower": lower,
                            "upper": upper,
                            "category": "甲",
                            "dependents": dependents,
                            "tax": tax,
                        }
                    )

            # 乙欄の固定税額。
            # 月額表1ページ目の105,000円未満は3.063%の計算式なので
            # CSVには含めず、tax_service.py側で計算する。
            otsu_taxes = tax_values(data_row[10])

            if page_no == 0:
                # 説明文中の「3.063」と、105,000円未満の計算式部分を除き、
                # 105,000円以上の固定税額45件だけを利用する。
                otsu_taxes = otsu_taxes[2:]
                otsu_ranges = ranges[1:]
            elif page_no == 4:
                # 最後の259,200円は740,000円ちょうどの基準税額。
                otsu_taxes = otsu_taxes[:-1]
                otsu_ranges = ranges
            else:
                otsu_ranges = ranges

            if len(otsu_taxes) != len(otsu_ranges):
                raise ValueError(
                    f"page {page_no + 1}: "
                    f"otsu tax count {len(otsu_taxes)} != "
                    f"range count {len(otsu_ranges)}"
                )

            for (lower, upper), tax in zip(otsu_ranges, otsu_taxes):
                rows.append(
                    {
                        "lower": lower,
                        "upper": upper,
                        "category": "乙",
                        "dependents": 0,
                        "tax": tax,
                    }
                )

    # 甲欄: 232区間 × 8人 = 1,856行
    # 乙欄: 105,000円以上740,000円未満の固定表 = 231行
    expected_total_rows = 2087

    if len(rows) != expected_total_rows:
        raise ValueError(
            f"unexpected output row count: {len(rows)} "
            f"(expected {expected_total_rows})"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "lower",
                "upper",
                "category",
                "dependents",
                "tax",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"created: {output_path}")
    print(f"data rows: {len(rows)}")


if __name__ == "__main__":
    main()
