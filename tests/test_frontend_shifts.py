from pathlib import Path


SHIFTS = Path(__file__).resolve().parents[1] / "frontend/app/shifts/page.tsx"


def test_shifts_page_is_guarded_for_employee():
    source = SHIFTS.read_text(encoding="utf-8")

    assert 'import AuthGuard from "@/components/auth/AuthGuard";' in source
    assert '<AuthGuard allow={["employee"]}>' in source
    assert "</AuthGuard>" in source
