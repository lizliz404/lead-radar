from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console

from lead_radar.config import load_config
from lead_radar.ingest import score_ingested_posts
from lead_radar.models import ScanResult
from lead_radar.notifier import NotificationPayload, resolve_notify_channels, send_notifications
from lead_radar.service import run_scan
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
    llm_report: Annotated[bool, typer.Option("--llm-report")] = False,
    llm_candidate_limit: Annotated[int, typer.Option("--llm-candidate-limit")] = 20,
) -> None:
    """Run one scan and generate a Markdown report."""

    load_dotenv()
    store_path = db_path or os.getenv("LEAD_RADAR_DB_PATH") or "data/lead_radar.sqlite"
    result, markdown, run_id = run_scan(
        config_path=config,
        topic_name=topic,
        mock=mock,
        output_dir=output_dir,
        db_path=store_path,
        llm_rerank=llm_rerank,
        llm_report=llm_report,
        llm_candidate_limit=llm_candidate_limit,
    )
    report_path = Path(result.report_path or "")

    if mock:
        console.print(f"[yellow]Loaded {result.total_posts} mock posts[/yellow]")
    else:
        console.print(f"[green]Fetched {result.total_posts} posts[/green]")
    if llm_rerank:
        console.print(f"[green]LLM reranked signals:[/green] {len(result.signals)}")
    if llm_report:
        console.print("[green]LLM generated strategic report[/green]")

    console.print(f"[bold green]Report written:[/bold green] {report_path}")
    console.print(f"[bold green]SQLite run id:[/bold green] {run_id}")
    console.print(f"[bold green]Signals:[/bold green] {len(result.signals)}")

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
            assert run_id is not None
            SQLiteStore(store_path).update_notification_status(
                run_id,
                status="failed",
                channels=notify_channels,
                error=str(exc),
            )
            raise
        assert run_id is not None
        SQLiteStore(store_path).update_notification_status(run_id, status="sent", channels=notify_channels)
        console.print(f"[bold green]Notifications sent:[/bold green] {', '.join(notify_channels)}")


def make_notification_summary(result: ScanResult, report_path: Path) -> str:
    strong = sum(1 for item in result.signals if item.signal_strength == "strong")
    lines = [
        f"Lead Radar: {result.topic_name}",
        f"Posts fetched: {result.total_posts}",
        f"Signals: {result.candidate_count}",
        f"Strong signals: {strong}",
        f"Report: {report_path}",
        "",
    ]
    for index, signal in enumerate(result.signals[:5], start=1):
        lines.append(f"{index}. [{signal.signal_strength}] {signal.post.title}")
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


@app.command("score-ingested")
def score_ingested(
    config: Annotated[str, typer.Option("--config", "-c")] = "config.yaml",
    topic: Annotated[str, typer.Option("--topic", "-t")] = "paid_demand_signals",
    output_dir: Annotated[str, typer.Option("--output-dir", "-o")] = "reports",
    db_path: Annotated[str | None, typer.Option("--db-path")] = None,
    source: Annotated[list[str] | None, typer.Option("--source")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=1000)] = 200,
) -> None:
    """Score already-ingested third-party alerts and generate a normal report."""
    load_dotenv()
    store_path = db_path or os.getenv("LEAD_RADAR_DB_PATH") or "data/lead_radar.sqlite"
    sources = source or None
    result, _markdown, run_id = score_ingested_posts(
        config_path=config,
        topic_name=topic,
        db_path=store_path,
        output_dir=output_dir,
        sources=sources,
        limit=limit,
    )
    console.print(f"[bold green]Ingested posts scored:[/bold green] {result.total_posts}")
    console.print(f"[bold green]Report written:[/bold green] {result.report_path}")
    console.print(f"[bold green]SQLite run id:[/bold green] {run_id}")
    console.print(f"[bold green]Signals:[/bold green] {len(result.signals)}")


@app.command("review")
def review_signal(
    run_id: Annotated[int, typer.Option("--run-id")],
    source: Annotated[str, typer.Option("--source")] = "reddit",
    source_id: Annotated[str, typer.Option("--source-id")] = "",
    status: Annotated[
        str,
        typer.Option("--status", help="new/useful/not_useful/contacted/replied/converted"),
    ] = "useful",
    note: Annotated[str, typer.Option("--note")] = "",
    db_path: Annotated[str | None, typer.Option("--db-path")] = None,
) -> None:
    """Mark a candidate signal after manual review."""
    if not source_id:
        raise typer.BadParameter("--source-id is required")
    allowed = {"new", "useful", "not_useful", "contacted", "replied", "converted"}
    if status not in allowed:
        raise typer.BadParameter(f"--status must be one of: {', '.join(sorted(allowed))}")

    store_path = db_path or os.getenv("LEAD_RADAR_DB_PATH") or "data/lead_radar.sqlite"
    SQLiteStore(store_path).update_signal_review(
        run_id=run_id,
        source=source,
        source_id=source_id,
        status=status,
        note=note,
    )
    console.print(f"[green]Review saved:[/green] run={run_id} {source}:{source_id} status={status}")


@app.command("review-summary")
def review_summary(
    run_id: Annotated[int | None, typer.Option("--run-id")] = None,
    db_path: Annotated[str | None, typer.Option("--db-path")] = None,
) -> None:
    """Show reviewed-vs-useful counts for validation tracking."""
    store_path = db_path or os.getenv("LEAD_RADAR_DB_PATH") or "data/lead_radar.sqlite"
    summary = SQLiteStore(store_path).get_review_summary(run_id)
    console.print(f"[bold]Review summary[/bold] db={store_path} run={run_id or 'all'}")
    console.print(f"Total signals: {summary['total']}")
    console.print(f"Reviewed: {summary['reviewed']}")
    console.print(f"Positive: {summary['positive']}")
    console.print(f"Positive rate: {summary['positive_rate']:.0%}")
    for status, count in dict(summary["by_status"]).items():
        console.print(f"- {status}: {count}")


if __name__ == "__main__":
    app()
