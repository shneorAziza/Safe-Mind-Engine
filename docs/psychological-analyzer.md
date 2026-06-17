# Psychological Signal Analyzer

## Status

Implemented.

This is the stage after the emotional relevance filter.

Current backend flow:

```text
POST /v1/ingest/messages
  -> privacy redaction
  -> emotional relevance filter
  -> psychological signal analyzer, only if the message passed the filter
  -> API response with numeric signal features
```

## Purpose

The analyzer does not diagnose, treat, or produce a clinical opinion.

Its job is to convert a filtered emotional message into structured internal signals that can later be:

- embedded into a vector,
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
  -> summary_for_embedding
```

`features` contains numeric and enum fields.

`summary_for_embedding` is temporary text used only for creating an embedding later.

## API Output

The API response exposes only `signal_features`.

Example:

```json
{
  "signal_features": {
    "should_store": true,
    "signal_strength": 0.85,
    "risk_level": "low",
    "emotion_scores": {
      "anxiety": 0.7,
      "sadness": 0.2,
      "anger": 0.1,
      "loneliness": 0.3,
      "shame": 0.1,
      "hopelessness": 0.1
    },
    "cbt_pattern_scores": {
      "catastrophizing": 0.2,
      "all_or_nothing": 0.1,
      "mind_reading": 0.1,
      "overgeneralization": 0.2,
      "self_blame": 0.1,
      "avoidance": 0.3
    },
    "theme_scores": {
      "school": 0.2,
      "friends": 0.3,
      "parents": 0.2,
      "ai_dependency": 0.1,
      "academic_pressure": 0.3,
      "social_rejection": 0.2,
      "bullying": 0.1
    },
    "protective_signal_scores": {
      "seeking_help": 0.4,
      "future_orientation": 0.3,
      "trusted_adult": 0.2,
      "problem_solving": 0.3,
      "social_support": 0.4
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
- `summary_for_embedding`,
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

The next step is embedding generation:

```text
summary_for_embedding
  -> embedding model
  -> vector
  -> store vector + signal_features + metadata
  -> discard summary_for_embedding
```

