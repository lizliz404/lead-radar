from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from lead_radar.models import ScanResult, TopicConfig


def build_markdown_report(result: ScanResult, topic: TopicConfig) -> str:
    strong = sum(1 for item in result.signals if item.buying_intent == "strong")
    medium = sum(1 for item in result.signals if item.buying_intent == "medium")

    lines: list[str] = []
    lines.append(f"# Lead Radar Report: {topic.name}")
    lines.append("")
    lines.append(f"- Scanned at: {result.scanned_at.isoformat()}")
    lines.append(f"- Topic: {topic.description}")
    lines.append(f"- Total posts fetched: {result.total_posts}")
    lines.append(f"- Candidate signals: {result.candidate_count}")
    lines.append(f"- Strong intent: {strong}")
    lines.append(f"- Medium intent: {medium}")
    lines.append("")
    lines.append("## Daily Judgment")
    lines.append("")
    if strong:
        lines.append(f"Found {strong} strong payment or outsourcing intent signals. Review these first.")
    elif medium:
        lines.append(f"No strong payment signals found, but {medium} medium-intent signals may be useful leads.")
    elif result.signals:
        lines.append("Found weak signals. Treat them as trend observations, not immediate outreach targets.")
    else:
        lines.append("No high-signal actionable leads were found in this run.")
    lines.append("")
    lines.append("## Top Leads")
    lines.append("")

    for index, signal in enumerate(result.signals, start=1):
        post = signal.post
        lines.append(f"### {index}. {post.title}")
        lines.append("")
        lines.append(f"- Source: {post.source} / {post.community or 'unknown'}")
        lines.append(f"- Score: {signal.score}")
        lines.append(f"- Confidence: {signal.confidence}")
        lines.append(f"- Buying intent: {signal.buying_intent}")
        lines.append(f"- Created at: {post.created_at.isoformat()}")
        lines.append(f"- Upvotes / comments: {post.upvotes} / {post.num_comments}")
        lines.append(f"- Pain: {signal.pain_summary}")
        lines.append(f"- Recommended action: {signal.recommended_action}")
        if signal.evidence:
            lines.append(f"- Evidence: {', '.join(signal.evidence)}")
        if signal.tags:
            lines.append(f"- Tags: {', '.join(signal.tags)}")
        lines.append(f"- URL: {post.url}")
        lines.append("")

    lines.append("## Review Questions")
    lines.append("")
    lines.append("1. How many Top 10 leads are worth opening?")
    lines.append("2. Which keywords created noise?")
    lines.append("3. Which subreddits produced the highest-quality signals?")
    lines.append("4. Should any include_phrases or exclude_phrases be added or removed?")
    lines.append("")
    return "\n".join(lines)


def write_report(markdown: str, output_dir: str | Path, topic_name: str) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"{topic_name}-{timestamp}.md"
    path.write_text(markdown, encoding="utf-8")
    return path
