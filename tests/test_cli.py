from typer.testing import CliRunner

from lead_radar.cli import app
from lead_radar.ingest import ingest_alerts
from lead_radar.models import IngestedAlert

runner = CliRunner()


def test_score_ingested_cli_scores_alerts(tmp_path) -> None:
    db_path = tmp_path / "lead_radar.sqlite"
    reports_dir = tmp_path / "reports"
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
            )
        ],
        db_path=str(db_path),
    )

    result = runner.invoke(
        app,
        [
            "score-ingested",
            "--config",
            "config.example.yaml",
            "--topic",
            "saas_idea_hunt",
            "--db-path",
            str(db_path),
            "--output-dir",
            str(reports_dir),
            "--source",
            "f5bot",
        ],
    )

    assert result.exit_code == 0
    assert "Ingested posts scored" in result.output
    assert "Signals" in result.output
    assert list(reports_dir.glob("saas_idea_hunt-ingested-*.md"))
