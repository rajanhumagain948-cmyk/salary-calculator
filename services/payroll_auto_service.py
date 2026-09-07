from __future__ import annotations

from datetime import date

from services.payroll_batch_service import (
    BatchPayrollItem,
    run_due_payroll_batch,
)
from services.storage_service import PayrollRepository


def run_payroll_auto_check(
    repo: PayrollRepository,
    today: date | None = None,
) -> list[BatchPayrollItem] | None:
    """終了済み前月の給与が未処理なら自動計算する。確定はしない。"""
    target_date = today or date.today()

    return run_due_payroll_batch(
        repo,
        target_date,
    )
