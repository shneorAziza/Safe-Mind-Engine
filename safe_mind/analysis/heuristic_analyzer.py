from safe_mind.analysis.models import PsychologicalAnalysisResult, PsychologicalScores, SignalFeatures


def analyze_with_heuristics(text: str) -> PsychologicalAnalysisResult:
    scores = PsychologicalScores(
        positive_emotion=_score(text, ("hope", "good", "better", "relieved", "ok"), default=5),
        negative_emotion=_score(text, ("sad", "angry", "overwhelmed", "upset", "cry", "bad")),
        loneliness=_score(text, ("alone", "lonely", "nobody", "isolated")),
        anxiety_stress=_score(text, ("anxious", "stress", "worried", "panic", "overwhelmed")),
        hopelessness=_score(text, ("hopeless", "no point", "never better")),
        self_worth_low=_score(text, ("worthless", "my fault", "hate myself")),
        risk=_score(text, ("hurt myself", "kill myself", "suicide", "end my life")),
    )
    risk_level = "urgent" if scores.risk >= 70 else "none"

    features = SignalFeatures(
        should_store=True,
        signal_strength=max(
            scores.negative_emotion,
            scores.loneliness,
            scores.anxiety_stress,
            scores.hopelessness,
            scores.self_worth_low,
            scores.risk,
        )
        / 100,
        risk_level=risk_level,
        scores=scores,
        confidence=0.6,
        provider="heuristic",
    )

    return PsychologicalAnalysisResult(features=features)


def _score(text: str, keywords: tuple[str, ...], *, default: int = 1) -> int:
    lowered = text.lower()
    return 7 if any(keyword in lowered for keyword in keywords) else default
