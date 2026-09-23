import webapp.main as main


def test_session_secret_can_be_loaded_from_environment(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")

    assert main.session_secret_from_env() == "test-session-secret"
