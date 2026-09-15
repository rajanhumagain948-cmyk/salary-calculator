from pathlib import Path


APP_SHELL = Path(__file__).resolve().parents[1] / "frontend/components/AppShell.tsx"


def test_completed_ai_assistant_is_not_marked_coming_soon():
    source = APP_SHELL.read_text(encoding="utf-8")

    assert "<strong>AIアシスタント</strong>" in source
    assert "<span>近日公開</span>" not in source
