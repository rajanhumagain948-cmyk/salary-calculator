from pathlib import Path


DASHBOARD = Path(__file__).resolve().parents[1] / "frontend/app/dashboard/page.tsx"


def test_dashboard_uses_admin_page_heading_style():
    source = DASHBOARD.read_text(encoding="utf-8")

    assert 'letterSpacing: ".12em"' in source
    assert '<h1 style={{ margin: "7px 0 5px", fontSize: 30 }}>' in source
    assert '<p style={{ margin: 0, color: "#8298ae", fontSize: 12 }}>' in source
