from __future__ import annotations

from typing import Any


class PostgresPayrollRepository:
    @classmethod
    def from_database_url(cls, database_url: str, connect=None):
        if connect is None:
            import psycopg

            connect = psycopg.connect

        return cls(connect(database_url))

    def __init__(self, connection: Any) -> None:
        self.connection = connection
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                employee_id TEXT,
                active BOOLEAN NOT NULL DEFAULT TRUE
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
            CREATE TABLE IF NOT EXISTS audit_log (
                id BIGSERIAL PRIMARY KEY,
                created_at TEXT NOT NULL,
                action TEXT NOT NULL,
                subject TEXT NOT NULL,
                detail TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def save_user(self, user) -> None:
        self.connection.execute(
            """
            INSERT INTO users
                (username, password_hash, role, employee_id, active)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (username) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role,
                employee_id = EXCLUDED.employee_id,
                active = EXCLUDED.active
            """,
            (
                user.username,
                user.password_hash,
                user.role,
                user.employee_id,
                user.active,
            ),
        )
        self.connection.commit()

    def user(self, username: str):
        from models.user import User

        row = self.connection.execute(
            """
            SELECT username, password_hash, role, employee_id, active
            FROM users
            WHERE username = %s
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

    def company(self):
        from models.company import Company

        row = self.connection.execute(
            """
            SELECT payload
            FROM settings
            WHERE key = %s
            """,
            ("company",),
        ).fetchone()

        if not row:
            return Company()

        import json

        return Company(**json.loads(row[0]))

    def save_company(self, company) -> None:
        import json
        from dataclasses import asdict

        self.connection.execute(
            """
            INSERT INTO settings (key, payload)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET
                payload = EXCLUDED.payload
            """,
            (
                "company",
                json.dumps(asdict(company), ensure_ascii=False),
            ),
        )
        self.connection.commit()

        self.audit(
            "会社情報保存",
            "company",
            company.name,
        )

    def audit(
        self,
        action: str,
        subject: str,
        detail: str,
    ) -> None:
        from datetime import datetime

        self.connection.execute(
            """
            INSERT INTO audit_log(
                created_at,
                action,
                subject,
                detail
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                action,
                subject,
                detail,
            ),
        )
        self.connection.commit()

    def save_employee(self, employee) -> None:
        import json
        from dataclasses import asdict

        self.connection.execute(
            """
            INSERT INTO employees (employee_id, payload)
            VALUES (%s, %s)
            ON CONFLICT (employee_id) DO UPDATE SET
                payload = EXCLUDED.payload
            """,
            (
                employee.employee_id,
                json.dumps(
                    asdict(employee),
                    ensure_ascii=False,
                    default=lambda value: str(value),
                ),
            ),
        )
        self.connection.commit()
