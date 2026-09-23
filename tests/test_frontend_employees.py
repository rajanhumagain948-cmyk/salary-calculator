from pathlib import Path


EMPLOYEES = Path(__file__).resolve().parents[1] / "frontend/app/employees/page.tsx"


def test_employees_page_is_guarded_for_admin():
    source = EMPLOYEES.read_text(encoding="utf-8")

    assert 'import AuthGuard from "@/components/auth/AuthGuard";' in source
    assert '<AuthGuard allow={["admin"]}>' in source
    assert "</AuthGuard>" in source
