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


def test_postgres_repository_loads_user():
    executed = []

    class FakeResult:
        def fetchone(self):
            return ("admin", "hash", "admin", None, True)

    class FakeConnection:
        def execute(self, sql, params=None):
            executed.append((sql, params))
            if "SELECT username" in sql:
                return FakeResult()
            return self

        def commit(self):
            pass

    repo = PostgresPayrollRepository(connection=FakeConnection())
    user = repo.user("admin")

    assert user is not None
    assert user.username == "admin"
    assert user.password_hash == "hash"
    assert user.role == "admin"
    assert user.employee_id is None
    assert user.active is True
    assert executed[-1][1] == ("admin",)


def test_postgres_repository_can_connect_from_database_url():
    captured = {}

    class FakeConnection:
        def execute(self, sql, params=None):
            return self

        def commit(self):
            pass

    connection = FakeConnection()

    def fake_connect(database_url):
        captured["database_url"] = database_url
        return connection

    PostgresPayrollRepository.from_database_url(
        "postgresql://user:password@db.example.com/payroll",
        connect=fake_connect,
    )

    assert captured["database_url"] == (
        "postgresql://user:password@db.example.com/payroll"
    )


def test_postgres_repository_initializes_settings_table():
    executed = []

    class FakeConnection:
        def execute(self, sql, params=None):
            executed.append((sql, params))
            return self

        def commit(self):
            pass

    PostgresPayrollRepository(connection=FakeConnection())

    assert any(
        "CREATE TABLE IF NOT EXISTS settings" in sql
        for sql, _ in executed
    )
