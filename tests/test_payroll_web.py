from decimal import Decimal

from fastapi.testclient import TestClient

import webapp.main as main
from models.payroll import PayrollResult, TimeClassification
from models.user import User
from services.storage_service import PayrollRepository


def test_admin_can_finalize_payroll_without_blocking_issues(tmp_path, monkeypatch):
    test_repo = PayrollRepository(tmp_path / "payroll.sqlite3")
    monkeypatch.setattr(main, "repo", test_repo)

    test_repo.save_user(
        User(
            username="admin",
            password_hash="unused",
            role="admin",
        )
    )

    test_repo.save_payroll_result(
        PayrollResult(
            employee_id="E1",
            year_month="2026-08",
            classification=TimeClassification(),
            payments={"基本給": Decimal("200000")},
            deductions={"所得税": Decimal("3270")},
            blocking_issues=[],
        )
    )

    client = TestClient(main.app)
    token = main.serializer.dumps({"username": "admin"})
    client.cookies.set(main.COOKIE_NAME, token)

    response = client.post(
        "/payroll/finalize",
        data={
            "employee_id": "E1",
            "year_month": "2026-08",
        },
    )

    assert response.status_code == 200

    saved = test_repo.payroll_result("E1", "2026-08")
    assert saved is not None
    assert saved.finalized is True
    assert saved.payments["基本給"] == Decimal("200000")
    assert saved.deductions["所得税"] == Decimal("3270")
