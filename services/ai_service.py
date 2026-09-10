from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any
from urllib.request import Request, urlopen


PostJson = Callable[[str, dict[str, Any]], dict[str, Any]]


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


class OllamaAssistant:
    def __init__(
        self,
        *,
        model: str = "qwen3:8b",
        base_url: str = "http://localhost:11434",
        post_json: PostJson = _post_json,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.post_json = post_json

    @classmethod
    def from_env(cls) -> "OllamaAssistant":
        return cls(
            model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
            base_url=os.getenv(
                "OLLAMA_BASE_URL",
                "http://localhost:11434",
            ),
        )

    def chat(self, message: str) -> str:
        return self.chat_messages(
            [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        )

    def chat_messages(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        response = self.post_json(
            f"{self.base_url}/api/chat",
            {
                "model": self.model,
                "messages": messages,
                "stream": False,
            },
        )

        return str(response["message"]["content"])
