from __future__ import annotations
from pathlib import Path
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from models.employee import Employee
from models.payroll import PayrollResult
from services.time_service import format_minutes

def render_text(employee: Employee, result: PayrollResult) -> str:
    c = result.classification
    lines = ["給与明細書", result.company_name, f"氏名: {employee.name}  社員番号: {employee.employee_id}  対象年月: {result.year_month}", "",
             "【勤怠】", f"出勤時間: {format_minutes(c.regular_minutes + c.overtime_minutes + c.holiday_minutes)}",
             f"時間外: {format_minutes(c.overtime_minutes)}  深夜: {format_minutes(c.night_minutes + c.overtime_night_minutes + c.holiday_night_minutes)}  休日: {format_minutes(c.holiday_minutes)}", "", "【支給】"]
    lines += [f"{k}: {v:,.0f}円" for k, v in result.payments.items() if v]
    lines += [f"総支給額: {result.gross_pay:,.0f}円", "", "【控除】"]
    lines += [f"{k}: {v:,.0f}円" for k, v in result.deductions.items() if v]
    lines += [f"控除合計: {result.total_deductions:,.0f}円", "", f"差引支給額: {result.net_pay:,.0f}円"]
    return "\n".join(lines)

def export_pdf(employee: Employee, result: PayrollResult, path: Path) -> None:
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    page = canvas.Canvas(str(path), pagesize=A4)
    page.setFont("HeiseiKakuGo-W5", 11)
    y = 800
    for line in render_text(employee, result).splitlines():
        page.drawString(48, y, line)
        y -= 18
    page.save()
