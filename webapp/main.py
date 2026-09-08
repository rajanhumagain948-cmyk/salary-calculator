import json
import unicodedata
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, HTTPException, Response, Request
from fastapi.responses import JSONResponse, FileResponse
from starlette.background import BackgroundTask
from itsdangerous import URLSafeSerializer, BadSignature
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from services.storage_service import PayrollRepository
from services.auth_service import verify_password
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, datetime
from decimal import Decimal
from models.break_record import BreakRecord
from models.company import Company
from models.employee import Employee
from models.leave_request import LeaveRequest
from models.shifts import Shift
from models.work_record import WorkRecord
from models.allowance import Allowance
from models.deduction import OtherDeduction
from models.transportation import Transportation
from services.payroll_service import calculate_payroll
from services.payroll_batch_service import calculate_monthly_payrolls
from services.payroll_auto_service import run_payroll_auto_check
from services.leave_service import due_leave_grant
from services.payslip_service import export_pdf

@asynccontextmanager
async def lifespan(app: FastAPI):
    run_payroll_auto_check(repo)
    yield


app = FastAPI(title="Salary Calculator Web", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="webapp/templates")

repo = PayrollRepository(Path("data/payroll.sqlite3"))
serializer = URLSafeSerializer("dev-secret-change-me", salt="session")

COOKIE_NAME = "salary_session"


def normalize_input(value: str) -> str:
    """全角英数字・記号を半角へ寄せ、前後の空白を除去する。"""
    return unicodedata.normalize("NFKC", value).strip()




def set_session_cookie(resp: Response, username: str) -> None:
    token = serializer.dumps({"username": username})
    resp.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
    )


def get_current_user(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        data = serializer.loads(token)
    except BadSignature:
        return None
    return repo.user(data.get("username", ""))

def require_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="not logged in")
    return user


@app.get("/")
def health():
    return {"status": "ok"}

@app.get("/login-ui", response_class=HTMLResponse)
def login_ui(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "error": ""},
    )

@app.post("/login-ui", response_class=HTMLResponse)
def login_ui_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = repo.user(username.strip())
    if not user or not user.active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": "ユーザー名またはパスワードが正しくありません。"},
        )

    resp = RedirectResponse(url="/app", status_code=303)
    set_session_cookie(resp, user.username)
    return resp


@app.get("/app", response_class=HTMLResponse)
def app_home(request: Request):
    user = require_user(request)
    return HTMLResponse(
        f"<h1>ログイン中: {user.username} ({user.role})</h1>"
        f"<p><a href='/docs'>API Docs</a></p>"
    )


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    user = repo.user(username.strip())
    if not user or not user.active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")

    resp = JSONResponse(
        {"ok": True, "role": user.role, "employee_id": user.employee_id}
    )
    set_session_cookie(resp, user.username)
    return resp


@app.post("/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.get("/me")
def me(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="not logged in")
    return {
        "username": user.username,
        "role": user.role,
        "employee_id": user.employee_id,
    }

@app.get("/company")
def company_info(request: Request):
    require_user(request)
    company = repo.company()

    return {
        "name": company.name,
        "address": company.address,
        "representative": company.representative,
    }


@app.put("/company")
def update_company(
    request: Request,
    name: str = Form(...),
    address: str = Form(""),
    representative: str = Form(""),
):
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="company name is required")

    company = Company(
        name=name,
        address=address.strip(),
        representative=representative.strip(),
    )
    repo.save_company(company)

    return {
        "ok": True,
        "company": {
            "name": company.name,
            "address": company.address,
            "representative": company.representative,
        },
    }


@app.get("/employees")
def employees(request: Request):
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    return [
        {"employee_id": e.employee_id, "name": e.name}
        for e in repo.employees()
    ]


def employee_to_dict(e: Employee):
    return {
        "employee_id": e.employee_id,
        "name": e.name,
        "employment_type": e.employment_type,
        "hire_date": e.hire_date.isoformat(),
        "pay_type": e.pay_type,
        "hourly_rate": str(e.hourly_rate),
        "monthly_salary": str(e.monthly_salary),
        "weekly_hours": str(e.weekly_hours),
        "weekly_days": e.weekly_days,
        "contract_months": e.contract_months,
        "workplace_size": e.workplace_size,
        "is_student": e.is_student,
        "dependents": e.dependents,
        "tax_category": e.tax_category,
        "birth_date": e.birth_date.isoformat() if e.birth_date else None,
        "termination_date": e.termination_date.isoformat() if e.termination_date else None,
        "prefecture": e.prefecture,
        "resident_tax_monthly": str(e.resident_tax_monthly),
        "resident_tax_method": e.resident_tax_method,
        "standard_monthly_remuneration": str(e.standard_monthly_remuneration),
    }


@app.get("/employees/{employee_id}")
def employee_detail(employee_id: str, request: Request):
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    employee = next(
        (e for e in repo.employees() if e.employee_id == employee_id),
        None,
    )

    if employee is None:
        raise HTTPException(status_code=404, detail="employee not found")

    return employee_to_dict(employee)


def build_employee(
    employee_id: str,
    name: str,
    employment_type: str,
    hire_date: str,
    pay_type: str,
    hourly_rate: str,
    monthly_salary: str,
    weekly_hours: str,
    weekly_days: int,
    contract_months: str,
    workplace_size: int,
    is_student: int,
    dependents: int,
    tax_category: str,
    birth_date: str,
    termination_date: str,
    prefecture: str,
    resident_tax_monthly: str,
    resident_tax_method: str,
    standard_monthly_remuneration: str,
) -> Employee:
    employee_id = employee_id.strip()
    name = name.strip()

    if not employee_id or not name:
        raise HTTPException(
            status_code=400,
            detail="employee_id and name are required",
        )

    if employment_type not in ("正社員", "契約社員", "パート", "アルバイト"):
        raise HTTPException(status_code=400, detail="invalid employment_type")

    if pay_type not in ("時給", "月給"):
        raise HTTPException(status_code=400, detail="invalid pay_type")

    if tax_category not in ("甲", "乙"):
        raise HTTPException(status_code=400, detail="invalid tax_category")

    if resident_tax_method not in ("特別徴収", "普通徴収"):
        raise HTTPException(status_code=400, detail="invalid resident_tax_method")

    try:
        return Employee(
            employee_id=employee_id,
            name=name,
            employment_type=employment_type,
            hire_date=date.fromisoformat(hire_date),
            pay_type=pay_type,
            hourly_rate=Decimal(hourly_rate or "0"),
            monthly_salary=Decimal(monthly_salary or "0"),
            weekly_hours=Decimal(weekly_hours or "0"),
            weekly_days=int(weekly_days),
            contract_months=int(contract_months) if contract_months else None,
            workplace_size=int(workplace_size),
            is_student=bool(int(is_student)),
            dependents=int(dependents),
            tax_category=tax_category,
            birth_date=date.fromisoformat(birth_date) if birth_date else None,
            termination_date=(
                date.fromisoformat(termination_date)
                if termination_date
                else None
            ),
            prefecture=prefecture.strip() or "東京都",
            resident_tax_monthly=Decimal(resident_tax_monthly or "0"),
            resident_tax_method=resident_tax_method,
            standard_monthly_remuneration=Decimal(
                standard_monthly_remuneration or "0"
            ),
        )
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/employees")
def save_employee(
    request: Request,
    employee_id: str = Form(...),
    name: str = Form(...),
    employment_type: str = Form(...),
    hire_date: str = Form(...),
    pay_type: str = Form(...),
    hourly_rate: str = Form("0"),
    monthly_salary: str = Form("0"),
    weekly_hours: str = Form("0"),
    weekly_days: int = Form(0),
    contract_months: str = Form(""),
    workplace_size: int = Form(0),
    is_student: int = Form(0),
    dependents: int = Form(0),
    tax_category: str = Form("甲"),
    birth_date: str = Form(""),
    termination_date: str = Form(""),
    prefecture: str = Form("東京都"),
    resident_tax_monthly: str = Form("0"),
    resident_tax_method: str = Form("特別徴収"),
    standard_monthly_remuneration: str = Form("0"),
):
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    employee_id = employee_id.strip()

    if any(e.employee_id == employee_id for e in repo.employees()):
        raise HTTPException(
            status_code=409,
            detail="employee_id already exists",
        )

    employee = build_employee(
        employee_id=employee_id,
        name=name,
        employment_type=employment_type,
        hire_date=hire_date,
        pay_type=pay_type,
        hourly_rate=hourly_rate,
        monthly_salary=monthly_salary,
        weekly_hours=weekly_hours,
        weekly_days=weekly_days,
        contract_months=contract_months,
        workplace_size=workplace_size,
        is_student=is_student,
        dependents=dependents,
        tax_category=tax_category,
        birth_date=birth_date,
        termination_date=termination_date,
        prefecture=prefecture,
        resident_tax_monthly=resident_tax_monthly,
        resident_tax_method=resident_tax_method,
        standard_monthly_remuneration=standard_monthly_remuneration,
    )

    repo.save_employee(employee)

    return {"ok": True, "employee": employee_to_dict(employee)}


@app.put("/employees/{employee_id}")
def update_employee(
    employee_id: str,
    request: Request,
    name: str = Form(...),
    employment_type: str = Form(...),
    hire_date: str = Form(...),
    pay_type: str = Form(...),
    hourly_rate: str = Form("0"),
    monthly_salary: str = Form("0"),
    weekly_hours: str = Form("0"),
    weekly_days: int = Form(0),
    contract_months: str = Form(""),
    workplace_size: int = Form(0),
    is_student: int = Form(0),
    dependents: int = Form(0),
    tax_category: str = Form("甲"),
    birth_date: str = Form(""),
    termination_date: str = Form(""),
    prefecture: str = Form("東京都"),
    resident_tax_monthly: str = Form("0"),
    resident_tax_method: str = Form("特別徴収"),
    standard_monthly_remuneration: str = Form("0"),
):
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    employee_id = employee_id.strip()

    if not any(e.employee_id == employee_id for e in repo.employees()):
        raise HTTPException(status_code=404, detail="employee not found")

    employee = build_employee(
        employee_id=employee_id,
        name=name,
        employment_type=employment_type,
        hire_date=hire_date,
        pay_type=pay_type,
        hourly_rate=hourly_rate,
        monthly_salary=monthly_salary,
        weekly_hours=weekly_hours,
        weekly_days=weekly_days,
        contract_months=contract_months,
        workplace_size=workplace_size,
        is_student=is_student,
        dependents=dependents,
        tax_category=tax_category,
        birth_date=birth_date,
        termination_date=termination_date,
        prefecture=prefecture,
        resident_tax_monthly=resident_tax_monthly,
        resident_tax_method=resident_tax_method,
        standard_monthly_remuneration=standard_monthly_remuneration,
    )

    repo.save_employee(employee)

    return {"ok": True, "employee": employee_to_dict(employee)}


from services.time_service import parse_date  # 既存利用（未使用なら後で整理）


@app.get("/shifts/{year_month}")
def get_shifts(year_month: str, request: Request, employee_id: str | None = None):
    """
    - employee(社員): employee_id を指定しても無視し、自分のシフトのみ返す
    - admin(管理者): employee_id を指定した場合はその社員のシフト、未指定ならエラー
    """
    user = require_user(request)

    if user.role == "employee":
        if not user.employee_id:
            raise HTTPException(status_code=400, detail="employee_id not set")
        target_employee_id = user.employee_id
    else:
        if not employee_id:
            raise HTTPException(status_code=400, detail="employee_id required for admin")
        target_employee_id = employee_id

    shifts = repo.shifts(target_employee_id, year_month)

    return [
        {
            "shift_id": s.shift_id,
            "employee_id": s.employee_id,
            "shift_date": s.shift_date.isoformat(),
            "start_minute": s.start_minute,
            "end_minute": s.end_minute,
            "break_minutes": s.break_minutes,
            "note": s.note,
            "confirmed": s.confirmed,
        }
        for s in shifts
    ]

@app.post("/shifts")
def upsert_shift(
    request: Request,
    employee_id: str = Form(...),
    shift_date: str = Form(...),  # YYYY-MM-DD
    start_minute: int = Form(...),
    end_minute: int = Form(...),
    break_minutes: int = Form(0),
    note: str = Form(""),
    confirmed: int = Form(0),
    shift_id: int | None = Form(None),
):
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    s = Shift(
        employee_id=employee_id,
        shift_date=date.fromisoformat(shift_date),
        start_minute=int(start_minute),
        end_minute=int(end_minute),
        break_minutes=int(break_minutes),
        note=note,
        confirmed=bool(int(confirmed)),
        shift_id=int(shift_id) if shift_id is not None else None,
    )

    saved = repo.save_shift(s)
    return {"ok": True, "shift_id": saved.shift_id}


@app.post("/shifts/delete")
def delete_shift(
    request: Request,
    employee_id: str = Form(...),
    shift_id: int = Form(...),
):
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    repo.delete_shift(employee_id, int(shift_id))
    return {"ok": True}

@app.get("/attendance/{year_month}")
def get_attendance(
    year_month: str,
    request: Request,
    employee_id: str | None = None,
):
    user = require_user(request)
    year_month = normalize_input(year_month)

    if user.role == "employee":
        if not user.employee_id:
            raise HTTPException(status_code=400, detail="employee_id not set")
        target_employee_id = normalize_input(user.employee_id)
    else:
        if not employee_id:
            raise HTTPException(status_code=400, detail="employee_id required")
        target_employee_id = normalize_input(employee_id)

    try:
        year, month = year_month.split("-")
        if len(year) != 4 or len(month) != 2:
            raise ValueError
        date(int(year), int(month), 1)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="year_month must be YYYY-MM",
        ) from error

    records = repo.work_records(target_employee_id, year_month)

    return [
        {
            "record_id": record.record_id,
            "employee_id": record.employee_id,
            "work_date": record.work_date.isoformat(),
            "start_minute": record.start_minute,
            "end_minute": record.end_minute,
            "is_holiday": record.is_holiday,
            "break_total_minutes": record.actual_break_minutes,
            "breaks": [
                {
                    "start_minute": item.start_minute,
                    "end_minute": item.end_minute,
                }
                for item in record.breaks
            ],
            "span_minutes": record.span_minutes,
            "work_minutes": max(
                0,
                record.span_minutes - record.actual_break_minutes,
            ),
        }
        for record in records
    ]


@app.post("/attendance")
def save_attendance(
    request: Request,
    work_date: str = Form(...),
    start_minute: int = Form(...),
    end_minute: int = Form(...),
    break_minutes: int = Form(0),
    is_holiday: int = Form(0),
    employee_id: str = Form(""),
    record_id: int | None = Form(None),
):
    user = require_user(request)
    work_date = normalize_input(work_date)
    employee_id = normalize_input(employee_id)

    if user.role == "employee":
        if not user.employee_id:
            raise HTTPException(status_code=400, detail="employee_id not set")
        target_employee_id = user.employee_id
    else:
        target_employee_id = employee_id.strip()
        if not target_employee_id:
            raise HTTPException(
                status_code=400,
                detail="employee_id required",
            )

    try:
        parsed_date = date.fromisoformat(work_date)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="work_date must be YYYY-MM-DD",
        ) from error

    if not 0 <= start_minute < 1440:
        raise HTTPException(status_code=400, detail="invalid start_minute")

    if not 0 <= end_minute < 1440:
        raise HTTPException(status_code=400, detail="invalid end_minute")

    if break_minutes < 0:
        raise HTTPException(status_code=400, detail="invalid break_minutes")

    record = WorkRecord(
        employee_id=target_employee_id,
        work_date=parsed_date,
        start_minute=start_minute,
        end_minute=end_minute,
        is_holiday=bool(is_holiday),
        break_total_minutes=break_minutes,
        record_id=record_id,
    )

    if record.actual_break_minutes > record.span_minutes:
        raise HTTPException(
            status_code=400,
            detail="break time exceeds work span",
        )

    saved = repo.save_work_record(record)

    return {
        "ok": True,
        "record_id": saved.record_id,
    }


@app.post("/attendance/delete")
def delete_attendance(
    request: Request,
    record_id: int = Form(...),
    employee_id: str = Form(""),
):
    user = require_user(request)

    if user.role == "employee":
        if not user.employee_id:
            raise HTTPException(status_code=400, detail="employee_id not set")
        target_employee_id = user.employee_id
    else:
        target_employee_id = employee_id.strip()
        if not target_employee_id:
            raise HTTPException(
                status_code=400,
                detail="employee_id required",
            )

    repo.delete_work_record(target_employee_id, record_id)

    return {"ok": True}


@app.get("/attendance/today/events")
def attendance_today_events(request: Request):
    user = require_user(request)

    if user.role != "employee":
        raise HTTPException(status_code=403, detail="employee only")

    if not user.employee_id:
        raise HTTPException(status_code=400, detail="employee_id not set")

    today = date.today()
    events = repo.attendance_events(user.employee_id, today)

    return {
        "date": today.isoformat(),
        "employee_id": user.employee_id,
        "events": events,
    }


@app.post("/attendance/clock")
def attendance_clock(
    request: Request,
    event_type: str = Form(...),
):
    user = require_user(request)

    if user.role != "employee":
        raise HTTPException(status_code=403, detail="employee only")

    if not user.employee_id:
        raise HTTPException(status_code=400, detail="employee_id not set")

    allowed_types = {
        "clock_in",
        "break_start",
        "break_end",
        "clock_out",
    }

    if event_type not in allowed_types:
        raise HTTPException(status_code=400, detail="invalid event_type")

    today = date.today()
    events = repo.attendance_events(user.employee_id, today)
    types = [str(event["event_type"]) for event in events]

    if not types:
        expected = {"clock_in"}
    else:
        last = types[-1]

        if last == "clock_in":
            expected = {"break_start", "clock_out"}
        elif last == "break_start":
            expected = {"break_end"}
        elif last == "break_end":
            expected = {"break_start", "clock_out"}
        else:
            expected = set()

    if event_type not in expected:
        raise HTTPException(
            status_code=409,
            detail="invalid attendance event order",
        )

    event_id = repo.save_attendance_event(
        employee_id=user.employee_id,
        event_type=event_type,
        method="web",
    )

    record_id = None

    if event_type == "clock_out":
        completed_events = repo.attendance_events(
            user.employee_id,
            today,
        )

        clock_in_event = next(
            event
            for event in completed_events
            if event["event_type"] == "clock_in"
        )

        clock_out_event = completed_events[-1]

        start_at = datetime.fromisoformat(
            str(clock_in_event["event_at"])
        )
        end_at = datetime.fromisoformat(
            str(clock_out_event["event_at"])
        )

        start_minute = start_at.hour * 60 + start_at.minute
        end_minute = end_at.hour * 60 + end_at.minute

        breaks: list[BreakRecord] = []
        break_start_at: datetime | None = None

        for event in completed_events:
            event_at = datetime.fromisoformat(str(event["event_at"]))

            if event["event_type"] == "break_start":
                break_start_at = event_at

            elif (
                event["event_type"] == "break_end"
                and break_start_at is not None
            ):
                breaks.append(
                    BreakRecord(
                        start_minute=(
                            break_start_at.hour * 60
                            + break_start_at.minute
                        ),
                        end_minute=(
                            event_at.hour * 60
                            + event_at.minute
                        ),
                    )
                )
                break_start_at = None

        existing = next(
            (
                record
                for record in repo.work_records(
                    user.employee_id,
                    today.strftime("%Y-%m"),
                )
                if record.work_date == today
            ),
            None,
        )

        work_record = WorkRecord(
            employee_id=user.employee_id,
            work_date=today,
            start_minute=start_minute,
            end_minute=end_minute,
            breaks=breaks,
            break_total_minutes=sum(
                item.minutes for item in breaks
            ),
            record_id=existing.record_id if existing else None,
        )

        saved_record = repo.save_work_record(work_record)
        record_id = saved_record.record_id

    return {
        "ok": True,
        "event_id": event_id,
        "event_type": event_type,
        "record_id": record_id,
    }


@app.get("/audit")
def audit_log(
    request: Request,
    limit: int = 50,
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    limit = max(1, min(limit, 200))

    return [
        {
            "created_at": created_at,
            "action": action,
            "subject": subject,
            "detail": detail,
        }
        for created_at, action, subject, detail
        in repo.recent_audit(limit)
    ]


def payroll_result_to_dict(result):
    return {
        "employee_id": result.employee_id,
        "year_month": result.year_month,
        "payments": {
            key: str(value)
            for key, value in result.payments.items()
        },
        "deductions": {
            key: str(value)
            for key, value in result.deductions.items()
        },
        "gross_pay": str(result.gross_pay),
        "total_deductions": str(result.total_deductions),
        "net_pay": str(result.net_pay),
        "classification": {
            "regular_minutes": result.classification.regular_minutes,
            "overtime_minutes": result.classification.overtime_minutes,
            "night_minutes": result.classification.night_minutes,
            "regular_night_minutes": result.classification.regular_night_minutes,
            "holiday_minutes": result.classification.holiday_minutes,
            "overtime_night_minutes": result.classification.overtime_night_minutes,
            "holiday_night_minutes": result.classification.holiday_night_minutes,
            "overtime_over_60_minutes": (
                result.classification.overtime_over_60_minutes
            ),
        },
        "warnings": result.warnings,
        "blocking_issues": result.blocking_issues,
        "finalized": result.finalized,
        "company_name": result.company_name,
    }


@app.post("/payroll/calculate")
def calculate_employee_payroll(
    request: Request,
    employee_id: str = Form(...),
    year_month: str = Form(...),
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    employee_id = normalize_input(employee_id)
    year_month = normalize_input(year_month)

    employee = next(
        (
            employee
            for employee in repo.employees()
            if employee.employee_id == employee_id
        ),
        None,
    )

    if employee is None:
        raise HTTPException(status_code=404, detail="employee not found")

    try:
        year, month = year_month.split("-")
        if len(year) != 4 or len(month) != 2:
            raise ValueError
        date(int(year), int(month), 1)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="year_month must be YYYY-MM",
        ) from error

    existing_result = repo.payroll_result(employee_id, year_month)

    if existing_result is not None and existing_result.finalized:
        raise HTTPException(
            status_code=409,
            detail="確定済みの給与は再計算できません。",
        )

    terms = repo.terms(employee_id)
    records = repo.work_records(employee_id, year_month)
    allowances, deductions, transport = repo.monthly_inputs(
        employee_id,
        year_month,
    )

    transport.attendance_days = len(records)

    try:
        result = calculate_payroll(
            employee=employee,
            terms=terms,
            records=records,
            allowances=allowances,
            transport=transport,
            other_deductions=deductions,
            year_month=year_month,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    result.company_name = repo.company().name
    repo.save_payroll_result(result)

    return payroll_result_to_dict(result)


@app.get("/payroll/{year_month}/{employee_id}")
def get_payroll_result(
    year_month: str,
    employee_id: str,
    request: Request,
):
    user = require_user(request)

    employee_id = normalize_input(employee_id)
    year_month = normalize_input(year_month)

    if user.role == "employee":
        if not user.employee_id:
            raise HTTPException(status_code=400, detail="employee_id not set")

        if normalize_input(user.employee_id) != employee_id:
            raise HTTPException(status_code=403, detail="forbidden")

    result = repo.payroll_result(employee_id, year_month)

    if result is None:
        raise HTTPException(status_code=404, detail="payroll not found")

    if user.role == "employee" and not result.finalized:
        raise HTTPException(status_code=404, detail="payroll not found")

    return payroll_result_to_dict(result)


@app.get("/payroll-inputs/{year_month}/{employee_id}")
def get_payroll_inputs(
    year_month: str,
    employee_id: str,
    request: Request,
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    employee_id = normalize_input(employee_id)
    year_month = normalize_input(year_month)

    allowances, deductions, transport = repo.monthly_inputs(
        employee_id,
        year_month,
    )

    return {
        "employee_id": employee_id,
        "year_month": year_month,
        "allowances": [
            {
                "name": item.name,
                "amount": str(item.amount),
                "taxable": item.taxable,
            }
            for item in allowances
        ],
        "deductions": [
            {
                "name": item.name,
                "amount": str(item.amount),
            }
            for item in deductions
        ],
        "transport": {
            "method": transport.method,
            "unit_amount": str(transport.unit_amount),
            "attendance_days": transport.attendance_days,
            "taxable": transport.taxable,
            "amount": str(transport.amount),
        },
    }


@app.post("/payroll-inputs")
def save_payroll_inputs(
    request: Request,
    employee_id: str = Form(...),
    year_month: str = Form(...),
    allowances_json: str = Form("[]"),
    deductions_json: str = Form("[]"),
    transport_method: str = Form("なし"),
    transport_amount: str = Form("0"),
    transport_taxable: int = Form(0),
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    employee_id = normalize_input(employee_id)
    year_month = normalize_input(year_month)
    transport_method = normalize_input(transport_method)
    transport_amount = normalize_input(transport_amount)

    if transport_method not in ("なし", "月額固定", "日額", "実費"):
        raise HTTPException(
            status_code=400,
            detail="invalid transport_method",
        )

    try:
        raw_allowances = json.loads(
            normalize_input(allowances_json)
        )
        raw_deductions = json.loads(
            normalize_input(deductions_json)
        )

        if not isinstance(raw_allowances, list):
            raise ValueError("allowances must be a list")

        if not isinstance(raw_deductions, list):
            raise ValueError("deductions must be a list")

        allowances: list[Allowance] = []

        for item in raw_allowances:
            name = normalize_input(str(item.get("name", "")))
            amount = Decimal(
                normalize_input(str(item.get("amount", "0")))
            )
            taxable = bool(item.get("taxable", True))

            if not name:
                raise ValueError("手当名を入力してください。")

            if amount < 0:
                raise ValueError("手当は0円以上で入力してください。")

            allowances.append(
                Allowance(
                    name=name,
                    amount=amount,
                    taxable=taxable,
                )
            )

        deductions: list[OtherDeduction] = []

        for item in raw_deductions:
            name = normalize_input(str(item.get("name", "")))
            amount = Decimal(
                normalize_input(str(item.get("amount", "0")))
            )

            if not name:
                raise ValueError("控除名を入力してください。")

            if amount < 0:
                raise ValueError("控除は0円以上で入力してください。")

            deductions.append(
                OtherDeduction(
                    name=name,
                    amount=amount,
                )
            )

        transport_value = Decimal(transport_amount or "0")

        if transport_value < 0:
            raise ValueError("交通費は0円以上で入力してください。")

    except (
        json.JSONDecodeError,
        ValueError,
        TypeError,
    ) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    records = repo.work_records(employee_id, year_month)

    transport = Transportation(
        method=transport_method,
        unit_amount=transport_value,
        attendance_days=len(records),
        taxable=bool(transport_taxable),
    )

    repo.save_monthly_inputs(
        employee_id,
        year_month,
        allowances,
        deductions,
        transport,
    )

    return {
        "ok": True,
        "allowances": len(allowances),
        "deductions": len(deductions),
        "transport_amount": str(transport.amount),
    }


@app.post("/payroll/finalize")
def finalize_payroll(
    request: Request,
    employee_id: str = Form(...),
    year_month: str = Form(...),
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    employee_id = normalize_input(employee_id)
    year_month = normalize_input(year_month)

    result = repo.payroll_result(employee_id, year_month)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="先に給与を計算してください。",
        )

    if result.blocking_issues:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "要対応の問題があるため給与を確定できません。",
                "blocking_issues": result.blocking_issues,
            },
        )

    if result.finalized:
        return payroll_result_to_dict(result)

    result.finalized = True
    repo.save_payroll_result(result)

    return payroll_result_to_dict(result)


@app.get("/payroll/{year_month}/{employee_id}/pdf")
def download_payroll_pdf(
    year_month: str,
    employee_id: str,
    request: Request,
):
    user = require_user(request)

    employee_id = normalize_input(employee_id)
    year_month = normalize_input(year_month)

    if user.role == "employee":
        if not user.employee_id:
            raise HTTPException(status_code=400, detail="employee_id not set")

        if normalize_input(user.employee_id) != employee_id:
            raise HTTPException(status_code=403, detail="forbidden")

    result = repo.payroll_result(employee_id, year_month)

    if result is None:
        raise HTTPException(status_code=404, detail="payroll not found")

    if user.role == "employee" and not result.finalized:
        raise HTTPException(status_code=404, detail="payroll not found")

    employee = next(
        (
            item
            for item in repo.employees()
            if item.employee_id == employee_id
        ),
        None,
    )

    if employee is None:
        raise HTTPException(status_code=404, detail="employee not found")

    temp = tempfile.NamedTemporaryFile(
        prefix="payslip_",
        suffix=".pdf",
        delete=False,
    )
    temp_path = Path(temp.name)
    temp.close()

    try:
        export_pdf(employee, result, temp_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    filename = f"payslip_{year_month}_{employee_id}.pdf"

    return FileResponse(
        path=temp_path,
        media_type="application/pdf",
        filename=filename,
        background=BackgroundTask(
            temp_path.unlink,
            missing_ok=True,
        ),
    )


@app.post("/payroll/calculate-all")
def calculate_all_employee_payrolls(
    request: Request,
    year_month: str = Form(...),
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    year_month = normalize_input(year_month)

    try:
        year, month = year_month.split("-")
        if len(year) != 4 or len(month) != 2:
            raise ValueError
        date(int(year), int(month), 1)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="year_month must be YYYY-MM",
        ) from error

    batch_results = calculate_monthly_payrolls(repo, year_month)

    return {
        "year_month": year_month,
        "results": [
            {
                "employee_id": item.employee_id,
                "name": item.name,
                "status": item.status,
                "payroll": (
                    payroll_result_to_dict(item.payroll)
                    if item.payroll is not None
                    else None
                ),
                "error": item.error,
            }
            for item in batch_results
        ],
    }


@app.get("/payroll-results/{year_month}")
def list_payroll_results(
    year_month: str,
    request: Request,
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    year_month = normalize_input(year_month)

    try:
        year, month = year_month.split("-")
        if len(year) != 4 or len(month) != 2:
            raise ValueError
        date(int(year), int(month), 1)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="year_month must be YYYY-MM",
        ) from error

    return {
        "year_month": year_month,
        "results": [
            payroll_result_to_dict(result)
            for result in repo.payroll_results(year_month)
        ],
    }



def leave_request_to_dict(item: LeaveRequest) -> dict:
    return {
        "request_id": item.request_id,
        "employee_id": item.employee_id,
        "leave_date": item.leave_date.isoformat(),
        "reason": item.reason,
        "status": item.status,
        "created_at": (
            item.created_at.isoformat()
            if item.created_at is not None
            else None
        ),
    }


@app.get("/my/leave-requests")
def get_my_leave_requests(request: Request):
    user = require_user(request)

    if user.role != "employee":
        raise HTTPException(status_code=403, detail="employee only")

    if not user.employee_id:
        raise HTTPException(status_code=400, detail="employee_id not set")

    employee_id = normalize_input(user.employee_id)

    return [
        leave_request_to_dict(item)
        for item in repo.leave_requests(employee_id)
    ]


@app.post("/my/leave-requests")
def submit_my_leave_request(
    request: Request,
    leave_date: str = Form(...),
    reason: str = Form(""),
):
    user = require_user(request)

    if user.role != "employee":
        raise HTTPException(status_code=403, detail="employee only")

    if not user.employee_id:
        raise HTTPException(status_code=400, detail="employee_id not set")

    employee_id = normalize_input(user.employee_id)
    leave_date = normalize_input(leave_date)
    reason = normalize_input(reason)

    try:
        parsed_date = date.fromisoformat(leave_date)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="leave_date must be YYYY-MM-DD",
        ) from error

    item = repo.save_leave_request(
        LeaveRequest(
            employee_id=employee_id,
            leave_date=parsed_date,
            reason=reason,
            status="申請中",
        )
    )

    return leave_request_to_dict(item)


@app.get("/leave-requests")
def get_all_leave_requests(request: Request):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    return [
        leave_request_to_dict(item)
        for item in repo.leave_requests()
    ]


@app.post("/leave-requests/{request_id}/status")
def update_leave_request_status(
    request_id: int,
    request: Request,
    status: str = Form(...),
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    status = normalize_input(status)

    if status not in ("承認", "却下"):
        raise HTTPException(
            status_code=400,
            detail="status must be 承認 or 却下",
        )

    existing = next(
        (
            item
            for item in repo.leave_requests()
            if item.request_id == request_id
        ),
        None,
    )

    if existing is None:
        raise HTTPException(
            status_code=404,
            detail="leave request not found",
        )

    repo.update_leave_status(request_id, status)

    updated = next(
        item
        for item in repo.leave_requests()
        if item.request_id == request_id
    )

    return leave_request_to_dict(updated)



@app.get("/leave-grants/due")
def get_due_leave_grants(
    request: Request,
    as_of: str,
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    try:
        target_date = date.fromisoformat(normalize_input(as_of))
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="as_of must be YYYY-MM-DD",
        ) from error

    results = []

    for employee in repo.employees():
        candidate = due_leave_grant(
            repo,
            employee,
            target_date,
        )

        if candidate is None:
            continue

        results.append(
            {
                "employee_id": employee.employee_id,
                "name": employee.name,
                "grant_date": candidate.grant_date.isoformat(),
                "days": str(candidate.days),
                "service_months": candidate.service_months,
            }
        )

    return results
