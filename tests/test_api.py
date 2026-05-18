from fastapi.testclient import TestClient

from lead_radar.api import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_topics() -> None:
    response = client.get("/topics", params={"config_path": "config.example.yaml"})

    assert response.status_code == 200
    payload = response.json()
    assert any(item["name"] == "paid_demand_signals" for item in payload)
    assert all("intent_profile" in item for item in payload)
    assert payload[0]["source_names"] == ["reddit", "hacker_news"]


def test_mock_scan_returns_result(tmp_path) -> None:
    response = client.post(
        "/scan",
        json={
            "config_path": "config.example.yaml",
            "topic": "paid_demand_signals",
            "mock": True,
            "output_dir": str(tmp_path / "reports"),
            "db_path": str(tmp_path / "lead_radar.sqlite"),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == 1
    assert payload["result"]["topic_name"] == "paid_demand_signals"
    assert payload["result"]["candidate_count"] > 0
    assert "#" in payload["markdown"]


def test_mock_scan_can_skip_persistence(tmp_path) -> None:
    response = client.post(
        "/scan",
        json={
            "config_path": "config.example.yaml",
            "topic": "paid_demand_signals",
            "mock": True,
            "output_dir": str(tmp_path / "reports"),
            "persist": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["run_id"] is None


def test_ingest_alerts_endpoint(tmp_path) -> None:
    response = client.post(
        "/ingest/alerts",
        json={
            "batch_name": "f5bot-test",
            "db_path": str(tmp_path / "lead_radar.sqlite"),
            "alerts": [
                {
                    "source": "f5bot",
                    "source_id": "alert-1",
                    "url": "https://news.ycombinator.com/item?id=1",
                    "title": "Need a better monitoring workflow",
                    "body": "Looking for a tool because this manual workflow is tedious.",
                    "community": "hacker_news",
                    "tags": ["vendor:f5bot"],
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["batch_name"] == "f5bot-test"
    assert payload["received"] == 1
    assert payload["inserted"] == 1
    assert payload["updated"] == 0
    assert payload["source_counts"] == {"f5bot": 1}


def test_score_ingested_alerts_endpoint(tmp_path) -> None:
    db_path = tmp_path / "lead_radar.sqlite"
    ingest_response = client.post(
        "/ingest/alerts",
        json={
            "db_path": str(db_path),
            "alerts": [
                {
                    "source": "f5bot",
                    "source_id": "alert-1",
                    "url": "https://example.com/thread/1",
                    "title": "Looking for a tool to monitor public discussions",
                    "body": "Manual monitoring is tedious and I wish there was a better tool.",
                    "community": "hacker_news",
                    "num_comments": 2,
                    "topic_name": "saas_idea_hunt",
                }
            ],
        },
    )
    assert ingest_response.status_code == 200

    response = client.post(
        "/ingest/score",
        json={
            "config_path": "config.example.yaml",
            "topic": "saas_idea_hunt",
            "db_path": str(db_path),
            "output_dir": str(tmp_path / "reports"),
            "sources": ["f5bot"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == 1
    assert payload["result"]["topic_name"] == "saas_idea_hunt"
    assert payload["result"]["candidate_count"] == 1
    assert "# Idea Hunt Report" in payload["markdown"]
