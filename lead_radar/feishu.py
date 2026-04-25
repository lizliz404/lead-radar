from __future__ import annotations

import os

import httpx


class FeishuWebhookClient:
    def __init__(self, webhook_url: str | None = None, timeout: float = 20.0) -> None:
        self.webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL")
        self.timeout = timeout

    def send_text(self, text: str) -> None:
        if not self.webhook_url:
            raise RuntimeError("Missing FEISHU_WEBHOOK_URL")

        # Feishu custom bot text payload.
        # Long reports should be stored as Markdown files; webhook receives the summary.
        payload = {
            "msg_type": "text",
            "content": {
                "text": text[:3500],
            },
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.webhook_url, json=payload)
            response.raise_for_status()
