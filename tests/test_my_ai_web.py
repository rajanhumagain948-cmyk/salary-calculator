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
