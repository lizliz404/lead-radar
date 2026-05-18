from __future__ import annotations

from datetime import datetime, timezone

from lead_radar.config import load_config
from lead_radar.models import IngestedAlert, RawPost, ScanResult
from lead_radar.report import build_markdown_report, write_report
from lead_radar.scoring import score_posts
from lead_radar.storage import SQLiteStore


def ingest_alerts(
    alerts: list[IngestedAlert],
    *,
    db_path: str,
    batch_name: str | None = None,
) -> dict[str, object]:
    """Persist normalized third-party alerts without tying the app to one vendor."""

    posts = [alert.to_raw_post() for alert in alerts]
    store = SQLiteStore(db_path)
    inserted, updated = store.upsert_ingested_posts(posts)
    return {
        "status": "ok",
        "batch_name": batch_name,
        "received": len(alerts),
        "inserted": inserted,
        "updated": updated,
        "source_counts": count_sources(posts),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


def score_ingested_posts(
    *,
    config_path: str,
    topic_name: str,
    db_path: str,
    output_dir: str = "reports",
    sources: list[str] | None = None,
    limit: int = 200,
) -> tuple[ScanResult, str, int]:
    """Score already-ingested posts and save a normal scan run/report."""

    topic = load_config(config_path).get_topic(topic_name)
    posts = SQLiteStore(db_path).list_posts(sources=sources, topic_name=topic_name, limit=limit)
    signals = score_posts(posts, topic)
    result = ScanResult(
        topic_name=topic.name,
        scanned_at=datetime.now(timezone.utc),
        total_posts=len(posts),
        candidate_count=len(signals),
        signals=signals,
    )
    markdown = build_markdown_report(result, topic)
    report_path = write_report(markdown, output_dir=output_dir, topic_name=f"{topic.name}-ingested")
    result.report_path = str(report_path)
    run_id = SQLiteStore(db_path).save_scan_result(result)
    return result, markdown, run_id


def count_sources(posts: list[RawPost]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for post in posts:
        counts[post.source] = counts.get(post.source, 0) + 1
    return counts
