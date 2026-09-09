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
        LeaveRequest(
            employee_id="E3",
            leave_date=__import__("datetime").date(2026, 10, 1),
            status="申請中",
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


def test_find_referenced_employee_by_id_or_name():
    from datetime import date
    from models.employee import Employee

    employees = [
        Employee(
            employee_id="E001",
            name="山田太郎",
            employment_type="正社員",
            hire_date=date(2025, 1, 1),
            pay_type="月給",
        ),
        Employee(
            employee_id="E002",
            name="佐藤花子",
            employment_type="正社員",
            hire_date=date(2025, 1, 1),
            pay_type="月給",
        ),
    ]

    from services.ai_context_service import find_referenced_employee

    by_id = find_referenced_employee(
        "E002の9月の状況を教えて",
        employees,
    )
    assert by_id is not None
    assert by_id.employee_id == "E002"

    by_name = find_referenced_employee(
        "山田太郎さんの勤怠を確認して",
        employees,
    )
    assert by_name is not None
    assert by_name.employee_id == "E001"

    assert find_referenced_employee(
        "今月の会社全体の状況を教えて",
        employees,
    ) is None

    assert find_referenced_employee(
        "E001とE002を比較して",
        employees,
    ) is None


def test_build_employee_attendance_summary():
    from datetime import date
    from models.work_record import WorkRecord
    from services.ai_context_service import build_employee_attendance_summary

    records = [
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_total_minutes=60,
        ),
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 2),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_total_minutes=60,
        ),
    ]

    summary = build_employee_attendance_summary(
        employee_id="E001",
        employee_name="山田太郎",
        year_month="2026-09",
        records=records,
    )

    assert summary == {
        "employee_id": "E001",
        "employee_name": "山田太郎",
        "year_month": "2026-09",
        "record_count": 2,
        "attendance_days": 2,
    }


def test_build_employee_payroll_summary():
    from models.payroll import PayrollResult, TimeClassification
    from services.ai_context_service import build_employee_payroll_summary

    payroll = PayrollResult(
        employee_id="E001",
        year_month="2026-09",
        classification=TimeClassification(),
        warnings=["確認してください"],
        blocking_issues=["勤怠未確認"],
        finalized=False,
    )

    summary = build_employee_payroll_summary(
        employee_id="E001",
        year_month="2026-09",
        payroll=payroll,
    )

    assert summary == {
        "employee_id": "E001",
        "year_month": "2026-09",
        "calculated": True,
        "finalized": False,
        "warning_count": 1,
        "blocking_issue_count": 1,
    }

    missing = build_employee_payroll_summary(
        employee_id="E001",
        year_month="2026-10",
        payroll=None,
    )

    assert missing["calculated"] is False
    assert missing["finalized"] is False


def test_find_referenced_employee_candidates_handles_duplicate_names():
    from datetime import date
    from models.employee import Employee
    from services.ai_context_service import find_referenced_employee_candidates

    employees = [
        Employee(
            employee_id="W250651",
            name="ホムガイ",
            employment_type="正社員",
            hire_date=date(2026, 6, 1),
            pay_type="月給",
        ),
        Employee(
            employee_id="W250652",
            name="ホムガイ",
            employment_type="正社員",
            hire_date=date(2026, 6, 1),
            pay_type="月給",
        ),
    ]

    duplicate_name = find_referenced_employee_candidates(
        "ホムガイの状況を教えて",
        employees,
    )
    assert [item.employee_id for item in duplicate_name] == [
        "W250651",
        "W250652",
    ]

    explicit_id = find_referenced_employee_candidates(
        "W250651の状況を教えて",
        employees,
    )
    assert [item.employee_id for item in explicit_id] == [
        "W250651",
    ]
