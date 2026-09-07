from __future__ import annotations

from dataclasses import dataclass

from models.payroll import PayrollResult
from services.payroll_service import calculate_payroll
from services.storage_service import PayrollRepository


@dataclass(slots=True)
class BatchPayrollItem:
    employee_id: str
    name: str
    status: str
    payroll: PayrollResult | None = None
    error: str | None = None


def calculate_monthly_payrolls(
    repo: PayrollRepository,
    year_month: str,
) -> list[BatchPayrollItem]:
    results: list[BatchPayrollItem] = []

    for employee in repo.employees():
        existing = repo.payroll_result(
            employee.employee_id,
            year_month,
        )

        # 確定済み給与はスナップショットを維持する。
        if existing is not None and existing.finalized:
            results.append(
                BatchPayrollItem(
                    employee_id=employee.employee_id,
                    name=employee.name,
                    status="確定済",
                    payroll=existing,
                )
            )
            continue

        try:
            terms = repo.terms(employee.employee_id)
            records = repo.work_records(
                employee.employee_id,
                year_month,
            )
            allowances, deductions, transport = repo.monthly_inputs(
                employee.employee_id,
                year_month,
            )

            transport.attendance_days = len(records)

            result = calculate_payroll(
                employee=employee,
                terms=terms,
                records=records,
                allowances=allowances,
                transport=transport,
                other_deductions=deductions,
                year_month=year_month,
            )

            # 自動計算・一括計算では確定しない。
            result.finalized = False
            result.company_name = repo.company().name

            repo.save_payroll_result(result)

            status = (
                "要確認"
                if result.blocking_issues or result.warnings
                else "正常"
            )

            results.append(
                BatchPayrollItem(
                    employee_id=employee.employee_id,
                    name=employee.name,
                    status=status,
                    payroll=result,
                )
            )

        except (ValueError, TypeError) as error:
            results.append(
                BatchPayrollItem(
                    employee_id=employee.employee_id,
                    name=employee.name,
                    status="計算不可",
                    error=str(error),
                )
            )

    return results


def completed_payroll_month(today) -> str:
    """最後まで終了している直前月を YYYY-MM で返す。"""
    if today.month == 1:
        year = today.year - 1
        month = 12
    else:
        year = today.year
        month = today.month - 1

    return f"{year:04d}-{month:02d}"
