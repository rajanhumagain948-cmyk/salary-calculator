"""SQLite repository. Decimal values are stored as text to preserve exact yen."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from models.employee import Employee
from models.work_record import WorkRecord
from models.break_record import BreakRecord
from models.payroll import PayrollResult
from models.employment import EmploymentTerms
from models.company import Company
from models.allowance import Allowance
from models.deduction import OtherDeduction
from models.transportation import Transportation

class PayrollRepository:
    def __init__(self, database: Path) -> None:
        self.connection = sqlite3.connect(database)
        self.connection.execute("CREATE TABLE IF NOT EXISTS employees (employee_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS work_records (id INTEGER PRIMARY KEY, employee_id TEXT, work_date TEXT, payload TEXT NOT NULL)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS payroll_results (employee_id TEXT, year_month TEXT, payload TEXT NOT NULL, PRIMARY KEY(employee_id, year_month))")
        self.connection.execute("CREATE TABLE IF NOT EXISTS employment_terms (employee_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS payroll_inputs (employee_id TEXT, year_month TEXT, payload TEXT NOT NULL, PRIMARY KEY(employee_id, year_month))")
        self.connection.execute("CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, action TEXT NOT NULL, subject TEXT NOT NULL, detail TEXT NOT NULL)")
        self.connection.commit()

    @staticmethod
    def _dump(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, default=lambda o: str(o))

    def save_employee(self, employee: Employee) -> None:
        self.connection.execute("INSERT OR REPLACE INTO employees VALUES (?, ?)", (employee.employee_id, self._dump(asdict(employee))))
        self.connection.commit()
        self.audit("従業員保存", employee.employee_id, employee.name)

    def employees(self) -> list[Employee]:
        rows = self.connection.execute("SELECT payload FROM employees ORDER BY employee_id").fetchall()
        result = []
        for (payload,) in rows:
            data = json.loads(payload)
            for key in ("hourly_rate", "monthly_salary", "weekly_hours", "resident_tax_monthly", "standard_monthly_remuneration"):
                data[key] = Decimal(data.get(key, "0"))
            for key in ("weekly_days", "workplace_size", "dependents", "contract_months"):
                if data.get(key) not in (None, ""):
                    data[key] = int(data[key])
            for key in ("hire_date", "termination_date", "birth_date"):
                if data.get(key): data[key] = date.fromisoformat(data[key])
            result.append(Employee(**data))
        return result

    def save_work_record(self, record: WorkRecord) -> WorkRecord:
        payload = self._dump(asdict(record))
        if record.record_id is None:
            cursor = self.connection.execute("INSERT INTO work_records(employee_id, work_date, payload) VALUES (?, ?, ?)", (record.employee_id, record.work_date.isoformat(), payload))
            record.record_id = cursor.lastrowid
        else:
            self.connection.execute("UPDATE work_records SET work_date=?, payload=? WHERE id=? AND employee_id=?", (record.work_date.isoformat(), payload, record.record_id, record.employee_id))
        self.connection.commit()
        return record

    def work_records(self, employee_id: str, year_month: str) -> list[WorkRecord]:
        rows = self.connection.execute("SELECT id, payload FROM work_records WHERE employee_id=? AND work_date LIKE ? ORDER BY work_date, id", (employee_id, f"{year_month}%")).fetchall()
        return [WorkRecord(employee_id=d["employee_id"], work_date=date.fromisoformat(d["work_date"]), start_minute=d["start_minute"], end_minute=d["end_minute"], is_holiday=d["is_holiday"], break_total_minutes=d["break_total_minutes"], breaks=[BreakRecord(**item) for item in d.get("breaks", [])], record_id=record_id) for record_id, payload in rows if (d := json.loads(payload))]

    def delete_work_record(self, employee_id: str, record_id: int) -> None:
        self.connection.execute("DELETE FROM work_records WHERE id=? AND employee_id=?", (record_id, employee_id))
        self.connection.commit()
        self.audit("勤怠削除", employee_id, str(record_id))

    def save_payroll_result(self, result: PayrollResult) -> None:
        self.connection.execute("INSERT OR REPLACE INTO payroll_results VALUES (?, ?, ?)", (result.employee_id, result.year_month, self._dump(asdict(result))))
        self.connection.commit()
        self.audit("給与確定" if result.finalized else "給与計算", result.employee_id, result.year_month)

    def payroll_results(self, year_month: str) -> list[PayrollResult]:
        rows = self.connection.execute("SELECT payload FROM payroll_results WHERE year_month=? ORDER BY employee_id", (year_month,)).fetchall()
        results: list[PayrollResult] = []
        from models.payroll import TimeClassification
        for (payload,) in rows:
            data = json.loads(payload)
            data["classification"] = TimeClassification(**data["classification"])
            data["payments"] = {key: Decimal(value) for key, value in data["payments"].items()}
            data["deductions"] = {key: Decimal(value) for key, value in data["deductions"].items()}
            results.append(PayrollResult(**data))
        return results

    def save_terms(self, terms: EmploymentTerms) -> None:
        self.connection.execute("INSERT OR REPLACE INTO employment_terms VALUES (?, ?)", (terms.employee_id, self._dump(asdict(terms))))
        self.connection.commit()

    def terms(self, employee_id: str) -> EmploymentTerms:
        row = self.connection.execute("SELECT payload FROM employment_terms WHERE employee_id=?", (employee_id,)).fetchone()
        if not row:
            return EmploymentTerms(employee_id)
        data = json.loads(row[0])
        for key in ("fixed_overtime_amount", "housing_company_burden", "company_housing_employee_burden", "monthly_hourly_divisor"):
            data[key] = Decimal(data[key])
        return EmploymentTerms(**data)

    def save_company(self, company: Company) -> None:
        self.connection.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", ("company", self._dump(asdict(company))))
        self.connection.commit()
        self.audit("会社情報保存", "company", company.name)

    def audit(self, action: str, subject: str, detail: str) -> None:
        self.connection.execute("INSERT INTO audit_log(created_at, action, subject, detail) VALUES (?, ?, ?, ?)", (datetime.now().isoformat(timespec="seconds"), action, subject, detail))
        self.connection.commit()

    def recent_audit(self, limit: int = 30) -> list[tuple[str, str, str, str]]:
        return self.connection.execute("SELECT created_at, action, subject, detail FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def backup_to(self, destination: Path) -> None:
        target = sqlite3.connect(destination)
        self.connection.backup(target)
        target.close()
        self.audit("バックアップ", "database", str(destination))

    def company(self) -> Company:
        row = self.connection.execute("SELECT payload FROM settings WHERE key='company'").fetchone()
        return Company(**json.loads(row[0])) if row else Company()

    def save_monthly_inputs(self, employee_id: str, year_month: str, allowances: list[Allowance],
                            deductions: list[OtherDeduction], transport: Transportation) -> None:
        payload = self._dump({"allowances": [asdict(item) for item in allowances], "deductions": [asdict(item) for item in deductions], "transport": asdict(transport)})
        self.connection.execute("INSERT OR REPLACE INTO payroll_inputs VALUES (?, ?, ?)", (employee_id, year_month, payload))
        self.connection.commit()

    def monthly_inputs(self, employee_id: str, year_month: str) -> tuple[list[Allowance], list[OtherDeduction], Transportation]:
        row = self.connection.execute("SELECT payload FROM payroll_inputs WHERE employee_id=? AND year_month=?", (employee_id, year_month)).fetchone()
        if not row:
            return [], [], Transportation()
        data = json.loads(row[0])
        allowances = [Allowance(item["name"], Decimal(item["amount"]), item["taxable"]) for item in data["allowances"]]
        deductions = [OtherDeduction(item["name"], Decimal(item["amount"])) for item in data["deductions"]]
        transport_data = data["transport"]; transport_data["unit_amount"] = Decimal(transport_data["unit_amount"])
        return allowances, deductions, Transportation(**transport_data)
