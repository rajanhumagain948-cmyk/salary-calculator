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


def test_postgres_repository_returns_default_company_when_not_saved():
    class FakeResult:
        def fetchone(self):
            return None

    class FakeConnection:
        def execute(self, sql, params=None):
            if "SELECT payload" in sql:
                return FakeResult()
            return self

        def commit(self):
            pass

    repo = PostgresPayrollRepository(connection=FakeConnection())

    company = repo.company()

    assert company.name == ""
    assert company.address == ""
    assert company.representative == ""
    assert company.hourly_paid_leave_enabled is False
    assert company.hourly_paid_leave_unit_hours == 1
    assert company.hourly_paid_leave_year_start_month == 4
    assert company.hourly_paid_leave_year_start_day == 1


def test_postgres_repository_loads_saved_company():
    class FakeResult:
        def fetchone(self):
            return (
                '{"name":"Example","address":"Tokyo","representative":"Taro",'
                '"hourly_paid_leave_enabled":true,'
                '"hourly_paid_leave_unit_hours":2,'
                '"hourly_paid_leave_year_start_month":1,'
                '"hourly_paid_leave_year_start_day":10}',
            )

    class FakeConnection:
        def execute(self, sql, params=None):
            if "SELECT payload" in sql:
                return FakeResult()
            return self

        def commit(self):
            pass

    repo = PostgresPayrollRepository(connection=FakeConnection())

    company = repo.company()

    assert company.name == "Example"
    assert company.address == "Tokyo"
    assert company.representative == "Taro"
    assert company.hourly_paid_leave_enabled is True
    assert company.hourly_paid_leave_unit_hours == 2
    assert company.hourly_paid_leave_year_start_month == 1
    assert company.hourly_paid_leave_year_start_day == 10


def test_postgres_repository_saves_company_with_upsert():
    from models.company import Company

    executed = []

    class FakeConnection:
        def execute(self, sql, params=None):
            executed.append((sql, params))
            return self

        def commit(self):
            pass

    repo = PostgresPayrollRepository(connection=FakeConnection())
    executed.clear()

    repo.save_company(
        Company(
            name="Example",
            address="Tokyo",
            representative="Taro",
        )
    )

    sql, params = executed[0]
    assert "INSERT INTO settings" in sql
    assert "ON CONFLICT (key) DO UPDATE" in sql
    assert params[0] == "company"
    assert '"name": "Example"' in params[1]
    assert '"address": "Tokyo"' in params[1]
    assert '"representative": "Taro"' in params[1]


def test_postgres_repository_initializes_audit_log_table():
    executed = []

    class FakeConnection:
        def execute(self, sql, params=None):
            executed.append((sql, params))
            return self

        def commit(self):
            pass

    PostgresPayrollRepository(connection=FakeConnection())

    assert any(
        "CREATE TABLE IF NOT EXISTS audit_log" in sql
        for sql, _ in executed
    )


def test_postgres_repository_saves_audit_log():
    executed = []

    class FakeConnection:
        def execute(self, sql, params=None):
            executed.append((sql, params))
            return self

        def commit(self):
            pass

    repo = PostgresPayrollRepository(connection=FakeConnection())
    executed.clear()

    repo.audit(
        "会社情報保存",
        "company",
        "Example",
    )

    sql, params = executed[0]
    assert "INSERT INTO audit_log" in sql
    assert "VALUES (%s, %s, %s, %s)" in sql
    assert params[1:] == (
        "会社情報保存",
        "company",
        "Example",
    )
