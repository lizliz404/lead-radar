from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from lead_radar.config import load_config
from lead_radar.llm import LLMReportGenerator, LLMReranker
from lead_radar.models import RawPost, ScanResult, TopicConfig
from lead_radar.reddit import RedditClient
from lead_radar.report import build_markdown_report, write_report
from lead_radar.scoring import score_posts
from lead_radar.storage import SQLiteStore


def load_mock_posts(path: str | Path = "examples/sample_posts.json") -> list[RawPost]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [RawPost.model_validate(item) for item in payload]


def run_scan(
    *,
    config_path: str | Path = "config.yaml",
    topic_name: str = "paid_demand_signals",
    mock: bool = False,
    mock_posts_path: str | Path = "examples/sample_posts.json",
    output_dir: str | Path = "reports",
    db_path: str | Path | None = None,
    llm_rerank: bool = False,
    llm_report: bool = False,
    llm_candidate_limit: int = 20,
    persist: bool = True,
) -> tuple[ScanResult, str, int | None]:
    app_config = load_config(config_path)
    topic_config = app_config.get_topic(topic_name)
    return run_topic_scan(
        topic_config=topic_config,
        mock=mock,
        mock_posts_path=mock_posts_path,
        output_dir=output_dir,
        db_path=db_path,
        llm_rerank=llm_rerank,
        llm_report=llm_report,
        llm_candidate_limit=llm_candidate_limit,
        persist=persist,
    )


def run_topic_scan(
    *,
    topic_config: TopicConfig,
    mock: bool = False,
    mock_posts_path: str | Path = "examples/sample_posts.json",
    output_dir: str | Path = "reports",
    db_path: str | Path | None = None,
    llm_rerank: bool = False,
    llm_report: bool = False,
    llm_candidate_limit: int = 20,
    persist: bool = True,
) -> tuple[ScanResult, str, int | None]:
    posts = load_mock_posts(mock_posts_path) if mock else RedditClient().search_topic(topic_config)

    rule_limit = llm_candidate_limit if llm_rerank else None
    signals = score_posts(posts, topic_config, limit=rule_limit)
    if llm_rerank:
        signals = LLMReranker().rerank(signals, topic_config)

    result = ScanResult(
        topic_name=topic_config.name,
        scanned_at=datetime.now(timezone.utc),
        total_posts=len(posts),
        candidate_count=len(signals),
        signals=signals,
    )

    if llm_report:
        markdown = LLMReportGenerator().generate(result.signals, topic_config)
    else:
        markdown = build_markdown_report(result, topic_config)

    report_path = write_report(markdown, output_dir=output_dir, topic_name=topic_config.name)
    result.report_path = str(report_path)

    run_id: int | None = None
    if persist:
        store_path = db_path or os.getenv("LEAD_RADAR_DB_PATH") or "data/lead_radar.sqlite"
        run_id = SQLiteStore(store_path).save_scan_result(result)

    return result, markdown, run_id
