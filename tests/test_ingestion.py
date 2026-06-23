from fastapi.testclient import TestClient

from safe_mind.main import app


def test_ingest_message_acknowledges_event() -> None:
    client = TestClient(app)
    payload = {
        "event_id": "6fbdad90-89c7-4f7a-85a3-679a0ce29952",
        "child_user_id": "fd588728-5478-44c7-b887-673581a571bc",
        "device_id": "1736d0fe-f1a4-410e-bca2-696d36c029c3",
        "occurred_at": "2026-06-15T10:15:00Z",
        "source_type": "notification",
        "source_app": "example.ai.app",
        "text": "I feel overwhelmed today.",
        "locale": "en",
    }

    response = client.post("/v1/ingest/messages", json=payload)

    assert response.status_code == 202
    assert response.json() == {
        "event_id": payload["event_id"],
        "status": "accepted",
        "pipeline_stage": "psychologically_analyzed",
        "privacy": {
            "pii_detected": False,
            "pii_types": [],
            "redaction_count": 0,
            "risk_level": "low",
        },
        "signal_features": {
            "should_store": True,
            "signal_strength": 0.7,
            "risk_level": "none",
            "scores": {
                "positive_emotion": 5,
                "negative_emotion": 7,
                "loneliness": 1,
                "anxiety_stress": 7,
                "hopelessness": 1,
                "self_worth_low": 1,
                "risk": 1,
            },
            "confidence": 0.6,
            "provider": "heuristic",
        },
        "stored_signal": {
            "stored": False,
            "signal_id": None,
            "daily_score_id": None,
            "vector_id": None,
            "embedding_model": None,
            "embedding_dimensions": None,
        },
        "alert_decision": None,
    }


def test_ingest_message_returns_privacy_summary_without_redacted_text() -> None:
    client = TestClient(app)
    payload = {
        "event_id": "6fbdad90-89c7-4f7a-85a3-679a0ce29952",
        "child_user_id": "fd588728-5478-44c7-b887-673581a571bc",
        "device_id": "1736d0fe-f1a4-410e-bca2-696d36c029c3",
        "occurred_at": "2026-06-15T10:15:00Z",
        "source_type": "notification",
        "source_app": "example.ai.app",
        "text": "Please call me at 052-123-4567",
        "locale": "en",
    }

    response = client.post("/v1/ingest/messages", json=payload)

    assert response.status_code == 202
    body = response.json()
    assert body["pipeline_stage"] == "psychologically_analyzed"
    assert body["privacy"] == {
        "pii_detected": True,
        "pii_types": ["PHONE"],
        "redaction_count": 1,
        "risk_level": "medium",
    }
    assert body["signal_features"] == {
        "should_store": True,
        "signal_strength": 0.1,
        "risk_level": "none",
        "scores": {
            "positive_emotion": 5,
            "negative_emotion": 1,
            "loneliness": 1,
            "anxiety_stress": 1,
            "hopelessness": 1,
            "self_worth_low": 1,
            "risk": 1,
        },
        "confidence": 0.6,
        "provider": "heuristic",
    }
    assert body["stored_signal"] == {
        "stored": False,
        "signal_id": None,
        "daily_score_id": None,
        "vector_id": None,
        "embedding_model": None,
        "embedding_dimensions": None,
    }
    assert "redacted_text" not in body
    assert "summary_for_embedding" not in body
