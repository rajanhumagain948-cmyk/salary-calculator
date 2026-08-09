"""Company-wide exports for a selected payroll month."""
from __future__ import annotations
import csv
from decimal import Decimal
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from models.employee import Employee
from models.payroll import PayrollResult
from services.payslip_service import export_pdf

def export_payroll_ledger(items: list[tuple[Employee, PayrollResult]], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["社員番号", "氏名", "対象年月", "総支給額", "控除合計", "差引支給額", "確定状態"])
        for employee, result in items:
            writer.writerow([employee.employee_id, employee.name, result.year_month, result.gross_pay, result.total_deductions, result.net_pay, "確定" if result.finalized else "未確定"])

def export_payslip_zip(items: list[tuple[Employee, PayrollResult]], path: Path) -> None:
    temporary = path.parent / ".payslips_tmp"
    temporary.mkdir(exist_ok=True)
    files: list[Path] = []
    try:
        for employee, result in items:
            pdf = temporary / f"{result.year_month}_{employee.employee_id}_{employee.name}.pdf"
            export_pdf(employee, result, pdf); files.append(pdf)
        with ZipFile(path, "w", ZIP_DEFLATED) as archive:
            for pdf in files: archive.write(pdf, pdf.name)
    finally:
        for pdf in files: pdf.unlink(missing_ok=True)
        temporary.rmdir()
