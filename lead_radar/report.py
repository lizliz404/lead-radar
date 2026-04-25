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
    lines.append("## 今日判断")
    lines.append("")
    if strong:
        lines.append(f"发现 {strong} 条强付费/外包意图信号，建议优先人工复核。")
    elif medium:
        lines.append(f"未发现强付费信号，但有 {medium} 条中等需求信号，可作为选题或潜在线索复核。")
    elif result.signals:
        lines.append("发现少量弱信号，更适合做趋势观察，不建议立即触达。")
    else:
        lines.append("本次未发现值得行动的高信号线索。")
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

    lines.append("## 复盘问题")
    lines.append("")
    lines.append("1. Top 10 里有多少条值得点开？")
    lines.append("2. 哪些关键词带来了噪音？")
    lines.append("3. 哪些 subreddit 的信号质量最高？")
    lines.append("4. 是否需要增加/删除 include_phrases 或 exclude_phrases？")
    lines.append("")
    return "\n".join(lines)


def write_report(markdown: str, output_dir: str | Path, topic_name: str) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"{topic_name}-{timestamp}.md"
    path.write_text(markdown, encoding="utf-8")
    return path
