from pathlib import Path


MY_AI = Path(__file__).resolve().parents[1] / "frontend/app/my-ai/page.tsx"


def test_my_ai_uses_dedicated_ai_heading_style():
    source = MY_AI.read_text(encoding="utf-8")

    assert 'letterSpacing: "0.16em"' in source
    assert 'fontSize: "clamp(26px, 4vw, 38px)"' in source
    assert 'letterSpacing: "-0.03em"' in source
    assert 'margin: "5px 0 7px"' in source
