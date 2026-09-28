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


def test_payroll_db_path_can_be_configured_from_environment(tmp_path, monkeypatch):
    db_path = tmp_path / "persistent" / "payroll.sqlite3"
    monkeypatch.setenv("PAYROLL_DB_PATH", str(db_path))

    assert main.payroll_db_path_from_env() == db_path


def test_bootstrap_admin_creates_missing_user_from_environment(tmp_path, monkeypatch):
    from services.auth_service import verify_password
    from services.storage_service import PayrollRepository

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "demo-admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "demo-password")

    main.bootstrap_admin_from_env(test_repo)

    user = test_repo.user("demo-admin")
    assert user is not None
    assert user.role == "admin"
    assert user.active is True
    assert verify_password("demo-password", user.password_hash)


def test_database_url_from_env_prefers_postgresql_url(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@db.example.com:5432/payroll",
    )

    assert main.database_url_from_env() == (
        "postgresql://user:password@db.example.com:5432/payroll"
    )


def test_auth_repository_uses_postgres_when_database_url_is_configured(monkeypatch):
    sentinel = object()
    captured = {}

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@db.example.com/payroll",
    )

    def fake_factory(database_url):
        captured["database_url"] = database_url
        return sentinel

    result = main.auth_repository_from_env(
        sqlite_repository=object(),
        postgres_factory=fake_factory,
    )

    assert result is sentinel
    assert captured["database_url"] == (
        "postgresql://user:password@db.example.com/payroll"
    )


def test_auth_repository_keeps_sqlite_without_database_url(monkeypatch):
    sqlite_repository = object()
    monkeypatch.delenv("DATABASE_URL", raising=False)

    def unexpected_factory(database_url):
        raise AssertionError("PostgreSQL factory must not be called")

    result = main.auth_repository_from_env(
        sqlite_repository=sqlite_repository,
        postgres_factory=unexpected_factory,
    )

    assert result is sqlite_repository


def test_current_user_uses_auth_repository(monkeypatch):
    from fastapi.testclient import TestClient
    from models.user import User

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@db.example.com/payroll",
    )

    class AuthRepository:
        def user(self, username):
            if username == "postgres-admin":
                return User(
                    username="postgres-admin",
                    password_hash="unused",
                    role="admin",
                    active=True,
                )
            return None

    class BusinessRepository:
        def user(self, username):
            raise AssertionError("business repository must not handle authentication")

    monkeypatch.setattr(main, "auth_repo", AuthRepository(), raising=False)
    monkeypatch.setattr(main, "repo", BusinessRepository())

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "postgres-admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get("/me")

    assert response.status_code == 200
    assert response.json()["username"] == "postgres-admin"


def test_login_uses_auth_repository_when_database_url_is_configured(monkeypatch):
    from fastapi.testclient import TestClient
    from models.user import User
    from services.auth_service import hash_password

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@db.example.com/payroll",
    )

    class AuthRepository:
        def user(self, username):
            if username == "postgres-admin":
                return User(
                    username="postgres-admin",
                    password_hash=hash_password("secret-password"),
                    role="admin",
                    active=True,
                )
            return None

    class BusinessRepository:
        def user(self, username):
            raise AssertionError("business repository must not handle login")

    monkeypatch.setattr(main, "auth_repo", AuthRepository())
    monkeypatch.setattr(main, "repo", BusinessRepository())

    client = TestClient(main.app)
    response = client.post(
        "/login",
        data={
            "username": "postgres-admin",
            "password": "secret-password",
        },
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_lifespan_bootstraps_admin_into_auth_repository(monkeypatch):
    from fastapi.testclient import TestClient

    captured = {}

    def fake_bootstrap(repository):
        captured["repository"] = repository

    class AuthRepository:
        pass

    auth_repository = AuthRepository()

    monkeypatch.setattr(main, "auth_repo", auth_repository)
    monkeypatch.setattr(main, "bootstrap_admin_from_env", fake_bootstrap)
    monkeypatch.setattr(main, "run_payroll_auto_check", lambda repository: None)

    with TestClient(main.app):
        pass

    assert captured["repository"] is auth_repository


def test_login_ui_uses_auth_repository_when_database_url_is_configured(monkeypatch):
    from fastapi.testclient import TestClient
    from models.user import User
    from services.auth_service import hash_password

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@db.example.com/payroll",
    )

    class AuthRepository:
        def user(self, username):
            if username == "postgres-admin":
                return User(
                    username="postgres-admin",
                    password_hash=hash_password("secret-password"),
                    role="admin",
                    active=True,
                )
            return None

    class BusinessRepository:
        def user(self, username):
            raise AssertionError("business repository must not handle UI login")

    monkeypatch.setattr(main, "auth_repo", AuthRepository())
    monkeypatch.setattr(main, "repo", BusinessRepository())

    client = TestClient(main.app, follow_redirects=False)
    response = client.post(
        "/login-ui",
        data={
            "username": "postgres-admin",
            "password": "secret-password",
        },
    )

    assert response.status_code == 303
