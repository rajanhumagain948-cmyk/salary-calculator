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


def test_ollama_assistant_can_send_conversation_messages():
    captured = {}

    def fake_post(url, payload):
        captured["payload"] = payload
        return {
            "message": {
                "role": "assistant",
                "content": "続きの回答です。",
            }
        }

    assistant = OllamaAssistant(post_json=fake_post)

    answer = assistant.chat_messages(
        [
            {"role": "user", "content": "9月の状況を教えて"},
            {"role": "assistant", "content": "給与確定は3件です。"},
            {"role": "user", "content": "その中で問題は？"},
        ]
    )

    assert answer == "続きの回答です。"
    assert captured["payload"]["messages"] == [
        {"role": "user", "content": "9月の状況を教えて"},
        {"role": "assistant", "content": "給与確定は3件です。"},
        {"role": "user", "content": "その中で問題は？"},
    ]


def test_ollama_assistant_can_load_configuration_from_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "llama3:latest")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11435/")

    assistant = OllamaAssistant.from_env()

    assert assistant.model == "llama3:latest"
    assert assistant.base_url == "http://127.0.0.1:11435"
