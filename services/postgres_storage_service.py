from __future__ import annotations

from typing import Any


class PostgresPayrollRepository:
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
