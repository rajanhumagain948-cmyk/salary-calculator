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
