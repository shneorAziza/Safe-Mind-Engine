import json
import re
from typing import Any, Protocol

from openai import APIConnectionError, OpenAI, OpenAIError
from pydantic import ValidationError

from safe_mind.openai_curl_client import CurlOpenAIError, post_json
from safe_mind.signals.emotional_filter import EmotionalFilterResult, filter_emotional_relevance


class ChatCompletionClient(Protocol):
    chat: Any


SYSTEM_PROMPT = """You are SafeMind's emotional relevance filter for Hebrew and English teen messages.
Your job is to decide whether a short, privacy-redacted message may contain emotional signals.
You are not diagnosing, not giving therapy, and not making clinical claims.

Return JSON only with:
- is_emotionally_relevant: boolean
- confidence: number from 0 to 1
- categories: array containing only distress, anxiety, loneliness, anger, self_worth, hopelessness, safety_risk
- risk_hint: none, possible, or urgent

Category guidance:
- distress: sadness, bad day, crying, emotional overwhelm, asking for help with a sensitive personal conversation.
- anxiety: fear, worry, panic, avoiding school/social events because of fear or shame.
- loneliness: being ignored, excluded, not understood, feeling alone or not belonging.
- anger: rage, hatred, wanting to scream, exploding emotionally.
- self_worth: "I am a failure", "I am stupid", "I am weird", "not good enough", self-hate.
- hopelessness: nothing matters, no point, things will not improve, wanting to disappear.
- safety_risk: self-harm, suicide, not wanting to live, wanting to die, hurt myself.

Risk hint guidance:
- urgent: direct or near-direct self-harm/suicide/life-ending language, including Hebrew phrases like
  "לא בא לי לחיות יותר", "לא רוצה לחיות", "לפגוע בעצמי", "להתאבד".
- possible: hopelessness or severe self-worth collapse without direct immediate self-harm language.
- none: emotional distress/anxiety/anger/loneliness without self-harm or severe hopelessness.

Use urgent only for direct self-harm, suicide, or immediate safety language.
Use possible for hopelessness, severe self-worth collapse, or ambiguous self-harm concern.
Do not mark bullying, fear of school, anger at parents, or "people don't understand me" as possible unless
there is hopelessness, self-harm, or severe self-worth collapse.
Mark subtle help-seeking as relevant when the child asks for help with a personal emotional situation,
for example "bad day, tell me a joke", "help me ask my parents to talk", or "how do I ask for help".
Prefer false only for logistics, homework, scheduling, jokes, or ordinary factual messages with no emotional context.
"""

URGENT_SAFETY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(kill myself|hurt myself|end my life|suicide|self harm|want to die)\b", re.I),
    re.compile(
        r"(\u05dc\u05d0 \u05d1\u05d0 \u05dc\u05d9 \u05dc\u05d7\u05d9\u05d5\u05ea|"
        r"\u05dc\u05d0 \u05e8\u05d5\u05e6\u05d4 \u05dc\u05d7\u05d9\u05d5\u05ea|"
        r"\u05dc\u05e4\u05d2\u05d5\u05e2 \u05d1\u05e2\u05e6\u05de\u05d9|"
        r"\u05dc\u05d4\u05ea\u05d0\u05d1\u05d3|"
        r"\u05dc\u05de\u05d5\u05ea)"
    ),
)


class OpenAIEmotionalFilter:
    def __init__(self, api_key: str, model: str, client: ChatCompletionClient | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.client = client or OpenAI(api_key=api_key)

    def filter(self, text: str, *, allow_fallback: bool = True) -> EmotionalFilterResult:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
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
                        {"role": "user", "content": text},
                    ],
                },
            )
            content = response_json["choices"][0]["message"]["content"]
        try:
            if not content:
                raise ValueError("OpenAI returned an empty emotional filter response.")

            result = EmotionalFilterResult.model_validate_json(content)
            result = result.model_copy(update={"provider": "openai"})
            return _apply_safety_overrides(text, result)
        except (OpenAIError, ValidationError, ValueError, json.JSONDecodeError, CurlOpenAIError):
            if not allow_fallback:
                raise
            return filter_emotional_relevance(text)


def _apply_safety_overrides(text: str, result: EmotionalFilterResult) -> EmotionalFilterResult:
    if any(pattern.search(text) for pattern in URGENT_SAFETY_PATTERNS):
        categories = list(dict.fromkeys([*result.categories, "safety_risk", "hopelessness"]))
        return result.model_copy(
            update={
                "is_emotionally_relevant": True,
                "confidence": max(result.confidence, 0.95),
                "categories": categories,
                "risk_hint": "urgent",
            }
        )

    return result
