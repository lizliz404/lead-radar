from datetime import datetime, timezone

from lead_radar.models import LeadSignal, RawPost, ScanResult
from lead_radar.storage import SQLiteStore


def make_signal() -> LeadSignal:
    post = RawPost(
        source="reddit",
        source_id="abc123",
        url="https://reddit.com/r/test/comments/abc123/example",
        title="Need a tool to find buying intent in Reddit posts",
        body="I am willing to pay for something that saves time finding leads.",
        community="test",
        created_at=datetime.now(timezone.utc),
        upvotes=12,
        num_comments=4,
    )
    return LeadSignal(
        post=post,
        score=18.0,
        signal_strength="strong",
        confidence=0.8,
        evidence=["willing to pay"],
        pain_summary="User wants to save time finding qualified leads.",
        recommended_action="Reply with a concise workflow suggestion.",
        tags=["buying_intent"],
    )


def test_update_notification_status(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "lead_radar.sqlite")
    run_id = store.save_scan_result(
        ScanResult(
            topic_name="paid_demand_signals",
            scanned_at=datetime.now(timezone.utc),
            total_posts=0,
            candidate_count=0,
            signals=[],
            report_path="reports/example.md",
        )
    )

    store.update_notification_status(run_id, status="sent", channels=["telegram"])

    with store._connect() as conn:
        row = conn.execute(
            "SELECT notification_status, notification_channels FROM scan_runs WHERE id = ?",
            (run_id,),
        ).fetchone()

    assert row == ("sent", '["telegram"]')


def test_update_signal_review(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "lead_radar.sqlite")
    signal = make_signal()
    run_id = store.save_scan_result(
        ScanResult(
            topic_name="paid_demand_signals",
            scanned_at=datetime.now(timezone.utc),
            total_posts=1,
            candidate_count=1,
            signals=[signal],
            report_path="reports/example.md",
        )
    )

    store.update_signal_review(
        run_id=run_id,
        source=signal.post.source,
        source_id=signal.post.source_id,
        status="useful",
        note="Worth contacting.",
    )

    reviews = store.get_signal_reviews(run_id)

    review = reviews[("reddit", "abc123")]
    assert review["status"] == "useful"
    assert review["note"] == "Worth contacting."
    assert review["reviewed_at"]


def test_review_summary(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "lead_radar.sqlite")
    signal = make_signal()
    run_id = store.save_scan_result(
        ScanResult(
            topic_name="paid_demand_signals",
            scanned_at=datetime.now(timezone.utc),
            total_posts=1,
            candidate_count=1,
            signals=[signal],
            report_path="reports/example.md",
        )
    )
    assert store.get_review_summary(run_id)["by_status"] == {"new": 1}

    store.update_signal_review(
        run_id=run_id,
        source=signal.post.source,
        source_id=signal.post.source_id,
        status="contacted",
    )

    summary = store.get_review_summary(run_id)
    assert summary["total"] == 1
    assert summary["reviewed"] == 1
    assert summary["positive"] == 1
    assert summary["positive_rate"] == 1.0
    assert summary["by_status"] == {"contacted": 1}


def test_signal_strength_column_is_written(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "lead_radar.sqlite")
    signal = make_signal()
    run_id = store.save_scan_result(
        ScanResult(
            topic_name="paid_demand_signals",
            scanned_at=datetime.now(timezone.utc),
            total_posts=1,
            candidate_count=1,
            signals=[signal],
            report_path="reports/example.md",
        )
    )

    with store._connect() as conn:
        row = conn.execute(
            "SELECT signal_strength, buying_intent FROM signals WHERE run_id = ?",
            (run_id,),
        ).fetchone()

    assert row == ("strong", "strong")


def test_upsert_ingested_posts_counts_inserted_and_updated(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "lead_radar.sqlite")
    post = make_signal().post

    assert store.upsert_ingested_posts([post]) == (1, 0)
    assert store.upsert_ingested_posts([post.model_copy(update={"title": "Updated"})]) == (0, 1)

    with store._connect() as conn:
        row = conn.execute(
            "SELECT title FROM posts WHERE source = ? AND source_id = ?",
            (post.source, post.source_id),
        ).fetchone()

    assert row == ("Updated",)


def test_list_posts_filters_by_source_and_topic_name(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "lead_radar.sqlite")
    signal = make_signal()
    matching = signal.post.model_copy(
        update={
            "source": "f5bot",
            "source_id": "match",
            "raw": {"topic_name": "saas_idea_hunt"},
        }
    )
    other_source = signal.post.model_copy(
        update={
            "source": "syften",
            "source_id": "other-source",
            "raw": {"topic_name": "saas_idea_hunt"},
        }
    )
    other_topic = signal.post.model_copy(
        update={
            "source": "f5bot",
            "source_id": "other-topic",
            "raw": {"topic_name": "paid_demand_signals"},
        }
    )
    store.upsert_ingested_posts([matching, other_source, other_topic])

    posts = store.list_posts(sources=["f5bot"], topic_name="saas_idea_hunt")

    assert [(post.source, post.source_id) for post in posts] == [("f5bot", "match")]
