from fastapi import FastAPI, Form, HTTPException, Response, Request
from fastapi.responses import JSONResponse
from itsdangerous import URLSafeSerializer, BadSignature

from services.storage_service import PayrollRepository
from services.auth_service import verify_password
from pathlib import Path

app = FastAPI(title="Salary Calculator Web")

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


@app.get("/")
def health():
    return {"status": "ok"}


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