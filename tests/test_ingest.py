from lead_radar.ingest import ingest_alerts, score_ingested_posts
from lead_radar.models import IngestedAlert
from lead_radar.storage import SQLiteStore


def test_ingest_alerts_inserts_and_updates_posts(tmp_path) -> None:
    db_path = tmp_path / "lead_radar.sqlite"
    first = IngestedAlert(
        source="syften",
        source_id="alert-1",
        url="https://example.com/thread/1",
        title="Looking for a tool to monitor public discussions",
        body="Manual monitoring is tedious and expensive.",
        community="reddit:SaaS",
        topic_name="saas_idea_hunt",
        tags=["vendor:syften", " public-discussion "],
        raw={"vendor": "syften"},
    )
    second = first.model_copy(update={"title": "Updated alert title"})

    result_1 = ingest_alerts([first], db_path=str(db_path), batch_name="alerts")
    result_2 = ingest_alerts([second], db_path=str(db_path), batch_name="alerts")

    assert result_1["inserted"] == 1
    assert result_1["updated"] == 0
    assert result_2["inserted"] == 0
    assert result_2["updated"] == 1
    assert result_2["source_counts"] == {"syften": 1}

    store = SQLiteStore(db_path)
    with store._connect() as conn:
        row = conn.execute(
            "SELECT title, raw_json FROM posts WHERE source = ? AND source_id = ?",
            ("syften", "alert-1"),
        ).fetchone()

    assert row[0] == "Updated alert title"
    assert "saas_idea_hunt" in row[1]
    assert "public-discussion" in row[1]


def test_score_ingested_posts_creates_report_and_scan_run(tmp_path) -> None:
    db_path = tmp_path / "lead_radar.sqlite"
    ingest_alerts(
        [
            IngestedAlert(
                source="f5bot",
                source_id="alert-1",
                url="https://example.com/thread/1",
                title="Looking for a tool to monitor public discussions",
                body="Manual monitoring is tedious and I wish there was a better tool.",
                community="hacker_news",
                num_comments=2,
                topic_name="saas_idea_hunt",
                tags=["vendor:f5bot"],
            )
        ],
        db_path=str(db_path),
    )

    result, markdown, run_id = score_ingested_posts(
        config_path="config.example.yaml",
        topic_name="saas_idea_hunt",
        db_path=str(db_path),
        output_dir=str(tmp_path / "reports"),
        sources=["f5bot"],
    )

    assert run_id == 1
    assert result.topic_name == "saas_idea_hunt"
    assert result.total_posts == 1
    assert result.candidate_count == 1
    assert result.report_path
    assert "# Idea Hunt Report" in markdown
    assert "vendor:f5bot" in result.signals[0].post.raw["ingest_tags"]
