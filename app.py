from __future__ import annotations

import csv
import io
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from lead_radar.cli import load_mock_posts
from lead_radar.config import load_config
from lead_radar.llm import LLMIntentParser, LLMReportGenerator, LLMReranker, llm_is_configured
from lead_radar.models import LeadSignal, RedditSourceConfig, ScanResult, SourcesConfig, TopicConfig
from lead_radar.reddit import RedditClient
from lead_radar.report import build_markdown_report, write_report
from lead_radar.scoring import score_posts
from lead_radar.storage import SQLiteStore

APP_NAME = "Lead Radar"
DEFAULT_CONFIG_PATH = "config.example.yaml"
DEFAULT_OUTPUT_DIR = "reports"
DEFAULT_DB_PATH = "data/lead_radar.sqlite"
REVIEW_STATUSES = ["new", "useful", "not_useful", "contacted", "replied", "converted"]

DEFAULT_CUSTOM_SUBREDDITS = [
    "smallbusiness",
    "entrepreneur",
    "SaaS",
    "startups",
    "marketing",
    "productmanagement",
]

MARKET_BRIEF_EXAMPLES = [
    "I want to research Shopify sellers who struggle with inventory forecasting and cash-flow planning.",
    "Find demand signals from indie hackers looking for better Stripe analytics, churn alerts, or revenue dashboards.",
    "Analyze pain points from US pet owners dealing with insurance claims, denied reimbursements, and high vet bills.",
    "I am exploring an AI note-taking product for consultants who turn client calls into proposals and follow-up tasks.",
    "Find small-business owners complaining about manual reporting, spreadsheet workflows, and Zapier limits.",
]

DEFAULT_INTENT_PHRASES = [
    "need help",
    "looking for help",
    "can someone recommend",
    "is there a tool",
    "alternative to",
    "willing to pay",
    "paid help",
    "hire someone",
    "too much manual work",
    "manual process",
    "spreadsheet",
]

DEFAULT_EXCLUDE_PHRASES = ["course", "affiliate", "giveaway", "job posting", "hiring full-time"]

STOP_WORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "better",
    "can",
    "dealing",
    "find",
    "for",
    "from",
    "help",
    "into",
    "looking",
    "make",
    "market",
    "owners",
    "people",
    "product",
    "research",
    "signals",
    "that",
    "the",
    "their",
    "this",
    "tools",
    "want",
    "who",
    "with",
}

SECRET_KEYS = [
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_ACCESS_TOKEN",
    "REDDIT_USER_AGENT",
    "LEAD_RADAR_LLM_API_KEY",
    "LEAD_RADAR_LLM_BASE_URL",
    "LEAD_RADAR_LLM_MODEL",
]


def load_runtime_secrets() -> None:
    """Allow Streamlit Cloud secrets to populate the existing env-based pipeline."""
    load_dotenv()
    for key in SECRET_KEYS:
        if os.getenv(key):
            continue
        try:
            value = st.secrets.get(key)
        except Exception:
            value = None
        if value:
            os.environ[key] = str(value)


@st.cache_data(show_spinner=False)
def cached_topic_names(config_path: str) -> list[str]:
    return [topic.name for topic in load_config(config_path).topics]


def run_scan(
    *,
    config_path: str,
    topic_name: str,
    custom_topic: TopicConfig | None = None,
    use_mock: bool,
    output_dir: str,
    db_path: str,
    llm_rerank: bool,
    llm_report: bool,
    llm_candidate_limit: int,
) -> tuple[ScanResult, str, Path, int]:
    if custom_topic is not None:
        topic_config = custom_topic
    else:
        app_config = load_config(config_path)
        topic_config = app_config.get_topic(topic_name)

    if use_mock:
        posts = load_mock_posts()
    else:
        posts = RedditClient().search_topic(topic_config)

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
        markdown = LLMReportGenerator().generate(result.signals)
    else:
        markdown = build_markdown_report(result, topic_config)

    report_path = write_report(markdown, output_dir=output_dir, topic_name=topic_config.name)
    result.report_path = str(report_path)
    run_id = SQLiteStore(db_path).save_scan_result(result)
    return result, markdown, report_path, run_id


def slugify_topic_name(text: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())[:6]
    return "custom_" + "_".join(words or ["market_scan"])


def split_csv_field(value: str) -> list[str]:
    return [item.strip().removeprefix("r/") for item in value.split(",") if item.strip()]


def extract_brief_keywords(brief: str, target_users: str = "", must_include: str = "") -> list[str]:
    text = " ".join([brief, target_users, must_include])
    quoted = re.findall(r"['\"]([^'\"]{3,60})['\"]", text)
    phrases = re.findall(r"\b(?:[A-Za-z][A-Za-z0-9+.-]*\s+){1,3}[A-Za-z][A-Za-z0-9+.-]*\b", text)
    words = re.findall(r"[A-Za-z][A-Za-z0-9+.-]{2,}", text.lower())

    candidates: list[str] = []
    candidates.extend(quoted)
    candidates.extend(phrases[:12])
    candidates.extend(word for word in words if word not in STOP_WORDS)
    candidates.extend(split_csv_field(must_include))

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        normalized = re.sub(r"\s+", " ", item.strip(" .,:;!?-_/\n\t")).lower()
        if len(normalized) < 3 or normalized in STOP_WORDS or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
        if len(cleaned) >= 14:
            break
    return cleaned or ["manual workflow", "need help", "alternative", "recommendation"]


def build_custom_topic(
    *,
    brief: str,
    target_users: str,
    subreddits: str,
    must_include: str,
    exclude_phrases: str,
    include_phrases: str,
    lookback_hours: int,
    max_posts_per_source: int,
    output_top_n: int,
) -> TopicConfig:
    keywords = extract_brief_keywords(brief, target_users, must_include)
    communities = split_csv_field(subreddits) or DEFAULT_CUSTOM_SUBREDDITS
    includes = DEFAULT_INTENT_PHRASES + keywords[:6] + split_csv_field(must_include) + split_csv_field(include_phrases)
    excludes = DEFAULT_EXCLUDE_PHRASES + split_csv_field(exclude_phrases)

    return TopicConfig(
        name=slugify_topic_name(brief),
        description=brief.strip(),
        sources=SourcesConfig(reddit=RedditSourceConfig(subreddits=communities)),
        keywords=keywords,
        include_phrases=includes,
        exclude_phrases=excludes,
        lookback_hours=lookback_hours,
        max_posts_per_source=max_posts_per_source,
        min_comments=0,
        min_upvotes=0,
        output_top_n=output_top_n,
    )


def apply_plan_to_session(plan: dict[str, Any]) -> None:
    if plan.get("target_users"):
        st.session_state["target_users"] = plan["target_users"]
    if plan.get("keywords"):
        st.session_state["must_include"] = ", ".join(plan["keywords"][:12])
    if plan.get("subreddits"):
        st.session_state["subreddits"] = ", ".join(plan["subreddits"][:10])
    if plan.get("include_phrases"):
        st.session_state["include_phrases"] = ", ".join(plan["include_phrases"][:14])
    if plan.get("exclude_phrases"):
        st.session_state["exclude_phrases"] = ", ".join(plan["exclude_phrases"][:10])
    if plan.get("lookback_hours"):
        st.session_state["lookback_hours"] = int(plan["lookback_hours"])
    if plan.get("output_top_n"):
        st.session_state["output_top_n"] = int(plan["output_top_n"])


def heuristic_plan_from_brief(brief: str) -> dict[str, Any]:
    keywords = extract_brief_keywords(brief)
    return {
        "keywords": keywords,
        "subreddits": DEFAULT_CUSTOM_SUBREDDITS,
        "include_phrases": DEFAULT_INTENT_PHRASES + keywords[:6],
        "exclude_phrases": DEFAULT_EXCLUDE_PHRASES,
        "lookback_hours": 168,
        "output_top_n": 10,
    }


def initialize_custom_scan_state() -> None:
    defaults: dict[str, Any] = {
        "brief": "",
        "target_users": "",
        "must_include": "",
        "subreddits": ", ".join(DEFAULT_CUSTOM_SUBREDDITS),
        "include_phrases": ", ".join(DEFAULT_INTENT_PHRASES),
        "exclude_phrases": ", ".join(DEFAULT_EXCLUDE_PHRASES),
        "lookback_hours": 168,
        "output_top_n": 10,
        "max_posts_per_source": 25,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def render_scan_plan(topic: TopicConfig) -> None:
    with st.expander("Generated scan plan", expanded=True):
        st.markdown(f"**Topic:** `{topic.name}`")
        communities = topic.sources.reddit.subreddits if topic.sources.reddit else []
        st.markdown(f"**Communities:** {', '.join(communities)}")
        st.markdown(f"**Keywords:** {', '.join(topic.keywords)}")
        st.markdown(f"**Intent phrases:** {', '.join(topic.include_phrases[:18])}")
        st.markdown(f"**Exclude:** {', '.join(topic.exclude_phrases)}")


def signal_rows(
    signals: list[LeadSignal],
    reviews: dict[tuple[str, str], dict[str, str | None]] | None = None,
) -> list[dict[str, Any]]:
    rows = []
    reviews = reviews or {}
    for index, signal in enumerate(signals, start=1):
        post = signal.post
        review = reviews.get((post.source, post.source_id), {})
        rows.append(
            {
                "rank": index,
                "review_status": review.get("status") or "new",
                "review_note": review.get("note") or "",
                "title": post.title,
                "source": post.source,
                "community": post.community or "",
                "score": signal.score,
                "confidence": signal.confidence,
                "buying_intent": signal.buying_intent,
                "upvotes": post.upvotes,
                "comments": post.num_comments,
                "created_at": post.created_at.isoformat(),
                "pain_summary": signal.pain_summary,
                "recommended_action": signal.recommended_action,
                "evidence": "; ".join(signal.evidence),
                "tags": ", ".join(signal.tags),
                "url": post.url,
            }
        )
    return rows


def rows_to_csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


INTENT_COLORS = {"strong": "#dc3545", "medium": "#fd7e14", "weak": "#6c757d", "none": "#adb5bd"}

INTENT_LABELS = {"strong": "Strong intent", "medium": "Medium intent", "weak": "Weak signal", "none": "Low priority"}


def _escape_markdown(text: str) -> str:
    """Escape characters that would break Streamlit markdown rendering."""
    for char in ("#", "*", "_", "`", "[", "]"):
        text = text.replace(char, "\\" + char)
    return text


def render_lead_cards(
    signals: list[LeadSignal],
    *,
    db_path: str,
    run_id: int | None,
    reviews: dict[tuple[str, str], dict[str, str | None]],
) -> None:
    if not signals:
        st.info("No candidate signals found. Adjust keywords, sources, or thresholds.")
        return

    for index, signal in enumerate(signals, start=1):
        post = signal.post
        review = reviews.get((post.source, post.source_id), {})
        current_status = review.get("status") or "new"
        current_note = review.get("note") or ""
        status_index = REVIEW_STATUSES.index(current_status) if current_status in REVIEW_STATUSES else 0

        color = INTENT_COLORS.get(signal.buying_intent, "#adb5bd")
        label = INTENT_LABELS.get(signal.buying_intent, signal.buying_intent)

        with st.container(border=True):
            st.markdown(
                f"### {index}. {_escape_markdown(post.title)}"
                f"&ensp;<span style='color:{color};font-size:0.65em;font-weight:600'>{label}</span>",
                unsafe_allow_html=True,
            )
            st.caption(
                f"{post.source} / {post.community or 'unknown'} · score {signal.score} · "
                f"confidence {signal.confidence} · review {current_status}"
            )
            st.write(signal.pain_summary)
            st.markdown(f"**Next action:** {signal.recommended_action}")
            if signal.evidence:
                st.markdown(f"**Evidence:** {', '.join(signal.evidence)}")

            action_col, status_col, note_col, save_col = st.columns([1.2, 1.1, 2.4, 0.9])
            with action_col:
                st.link_button("Open source", post.url, use_container_width=True)
            with status_col:
                selected_status = st.selectbox(
                    "Review",
                    REVIEW_STATUSES,
                    index=status_index,
                    key=f"status-{run_id}-{post.source}-{post.source_id}",
                    label_visibility="collapsed",
                )
            with note_col:
                note = st.text_input(
                    "Review note",
                    value=current_note,
                    key=f"note-{run_id}-{post.source}-{post.source_id}",
                    placeholder="Why useful / not useful?",
                    label_visibility="collapsed",
                )
            with save_col:
                if st.button(
                    "Save",
                    key=f"save-{run_id}-{post.source}-{post.source_id}",
                    use_container_width=True,
                    disabled=run_id is None,
                ):
                    SQLiteStore(db_path).update_signal_review(
                        run_id=int(run_id),
                        source=post.source,
                        source_id=post.source_id,
                        status=selected_status,
                        note=note,
                    )
                    st.success("Saved")


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="collapsed")
    load_runtime_secrets()

    st.title(APP_NAME)
    st.caption("Public-community demand radar: collect → score → preview → export → review.")

    initialize_custom_scan_state()

    st.subheader("Describe the market you want to investigate")
    st.caption("One paragraph is enough. Lead Radar will turn it into Reddit search parameters and a demand-signal report.")

    example_cols = st.columns(len(MARKET_BRIEF_EXAMPLES))
    for index, example in enumerate(MARKET_BRIEF_EXAMPLES):
        if example_cols[index].button(f"Example {index + 1}", use_container_width=True):
            st.session_state["brief"] = example
            apply_plan_to_session(heuristic_plan_from_brief(example))

    brief = st.text_area(
        "Market / product brief",
        height=125,
        placeholder="Example: I want to research Shopify sellers who struggle with inventory forecasting, cash-flow planning, and manual spreadsheet reporting.",
        key="brief",
        label_visibility="collapsed",
    )

    ai_configured = llm_is_configured()
    parse_col, run_col = st.columns([1, 1])
    with parse_col:
        parse_clicked = st.button(
            "AI-generate scan plan",
            use_container_width=True,
            disabled=not brief.strip() or not ai_configured,
            help="Uses LEAD_RADAR_LLM_* env vars. If disabled, the app still generates a local heuristic plan automatically.",
        )
    with run_col:
        run_clicked = st.button("Run scan", type="primary", use_container_width=True, disabled=not brief.strip())

    if brief.strip() and not any(st.session_state.get(key) for key in ["must_include", "target_users"]):
        apply_plan_to_session(heuristic_plan_from_brief(brief))

    if parse_clicked:
        try:
            with st.spinner("Parsing intent into scan parameters…"):
                apply_plan_to_session(LLMIntentParser().parse(brief))
            st.success("Scan plan generated")
        except Exception as exc:
            apply_plan_to_session(heuristic_plan_from_brief(brief))
            st.warning(f"AI parsing failed; using local heuristic plan instead. {exc}")

    if not ai_configured:
        st.caption("AI scan-plan generation is not configured in this environment, so this demo uses a local heuristic parser.")

    with st.expander("Advanced scan parameters", expanded=False):
        st.text_input(
            "Target users / buyers",
            placeholder="Example: Shopify merchants, indie hackers, pet owners, consultants",
            key="target_users",
        )
        st.text_input(
            "Must-include keywords",
            placeholder="Example: inventory forecasting, cash flow, spreadsheet",
            key="must_include",
        )
        st.text_input(
            "Communities",
            help="Comma-separated subreddit names. Keep this broad for discovery; narrow it after the first run.",
            key="subreddits",
        )
        st.text_input(
            "Intent phrases",
            help="Pain, buying, help-request, alternative, and recommendation phrases used for scoring.",
            key="include_phrases",
        )
        st.text_input("Exclude phrases", help="Comma-separated noise filters.", key="exclude_phrases")
        plan_col1, plan_col2, plan_col3 = st.columns(3)
        with plan_col1:
            st.number_input("Lookback hours", min_value=1, max_value=720, key="lookback_hours")
        with plan_col2:
            st.number_input("Top signals", min_value=1, max_value=50, key="output_top_n")
        with plan_col3:
            st.slider("Max posts per community / keyword", min_value=5, max_value=100, key="max_posts_per_source")

    with st.sidebar:
        st.header("Run settings")
        config_path = st.text_input("Config path", value=DEFAULT_CONFIG_PATH)
        output_dir = st.text_input("Output directory", value=DEFAULT_OUTPUT_DIR)
        db_path = st.text_input("SQLite path", value=os.getenv("LEAD_RADAR_DB_PATH") or DEFAULT_DB_PATH)
        use_mock = st.checkbox("Use mock data", value=True)
        if not use_mock:
            st.warning(
                "Will call real Reddit API. Ensure REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, "
                "and REDDIT_USER_AGENT are set via env vars or Streamlit secrets.",
            )
        llm_rerank = st.checkbox("LLM rerank", value=False)
        llm_report = st.checkbox("LLM report", value=False)
        llm_candidate_limit = st.number_input("LLM candidate limit", min_value=1, max_value=100, value=20)

        st.divider()
        st.caption("For real Reddit or LLM runs, set env vars or Streamlit secrets. API keys are not entered in this UI.")

    custom_topic: TopicConfig | None = None
    topic_name = ""
    if brief.strip():
        custom_topic = build_custom_topic(
            brief=brief,
            target_users=st.session_state["target_users"],
            subreddits=st.session_state["subreddits"],
            must_include=st.session_state["must_include"],
            exclude_phrases=st.session_state["exclude_phrases"],
            include_phrases=st.session_state["include_phrases"],
            lookback_hours=int(st.session_state["lookback_hours"]),
            max_posts_per_source=int(st.session_state["max_posts_per_source"]),
            output_top_n=int(st.session_state["output_top_n"]),
        )
        topic_name = custom_topic.name
        render_scan_plan(custom_topic)
    else:
        st.info("Paste a market brief or click an example to start.")

    with st.expander("How it works", expanded=False):
        st.markdown(
            """
            1. Describe the market, user, product idea, or pain you want to investigate.
            2. Lead Radar turns that brief into a scan plan: keywords, intent phrases, communities, and filters.
            3. Collect mock data or real Reddit posts.
            4. Score demand signals with deterministic rules first; optionally rerank or write the report with an LLM.
            5. Preview top leads, download CSV/Markdown, and mark which signals are actually useful.
            """
        )

    if run_clicked:
        try:
            with st.spinner("Running scan…"):
                result, markdown, report_path, run_id = run_scan(
                    config_path=config_path,
                    topic_name=topic_name,
                    custom_topic=custom_topic,
                    use_mock=use_mock,
                    output_dir=output_dir,
                    db_path=db_path,
                    llm_rerank=llm_rerank,
                    llm_report=llm_report,
                    llm_candidate_limit=int(llm_candidate_limit),
                )
            st.session_state["last_result"] = result
            st.session_state["last_markdown"] = markdown
            st.session_state["last_report_path"] = str(report_path)
            st.session_state["last_run_id"] = run_id
            st.success(f"Scan complete. Report written to {report_path}")
        except Exception as exc:
            st.error(f"Scan failed: {exc}")

    result: ScanResult | None = st.session_state.get("last_result")
    markdown = st.session_state.get("last_markdown", "")
    report_path = st.session_state.get("last_report_path", "")
    run_id = st.session_state.get("last_run_id")

    if not result:
        st.info("Run a scan to preview leads and export results.")
        return

    strong = sum(1 for item in result.signals if item.buying_intent == "strong")
    medium = sum(1 for item in result.signals if item.buying_intent == "medium")
    reviews = SQLiteStore(db_path).get_signal_reviews(int(run_id)) if run_id is not None else {}
    rows = signal_rows(result.signals, reviews)
    reviewed_count = sum(1 for item in reviews.values() if item.get("status") != "new")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Posts fetched", result.total_posts)
    col2.metric("Signals", result.candidate_count)
    col3.metric("Strong intent", strong)
    col4.metric("Medium intent", medium)
    col5.metric("Reviewed", reviewed_count)
    st.caption(f"Run ID: {run_id} · Report path: {report_path}")

    st.subheader("Data preview")
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No rows to preview.")

    st.subheader("Top leads")
    render_lead_cards(result.signals, db_path=db_path, run_id=run_id, reviews=reviews)

    st.subheader("Exports")
    dl1, dl2 = st.columns(2)
    dl1.download_button(
        "Download CSV",
        data=rows_to_csv_bytes(rows),
        file_name=f"lead-radar-{result.topic_name}-signals.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=not rows,
    )
    dl2.download_button(
        "Download Markdown report",
        data=markdown.encode("utf-8"),
        file_name=Path(report_path).name if report_path else "lead-radar-report.md",
        mime="text/markdown",
        use_container_width=True,
    )

    with st.expander("Markdown preview", expanded=False):
        st.markdown(markdown)


if __name__ == "__main__":
    main()
