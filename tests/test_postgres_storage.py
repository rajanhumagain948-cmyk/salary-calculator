from services.postgres_storage_service import PostgresPayrollRepository


def test_postgres_repository_initializes_users_table():
    executed = []

    class FakeConnection:
        def execute(self, sql, params=None):
            executed.append((sql, params))
            return self

        def commit(self):
            pass

    PostgresPayrollRepository(connection=FakeConnection())

    assert any(
        "CREATE TABLE IF NOT EXISTS users" in sql
        for sql, _ in executed
    )


def test_postgres_repository_saves_user_with_upsert():
    from models.user import User

    executed = []

    class FakeConnection:
        def execute(self, sql, params=None):
            executed.append((sql, params))
            return self

        def commit(self):
            pass

    repo = PostgresPayrollRepository(connection=FakeConnection())
    executed.clear()

    repo.save_user(
        User(
            username="admin",
            password_hash="hash",
            role="admin",
            active=True,
        )
    )

    sql, params = executed[0]
    assert "INSERT INTO users" in sql
    assert "ON CONFLICT (username) DO UPDATE" in sql
    assert params == ("admin", "hash", "admin", None, True)
