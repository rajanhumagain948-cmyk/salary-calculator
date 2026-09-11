from fastapi.testclient import TestClient

import webapp.main as main
from models.user import User
from services.storage_service import PayrollRepository


def test_admin_cannot_use_employee_ai(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

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
        "/my/ai/chat",
        data={"message": "今月の給与を教えて"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "employee only"


def test_employee_ai_requires_employee_id(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="employee",
            password_hash="unused",
            role="employee",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/my/ai/chat",
        data={"message": "今月の給与を教えて"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "employee_id not set"


def test_employee_ai_calls_assistant_for_employee(tmp_path, monkeypatch):
    from datetime import date
    from models.employee import Employee

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    captured = {}

    class CapturingAssistant:
        def chat(self, message: str) -> str:
            captured["message"] = message
            return "本人向け回答です。"

    monkeypatch.setattr(main, "ai_assistant", CapturingAssistant())

    test_repo.save_employee(
        Employee(
            employee_id="E001",
            name="山田太郎",
            employment_type="正社員",
            hire_date=date(2025, 1, 1),
            pay_type="月給",
        )
    )
    test_repo.save_user(
        User(
            username="employee",
            password_hash="unused",
            role="employee",
            employee_id="E001",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/my/ai/chat",
        data={"message": "自分の情報を教えて"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "本人向け回答です。"
    assert "対象従業員: 山田太郎 (E001)" in captured["message"]
