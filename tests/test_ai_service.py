from services.ai_service import OllamaAssistant


def test_ollama_assistant_returns_message_content():
    captured = {}

    def fake_post(url, payload):
        captured["url"] = url
        captured["payload"] = payload
        return {
            "message": {
                "role": "assistant",
                "content": "給与の確認結果です。",
            }
        }

    assistant = OllamaAssistant(
        model="qwen3:8b",
        base_url="http://localhost:11434",
        post_json=fake_post,
    )

    answer = assistant.chat("今月の給与を確認して")

    assert answer == "給与の確認結果です。"
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["payload"]["model"] == "qwen3:8b"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["messages"] == [
        {
            "role": "user",
            "content": "今月の給与を確認して",
        }
    ]
