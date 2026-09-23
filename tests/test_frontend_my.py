from pathlib import Path


MY_PAGE = Path(__file__).resolve().parents[1] / "frontend/app/my/page.tsx"


def test_my_page_uses_employee_heading_style():
    source = MY_PAGE.read_text(encoding="utf-8")

    assert 'letterSpacing: ".12em"' in source
    assert '<h1 style={{ margin: "7px 0 5px", fontSize: 30 }}>' in source
    assert '<p style={{ margin: 0, color: "#8298ae", fontSize: 12 }}>' in source
