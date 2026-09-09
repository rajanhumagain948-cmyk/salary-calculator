from models.leave_request import LeaveRequest
from models.payroll import PayrollResult, TimeClassification
from services.ai_context_service import build_ai_monthly_summary


def test_build_ai_monthly_summary_counts_company_status():
    payrolls = [
        PayrollResult(
            employee_id="E1",
            year_month="2026-09",
            classification=TimeClassification(),
            finalized=True,
        ),
        PayrollResult(
            employee_id="E2",
            year_month="2026-09",
            classification=TimeClassification(),
            blocking_issues=["勤怠を確認してください"],
        ),
    ]

    leave_requests = [
        LeaveRequest(
            employee_id="E1",
            leave_date=__import__("datetime").date(2026, 9, 15),
            status="申請中",
        ),
        LeaveRequest(
            employee_id="E2",
            leave_date=__import__("datetime").date(2026, 9, 20),
            status="承認",
        ),
    ]

    summary = build_ai_monthly_summary(
        year_month="2026-09",
        employee_count=3,
        payrolls=payrolls,
        leave_requests=leave_requests,
    )

    assert summary == {
        "year_month": "2026-09",
        "employee_count": 3,
        "calculated_payroll_count": 2,
        "finalized_payroll_count": 1,
        "blocked_payroll_count": 1,
        "pending_leave_count": 1,
    }
