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
