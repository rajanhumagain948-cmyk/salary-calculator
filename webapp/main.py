import json
import os
import unicodedata
import tempfile
import calendar
from urllib.error import URLError
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
from models.leave_grant import LeaveGrant
from models.shifts import Shift
from models.work_record import WorkRecord
from models.allowance import Allowance
from models.deduction import OtherDeduction
from models.transportation import Transportation
from services.payroll_service import calculate_payroll
from services.payroll_batch_service import calculate_monthly_payrolls
from services.payroll_auto_service import run_payroll_auto_check
from services.leave_service import (
    calculate_leave_balance,
    due_leave_grant,
    has_overlapping_leave_request,
    hourly_leave_days,
    validate_hourly_annual_limit,
    validate_hourly_leave_request,
    leave_grant_expiry_date,
    leave_request_days,
    next_leave_grant,
)
from services.payslip_service import export_pdf
from services.prediction_service import (
    build_attendance_review,
    build_overtime_forecast,
    build_payroll_estimate,
    build_leave_trend,
    build_payroll_processing_risk,
    summarize_payroll_estimates,
)
from services.time_service import format_minutes
from services.ai_service import OllamaAssistant
from services.ai_context_service import (
    build_ai_monthly_summary,
    build_employee_attendance_summary,
    build_employee_payroll_summary,
    build_payroll_review_items,
    build_pending_leave_review_items,
    find_referenced_employee,
    find_referenced_employee_candidates,
    find_referenced_employee_from_history,
)

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
ai_assistant = OllamaAssistant.from_env()


def session_secret_from_env() -> str:
    return os.getenv("SESSION_SECRET") or "dev-secret-change-me"


serializer = URLSafeSerializer(session_secret_from_env(), salt="session")

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


@app.get("/predictions/payroll-risk")
def payroll_risk_predictions(
    request: Request,
    year_month: str,
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    year_month = normalize_input(year_month)

    try:
        parsed_year_month = datetime.strptime(year_month, "%Y-%m")
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="year_month must be YYYY-MM",
        ) from error

    if parsed_year_month.strftime("%Y-%m") != year_month:
        raise HTTPException(
            status_code=400,
            detail="year_month must be YYYY-MM",
        )

    employee_names = {
        employee.employee_id: employee.name
        for employee in repo.employees()
    }
    items = []

    for payroll in repo.payroll_results(year_month):
        risk = build_payroll_processing_risk(
            warnings=list(payroll.warnings),
            blocking_issues=list(payroll.blocking_issues),
        )
        if risk["level"] == "none":
            continue

        items.append(
            {
                "employee_id": payroll.employee_id,
                "employee_name": employee_names.get(
                    payroll.employee_id,
                    payroll.employee_id,
                ),
                **risk,
            }
        )

    return {"items": items}


@app.get("/predictions/leave-trend")
def leave_trend_predictions(
    request: Request,
    year: str,
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    year = normalize_input(year)
    if len(year) != 4 or not year.isdigit():
        raise HTTPException(
            status_code=400,
            detail="year must be YYYY",
        )

    items = []

    for employee in repo.employees():
        trend = build_leave_trend(
            requests=repo.leave_requests(employee.employee_id),
            year=int(year),
            standard_daily_minutes=repo.terms(
                employee.employee_id
            ).standard_daily_minutes,
        )

        items.append(
            {
                "employee_id": employee.employee_id,
                "employee_name": employee.name,
                "approved_request_count": trend["approved_request_count"],
                "approved_days": str(trend["approved_days"]),
                "monthly_approved_days": {
                    key: str(value)
                    for key, value in trend["monthly_approved_days"].items()
                },
            }
        )

    return {"items": items}


@app.get("/predictions/payroll-estimate")
def payroll_estimate_predictions(
    request: Request,
    year_month: str,
    as_of: str,
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    year_month = normalize_input(year_month)

    try:
        parsed_year_month = datetime.strptime(year_month, "%Y-%m")
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="year_month must be YYYY-MM",
        ) from error

    if parsed_year_month.strftime("%Y-%m") != year_month:
        raise HTTPException(
            status_code=400,
            detail="year_month must be YYYY-MM",
        )

    try:
        parsed_as_of = date.fromisoformat(normalize_input(as_of))
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="as_of must be YYYY-MM-DD",
        ) from error

    if parsed_as_of.strftime("%Y-%m") != year_month:
        raise HTTPException(
            status_code=400,
            detail="as_of must be within year_month",
        )

    items = []

    for employee in repo.employees():
        existing = repo.payroll_result(
            employee.employee_id,
            year_month,
        )
        if existing is not None and existing.finalized:
            items.append(
                {
                    "employee_id": employee.employee_id,
                    "employee_name": employee.name,
                    "status": "確定済",
                    "reference_only": True,
                    "used_for_payroll": False,
                    "gross_pay": str(existing.gross_pay),
                    "total_deductions": str(existing.total_deductions),
                    "net_pay": str(existing.net_pay),
                    "warnings": list(existing.warnings),
                    "blocking_issues": list(existing.blocking_issues),
                }
            )
            continue

        try:
            records = repo.work_records(
                employee.employee_id,
                year_month,
            )
            allowances, deductions, transport = repo.monthly_inputs(
                employee.employee_id,
                year_month,
            )
            estimate = build_payroll_estimate(
                employee=employee,
                terms=repo.terms(employee.employee_id),
                records=records,
                allowances=allowances,
                transport=transport,
                other_deductions=deductions,
                year_month=year_month,
                as_of=parsed_as_of,
            )
        except (ValueError, TypeError) as error:
            items.append(
                {
                    "employee_id": employee.employee_id,
                    "employee_name": employee.name,
                    "status": "計算不可",
                    "error": str(error),
                }
            )
            continue

        items.append(
            {
                "employee_id": employee.employee_id,
                "employee_name": employee.name,
                "status": "参考試算",
                **estimate,
            }
        )

    return {
        "reference_only": True,
        "used_for_payroll": False,
        "includes_future_work": False,
        "method": (
            "基準日までの実績勤怠と現在入力済みの給与条件による参考試算"
        ),
        "summary": summarize_payroll_estimates(items),
        "items": items,
    }


@app.get("/predictions/attendance-review")
def attendance_review_predictions(
    request: Request,
    year_month: str,
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    year_month = normalize_input(year_month)

    try:
        parsed_year_month = datetime.strptime(year_month, "%Y-%m")
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="year_month must be YYYY-MM",
        ) from error

    if parsed_year_month.strftime("%Y-%m") != year_month:
        raise HTTPException(
            status_code=400,
            detail="year_month must be YYYY-MM",
        )

    items = []

    for employee in repo.employees():
        review = build_attendance_review(
            records=repo.work_records(
                employee.employee_id,
                year_month,
            ),
        )
        if review["warning_count"] == 0:
            continue

        items.append(
            {
                "employee_id": employee.employee_id,
                "employee_name": employee.name,
                **review,
            }
        )

    return {"items": items}


@app.get("/predictions/overtime")
def overtime_predictions(
    request: Request,
    year_month: str,
    as_of: str,
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    year_month = normalize_input(year_month)

    try:
        parsed_year_month = datetime.strptime(year_month, "%Y-%m")
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="year_month must be YYYY-MM",
        ) from error

    if parsed_year_month.strftime("%Y-%m") != year_month:
        raise HTTPException(
            status_code=400,
            detail="year_month must be YYYY-MM",
        )

    try:
        parsed_as_of = date.fromisoformat(normalize_input(as_of))
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="as_of must be YYYY-MM-DD",
        ) from error

    if parsed_as_of.strftime("%Y-%m") != year_month:
        raise HTTPException(
            status_code=400,
            detail="as_of must be within year_month",
        )

    items = []

    for employee in repo.employees():
        forecast = build_overtime_forecast(
            records=repo.work_records(
                employee.employee_id,
                year_month,
            ),
            terms=repo.terms(employee.employee_id),
            shifts=repo.shifts(
                employee.employee_id,
                year_month,
            ),
            as_of=parsed_as_of,
        )
        items.append(
            {
                "employee_id": employee.employee_id,
                "employee_name": employee.name,
                **forecast,
            }
        )

    return {
        "reference_only": True,
        "used_for_payroll": False,
        "method": (
            "実績勤務日1日あたりの平均残業時間を、"
            "基準日より後の確定シフト日数へ外挿"
        ),
        "items": items,
    }


@app.get("/ai/status")
def ai_status(request: Request):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    base_url = ai_assistant.base_url

    return {
        "model": ai_assistant.model,
        "local": (
            base_url.startswith("http://localhost:")
            or base_url.startswith("http://127.0.0.1:")
        ),
        "available": ai_assistant.is_available(),
    }


@app.get("/my/ai/status")
def my_ai_status(request: Request):
    user = require_user(request)

    if user.role != "employee":
        raise HTTPException(status_code=403, detail="employee only")

    if not user.employee_id:
        raise HTTPException(status_code=400, detail="employee_id not set")

    base_url = ai_assistant.base_url

    return {
        "model": ai_assistant.model,
        "local": (
            base_url.startswith("http://localhost:")
            or base_url.startswith("http://127.0.0.1:")
        ),
        "available": ai_assistant.is_available(),
    }


@app.post("/my/ai/chat")
def my_ai_chat(
    request: Request,
    message: str = Form(...),
    year_month: str | None = Form(None),
    history: str | None = Form(None),
):
    user = require_user(request)

    if user.role != "employee":
        raise HTTPException(status_code=403, detail="employee only")

    if not user.employee_id:
        raise HTTPException(status_code=400, detail="employee_id not set")

    message = normalize_input(message)
    if not message:
        raise HTTPException(
            status_code=400,
            detail="message is required",
        )

    if len(message) > 2000:
        raise HTTPException(
            status_code=400,
            detail="message must be 2000 characters or fewer",
        )

    conversation = []

    if history:
        try:
            parsed_history = json.loads(history)
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=400,
                detail="invalid AI chat history",
            ) from error

        if not isinstance(parsed_history, list) or len(parsed_history) > 20:
            raise HTTPException(
                status_code=400,
                detail="invalid AI chat history",
            )

        for item in parsed_history:
            if (
                not isinstance(item, dict)
                or item.get("role") not in ("user", "assistant")
                or not isinstance(item.get("content"), str)
                or not item["content"].strip()
                or len(item["content"].strip()) > 2000
            ):
                raise HTTPException(
                    status_code=400,
                    detail="invalid AI chat history",
                )

            conversation.append(
                {
                    "role": item["role"],
                    "content": item["content"].strip(),
                }
            )

    if year_month:
        year_month = normalize_input(year_month)

        try:
            parsed_year_month = datetime.strptime(
                year_month,
                "%Y-%m",
            )
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail="year_month must be YYYY-MM",
            ) from error

        if parsed_year_month.strftime("%Y-%m") != year_month:
            raise HTTPException(
                status_code=400,
                detail="year_month must be YYYY-MM",
            )

    employee_id = normalize_input(user.employee_id)
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

    attendance_context = ""
    payroll_context = ""
    leave_context = ""
    sources = []

    if year_month:
        sources.extend(
            [
                "本人の勤怠",
                "本人の有給残数",
            ]
        )

        attendance = build_employee_attendance_summary(
            employee_id=employee.employee_id,
            employee_name=employee.name,
            year_month=year_month,
            records=repo.work_records(
                employee.employee_id,
                year_month,
            ),
        )
        attendance_context = (
            f"対象月: {year_month}\n"
            f"勤怠記録件数: {attendance['record_count']}\n"
            f"出勤日数: {attendance['attendance_days']}\n"
        )

        year = parsed_year_month.year
        month = parsed_year_month.month
        month_end = date(
            year,
            month,
            calendar.monthrange(year, month)[1],
        )
        leave_balance = calculate_leave_balance(
            repo,
            employee.employee_id,
            month_end,
        )
        try:
            next_grant = next_leave_grant(
                employee,
                month_end,
            )
        except ValueError:
            next_grant = None

        pending_leave_requests = [
            item
            for item in repo.leave_requests(employee.employee_id)
            if item.status == "申請中"
            and item.leave_date.strftime("%Y-%m") == year_month
        ]
        if pending_leave_requests:
            pending_leave_lines = ["申請中の有給:"]
            for item in pending_leave_requests:
                pending_leave_lines.append(
                    f"- {item.leave_date.isoformat()} | {item.leave_unit}"
                )
            pending_leave_context = "\n".join(pending_leave_lines) + "\n"
        else:
            pending_leave_context = "申請中の有給: なし\n"

        leave_context = (
            f"有給残日数: {leave_balance.remaining_days}\n"
            f"有給申請中日数: {leave_balance.pending_days}\n"
            f"有給申請可能日数: {leave_balance.available_days}\n"
            + pending_leave_context
            + (
                f"次回有給付与予定日: {next_grant.grant_date.isoformat()}\n"
                f"次回有給付与予定日数: {next_grant.days}\n"
                "実際の付与にはadminによる要件確認が必要です。\n"
                if next_grant is not None
                else "次回有給付与予定: 勤務条件未設定のため算出不可\n"
            )
        )

        payroll = repo.payroll_result(
            employee.employee_id,
            year_month,
        )
        if payroll is not None and not payroll.finalized:
            payroll_context = "未確定給与は参照できません。\n"
        elif payroll is not None and payroll.finalized:
            sources.insert(1, "本人の給与明細")
            payroll_status = build_employee_payroll_summary(
                employee_id=employee.employee_id,
                year_month=year_month,
                payroll=payroll,
            )
            payment_details = " / ".join(
                f"{name}={amount}円"
                for name, amount in payroll_status["payments"].items()
            ) or "なし"
            deduction_details = " / ".join(
                f"{name}={amount}円"
                for name, amount in payroll_status["deductions"].items()
            ) or "なし"

            payroll_context = (
                "給与確定済み: はい\n"
                f"総支給: {payroll_status['gross_pay']}円\n"
                f"控除合計: {payroll_status['total_deductions']}円\n"
                f"手取り: {payroll_status['net_pay']}円\n"
                f"支給内訳: {payment_details}\n"
                f"控除内訳: {deduction_details}\n"
                "所定内時間: "
                f"{format_minutes(payroll_status['regular_minutes'])}\n"
                "時間外: "
                f"{format_minutes(payroll_status['overtime_minutes'])}\n"
                "深夜: "
                f"{format_minutes(payroll_status['night_minutes'])}\n"
                "休日: "
                f"{format_minutes(payroll_status['holiday_minutes'])}\n"
                "月60時間超: "
                f"{format_minutes(payroll_status['overtime_over_60_minutes'])}\n"
            )

    prompt = (
        "以下はログイン中の従業員本人向けの読み取り専用AIです。\n"
        "回答ルール:\n"
        "- ログイン中の従業員本人の情報だけを回答してください。\n"
        "- 他の従業員の情報を推測・回答しないでください。\n"
        "- 提供されていない事実を推測で作らないでください。\n"
        "- 不明な情報は不明と明示してください。\n"
        "- 未確定給与は従業員には開示しないでください。\n"
        "- 給与確定・勤怠修正・有給申請などの変更操作を"
        "AI自身が実行できるとは説明しないでください。\n"
        f"対象従業員: {employee.name} ({employee.employee_id})\n"
        f"{attendance_context}"
        f"{payroll_context}"
        f"{leave_context}"
        f"質問: {message}"
    )

    conversation.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    try:
        if history:
            answer = ai_assistant.chat_messages(conversation)
        else:
            answer = ai_assistant.chat(prompt)
    except (ConnectionError, TimeoutError, URLError) as error:
        repo.audit(
            "従業員AIアシスタント利用",
            user.username,
            f"対象月={year_month or '未指定'} 結果=失敗",
        )
        raise HTTPException(
            status_code=503,
            detail="AIアシスタントに接続できません。",
        ) from error

    repo.audit(
        "従業員AIアシスタント利用",
        user.username,
        f"対象月={year_month or '未指定'} 結果=成功",
    )

    return {
        "answer": answer,
        "sources": sources,
    }


@app.post("/ai/chat")
def ai_chat(
    request: Request,
    message: str = Form(...),
    year_month: str | None = Form(None),
    history: str | None = Form(None),
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    message = normalize_input(message)
    if not message:
        raise HTTPException(
            status_code=400,
            detail="message is required",
        )

    if len(message) > 2000:
        raise HTTPException(
            status_code=400,
            detail="message must be 2000 characters or fewer",
        )

    conversation = []

    if history:
        try:
            parsed_history = json.loads(history)
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=400,
                detail="invalid AI chat history",
            ) from error

        if not isinstance(parsed_history, list) or len(parsed_history) > 20:
            raise HTTPException(
                status_code=400,
                detail="invalid AI chat history",
            )

        for item in parsed_history:
            if (
                not isinstance(item, dict)
                or item.get("role") not in ("user", "assistant")
                or not isinstance(item.get("content"), str)
                or not item["content"].strip()
                or len(item["content"].strip()) > 2000
            ):
                raise HTTPException(
                    status_code=400,
                    detail="invalid AI chat history",
                )

            conversation.append(
                {
                    "role": item["role"],
                    "content": item["content"].strip(),
                }
            )

    prompt = message
    sources = []

    if year_month:
        year_month = normalize_input(year_month)

        try:
            parsed_year_month = datetime.strptime(
                year_month,
                "%Y-%m",
            )
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail="year_month must be YYYY-MM",
            ) from error

        if parsed_year_month.strftime("%Y-%m") != year_month:
            raise HTTPException(
                status_code=400,
                detail="year_month must be YYYY-MM",
            )

        sources = [
            "月次給与状況",
            "給与要確認",
            "有給承認待ち",
        ]

        employees = repo.employees()

        payrolls = repo.payroll_results(year_month)

        leave_requests = repo.leave_requests()

        summary = build_ai_monthly_summary(
            year_month=year_month,
            employee_count=len(employees),
            payrolls=payrolls,
            leave_requests=leave_requests,
        )

        employee_names = {
            employee.employee_id: employee.name
            for employee in employees
        }
        review_items = build_payroll_review_items(
            payrolls,
            employee_names=employee_names,
        )

        pending_leave_items = build_pending_leave_review_items(
            leave_requests,
            year_month=year_month,
            employee_names=employee_names,
        )

        if pending_leave_items:
            leave_lines = ["有給承認待ち:"]
            for item in pending_leave_items:
                leave_lines.append(
                    f"- {item['employee_id']} / {item['employee_name']} | "
                    f"{item['leave_date']} | {item['leave_unit']}"
                )
            leave_context = "\n".join(leave_lines) + "\n"
        else:
            leave_context = "有給承認待ち: なし\n"

        if review_items:
            review_lines = ["給与要確認従業員:"]
            for item in review_items:
                warnings = " / ".join(item["warnings"]) or "なし"
                blocking = (
                    " / ".join(item["blocking_issues"]) or "なし"
                )
                review_lines.append(
                    f"- {item['employee_id']} / {item['employee_name']} | "
                    f"warning: {warnings} | "
                    f"blocking issue: {blocking}"
                )
            review_context = "\n".join(review_lines) + "\n"
        else:
            review_context = "給与要確認従業員: なし\n"

        employee_candidates = find_referenced_employee_candidates(
            message,
            employees,
        )

        if len(employee_candidates) > 1:
            names = {item.name for item in employee_candidates}

            if len(names) == 1:
                employee_name = employee_candidates[0].name
                employee_ids = " または ".join(
                    item.employee_id
                    for item in employee_candidates
                )

                return {
                    "answer": (
                        f"「{employee_name}」に一致する従業員が複数います。"
                        f"社員番号 {employee_ids} を指定してください。"
                    ),
                    "sources": [],
                }

        referenced_employee = find_referenced_employee(
            message,
            employees,
        )

        if (
            referenced_employee is None
            and not employee_candidates
            and conversation
        ):
            referenced_employee = find_referenced_employee_from_history(
                conversation,
                employees,
            )

        employee_context = ""

        if referenced_employee is not None:
            sources.extend(
                [
                    "対象従業員の勤怠",
                    "対象従業員の給与結果",
                    "対象従業員の有給残数",
                ]
            )

            attendance = build_employee_attendance_summary(
                employee_id=referenced_employee.employee_id,
                employee_name=referenced_employee.name,
                year_month=year_month,
                records=repo.work_records(
                    referenced_employee.employee_id,
                    year_month,
                ),
            )

            employee_payroll = next(
                (
                    item
                    for item in payrolls
                    if item.employee_id == referenced_employee.employee_id
                ),
                None,
            )

            payroll_status = build_employee_payroll_summary(
                employee_id=referenced_employee.employee_id,
                year_month=year_month,
                payroll=employee_payroll,
            )

            year = parsed_year_month.year
            month = parsed_year_month.month
            month_end = date(
                year,
                month,
                calendar.monthrange(year, month)[1],
            )
            leave_balance = calculate_leave_balance(
                repo,
                referenced_employee.employee_id,
                month_end,
            )
            try:
                next_grant = next_leave_grant(
                    referenced_employee,
                    month_end,
                )
            except ValueError:
                next_grant = None

            warning_details = " / ".join(
                payroll_status["warnings"]
            ) or "なし"
            blocking_details = " / ".join(
                payroll_status["blocking_issues"]
            ) or "なし"

            if payroll_status["calculated"]:
                payment_details = " / ".join(
                    f"{name}={amount}円"
                    for name, amount in payroll_status["payments"].items()
                ) or "なし"
                deduction_details = " / ".join(
                    f"{name}={amount}円"
                    for name, amount in payroll_status["deductions"].items()
                ) or "なし"

                payroll_amount_context = (
                    f"総支給: {payroll_status['gross_pay']}円\n"
                    f"控除合計: {payroll_status['total_deductions']}円\n"
                    f"手取り: {payroll_status['net_pay']}円\n"
                    f"支給内訳: {payment_details}\n"
                    f"控除内訳: {deduction_details}\n"
                )
                attendance_time_context = (
                    "所定内時間: "
                    f"{format_minutes(payroll_status['regular_minutes'])}\n"
                    "時間外: "
                    f"{format_minutes(payroll_status['overtime_minutes'])}\n"
                    "深夜: "
                    f"{format_minutes(payroll_status['night_minutes'])}\n"
                    "休日: "
                    f"{format_minutes(payroll_status['holiday_minutes'])}\n"
                    "月60時間超: "
                    f"{format_minutes(payroll_status['overtime_over_60_minutes'])}\n"
                )
            else:
                payroll_amount_context = ""
                attendance_time_context = ""

            employee_context = (
                "\n"
                f"対象従業員: {attendance['employee_name']} "
                f"({attendance['employee_id']})\n"
                f"勤怠記録件数: {attendance['record_count']}\n"
                f"出勤日数: {attendance['attendance_days']}\n"
                f"給与計算済み: "
                f"{'はい' if payroll_status['calculated'] else 'いいえ'}\n"
                f"給与確定済み: "
                f"{'はい' if payroll_status['finalized'] else 'いいえ'}\n"
                f"給与warning件数: {payroll_status['warning_count']}\n"
                f"給与warning内容: {warning_details}\n"
                f"給与blocking issue件数: "
                f"{payroll_status['blocking_issue_count']}\n"
                f"給与blocking issue内容: {blocking_details}\n"
                f"{payroll_amount_context}"
                f"{attendance_time_context}"
                "給与warningは給与計算結果の警告であり、勤怠警告とは限りません。\n"
                f"有給残日数: {leave_balance.remaining_days}\n"
                f"有給申請中日数: {leave_balance.pending_days}\n"
                f"有給申請可能日数: {leave_balance.available_days}\n"
                + (
                    f"次回有給付与予定日: {next_grant.grant_date.isoformat()}\n"
                    f"次回有給付与予定日数: {next_grant.days}\n"
                    "実際の付与にはadminによる要件確認が必要です。\n"
                    if next_grant is not None
                    else "次回有給付与予定: 勤務条件未設定のため算出不可\n"
                )
            )

        prompt = (
            "以下は給与管理システムの読み取り専用月次サマリーです。\n"
            "回答ルール:\n"
            "- 提供されていない事実・従業員・制度を推測で作らないでください。\n"
            "- 不明な情報は不明と明示してください。\n"
            "- このシステムでは確定済み給与は保護されています。"
            "確定済み給与の再計算・再確定を提案しないでください。\n"
            "- 給与確定・勤怠修正・有給承認などの変更操作を"
            "AI自身が実行できるとは説明しないでください。\n"
            f"対象月: {summary['year_month']}\n"
            f"従業員数: {summary['employee_count']}\n"
            f"給与計算済み件数: {summary['calculated_payroll_count']}\n"
            f"給与確定済み件数: {summary['finalized_payroll_count']}\n"
            f"給与確定不可件数: {summary['blocked_payroll_count']}\n"
            f"有給申請中件数: {summary['pending_leave_count']}\n"
            f"{review_context}"
            f"{leave_context}"
            f"{employee_context}"
            "\n"
            f"質問: {message}"
        )

    conversation.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    try:
        if history:
            answer = ai_assistant.chat_messages(conversation)
        else:
            answer = ai_assistant.chat(prompt)
    except (ConnectionError, TimeoutError, URLError) as error:
        repo.audit(
            "AIアシスタント利用",
            user.username,
            f"対象月={year_month or '未指定'} 結果=失敗",
        )
        raise HTTPException(
            status_code=503,
            detail="AIアシスタントに接続できません。",
        ) from error

    repo.audit(
        "AIアシスタント利用",
        user.username,
        f"対象月={year_month or '未指定'} 結果=成功",
    )

    return {
        "answer": answer,
        "sources": sources,
    }


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
        "hourly_paid_leave_enabled": company.hourly_paid_leave_enabled,
        "hourly_paid_leave_unit_hours": company.hourly_paid_leave_unit_hours,
        "hourly_paid_leave_year_start_month": company.hourly_paid_leave_year_start_month,
        "hourly_paid_leave_year_start_day": company.hourly_paid_leave_year_start_day,
    }


@app.put("/company")
def update_company(
    request: Request,
    name: str = Form(...),
    address: str = Form(""),
    representative: str = Form(""),
    hourly_paid_leave_enabled: str | None = Form(None),
    hourly_paid_leave_unit_hours: str | None = Form(None),
    hourly_paid_leave_year_start_month: str | None = Form(None),
    hourly_paid_leave_year_start_day: str | None = Form(None),
):
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="company name is required")

    current_company = repo.company()

    if hourly_paid_leave_enabled is None:
        hourly_enabled = current_company.hourly_paid_leave_enabled
    else:
        hourly_enabled = normalize_input(
            hourly_paid_leave_enabled
        ).lower() in ("1", "true", "on", "yes")

    if hourly_paid_leave_unit_hours is None:
        hourly_unit = current_company.hourly_paid_leave_unit_hours
    else:
        try:
            hourly_unit = int(
                normalize_input(hourly_paid_leave_unit_hours)
            )
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail="hourly_paid_leave_unit_hours must be an integer",
            ) from error

        if hourly_unit <= 0:
            raise HTTPException(
                status_code=400,
                detail="hourly_paid_leave_unit_hours must be greater than 0",
            )

    if hourly_paid_leave_year_start_month is None:
        year_start_month = (
            current_company.hourly_paid_leave_year_start_month
        )
    else:
        try:
            year_start_month = int(
                normalize_input(hourly_paid_leave_year_start_month)
            )
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail="時間単位年休の年度開始月が不正です。",
            ) from error

    if hourly_paid_leave_year_start_day is None:
        year_start_day = (
            current_company.hourly_paid_leave_year_start_day
        )
    else:
        try:
            year_start_day = int(
                normalize_input(hourly_paid_leave_year_start_day)
            )
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail="時間単位年休の年度開始日が不正です。",
            ) from error

    try:
        date(2026, year_start_month, year_start_day)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="時間単位年休の年度開始月日が不正です。",
        ) from error

    company = Company(
        name=name,
        address=address.strip(),
        representative=representative.strip(),
        hourly_paid_leave_enabled=hourly_enabled,
        hourly_paid_leave_unit_hours=hourly_unit,
        hourly_paid_leave_year_start_month=year_start_month,
        hourly_paid_leave_year_start_day=year_start_day,
    )
    repo.save_company(company)

    return {
        "ok": True,
        "company": {
            "name": company.name,
            "address": company.address,
            "representative": company.representative,
            "hourly_paid_leave_enabled": company.hourly_paid_leave_enabled,
            "hourly_paid_leave_unit_hours": company.hourly_paid_leave_unit_hours,
            "hourly_paid_leave_year_start_month": company.hourly_paid_leave_year_start_month,
            "hourly_paid_leave_year_start_day": company.hourly_paid_leave_year_start_day,
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
        "leave_unit": item.leave_unit,
        "half_day_period": item.half_day_period,
        "start_minute": item.start_minute,
        "end_minute": item.end_minute,
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
    leave_unit: str = Form("全日"),
    half_day_period: str = Form(""),
    start_time: str = Form(""),
    end_time: str = Form(""),
):
    user = require_user(request)

    if user.role != "employee":
        raise HTTPException(status_code=403, detail="employee only")

    if not user.employee_id:
        raise HTTPException(status_code=400, detail="employee_id not set")

    employee_id = normalize_input(user.employee_id)
    leave_unit = normalize_input(leave_unit)
    half_day_period = normalize_input(half_day_period)
    reason = normalize_input(reason)

    try:
        parsed_date = date.fromisoformat(normalize_input(leave_date))
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="leave_date must be YYYY-MM-DD",
        ) from error

    if leave_unit not in ("全日", "半日", "時間"):
        raise HTTPException(status_code=400, detail="不正な取得単位です。")

    company = repo.company()
    terms = repo.terms(employee_id)

    start_minute = None
    end_minute = None

    if leave_unit == "半日":
        if half_day_period not in ("午前", "午後"):
            raise HTTPException(
                status_code=400,
                detail="半日有給は午前または午後を指定してください。",
            )

    elif leave_unit == "時間":
        if not company.hourly_paid_leave_enabled:
            raise HTTPException(
                status_code=409,
                detail="会社で時間単位年休が有効になっていません。",
            )

        def parse_time(value: str) -> int:
            try:
                hour, minute = normalize_input(value).split(":")
                h = int(hour)
                m = int(minute)
                if not (0 <= h <= 23 and 0 <= m <= 59):
                    raise ValueError
                return h * 60 + m
            except (ValueError, TypeError) as error:
                raise HTTPException(
                    status_code=400,
                    detail="時刻はHH:MM形式で指定してください。",
                ) from error

        start_minute = parse_time(start_time)
        end_minute = parse_time(end_time)

        try:
            requested_hours = validate_hourly_leave_request(
                start_minute=start_minute,
                end_minute=end_minute,
                unit_hours=company.hourly_paid_leave_unit_hours,
                standard_daily_minutes=terms.standard_daily_minutes,
            )

            validate_hourly_annual_limit(
                repo.leave_requests(employee_id),
                requested_hours=requested_hours,
                standard_daily_minutes=terms.standard_daily_minutes,
                as_of=parsed_date,
                year_start_month=company.hourly_paid_leave_year_start_month,
                year_start_day=company.hourly_paid_leave_year_start_day,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=409,
                detail=str(error),
            ) from error

    else:
        half_day_period = ""

    if has_overlapping_leave_request(
        repo.leave_requests(employee_id),
        parsed_date,
        leave_unit,
        half_day_period if leave_unit == "半日" else None,
        start_minute,
        end_minute,
    ):
        raise HTTPException(
            status_code=409,
            detail="同じ取得日の有給休暇申請と重複しています。",
        )

    if leave_unit == "全日":
        requested_days = Decimal("1")
    elif leave_unit == "半日":
        requested_days = Decimal("0.5")
    else:
        requested_days = hourly_leave_days(
            requested_hours,
            terms.standard_daily_minutes,
        )

    balance = calculate_leave_balance(
        repo,
        employee_id,
        parsed_date,
    )

    if requested_days > balance.available_days:
        raise HTTPException(
            status_code=409,
            detail="有給休暇の申請可能日数が不足しています。",
        )

    item = repo.save_leave_request(
        LeaveRequest(
            employee_id=employee_id,
            leave_date=parsed_date,
            reason=reason,
            status="申請中",
            leave_unit=leave_unit,
            half_day_period=(
                half_day_period if leave_unit == "半日" else None
            ),
            start_minute=start_minute,
            end_minute=end_minute,
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

    if status == "承認":
        balance = calculate_leave_balance(
            repo,
            existing.employee_id,
            existing.leave_date,
        )

        required_days = leave_request_days(existing)

        if balance.remaining_days < required_days:
            raise HTTPException(
                status_code=409,
                detail="有給休暇の残日数が不足しているため承認できません。",
            )

        if existing.leave_unit == "時間":
            company = repo.company()
            terms = repo.terms(existing.employee_id)

            if (
                existing.start_minute is None
                or existing.end_minute is None
            ):
                raise HTTPException(
                    status_code=409,
                    detail="時間単位年休の時間帯が不正です。",
                )

            requested_hours = (
                existing.end_minute - existing.start_minute
            ) // 60

            other_requests = [
                item
                for item in repo.leave_requests(existing.employee_id)
                if item.request_id != existing.request_id
            ]

            try:
                validate_hourly_annual_limit(
                    other_requests,
                    requested_hours=requested_hours,
                    standard_daily_minutes=terms.standard_daily_minutes,
                    as_of=existing.leave_date,
                    year_start_month=company.hourly_paid_leave_year_start_month,
                    year_start_day=company.hourly_paid_leave_year_start_day,
                )
            except ValueError as error:
                raise HTTPException(
                    status_code=409,
                    detail=str(error),
                ) from error

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



@app.post("/leave-grants/confirm")
def confirm_leave_grant(
    request: Request,
    employee_id: str = Form(...),
    as_of: str = Form(...),
):
    user = require_user(request)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")

    employee_id = normalize_input(employee_id)

    try:
        target_date = date.fromisoformat(normalize_input(as_of))
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="as_of must be YYYY-MM-DD",
        ) from error

    employee = next(
        (
            item
            for item in repo.employees()
            if item.employee_id == employee_id
        ),
        None,
    )

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="employee not found",
        )

    candidate = due_leave_grant(
        repo,
        employee,
        target_date,
    )

    if candidate is None:
        raise HTTPException(
            status_code=409,
            detail="付与対象の有給休暇はありません。",
        )

    grant = repo.save_leave_grant(
        LeaveGrant(
            employee_id=employee.employee_id,
            grant_date=candidate.grant_date,
            granted_days=candidate.days,
            expires_on=leave_grant_expiry_date(
                candidate.grant_date
            ),
        )
    )

    return {
        "grant_id": grant.grant_id,
        "employee_id": grant.employee_id,
        "grant_date": grant.grant_date.isoformat(),
        "granted_days": str(grant.granted_days),
        "expires_on": grant.expires_on.isoformat(),
    }



@app.get("/my/leave-balance")
def get_my_leave_balance(
    request: Request,
    as_of: str,
):
    user = require_user(request)

    if user.role != "employee":
        raise HTTPException(status_code=403, detail="employee only")

    if not user.employee_id:
        raise HTTPException(status_code=400, detail="employee_id not set")

    try:
        target_date = date.fromisoformat(normalize_input(as_of))
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="as_of must be YYYY-MM-DD",
        ) from error

    employee_id = normalize_input(user.employee_id)

    employee = next(
        (
            item
            for item in repo.employees()
            if item.employee_id == employee_id
        ),
        None,
    )

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="employee not found",
        )

    balance = calculate_leave_balance(
        repo,
        employee_id,
        target_date,
    )

    next_grant = next_leave_grant(
        employee,
        target_date,
    )

    return {
        "granted_days": str(balance.granted_days),
        "used_days": str(balance.used_days),
        "pending_days": str(balance.pending_days),
        "remaining_days": str(balance.remaining_days),
        "available_days": str(balance.available_days),
        "next_grant_date": next_grant.grant_date.isoformat(),
        "next_grant_days": str(next_grant.days),
    }
