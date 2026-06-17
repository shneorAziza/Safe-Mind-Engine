from safe_mind.signals.emotional_filter import filter_emotional_relevance


def test_filter_marks_neutral_text_as_not_relevant() -> None:
    result = filter_emotional_relevance("Can you send me the homework file?")

    assert result.is_emotionally_relevant is False
    assert result.confidence == 0
    assert result.categories == []
    assert result.risk_hint == "none"
    assert result.provider == "heuristic"


def test_filter_detects_distress_signal() -> None:
    result = filter_emotional_relevance("I feel overwhelmed and anxious today.")

    assert result.is_emotionally_relevant is True
    assert result.categories == ["distress", "anxiety"]
    assert result.risk_hint == "none"
    assert result.confidence > 0.8
    assert result.provider == "heuristic"


def test_filter_detects_urgent_safety_risk() -> None:
    result = filter_emotional_relevance("I want to hurt myself.")

    assert result.is_emotionally_relevant is True
    assert result.categories == ["safety_risk"]
    assert result.risk_hint == "urgent"
    assert result.confidence == 0.98
    assert result.provider == "heuristic"


def test_filter_detects_hebrew_anxiety_signal() -> None:
    result = filter_emotional_relevance("\u05d0\u05e0\u05d9 \u05de\u05e4\u05d7\u05d3 \u05d5\u05de\u05de\u05e9 \u05dc\u05d7\u05d5\u05e5")

    assert result.is_emotionally_relevant is True
    assert result.categories == ["distress", "anxiety"]
    assert result.risk_hint == "none"
