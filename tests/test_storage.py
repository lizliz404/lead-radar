from datetime import datetime, timezone

from lead_radar.models import ScanResult
from lead_radar.storage import SQLiteStore


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
