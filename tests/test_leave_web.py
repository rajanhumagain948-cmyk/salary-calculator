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

    from decimal import Decimal
    from models.leave_grant import LeaveGrant

    test_repo.save_leave_grant(
        LeaveGrant(
            employee_id="E1",
            grant_date=date(2026, 7, 1),
            granted_days=Decimal("10"),
            expires_on=date(2028, 6, 30),
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


def test_admin_can_approve_leave_request(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="admin",
            password_hash="unused",
            role="admin",
        )
    )

    from decimal import Decimal
    from models.leave_grant import LeaveGrant

    test_repo.save_leave_grant(
        LeaveGrant(
            employee_id="E1",
            grant_date=date(2026, 7, 1),
            granted_days=Decimal("10"),
            expires_on=date(2028, 6, 30),
        )
    )

    item = test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 15),
            reason="私用",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        f"/leave-requests/{item.request_id}/status",
        data={"status": "承認"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "承認"

    saved = test_repo.leave_requests("E1")

    assert len(saved) == 1
    assert saved[0].status == "承認"


def test_employee_cannot_approve_leave_request(tmp_path, monkeypatch):
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

    item = test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 15),
            reason="私用",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        f"/leave-requests/{item.request_id}/status",
        data={"status": "承認"},
    )

    assert response.status_code == 403

    saved = test_repo.leave_requests("E1")

    assert len(saved) == 1
    assert saved[0].status == "申請中"


def test_admin_can_list_due_leave_grants(tmp_path, monkeypatch):
    from datetime import date
    from decimal import Decimal

    from models.employee import Employee

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

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
            name="付与対象",
            employment_type="正社員",
            hire_date=date(2026, 3, 1),
            pay_type="月給",
            monthly_salary=Decimal("200000"),
            weekly_hours=Decimal("40"),
            weekly_days=5,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/leave-grants/due",
        params={"as_of": "2026-09-07"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["employee_id"] == "E1"
    assert data[0]["name"] == "付与対象"
    assert data[0]["grant_date"] == "2026-09-01"
    assert data[0]["days"] == "10"
    assert data[0]["service_months"] == 6


def test_admin_can_confirm_due_leave_grant(tmp_path, monkeypatch):
    from datetime import date
    from decimal import Decimal

    from models.employee import Employee

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

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
            name="付与確定テスト",
            employment_type="正社員",
            hire_date=date(2026, 3, 1),
            pay_type="月給",
            monthly_salary=Decimal("200000"),
            weekly_hours=Decimal("40"),
            weekly_days=5,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/leave-grants/confirm",
        data={
            "employee_id": "E1",
            "as_of": "2026-09-07",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["employee_id"] == "E1"
    assert data["grant_date"] == "2026-09-01"
    assert data["granted_days"] == "10"
    assert data["expires_on"] == "2028-08-31"

    grants = test_repo.leave_grants("E1")

    assert len(grants) == 1
    assert grants[0].granted_days == Decimal("10")


def test_employee_can_view_own_leave_balance(tmp_path, monkeypatch):
    from decimal import Decimal

    from models.leave_grant import LeaveGrant

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

    from models.employee import Employee

    test_repo.save_employee(
        Employee(
            employee_id="E1",
            name="有給残数テスト",
            employment_type="正社員",
            hire_date=date(2026, 1, 1),
            pay_type="月給",
            monthly_salary=Decimal("200000"),
            weekly_hours=Decimal("40"),
            weekly_days=5,
        )
    )

    test_repo.save_leave_grant(
        LeaveGrant(
            employee_id="E1",
            grant_date=date(2026, 7, 1),
            granted_days=Decimal("10"),
            expires_on=date(2028, 6, 30),
        )
    )

    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 10),
            status="承認",
        )
    )

    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 20),
            status="申請中",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.get(
        "/my/leave-balance",
        params={"as_of": "2026-09-30"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["granted_days"] == "10"
    assert data["used_days"] == "1"
    assert data["pending_days"] == "1"
    assert data["remaining_days"] == "9"
    assert data["available_days"] == "8"
    assert data["next_grant_date"] == "2027-07-01"
    assert data["next_grant_days"] == "11"


def test_employee_cannot_request_more_leave_than_available(
    tmp_path,
    monkeypatch,
):
    from decimal import Decimal

    from models.leave_grant import LeaveGrant

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

    test_repo.save_leave_grant(
        LeaveGrant(
            employee_id="E1",
            grant_date=date(2026, 7, 1),
            granted_days=Decimal("1"),
            expires_on=date(2028, 6, 30),
        )
    )

    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 10),
            status="申請中",
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
            "leave_unit": "全日",
        },
    )

    assert response.status_code == 409

    # 既存の1件から増えていない。
    assert len(test_repo.leave_requests("E1")) == 1


def test_employee_cannot_submit_duplicate_full_day_leave(
    tmp_path,
    monkeypatch,
):
    from decimal import Decimal
    from models.leave_grant import LeaveGrant

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

    test_repo.save_leave_grant(
        LeaveGrant(
            employee_id="E1",
            grant_date=date(2026, 7, 1),
            granted_days=Decimal("10"),
            expires_on=date(2028, 6, 30),
        )
    )

    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 15),
            status="申請中",
            leave_unit="全日",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/my/leave-requests",
        data={
            "leave_date": "2026-09-15",
            "leave_unit": "全日",
            "reason": "重複",
        },
    )

    assert response.status_code == 409
    assert len(test_repo.leave_requests("E1")) == 1


def test_employee_can_request_am_and_pm_half_day_on_same_date(
    tmp_path,
    monkeypatch,
):
    from decimal import Decimal
    from models.leave_grant import LeaveGrant

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

    test_repo.save_leave_grant(
        LeaveGrant(
            employee_id="E1",
            grant_date=date(2026, 7, 1),
            granted_days=Decimal("10"),
            expires_on=date(2028, 6, 30),
        )
    )

    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 15),
            status="申請中",
            leave_unit="半日",
            half_day_period="午前",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/my/leave-requests",
        data={
            "leave_date": "2026-09-15",
            "leave_unit": "半日",
            "half_day_period": "午後",
        },
    )

    assert response.status_code == 200
    assert len(test_repo.leave_requests("E1")) == 2


def test_employee_cannot_request_same_half_day_twice(
    tmp_path,
    monkeypatch,
):
    from decimal import Decimal
    from models.leave_grant import LeaveGrant

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

    test_repo.save_leave_grant(
        LeaveGrant(
            employee_id="E1",
            grant_date=date(2026, 7, 1),
            granted_days=Decimal("10"),
            expires_on=date(2028, 6, 30),
        )
    )

    test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 15),
            status="申請中",
            leave_unit="半日",
            half_day_period="午前",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/my/leave-requests",
        data={
            "leave_date": "2026-09-15",
            "leave_unit": "半日",
            "half_day_period": "午前",
        },
    )

    assert response.status_code == 409
    assert len(test_repo.leave_requests("E1")) == 1


def test_admin_cannot_approve_leave_when_balance_is_insufficient(
    tmp_path,
    monkeypatch,
):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="admin",
            password_hash="unused",
            role="admin",
        )
    )

    item = test_repo.save_leave_request(
        LeaveRequest(
            employee_id="E1",
            leave_date=date(2026, 9, 15),
            status="申請中",
            leave_unit="全日",
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        f"/leave-requests/{item.request_id}/status",
        data={"status": "承認"},
    )

    assert response.status_code == 409

    saved = test_repo.leave_requests("E1")
    assert saved[0].status == "申請中"
