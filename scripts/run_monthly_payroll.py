from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.payroll_auto_service import run_payroll_auto_check
from services.storage_service import PayrollRepository


def main() -> int:
    repo = PayrollRepository(ROOT / "data" / "payroll.sqlite3")

    results = run_payroll_auto_check(
        repo,
        date.today(),
    )

    if results is None:
        print("自動給与計算: 今月はすでに処理済みです。")
        return 0

    counts: dict[str, int] = {}

    for item in results:
        counts[item.status] = counts.get(item.status, 0) + 1

    summary = ", ".join(
        f"{status}={count}"
        for status, count in counts.items()
    )

    print(
        f"自動給与計算完了: {summary or '対象従業員なし'}"
    )
    print("給与は未確定です。管理者による確認・確定が必要です。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
