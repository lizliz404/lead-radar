from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from lead_radar.feishu import FeishuWebhookClient
from lead_radar.telegram import TelegramBotClient


@dataclass(frozen=True)
class NotificationPayload:
    markdown: str
    summary: str
    report_path: Path


class Notifier(Protocol):
    def send(self, payload: NotificationPayload) -> None:
        ...


class TelegramNotifier:
    def __init__(self, client: TelegramBotClient | None = None) -> None:
        self.client = client or TelegramBotClient()

    def send(self, payload: NotificationPayload) -> None:
        self.client.send_text(payload.markdown)


class FeishuNotifier:
    def __init__(self, client: FeishuWebhookClient | None = None) -> None:
        self.client = client or FeishuWebhookClient()

    def send(self, payload: NotificationPayload) -> None:
        self.client.send_text(payload.summary)


def resolve_notify_channels(
    notify: str | None,
    *,
    send_feishu: bool = False,
    send_telegram: bool = False,
) -> list[str]:
    channels: list[str] = []
    if notify:
        channels.extend(item.strip().lower() for item in notify.split(",") if item.strip())
    if send_feishu:
        channels.append("feishu")
    if send_telegram:
        channels.append("telegram")

    deduped: list[str] = []
    for channel in channels:
        if channel not in deduped:
            deduped.append(channel)
    return deduped


def send_notifications(channels: list[str], payload: NotificationPayload) -> None:
    for channel in channels:
        get_notifier(channel).send(payload)


def get_notifier(channel: str) -> Notifier:
    normalized = channel.strip().lower()
    if normalized == "telegram":
        return TelegramNotifier()
    if normalized == "feishu":
        return FeishuNotifier()
    raise ValueError(f"Unsupported notify channel: {channel}. Available: telegram, feishu")
