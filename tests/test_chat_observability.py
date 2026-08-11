from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import logging_config
from app.main import app


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "user_id": "student-01",
                "session_id": "session-01",
                "feature": "qa",
                "message": "Explain observability",
            },
        )

    assert response.status_code == 200
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert response_event["quality_score"] == response.json()["quality_score"]


def test_chat_propagates_correlation_id_enriches_logs_and_scrubs_pii(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": "req-1234abcd"},
            json={
                "user_id": "student-02",
                "session_id": "session-02",
                "feature": "qa",
                "message": "Contact me at student@vinuni.edu.vn or 090 123 4567",
            },
        )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-1234abcd"
    assert float(response.headers["x-response-time-ms"]) >= 0
    assert response.json()["correlation_id"] == "req-1234abcd"

    raw_logs = log_path.read_text(encoding="utf-8")
    assert "student@vinuni.edu.vn" not in raw_logs
    assert "090 123 4567" not in raw_logs
    assert "REDACTED_EMAIL" in raw_logs
    assert "REDACTED_PHONE_VN" in raw_logs

    api_events = [
        event
        for event in map(json.loads, raw_logs.splitlines())
        if event.get("service") == "api"
    ]
    for event in api_events:
        assert event["correlation_id"] == "req-1234abcd"
        assert event["user_id_hash"]
        assert event["session_id"] == "session-02"
        assert event["feature"] == "qa"
        assert event["model"]
        assert event["env"] == "dev"
