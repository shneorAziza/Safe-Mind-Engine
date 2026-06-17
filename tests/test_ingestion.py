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
        "emotional_filter": {
            "is_emotionally_relevant": True,
            "confidence": 0.55,
            "categories": ["distress"],
            "risk_hint": "none",
            "provider": "heuristic",
        },
        "signal_features": {
            "should_store": True,
            "signal_strength": 0.6,
            "risk_level": "none",
            "emotion_scores": {
                "anxiety": 0.0,
                "sadness": 0.6,
                "anger": 0.0,
                "loneliness": 0.0,
                "shame": 0.0,
                "hopelessness": 0.0,
            },
            "cbt_pattern_scores": {
                "catastrophizing": 0.0,
                "all_or_nothing": 0.0,
                "mind_reading": 0.0,
                "overgeneralization": 0.0,
                "self_blame": 0.0,
                "avoidance": 0.0,
            },
            "theme_scores": {
                "school": 0.0,
                "friends": 0.0,
                "parents": 0.0,
                "ai_dependency": 0.0,
                "academic_pressure": 0.0,
                "social_rejection": 0.0,
                "bullying": 0.0,
            },
            "protective_signal_scores": {
                "seeking_help": 0.0,
                "future_orientation": 0.0,
                "trusted_adult": 0.0,
                "problem_solving": 0.0,
                "social_support": 0.0,
            },
            "confidence": 0.55,
            "provider": "heuristic",
        },
        "stored_signal": {
            "stored": False,
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
    assert body["pipeline_stage"] == "emotional_filtered"
    assert body["privacy"] == {
        "pii_detected": True,
        "pii_types": ["PHONE"],
        "redaction_count": 1,
        "risk_level": "medium",
    }
    assert body["emotional_filter"] == {
        "is_emotionally_relevant": False,
        "confidence": 0.0,
        "categories": [],
        "risk_hint": "none",
        "provider": "heuristic",
    }
    assert body["signal_features"] is None
    assert body["stored_signal"] == {
        "stored": False,
        "vector_id": None,
        "embedding_model": None,
        "embedding_dimensions": None,
    }
    assert "redacted_text" not in body
    assert "summary_for_embedding" not in body
