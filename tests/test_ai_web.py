from fastapi.testclient import TestClient

import webapp.main as main
from models.user import User
from services.storage_service import PayrollRepository


class FakeAssistant:
    def chat(self, message: str) -> str:
        assert message == "今月の給与について教えて"
        return "給与についての回答です。"


def test_admin_can_chat_with_ai_assistant(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)
    monkeypatch.setattr(main, "ai_assistant", FakeAssistant())

    test_repo.save_user(
        User(
            username="admin",
            password_hash="unused",
            role="admin",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/ai/chat",
        data={"message": "今月の給与について教えて"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "給与についての回答です。",
    }
