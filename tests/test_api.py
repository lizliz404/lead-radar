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
