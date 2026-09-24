import webapp.main as main


def test_session_secret_can_be_loaded_from_environment(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")

    assert main.session_secret_from_env() == "test-session-secret"


def test_empty_session_secret_uses_development_fallback(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "")

    assert main.session_secret_from_env() == "dev-secret-change-me"


def test_secure_session_cookie_can_be_enabled_from_environment(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")

    assert main.session_cookie_secure_from_env() is True


def test_inactive_user_existing_session_is_rejected(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from models.user import User
    from services.storage_service import PayrollRepository

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="disabled-user",
            password_hash="unused",
            role="admin",
            active=False,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "disabled-user"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get("/me")

    assert response.status_code == 401


def test_cors_origins_can_include_configured_frontend(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://salary.example.com")

    assert main.cors_origins_from_env() == [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "https://salary.example.com",
    ]


def test_session_cookie_samesite_can_be_configured_for_cross_site(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "none")

    assert main.session_cookie_samesite_from_env() == "none"


def test_logout_deletes_cookie_with_configured_security_attributes(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "none")

    client = TestClient(main.app)
    response = client.post("/logout")

    cookie = response.headers["set-cookie"].lower()
    assert "salary_session=" in cookie
    assert "secure" in cookie
    assert "samesite=none" in cookie
