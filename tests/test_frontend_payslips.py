from pathlib import Path


PAYSLIPS = Path(__file__).resolve().parents[1] / "frontend/app/payslips/page.tsx"


def test_payslips_uses_employee_heading_style():
    source = PAYSLIPS.read_text(encoding="utf-8")

    assert "fontSize: 11" in source
    assert '<h1 style={{ margin: "7px 0 5px", fontSize: 30 }}>' in source
    assert '<p style={{ margin: 0, color: "#8298ae", fontSize: 12 }}>' in source
