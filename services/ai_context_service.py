from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def build_ai_monthly_summary(
    *,
    year_month: str,
    employee_count: int,
    payrolls: Iterable[Any],
    leave_requests: Iterable[Any],
) -> dict[str, int | str]:
    payrolls = list(payrolls)
    leave_requests = list(leave_requests)

    return {
        "year_month": year_month,
        "employee_count": employee_count,
        "calculated_payroll_count": len(payrolls),
        "finalized_payroll_count": sum(
            1 for item in payrolls if item.finalized
        ),
        "blocked_payroll_count": sum(
            1 for item in payrolls if item.blocking_issues
        ),
        "pending_leave_count": sum(
            1
            for item in leave_requests
            if item.status == "申請中"
            and item.leave_date.strftime("%Y-%m") == year_month
        ),
    }


def find_referenced_employee(
    message: str,
    employees: Iterable[Any],
):
    employees = list(employees)

    id_matches = [
        employee
        for employee in employees
        if employee.employee_id
        and employee.employee_id in message
    ]

    if len(id_matches) == 1:
        return id_matches[0]

    if len(id_matches) > 1:
        return None

    name_matches = [
        employee
        for employee in employees
        if employee.name
        and employee.name in message
    ]

    if len(name_matches) == 1:
        return name_matches[0]

    return None


def build_employee_attendance_summary(
    *,
    employee_id: str,
    employee_name: str,
    year_month: str,
    records: Iterable[Any],
) -> dict[str, int | str]:
    from services.attendance_service import attendance_days

    records = list(records)

    return {
        "employee_id": employee_id,
        "employee_name": employee_name,
        "year_month": year_month,
        "record_count": len(records),
        "attendance_days": attendance_days(records),
    }


def build_employee_payroll_summary(
    *,
    employee_id: str,
    year_month: str,
    payroll: Any | None,
) -> dict[str, int | str | bool]:
    if payroll is None:
        return {
            "employee_id": employee_id,
            "year_month": year_month,
            "calculated": False,
            "finalized": False,
            "warning_count": 0,
            "blocking_issue_count": 0,
        }

    return {
        "employee_id": employee_id,
        "year_month": year_month,
        "calculated": True,
        "finalized": payroll.finalized,
        "warning_count": len(payroll.warnings),
        "blocking_issue_count": len(payroll.blocking_issues),
    }


def find_referenced_employee_candidates(
    message: str,
    employees: Iterable[Any],
) -> list[Any]:
    employees = list(employees)

    id_matches = [
        employee
        for employee in employees
        if employee.employee_id
        and employee.employee_id in message
    ]

    if id_matches:
        return id_matches

    return [
        employee
        for employee in employees
        if employee.name
        and employee.name in message
    ]
