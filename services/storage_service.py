"""SQLite repository. Decimal values are stored as text to preserve exact yen."""
from __future__ import annotations

import json
import sqlite3
from models.leave_request import LeaveRequest
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from models.allowance import Allowance
from models.break_record import BreakRecord
from models.company import Company
from models.deduction import OtherDeduction
from models.employee import Employee
from models.employment import EmploymentTerms
from models.payroll import PayrollResult
from models.transportation import Transportation
from models.user import User
from models.work_record import WorkRecord
from models.shifts import Shift


class PayrollRepository:
    def __init__(self, database: Path) -> None:
        # SQLiteは親ディレクトリが存在しないとDBを作成できないため、
        # 初回起動でも動作するよう自動作成する。
        database.parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS work_records (
                id INTEGER PRIMARY KEY,
                employee_id TEXT,
                work_date TEXT,
                payload TEXT NOT NULL
            )
            """
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS payroll_results (
                employee_id TEXT,
                year_month TEXT,
                payload TEXT NOT NULL,
                PRIMARY KEY(employee_id, year_month)
            )
            """
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS employment_terms (
                employee_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS payroll_inputs (
                employee_id TEXT,
                year_month TEXT,
                payload TEXT NOT NULL,
                PRIMARY KEY(employee_id, year_month)
            )
            """
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                action TEXT NOT NULL,
                subject TEXT NOT NULL,
                detail TEXT NOT NULL
            )
            """
        )

        # ログインユーザー
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                employee_id TEXT,
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS leave_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                leave_date TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT '申請中',
                created_at TEXT NOT NULL
            )
            """
        )

        self.connection.commit()

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                shift_date TEXT NOT NULL,
                start_minute INTEGER NOT NULL,
                end_minute INTEGER NOT NULL,
                break_minutes INTEGER NOT NULL DEFAULT 0,
                note TEXT NOT NULL DEFAULT '',
                confirmed INTEGER NOT NULL DEFAULT 0
            )
            """
        )

    @staticmethod
    def _dump(value: object) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            default=lambda o: str(o),
        )

    def save_leave_request(self, request: LeaveRequest) -> LeaveRequest:
        created_at = request.created_at or datetime.now()

        cursor = self.connection.execute(
            """
            INSERT INTO leave_requests
            (employee_id, leave_date, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                request.employee_id,
                request.leave_date.isoformat(),
                request.reason,
                request.status,
                created_at.isoformat(timespec="seconds"),
            ),
        )

        self.connection.commit()

        request.request_id = cursor.lastrowid
        request.created_at = created_at

        return request

    def leave_requests(
        self,
        employee_id: str | None = None,
    ) -> list[LeaveRequest]:
        if employee_id:
            rows = self.connection.execute(
                """
                SELECT id, employee_id, leave_date, reason, status, created_at
                FROM leave_requests
                WHERE employee_id = ?
                ORDER BY leave_date DESC, id DESC
                """,
                (employee_id,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT id, employee_id, leave_date, reason, status, created_at
                FROM leave_requests
                ORDER BY leave_date DESC, id DESC
                """
            ).fetchall()

        return [
            LeaveRequest(
                request_id=row[0],
                employee_id=row[1],
                leave_date=date.fromisoformat(row[2]),
                reason=row[3],
                status=row[4],
                created_at=datetime.fromisoformat(row[5]),
            )
            for row in rows
        ]

    def update_leave_status(
        self,
        request_id: int,
        status: str,
    ) -> None:
        if status not in ("承認", "却下"):
            raise ValueError("不正な承認状態です。")

        self.connection.execute(
            """
            UPDATE leave_requests
            SET status = ?
            WHERE id = ?
            """,
            (status, request_id),
        )
        self.connection.commit()

    def shifts(
        self,
        employee_id: str,
        year_month: str,
    ) -> list[Shift]:
        rows = self.connection.execute(
            """
            SELECT id, employee_id, shift_date, start_minute, end_minute, break_minutes, note, confirmed
            FROM shifts
            WHERE employee_id = ?
              AND shift_date LIKE ?
            ORDER BY shift_date, id
            """,
            (employee_id, f"{year_month}%"),
        ).fetchall()

        return [
            Shift(
                shift_id=row[0],
                employee_id=row[1],
                shift_date=date.fromisoformat(row[2]),
                start_minute=int(row[3]),
                end_minute=int(row[4]),
                break_minutes=int(row[5]),
                note=row[6],
                confirmed=bool(row[7]),
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Users / Authentication
    # ------------------------------------------------------------------

    def save_user(self, user: User) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO users
            (username, password_hash, role, employee_id, active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user.username,
                user.password_hash,
                user.role,
                user.employee_id,
                int(user.active),
            ),
        )
        self.connection.commit()

    def user(self, username: str) -> User | None:
        row = self.connection.execute(
            """
            SELECT username, password_hash, role, employee_id, active
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

        if not row:
            return None

        return User(
            username=row[0],
            password_hash=row[1],
            role=row[2],
            employee_id=row[3],
            active=bool(row[4]),
        )

    def users(self) -> list[User]:
        rows = self.connection.execute(
            """
            SELECT username, password_hash, role, employee_id, active
            FROM users
            ORDER BY username
            """
        ).fetchall()

        return [
            User(
                username=row[0],
                password_hash=row[1],
                role=row[2],
                employee_id=row[3],
                active=bool(row[4]),
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Employees
    # ------------------------------------------------------------------

    def save_employee(self, employee: Employee) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO employees VALUES (?, ?)",
            (
                employee.employee_id,
                self._dump(asdict(employee)),
            ),
        )
        self.connection.commit()
        self.audit(
            "従業員保存",
            employee.employee_id,
            employee.name,
        )

    def employees(self) -> list[Employee]:
        rows = self.connection.execute(
            """
            SELECT payload
            FROM employees
            ORDER BY employee_id
            """
        ).fetchall()

        result: list[Employee] = []

        for (payload,) in rows:
            data = json.loads(payload)

            for key in (
                "hourly_rate",
                "monthly_salary",
                "weekly_hours",
                "resident_tax_monthly",
                "standard_monthly_remuneration",
            ):
                data[key] = Decimal(data.get(key, "0"))

            for key in (
                "weekly_days",
                "workplace_size",
                "dependents",
                "contract_months",
            ):
                if data.get(key) not in (None, ""):
                    data[key] = int(data[key])

            for key in (
                "hire_date",
                "termination_date",
                "birth_date",
            ):
                if data.get(key):
                    data[key] = date.fromisoformat(data[key])

            result.append(Employee(**data))

        return result

    # ------------------------------------------------------------------
    # Work records
    # ------------------------------------------------------------------

    def save_work_record(self, record: WorkRecord) -> WorkRecord:
        payload = self._dump(asdict(record))

        if record.record_id is None:
            cursor = self.connection.execute(
                """
                INSERT INTO work_records(
                    employee_id,
                    work_date,
                    payload
                )
                VALUES (?, ?, ?)
                """,
                (
                    record.employee_id,
                    record.work_date.isoformat(),
                    payload,
                ),
            )
            record.record_id = cursor.lastrowid

        else:
            self.connection.execute(
                """
                UPDATE work_records
                SET work_date = ?, payload = ?
                WHERE id = ? AND employee_id = ?
                """,
                (
                    record.work_date.isoformat(),
                    payload,
                    record.record_id,
                    record.employee_id,
                ),
            )

        self.connection.commit()
        return record

    def work_records(
        self,
        employee_id: str,
        year_month: str,
    ) -> list[WorkRecord]:
        rows = self.connection.execute(
            """
            SELECT id, payload
            FROM work_records
            WHERE employee_id = ?
              AND work_date LIKE ?
            ORDER BY work_date, id
            """,
            (
                employee_id,
                f"{year_month}%",
            ),
        ).fetchall()

        result: list[WorkRecord] = []

        for record_id, payload in rows:
            data = json.loads(payload)

            result.append(
                WorkRecord(
                    employee_id=data["employee_id"],
                    work_date=date.fromisoformat(data["work_date"]),
                    start_minute=data["start_minute"],
                    end_minute=data["end_minute"],
                    is_holiday=data["is_holiday"],
                    break_total_minutes=data["break_total_minutes"],
                    breaks=[
                        BreakRecord(**item)
                        for item in data.get("breaks", [])
                    ],
                    record_id=record_id,
                )
            )

        return result

    def delete_work_record(
        self,
        employee_id: str,
        record_id: int,
    ) -> None:
        self.connection.execute(
            """
            DELETE FROM work_records
            WHERE id = ? AND employee_id = ?
            """,
            (
                record_id,
                employee_id,
            ),
        )

        self.connection.commit()

        self.audit(
            "勤怠削除",
            employee_id,
            str(record_id),
        )

    # ------------------------------------------------------------------
    # Payroll
    # ------------------------------------------------------------------

    def save_payroll_result(
        self,
        result: PayrollResult,
    ) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO payroll_results
            VALUES (?, ?, ?)
            """,
            (
                result.employee_id,
                result.year_month,
                self._dump(asdict(result)),
            ),
        )

        self.connection.commit()

        self.audit(
            "給与確定" if result.finalized else "給与計算",
            result.employee_id,
            result.year_month,
        )

    def payroll_results(
        self,
        year_month: str,
    ) -> list[PayrollResult]:
        rows = self.connection.execute(
            """
            SELECT payload
            FROM payroll_results
            WHERE year_month = ?
            ORDER BY employee_id
            """,
            (year_month,),
        ).fetchall()

        results: list[PayrollResult] = []

        from models.payroll import TimeClassification

        for (payload,) in rows:
            data = json.loads(payload)

            data["classification"] = TimeClassification(
                **data["classification"]
            )

            data["payments"] = {
                key: Decimal(value)
                for key, value in data["payments"].items()
            }

            data["deductions"] = {
                key: Decimal(value)
                for key, value in data["deductions"].items()
            }

            results.append(
                PayrollResult(**data)
            )

        return results

    def payroll_result(
        self,
        employee_id: str,
        year_month: str,
    ) -> PayrollResult | None:
        results = self.payroll_results(year_month)

        return next(
            (
                result
                for result in results
                if result.employee_id == employee_id
            ),
            None,
        )

    # ------------------------------------------------------------------
    # Employment terms
    # ------------------------------------------------------------------

    def save_terms(
        self,
        terms: EmploymentTerms,
    ) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO employment_terms
            VALUES (?, ?)
            """,
            (
                terms.employee_id,
                self._dump(asdict(terms)),
            ),
        )

        self.connection.commit()

    def terms(
        self,
        employee_id: str,
    ) -> EmploymentTerms:
        row = self.connection.execute(
            """
            SELECT payload
            FROM employment_terms
            WHERE employee_id = ?
            """,
            (employee_id,),
        ).fetchone()

        if not row:
            return EmploymentTerms(employee_id)

        data = json.loads(row[0])

        for key in (
            "fixed_overtime_amount",
            "housing_company_burden",
            "company_housing_employee_burden",
            "monthly_hourly_divisor",
        ):
            data[key] = Decimal(data[key])

        return EmploymentTerms(**data)

    # ------------------------------------------------------------------
    # Company
    # ------------------------------------------------------------------

    def save_company(
        self,
        company: Company,
    ) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO settings
            VALUES (?, ?)
            """,
            (
                "company",
                self._dump(asdict(company)),
            ),
        )

        self.connection.commit()

        self.audit(
            "会社情報保存",
            "company",
            company.name,
        )

    def company(self) -> Company:
        row = self.connection.execute(
            """
            SELECT payload
            FROM settings
            WHERE key = 'company'
            """
        ).fetchone()

        if not row:
            return Company()

        return Company(
            **json.loads(row[0])
        )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def audit(
        self,
        action: str,
        subject: str,
        detail: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO audit_log(
                created_at,
                action,
                subject,
                detail
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                action,
                subject,
                detail,
            ),
        )

        self.connection.commit()

    def recent_audit(
        self,
        limit: int = 30,
    ) -> list[tuple[str, str, str, str]]:
        return self.connection.execute(
            """
            SELECT created_at, action, subject, detail
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    def backup_to(
        self,
        destination: Path,
    ) -> None:
        target = sqlite3.connect(destination)

        try:
            self.connection.backup(target)
        finally:
            target.close()

        self.audit(
            "バックアップ",
            "database",
            str(destination),
        )

    # ------------------------------------------------------------------
    # Monthly payroll inputs
    # ------------------------------------------------------------------

    def save_monthly_inputs(
        self,
        employee_id: str,
        year_month: str,
        allowances: list[Allowance],
        deductions: list[OtherDeduction],
        transport: Transportation,
    ) -> None:
        payload = self._dump(
            {
                "allowances": [
                    asdict(item)
                    for item in allowances
                ],
                "deductions": [
                    asdict(item)
                    for item in deductions
                ],
                "transport": asdict(transport),
            }
        )

        self.connection.execute(
            """
            INSERT OR REPLACE INTO payroll_inputs
            VALUES (?, ?, ?)
            """,
            (
                employee_id,
                year_month,
                payload,
            ),
        )

        self.connection.commit()

    def monthly_inputs(
        self,
        employee_id: str,
        year_month: str,
    ) -> tuple[
        list[Allowance],
        list[OtherDeduction],
        Transportation,
    ]:
        row = self.connection.execute(
            """
            SELECT payload
            FROM payroll_inputs
            WHERE employee_id = ?
              AND year_month = ?
            """,
            (
                employee_id,
                year_month,
            ),
        ).fetchone()

        if not row:
            return [], [], Transportation()

        data = json.loads(row[0])

        allowances = [
            Allowance(
                item["name"],
                Decimal(item["amount"]),
                item["taxable"],
            )
            for item in data["allowances"]
        ]

        deductions = [
            OtherDeduction(
                item["name"],
                Decimal(item["amount"]),
            )
            for item in data["deductions"]
        ]

        transport_data = data["transport"]
        transport_data["unit_amount"] = Decimal(
            transport_data["unit_amount"]
        )

        return (
            allowances,
            deductions,
            Transportation(**transport_data),
        )