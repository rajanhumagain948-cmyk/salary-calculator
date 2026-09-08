from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True)
class Company:
    name: str = ""
    address: str = ""
    representative: str = ""

    # 時間単位年休は労使協定を締結している会社だけ有効化する。
    hourly_paid_leave_enabled: bool = False

    # 取得できる最小時間単位。通常は1時間。
    hourly_paid_leave_unit_hours: int = 1

    # 時間単位年休の「1年間」の起算日（労使協定に合わせて設定）。
    hourly_paid_leave_year_start_month: int = 4
    hourly_paid_leave_year_start_day: int = 1
