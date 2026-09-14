from datetime import date

from models.employment import EmploymentTerms
from models.work_record import WorkRecord
from services.prediction_service import build_overtime_forecast


def test_overtime_forecast_uses_existing_overtime_classification():
    terms = EmploymentTerms(
        "E001",
        standard_daily_minutes=480,
        standard_weekly_minutes=2400,
    )
    records = [
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=19 * 60,
            break_total_minutes=60,
        )
    ]

    forecast = build_overtime_forecast(
        records=records,
        terms=terms,
        as_of=date(2026, 9, 1),
    )

    assert forecast["actual_overtime_minutes"] == 60


def test_overtime_forecast_projects_average_overtime_over_future_confirmed_shifts():
    from models.shifts import Shift

    terms = EmploymentTerms(
        "E001",
        standard_daily_minutes=480,
        standard_weekly_minutes=2400,
    )
    records = [
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=19 * 60,
            break_total_minutes=60,
        )
    ]
    shifts = [
        Shift(
            employee_id="E001",
            shift_date=date(2026, 9, 2),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_minutes=60,
            confirmed=True,
        ),
        Shift(
            employee_id="E001",
            shift_date=date(2026, 9, 3),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_minutes=60,
            confirmed=True,
        ),
    ]

    forecast = build_overtime_forecast(
        records=records,
        terms=terms,
        shifts=shifts,
        as_of=date(2026, 9, 1),
    )

    assert forecast["actual_overtime_minutes"] == 60
    assert forecast["future_confirmed_shift_days"] == 2
    assert forecast["forecast_overtime_minutes"] == 180


def test_overtime_forecast_ignores_unconfirmed_future_shifts():
    from models.shifts import Shift

    terms = EmploymentTerms("E001")
    records = [
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=19 * 60,
            break_total_minutes=60,
        )
    ]
    shifts = [
        Shift(
            employee_id="E001",
            shift_date=date(2026, 9, 2),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_minutes=60,
            confirmed=False,
        )
    ]

    forecast = build_overtime_forecast(
        records=records,
        terms=terms,
        shifts=shifts,
        as_of=date(2026, 9, 1),
    )

    assert forecast["future_confirmed_shift_days"] == 0
    assert forecast["forecast_overtime_minutes"] == 60


def test_overtime_forecast_ignores_work_records_after_as_of():
    terms = EmploymentTerms("E001")
    records = [
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=19 * 60,
            break_total_minutes=60,
        ),
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 20),
            start_minute=9 * 60,
            end_minute=21 * 60,
            break_total_minutes=60,
        ),
    ]

    forecast = build_overtime_forecast(
        records=records,
        terms=terms,
        as_of=date(2026, 9, 10),
    )

    assert forecast["actual_overtime_minutes"] == 60
    assert forecast["forecast_overtime_minutes"] == 60


def test_overtime_forecast_is_zero_without_actual_work_history():
    from models.shifts import Shift

    forecast = build_overtime_forecast(
        records=[],
        terms=EmploymentTerms("E001"),
        shifts=[
            Shift(
                employee_id="E001",
                shift_date=date(2026, 9, 2),
                start_minute=9 * 60,
                end_minute=18 * 60,
                break_minutes=60,
                confirmed=True,
            )
        ],
        as_of=date(2026, 9, 1),
    )

    assert forecast["actual_overtime_minutes"] == 0
    assert forecast["future_confirmed_shift_days"] == 1
    assert forecast["forecast_overtime_minutes"] == 0


def test_overtime_forecast_counts_confirmed_shift_dates_once():
    from models.shifts import Shift

    terms = EmploymentTerms("E001")
    records = [
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=19 * 60,
            break_total_minutes=60,
        )
    ]
    shifts = [
        Shift(
            employee_id="E001",
            shift_date=date(2026, 9, 2),
            start_minute=9 * 60,
            end_minute=12 * 60,
            confirmed=True,
        ),
        Shift(
            employee_id="E001",
            shift_date=date(2026, 9, 2),
            start_minute=13 * 60,
            end_minute=18 * 60,
            confirmed=True,
        ),
    ]

    forecast = build_overtime_forecast(
        records=records,
        terms=terms,
        shifts=shifts,
        as_of=date(2026, 9, 1),
    )

    assert forecast["future_confirmed_shift_days"] == 1
    assert forecast["forecast_overtime_minutes"] == 120


def test_attendance_review_finds_existing_attendance_warnings():
    from services.prediction_service import build_attendance_review

    records = [
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_total_minutes=0,
        )
    ]

    review = build_attendance_review(records=records)

    assert review["warning_count"] == 1
    assert review["warnings"] == [
        {
            "work_date": "2026-09-01",
            "messages": ["休憩が法定目安より60分不足しています。"],
        }
    ]


def test_build_payroll_estimate_uses_existing_payroll_calculation():
    from decimal import Decimal

    from models.employee import Employee
    from models.transportation import Transportation
    from services.prediction_service import build_payroll_estimate

    employee = Employee(
        employee_id="E001",
        name="山田太郎",
        employment_type="正社員",
        hire_date=date(2025, 1, 1),
        pay_type="月給",
        monthly_salary=Decimal("200000"),
    )
    terms = EmploymentTerms(
        "E001",
        monthly_hourly_divisor=Decimal("160"),
    )

    estimate = build_payroll_estimate(
        employee=employee,
        terms=terms,
        records=[],
        allowances=[],
        transport=Transportation(),
        other_deductions=[],
        year_month="2026-09",
    )

    assert estimate["reference_only"] is True
    assert estimate["used_for_payroll"] is False
    assert estimate["forecastable"] is True
    assert estimate["gross_pay"] == "200000"
    assert estimate["total_deductions"] is not None
    assert estimate["net_pay"] is not None
    assert isinstance(estimate["warnings"], list)
    assert isinstance(estimate["blocking_issues"], list)


def test_payroll_estimate_ignores_work_records_after_as_of():
    from decimal import Decimal

    from models.employee import Employee
    from models.transportation import Transportation
    from services.prediction_service import build_payroll_estimate

    employee = Employee(
        employee_id="E001",
        name="山田太郎",
        employment_type="正社員",
        hire_date=date(2025, 1, 1),
        pay_type="月給",
        monthly_salary=Decimal("200000"),
    )
    terms = EmploymentTerms(
        "E001",
        monthly_hourly_divisor=Decimal("160"),
    )
    records = [
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 20),
            start_minute=9 * 60,
            end_minute=21 * 60,
            break_total_minutes=60,
        )
    ]

    estimate = build_payroll_estimate(
        employee=employee,
        terms=terms,
        records=records,
        allowances=[],
        transport=Transportation(),
        other_deductions=[],
        year_month="2026-09",
        as_of=date(2026, 9, 10),
    )

    assert estimate["gross_pay"] == "200000"


def test_payroll_estimate_limits_daily_transport_to_actual_records():
    from decimal import Decimal

    from models.employee import Employee
    from models.transportation import Transportation
    from services.prediction_service import build_payroll_estimate

    employee = Employee(
        employee_id="E001",
        name="山田太郎",
        employment_type="正社員",
        hire_date=date(2025, 1, 1),
        pay_type="月給",
        monthly_salary=Decimal("200000"),
    )
    terms = EmploymentTerms(
        "E001",
        monthly_hourly_divisor=Decimal("160"),
    )
    records = [
        WorkRecord(
            employee_id="E001",
            work_date=date(2026, 9, 1),
            start_minute=9 * 60,
            end_minute=18 * 60,
            break_total_minutes=60,
        )
    ]
    transport = Transportation(
        method="日額",
        unit_amount=Decimal("1000"),
        attendance_days=20,
        taxable=False,
    )

    estimate = build_payroll_estimate(
        employee=employee,
        terms=terms,
        records=records,
        allowances=[],
        transport=transport,
        other_deductions=[],
        year_month="2026-09",
        as_of=date(2026, 9, 10),
    )

    assert estimate["gross_pay"] == "201000"


def test_payroll_estimate_marks_blocking_result_not_forecastable():
    from decimal import Decimal

    from models.employee import Employee
    from models.transportation import Transportation
    from services.prediction_service import build_payroll_estimate

    estimate = build_payroll_estimate(
        employee=Employee(
            employee_id="E001",
            name="山田太郎",
            employment_type="正社員",
            hire_date=date(2025, 1, 1),
            pay_type="月給",
            monthly_salary=Decimal("200000"),
        ),
        terms=EmploymentTerms(
            "E001",
            monthly_hourly_divisor=Decimal("0"),
        ),
        records=[],
        allowances=[],
        transport=Transportation(),
        other_deductions=[],
        year_month="2026-09",
        as_of=date(2026, 9, 10),
    )

    assert estimate["forecastable"] is False


def test_summarize_payroll_estimates_totals_eligible_gross_pay():
    from services.prediction_service import summarize_payroll_estimates

    summary = summarize_payroll_estimates(
        [
            {
                "status": "確定済",
                "gross_pay": "200000",
            },
            {
                "status": "参考試算",
                "forecastable": True,
                "gross_pay": "180000",
            },
            {
                "status": "参考試算",
                "forecastable": False,
                "gross_pay": "150000",
            },
            {
                "status": "計算不可",
                "error": "設定不足",
            },
        ]
    )

    assert summary == {
        "gross_pay_reference_total": "380000",
        "included_count": 2,
        "excluded_count": 2,
    }


def test_leave_trend_summarizes_approved_days_for_target_year():
    from decimal import Decimal

    from models.leave_request import LeaveRequest
    from services.prediction_service import build_leave_trend

    requests = [
        LeaveRequest(
            employee_id="E001",
            leave_date=date(2026, 2, 10),
            status="承認",
            leave_unit="全日",
        ),
        LeaveRequest(
            employee_id="E001",
            leave_date=date(2026, 7, 15),
            status="承認",
            leave_unit="半日",
            half_day_period="午前",
        ),
        LeaveRequest(
            employee_id="E001",
            leave_date=date(2026, 9, 20),
            status="申請中",
            leave_unit="全日",
        ),
        LeaveRequest(
            employee_id="E001",
            leave_date=date(2025, 12, 20),
            status="承認",
            leave_unit="全日",
        ),
    ]

    trend = build_leave_trend(
        requests=requests,
        year=2026,
        standard_daily_minutes=480,
    )

    assert trend["approved_request_count"] == 2
    assert trend["approved_days"] == Decimal("1.5")
    assert trend["monthly_approved_days"] == {
        "2026-02": Decimal("1"),
        "2026-07": Decimal("0.5"),
    }


def test_payroll_processing_risk_prioritizes_blocking_issues():
    from services.prediction_service import build_payroll_processing_risk

    risk = build_payroll_processing_risk(
        warnings=["標準報酬月額を確認してください"],
        blocking_issues=["月平均所定労働時間を設定してください"],
    )

    assert risk == {
        "level": "high",
        "reasons": [
            "月平均所定労働時間を設定してください",
            "標準報酬月額を確認してください",
        ],
    }


def test_payroll_processing_risk_marks_warnings_medium():
    from services.prediction_service import build_payroll_processing_risk

    risk = build_payroll_processing_risk(
        warnings=["標準報酬月額を確認してください"],
        blocking_issues=[],
    )

    assert risk == {
        "level": "medium",
        "reasons": ["標準報酬月額を確認してください"],
    }


def test_payroll_processing_risk_is_none_without_issues():
    from services.prediction_service import build_payroll_processing_risk

    risk = build_payroll_processing_risk(
        warnings=[],
        blocking_issues=[],
    )

    assert risk == {
        "level": "none",
        "reasons": [],
    }
