from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from lead_radar.models import ScanResult, TopicConfig

REPORT_PROFILES = {
    "lead": {
        "title": "Lead Radar Report",
        "top_heading": "Top Leads",
        "intent_label": "Buying intent",
        "positive": "strong payment or outsourcing intent signals. Review these first.",
        "medium": "medium-intent signals may be useful leads.",
        "weak": "Found weak signals. Treat them as trend observations, not immediate outreach targets.",
        "empty": "No high-signal actionable leads were found in this run.",
        "questions": [
            "How many Top 10 leads are worth opening?",
            "Which keywords created noise?",
            "Which subreddits produced the highest-quality signals?",
            "Should any include_phrases or exclude_phrases be added or removed?",
        ],
    },
    "idea": {
        "title": "Idea Hunt Report",
        "top_heading": "Top Idea Signals",
        "intent_label": "Opportunity strength",
        "positive": "strong idea signals. Review user, pain, workaround, and repeatability first.",
        "medium": "medium-strength idea signals may be useful validation targets.",
        "weak": "Found weak signals. Treat them as raw research, not product evidence.",
        "empty": "No strong idea signals were found in this run.",
        "questions": [
            "Which pains repeat across users or communities?",
            "Who is the actual user and current workaround?",
            "What would prove this idea useless within 7 days?",
            "Which keywords or communities created noise?",
        ],
    },
    "distribution": {
        "title": "Distribution Signal Report",
        "top_heading": "Top Distribution Signals",
        "intent_label": "Channel signal strength",
        "positive": "strong distribution signals. Review channel, audience, angle, and compliance risk first.",
        "medium": "medium-strength distribution signals may be worth one safe experiment.",
        "weak": "Found weak signals. Use them as market-language research only.",
        "empty": "No strong distribution signals were found in this run.",
        "questions": [
            "Which channels or communities repeat?",
            "What safe experiment can be run without spam or manipulation?",
            "What platform or compliance risk is visible?",
            "Which search terms created noise?",
        ],
    },
    "competitor_pain": {
        "title": "Competitor Pain Report",
        "top_heading": "Top Competitor Pain Signals",
        "intent_label": "Pain strength",
        "positive": "strong competitor pain signals. Review switching trigger and missing-feature evidence first.",
        "medium": "medium-strength complaint signals may inform positioning or comparison copy.",
        "weak": "Found weak signals. Treat them as objection language, not proof of demand.",
        "empty": "No strong competitor pain signals were found in this run.",
        "questions": [
            "Which competitors or categories repeat?",
            "What exact switching trigger appears?",
            "Is the complaint severe enough to change behavior?",
            "Which phrases created false positives?",
        ],
    },
    "alternative": {
        "title": "Alternative Request Report",
        "top_heading": "Top Alternative Requests",
        "intent_label": "Alternative intent",
        "positive": "strong alternative-request signals. Review incumbent, criteria, and switching context first.",
        "medium": "medium-strength alternative requests may inform positioning or feature gaps.",
        "weak": "Found weak signals. Use them as keyword and positioning research.",
        "empty": "No strong alternative requests were found in this run.",
        "questions": [
            "Which incumbents are users trying to replace?",
            "What criteria matter: price, privacy, features, support, or hosting?",
            "Is there repeated willingness to switch?",
            "Which communities produced the cleanest alternative requests?",
        ],
    },
}


def build_markdown_report(result: ScanResult, topic: TopicConfig) -> str:
    profile = REPORT_PROFILES[topic.intent_profile]
    strong = sum(1 for item in result.signals if item.signal_strength == "strong")
    medium = sum(1 for item in result.signals if item.signal_strength == "medium")

    lines: list[str] = []
    lines.append(f"# {profile['title']}: {topic.name}")
    lines.append("")
    lines.append(f"- Scanned at: {result.scanned_at.isoformat()}")
    lines.append(f"- Topic: {topic.description}")
    lines.append(f"- Intent profile: {topic.intent_profile}")
    lines.append(f"- Report goal: {topic.report_goal}")
    lines.append(f"- Total posts fetched: {result.total_posts}")
    lines.append(f"- Candidate signals: {result.candidate_count}")
    lines.append(f"- Strong signals: {strong}")
    lines.append(f"- Medium signals: {medium}")
    lines.append("")
    lines.append("## Daily Judgment")
    lines.append("")
    if strong:
        lines.append(f"Found {strong} {profile['positive']}")
    elif medium:
        lines.append(f"No strong signals found, but {medium} {profile['medium']}")
    elif result.signals:
        lines.append(profile["weak"])
    else:
        lines.append(profile["empty"])
    lines.append("")
    lines.append(f"## {profile['top_heading']}")
    lines.append("")

    for index, signal in enumerate(result.signals, start=1):
        post = signal.post
        lines.append(f"### {index}. {post.title}")
        lines.append("")
        lines.append(f"- Source: {post.source} / {post.community or 'unknown'}")
        lines.append(f"- Score: {signal.score}")
        lines.append(f"- Confidence: {signal.confidence}")
        lines.append(f"- {profile['intent_label']}: {signal.signal_strength}")
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
    for index, question in enumerate(profile["questions"], start=1):
        lines.append(f"{index}. {question}")
    lines.append("")
    return "\n".join(lines)


def write_report(markdown: str, output_dir: str | Path, topic_name: str) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"{topic_name}-{timestamp}.md"
    path.write_text(markdown, encoding="utf-8")
    return path
