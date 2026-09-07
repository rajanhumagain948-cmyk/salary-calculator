from datetime import date

from fastapi.testclient import TestClient

import webapp.main as main
from models.leave_request import LeaveRequest
from models.user import User
from services.storage_service import PayrollRepository


def test_employee_can_list_only_own_leave_requests(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="employee",
            password_hash="unused",
            role="employee",
            employee_id="E1",
        )
    )

    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 15),
            reason="私用",
        )
    )

    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E2",
            leave_date=date(2026, 9, 16),
            reason="他人の申請",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get("/my/leave-requests")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["employee_id"] == "E1"
    assert data[0]["leave_date"] == "2026-09-15"
    assert data[0]["reason"] == "私用"
    assert data[0]["status"] == "申請中"


def test_employee_can_submit_own_leave_request(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

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
        "/my/leave-requests",
        data={
            "leave_date": "2026-09-15",
            "reason": "私用",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["employee_id"] == "E1"
    assert data["leave_date"] == "2026-09-15"
    assert data["reason"] == "私用"
    assert data["status"] == "申請中"
    assert data["request_id"] is not None

    saved = test_repo.leave_requests("E1")

    assert len(saved) == 1
    assert saved[0].employee_id == "E1"
    assert saved[0].status == "申請中"


def test_admin_can_list_all_leave_requests(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="admin",
            password_hash="unused",
            role="admin",
        )
    )

    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 15),
            reason="私用",
        )
    )

    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E2",
            leave_date=date(2026, 9, 20),
            reason="通院",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get("/leave-requests")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert {item["employee_id"] for item in data} == {"E1", "E2"}
