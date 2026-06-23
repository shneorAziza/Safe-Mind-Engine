# Psychological Signal Analyzer

## Status

Implemented.

This is the stage after privacy redaction.

Current backend flow:

```text
POST /v1/ingest/messages
  -> privacy redaction
  -> psychological signal analyzer
  -> API response with numeric signal features
```

## Purpose

The analyzer does not diagnose, treat, or produce a clinical opinion.

Its job is to convert every privacy-redacted message into structured internal signals that can later be:

- stored as numeric features,
- aggregated by day,
- compared to a personal baseline,
- used by a later alerting engine.

## Files

- [safe_mind/analysis/models.py](../safe_mind/analysis/models.py)
- [safe_mind/analysis/heuristic_analyzer.py](../safe_mind/analysis/heuristic_analyzer.py)
- [safe_mind/analysis/openai_analyzer.py](../safe_mind/analysis/openai_analyzer.py)
- [safe_mind/analysis/service.py](../safe_mind/analysis/service.py)

## Configuration

```env
SAFE_MIND_PSYCHOLOGICAL_ANALYZER_PROVIDER=openai
SAFE_MIND_OPENAI_PSYCHOLOGICAL_ANALYZER_MODEL=gpt-4o-mini
OPENAI_API_KEY=...
```

If OpenAI is unavailable, the service falls back to the local heuristic analyzer.

## Internal Output

The analyzer returns an internal `PsychologicalAnalysisResult`:

```text
PsychologicalAnalysisResult
  -> features
  -> compact scores
```

`features` contains numeric and enum fields.

The current pilot output does not include an embedding summary.
For the pilot, every analyzed message sets `should_store=true` so daily averages can include neutral and practical messages too.

## API Output

The API response exposes only `signal_features`.

Example:

```json
{
  "signal_features": {
    "should_store": true,
    "signal_strength": 0.85,
    "risk_level": "low",
    "scores": {
      "positive_emotion": 15,
      "negative_emotion": 70,
      "loneliness": 30,
      "anxiety_stress": 80,
      "hopelessness": 10,
      "self_worth_low": 20,
      "risk": 0
    },
    "confidence": 0.85,
    "provider": "openai"
  }
}
```

## Privacy Rule

The API must not return:

- raw text,
- redacted text,
- evidence phrases,
- direct quotes.

Future storage should save only:

- vector,
- numeric scores,
- enums,
- timestamps,
- pseudonymous user/device ids,
- model and pipeline versions.

Future storage must not save:

- raw text,
- redacted text,
- summaries,
- evidence phrases,
- direct quotes.

## Next Step

The next step is signal-feature storage:

```text
signal_features
  -> store JSON numeric features + metadata
  -> update fixed 10-day baseline and alert decision
```
