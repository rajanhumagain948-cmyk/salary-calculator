from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMPLOYEES_LAYOUT = ROOT / "frontend/app/employees/layout.tsx"
EMPLOYEES_PAGE = ROOT / "frontend/app/employees/page.tsx"


def test_employees_route_is_guarded_once_by_admin_layout():
    layout = EMPLOYEES_LAYOUT.read_text(encoding="utf-8")
    page = EMPLOYEES_PAGE.read_text(encoding="utf-8")

    assert '<AuthGuard allow={["admin"]}>' in layout
    assert 'import AuthGuard from "@/components/auth/AuthGuard";' not in page
    assert '<AuthGuard allow={["admin"]}>' not in page
