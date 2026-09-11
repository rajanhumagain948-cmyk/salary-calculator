from __future__ import annotations

import json
import os
from collections.abc import Callable
from functools import partial
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


PostJson = Callable[[str, dict[str, Any]], dict[str, Any]]


def _post_json(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: float = 60,
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class OllamaAssistant:
    def __init__(
        self,
        *,
        model: str = "qwen3:8b",
        base_url: str = "http://localhost:11434",
        post_json: PostJson = _post_json,
        timeout_seconds: float = 60,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.post_json = (
            partial(_post_json, timeout=timeout_seconds)
            if post_json is _post_json
            else post_json
        )

    @classmethod
    def from_env(cls) -> "OllamaAssistant":
        try:
            timeout_seconds = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
        except ValueError:
            timeout_seconds = 60

        if timeout_seconds <= 0:
            timeout_seconds = 60

        return cls(
            model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
            base_url=os.getenv(
                "OLLAMA_BASE_URL",
                "http://localhost:11434",
            ),
            timeout_seconds=timeout_seconds,
        )

    def is_available(self) -> bool:
        request = Request(
            f"{self.base_url}/api/tags",
            method="GET",
        )

        try:
            with urlopen(request, timeout=2):
                return True
        except (OSError, URLError):
            return False

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
