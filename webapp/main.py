from fastapi import FastAPI, Form, HTTPException, Response, Request
from fastapi.responses import JSONResponse
from itsdangerous import URLSafeSerializer, BadSignature
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from services.storage_service import PayrollRepository
from services.auth_service import verify_password
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

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