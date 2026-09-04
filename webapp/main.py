from fastapi import FastAPI, Form, HTTPException, Response, Request
from fastapi.responses import JSONResponse
from itsdangerous import URLSafeSerializer, BadSignature
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from services.storage_service import PayrollRepository
from services.auth_service import verify_password
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from decimal import Decimal
from models.employee import Employee
from models.shifts import Shift

app = FastAPI(title="Salary Calculator Web")
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
    name = name.strip()

    if not employee_id or not name:
        raise HTTPException(
            status_code=400,
            detail="employee_id and name are required",
        )

    if any(e.employee_id == employee_id for e in repo.employees()):
        raise HTTPException(
            status_code=409,
            detail="employee_id already exists",
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
        employee = Employee(
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