from __future__ import annotations

import os
from collections.abc import Iterable

import httpx

TELEGRAM_TEXT_LIMIT = 4096
SAFE_CHUNK_SIZE = 3800


class TelegramBotClient:
    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.timeout = timeout

    def send_text(self, text: str) -> None:
        if not self.bot_token:
            raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
        if not self.chat_id:
            raise RuntimeError("Missing TELEGRAM_CHAT_ID")

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        with httpx.Client(timeout=self.timeout) as client:
            for chunk in split_telegram_text(text):
                self._send_chunk(client, url, chunk)

    def _send_chunk(self, client: httpx.Client, url: str, text: str) -> None:
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        response = client.post(url, json=payload)
        response.raise_for_status()


def split_telegram_text(text: str) -> Iterable[str]:
    if len(text) <= TELEGRAM_TEXT_LIMIT:
        yield text
        return

    remaining = text
    while remaining:
        if len(remaining) <= TELEGRAM_TEXT_LIMIT:
            yield remaining
            return

        split_at = remaining.rfind("\n\n", 0, SAFE_CHUNK_SIZE)
        if split_at == -1:
            split_at = remaining.rfind("\n", 0, SAFE_CHUNK_SIZE)
        if split_at == -1:
            split_at = SAFE_CHUNK_SIZE

        chunk = remaining[:split_at].strip()
        if chunk:
            yield chunk
        remaining = remaining[split_at:].strip()
