import json
from typing import Any, Protocol

from openai import APIConnectionError, OpenAI, OpenAIError
from pydantic import ValidationError

from safe_mind.analysis.heuristic_analyzer import analyze_with_heuristics
from safe_mind.analysis.models import PsychologicalAnalysisResult
from safe_mind.openai_curl_client import CurlOpenAIError, post_json


class ChatCompletionClient(Protocol):
    chat: Any


SYSTEM_PROMPT = """You are SafeMind's psychological signal analyzer for Hebrew and English teen AI conversations.
You receive only privacy-redacted text. Every message must be analyzed directly; there is no prior emotional relevance filter.

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
      "scores": {
      "positive_emotion": integer 1..10,
      "negative_emotion": integer 1..10,
      "loneliness": integer 1..10,
      "anxiety_stress": integer 1..10,
      "hopelessness": integer 1..10,
      "self_worth_low": integer 1..10,
      "risk": integer 1..10
    },
    "confidence": number 0..1,
    "provider": "openai"
  }
}

Do not return summaries, evidence phrases, quotes, or any other text extracted from the message.
Always set should_store=true so the pilot can compute daily averages for every incoming message.
For neutral or practical messages, keep emotional/risk scores low and use confidence to express uncertainty.
Use 1 for very low, 5 for moderate, and 10 for very high.
"""


class OpenAIPsychologicalAnalyzer:
    def __init__(self, api_key: str, model: str, client: ChatCompletionClient | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.client = client or OpenAI(api_key=api_key)

    def analyze(
        self,
        text: str,
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
            return analyze_with_heuristics(text)
