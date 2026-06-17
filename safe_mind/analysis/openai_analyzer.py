import json
from typing import Any, Protocol

from openai import APIConnectionError, OpenAI, OpenAIError
from pydantic import ValidationError

from safe_mind.analysis.heuristic_analyzer import analyze_with_heuristics
from safe_mind.analysis.models import PsychologicalAnalysisResult
from safe_mind.openai_curl_client import CurlOpenAIError, post_json
from safe_mind.signals.emotional_filter import EmotionalFilterResult


class ChatCompletionClient(Protocol):
    chat: Any


SYSTEM_PROMPT = """You are SafeMind's psychological signal analyzer for Hebrew and English teen AI conversations.
You receive only privacy-redacted text that already passed an emotional relevance filter.

Your job:
- Extract internal numeric signals for trend analysis.
- Do not diagnose.
- Do not provide therapy.
- Do not produce a clinical opinion.
- Do not include names, phone numbers, URLs, addresses, or direct quotes in the summary.

Return JSON only with this shape:
{
  "features": {
    "should_store": boolean,
    "signal_strength": number 0..1,
    "risk_level": "none" | "low" | "medium" | "high" | "urgent",
    "emotion_scores": {
      "anxiety": number 0..1,
      "sadness": number 0..1,
      "anger": number 0..1,
      "loneliness": number 0..1,
      "shame": number 0..1,
      "hopelessness": number 0..1
    },
    "cbt_pattern_scores": {
      "catastrophizing": number 0..1,
      "all_or_nothing": number 0..1,
      "mind_reading": number 0..1,
      "overgeneralization": number 0..1,
      "self_blame": number 0..1,
      "avoidance": number 0..1
    },
    "theme_scores": {
      "school": number 0..1,
      "friends": number 0..1,
      "parents": number 0..1,
      "ai_dependency": number 0..1,
      "academic_pressure": number 0..1,
      "social_rejection": number 0..1,
      "bullying": number 0..1
    },
    "protective_signal_scores": {
      "seeking_help": number 0..1,
      "future_orientation": number 0..1,
      "trusted_adult": number 0..1,
      "problem_solving": number 0..1,
      "social_support": number 0..1
    },
    "confidence": number 0..1,
    "provider": "openai"
  },
  "summary_for_embedding": "A short sanitized semantic summary for vectorization only."
}

The summary_for_embedding is temporary and will not be stored as text. Make it generic, concise, and free of identifying details.
If the message is too weak for storage, set should_store=false and keep all scores low.
"""


class OpenAIPsychologicalAnalyzer:
    def __init__(self, api_key: str, model: str, client: ChatCompletionClient | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.client = client or OpenAI(api_key=api_key)

    def analyze(
        self,
        text: str,
        emotional_filter: EmotionalFilterResult,
        *,
        allow_fallback: bool = True,
    ) -> PsychologicalAnalysisResult:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "redacted_text": text,
                                "filter_result": emotional_filter.model_dump(),
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
            )
            content = completion.choices[0].message.content
        except APIConnectionError:
            response_json = post_json(
                "/v1/chat/completions",
                api_key=self.api_key,
                payload={
                    "model": self.model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "redacted_text": text,
                                    "filter_result": emotional_filter.model_dump(),
                                },
                                ensure_ascii=False,
                            ),
                        },
                    ],
                },
            )
            content = response_json["choices"][0]["message"]["content"]
        try:
            if not content:
                raise ValueError("OpenAI returned an empty psychological analysis response.")

            result = PsychologicalAnalysisResult.model_validate_json(content)
            return result.model_copy(
                update={"features": result.features.model_copy(update={"provider": "openai"})}
            )
        except (OpenAIError, ValidationError, ValueError, json.JSONDecodeError, CurlOpenAIError):
            if not allow_fallback:
                raise
            return analyze_with_heuristics(text, emotional_filter)
