from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console

from lead_radar.config import load_config
from lead_radar.llm import LLMReranker
from lead_radar.models import RawPost, ScanResult
from lead_radar.notifier import NotificationPayload, resolve_notify_channels, send_notifications
from lead_radar.reddit import RedditClient
from lead_radar.report import build_markdown_report, write_report
from lead_radar.scoring import score_posts
from lead_radar.storage import SQLiteStore

app = typer.Typer(help="Lead Radar: social demand signal radar")
console = Console()


@app.command()
def run(
    config: Annotated[str, typer.Option("--config", "-c")] = "config.yaml",
    topic: Annotated[str, typer.Option("--topic", "-t")] = "paid_demand_signals",
    mock: Annotated[bool, typer.Option("--mock", help="Use examples/sample_posts.json")] = False,
    output_dir: Annotated[str, typer.Option("--output-dir", "-o")] = "reports",
    db_path: Annotated[str | None, typer.Option("--db-path")] = None,
    notify: Annotated[str | None, typer.Option("--notify")] = None,
    send_feishu: Annotated[bool, typer.Option("--send-feishu")] = False,
    send_telegram: Annotated[bool, typer.Option("--send-telegram")] = False,
    llm_rerank: Annotated[bool, typer.Option("--llm-rerank")] = False,
    llm_candidate_limit: Annotated[int, typer.Option("--llm-candidate-limit")] = 20,
) -> None:
    """Run one scan and generate a Markdown report."""

    load_dotenv()
    app_config = load_config(config)
    topic_config = app_config.get_topic(topic)

    if mock:
        posts = load_mock_posts()
        console.print(f"[yellow]Loaded {len(posts)} mock posts[/yellow]")
    else:
        reddit = RedditClient()
        posts = reddit.search_topic(topic_config)
        console.print(f"[green]Fetched {len(posts)} Reddit posts[/green]")

    rule_limit = llm_candidate_limit if llm_rerank else None
    signals = score_posts(posts, topic_config, limit=rule_limit)
    if llm_rerank:
        signals = LLMReranker().rerank(signals, topic_config)
        console.print(f"[green]LLM reranked signals:[/green] {len(signals)}")

    result = ScanResult(
        topic_name=topic_config.name,
        scanned_at=datetime.now(timezone.utc),
        total_posts=len(posts),
        candidate_count=len(signals),
        signals=signals,
    )

    markdown = build_markdown_report(result, topic_config)
    report_path = write_report(markdown, output_dir=output_dir, topic_name=topic_config.name)
    result.report_path = str(report_path)

    store_path = db_path or os.getenv("LEAD_RADAR_DB_PATH") or "data/lead_radar.sqlite"
    store = SQLiteStore(store_path)
    run_id = store.save_scan_result(result)

    console.print(f"[bold green]Report written:[/bold green] {report_path}")
    console.print(f"[bold green]SQLite run id:[/bold green] {run_id}")
    console.print(f"[bold green]Signals:[/bold green] {len(signals)}")

    notify_channels = resolve_notify_channels(
        notify,
        send_feishu=send_feishu,
        send_telegram=send_telegram,
    )
    if notify_channels:
        summary = make_notification_summary(result, report_path)
        payload = NotificationPayload(markdown=markdown, summary=summary, report_path=report_path)
        try:
            send_notifications(notify_channels, payload)
        except Exception as exc:
            store.update_notification_status(
                run_id,
                status="failed",
                channels=notify_channels,
                error=str(exc),
            )
            raise
        store.update_notification_status(run_id, status="sent", channels=notify_channels)
        console.print(f"[bold green]Notifications sent:[/bold green] {', '.join(notify_channels)}")


def load_mock_posts(path: str | Path = "examples/sample_posts.json") -> list[RawPost]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [RawPost.model_validate(item) for item in payload]


def make_notification_summary(result: ScanResult, report_path: Path) -> str:
    strong = sum(1 for item in result.signals if item.buying_intent == "strong")
    lines = [
        f"Lead Radar: {result.topic_name}",
        f"Posts fetched: {result.total_posts}",
        f"Signals: {result.candidate_count}",
        f"Strong intent: {strong}",
        f"Report: {report_path}",
        "",
    ]
    for index, signal in enumerate(result.signals[:5], start=1):
        lines.append(f"{index}. [{signal.buying_intent}] {signal.post.title}")
        lines.append(f"   score={signal.score} community={signal.post.community}")
        lines.append(f"   {signal.post.url}")
    return "\n".join(lines)


@app.command("topics")
def list_topics(
    config: Annotated[str, typer.Option("--config", "-c")] = "config.yaml",
) -> None:
    """List configured topics."""
    app_config = load_config(config)
    for item in app_config.topics:
        console.print(f"[bold]{item.name}[/bold] - {item.description}")


if __name__ == "__main__":
    app()
