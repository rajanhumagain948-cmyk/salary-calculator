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
