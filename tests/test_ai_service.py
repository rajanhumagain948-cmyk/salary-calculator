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


def test_ollama_assistant_reports_availability(monkeypatch):
    assistant = OllamaAssistant(
        base_url="http://localhost:11434",
    )

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"models":[]}'

    def fake_urlopen(request, timeout):
        assert request.full_url == "http://localhost:11434/api/tags"
        assert timeout == 2
        return FakeResponse()

    monkeypatch.setattr(
        "services.ai_service.urlopen",
        fake_urlopen,
    )

    assert assistant.is_available() is True


def test_ollama_assistant_reports_unavailable_on_connection_error(monkeypatch):
    from urllib.error import URLError

    assistant = OllamaAssistant()

    def failing_urlopen(request, timeout):
        raise URLError("connection refused")

    monkeypatch.setattr(
        "services.ai_service.urlopen",
        failing_urlopen,
    )

    assert assistant.is_available() is False


def test_ollama_assistant_loads_timeout_from_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "30")

    assistant = OllamaAssistant.from_env()

    assert assistant.timeout_seconds == 30
