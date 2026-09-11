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


def test_employee_ai_rejects_empty_message(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    class ShouldNotCallAssistant:
        def chat(self, message: str) -> str:
            raise AssertionError("AI must not be called for empty message")

    monkeypatch.setattr(main, "ai_assistant", ShouldNotCallAssistant())

    test_repo.save_user(
        User(
            username="employee",
            password_hash="unused",
            role="employee",
            employee_id="E001",
        )
    )

    client = TestClient(main.app, raise_server_exceptions=False)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/my/ai/chat",
        data={"message": "   "},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "message is required"


def test_employee_ai_rejects_message_over_2000_characters(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    class ShouldNotCallAssistant:
        def chat(self, message: str) -> str:
            raise AssertionError("AI must not be called for oversized message")

    monkeypatch.setattr(main, "ai_assistant", ShouldNotCallAssistant())

    test_repo.save_user(
        User(
            username="employee",
            password_hash="unused",
            role="employee",
            employee_id="E001",
        )
    )

    client = TestClient(main.app, raise_server_exceptions=False)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/my/ai/chat",
        data={"message": "あ" * 2001},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "message must be 2000 characters or fewer"


def test_employee_ai_rejects_invalid_year_month(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

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
        data={
            "message": "今月の給与を教えて",
            "year_month": "2026-9",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "year_month must be YYYY-MM"


def test_employee_ai_receives_own_attendance_summary(tmp_path, monkeypatch):
    from datetime import date

    from models.employee import Employee
    from models.work_record import WorkRecord

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    captured = {}

    class CapturingAssistant:
        def chat(self, message: str) -> str:
            captured["message"] = message
            return "勤怠を回答しました。"

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
    test_repo.save_work_record(
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_total_minutes=60,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/my/ai/chat",
        data={
            "message": "今月の勤務日数は？",
            "year_month": "2026-09",
        },
    )

    assert response.status_code == 200
    prompt = captured["message"]
    assert "対象月: 2026-09" in prompt
    assert "勤怠記録件数: 1" in prompt
    assert "出勤日数: 1" in prompt


def test_employee_ai_does_not_receive_unfinalized_payroll(tmp_path, monkeypatch):
    from datetime import date
    from decimal import Decimal

    from models.employee import Employee
    from models.payroll import PayrollResult, TimeClassification

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    captured = {}

    class CapturingAssistant:
        def chat(self, message: str) -> str:
            captured["message"] = message
            return "回答です。"

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
    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E001",
            year_month="2026-09",
            classification=TimeClassification(),
            payments={"基本給": Decimal("987654")},
            deductions={"所得税": Decimal("12345")},
            finalized=False,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/my/ai/chat",
        data={
            "message": "今月の給与はいくら？",
            "year_month": "2026-09",
        },
    )

    assert response.status_code == 200
    prompt = captured["message"]
    assert "987654" not in prompt
    assert "12345" not in prompt
    assert "未確定給与は参照できません" in prompt


def test_employee_ai_receives_finalized_payroll_amounts(tmp_path, monkeypatch):
    from datetime import date
    from decimal import Decimal

    from models.employee import Employee
    from models.payroll import PayrollResult, TimeClassification

    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    captured = {}

    class CapturingAssistant:
        def chat(self, message: str) -> str:
            captured["message"] = message
            return "給与を回答しました。"

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
    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E001",
            year_month="2026-09",
            classification=TimeClassification(
                regular_minutes=9600,
                overtime_minutes=300,
                night_minutes=60,
                holiday_minutes=420,
                overtime_over_60_minutes=30,
            ),
            payments={"基本給": Decimal("200000")},
            deductions={"所得税": Decimal("5000")},
            finalized=True,
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "employee"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/my/ai/chat",
        data={
            "message": "今月の給与と手取りはいくら？",
            "year_month": "2026-09",
        },
    )

    assert response.status_code == 200
    prompt = captured["message"]
    assert "給与確定済み: はい" in prompt
    assert "総支給: 200000円" in prompt
    assert "控除合計: 5000円" in prompt
    assert "手取り: 195000円" in prompt
    assert "支給内訳: 基本給=200000円" in prompt
    assert "控除内訳: 所得税=5000円" in prompt
    assert "所定内時間: 160時間00分" in prompt
    assert "時間外: 5時間00分" in prompt
    assert "深夜: 1時間00分" in prompt
    assert "休日: 7時間00分" in prompt
    assert "月60時間超: 0時間30分" in prompt
