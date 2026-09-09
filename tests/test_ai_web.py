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


def test_employee_cannot_chat_with_ai_assistant(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)
    monkeypatch.setattr(main, "ai_assistant", FakeAssistant())

    test_repo.save_user(
        User(
            username="employee",
            password_hash="unused",
            role="employee",
            employee_id="E1",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/ai/chat",
        data={"message": "給与について教えて"},
    )

    assert response.status_code == 403


def test_ai_chat_receives_monthly_company_summary(tmp_path, monkeypatch):
    from datetime import date
    from decimal import Decimal

    from models.employee import Employee
    from models.leave_request import LeaveRequest
    from models.payroll import PayrollResult, TimeClassification

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    captured = {}

    class CapturingAssistant:
        def chat(self, message: str) -> str:
            captured["message"] = message
            return "月次状況を回答しました。"

    monkeypatch.setattr(main, "ai_assistant", CapturingAssistant())

    test_repo.save_user(
        User(
            username="admin",
            password_hash="unused",
            role="admin",
        )
    )

    test_repo.save_employee(
        Employee(
            employee_id="E1",
            name="テスト社員",
            employment_type="正社員",
            hire_date=date(2025, 1, 1),
            pay_type="月給",
            monthly_salary=Decimal("200000"),
        )
    )

    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E1",
            year_month="2026-09",
            classification=TimeClassification(),
            finalized=True,
        )
    )

    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 15),
            status="申請中",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/ai/chat",
        data={
            "message": "9月の状況を教えて",
            "year_month": "2026-09",
        },
    )

    assert response.status_code == 200

    prompt = captured["message"]
    assert "2026-09" in prompt
    assert "従業員数: 1" in prompt
    assert "給与計算済み件数: 1" in prompt
    assert "給与確定済み件数: 1" in prompt
    assert "有給申請中件数: 1" in prompt
    assert "9月の状況を教えて" in prompt


def test_ai_chat_rejects_invalid_year_month(tmp_path, monkeypatch):
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
        data={
            "message": "給与状況を教えて",
            "year_month": "abc",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "year_month must be YYYY-MM"


def test_ai_chat_returns_503_when_assistant_is_unavailable(
    tmp_path,
    monkeypatch,
):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    class UnavailableAssistant:
        def chat(self, message: str) -> str:
            raise ConnectionError("Ollama is unavailable")

    monkeypatch.setattr(main, "ai_assistant", UnavailableAssistant())

    test_repo.save_user(
        User(
            username="admin",
            password_hash="unused",
            role="admin",
        )
    )

    client = TestClient(main.app, raise_server_exceptions=False)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/ai/chat",
        data={"message": "給与状況を教えて"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "AIアシスタントに接続できません。"


def test_ai_chat_passes_valid_conversation_history(tmp_path, monkeypatch):
    import json

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    captured = {}

    class ConversationAssistant:
        def chat_messages(self, messages):
            captured["messages"] = messages
            return "続きの回答です。"

    monkeypatch.setattr(main, "ai_assistant", ConversationAssistant())

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

    history = [
        {"role": "user", "content": "9月の状況を教えて"},
        {"role": "assistant", "content": "給与確定は3件です。"},
    ]

    response = client.post(
        "/ai/chat",
        data={
            "message": "その中で問題は？",
            "history": json.dumps(history, ensure_ascii=False),
        },
    )

    assert response.status_code == 200
    assert captured["messages"] == [
        {"role": "user", "content": "9月の状況を教えて"},
        {"role": "assistant", "content": "給与確定は3件です。"},
        {"role": "user", "content": "その中で問題は?"},
    ]
