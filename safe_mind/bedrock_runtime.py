import json
from typing import Any, Protocol


class BedrockRuntimeClient(Protocol):
    def invoke_model(self, **kwargs: Any) -> dict[str, Any]:
        ...


class BedrockClaudeMessagesClient:
    def __init__(
        self,
        *,
        model: str,
        region: str,
        client: BedrockRuntimeClient | None = None,
    ) -> None:
        self.model = model
        self.region = region
        if client is None:
            import boto3

            client = boto3.client("bedrock-runtime", region_name=region)
        self.client = client

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_content: str,
        max_tokens: int = 1000,
    ) -> str:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": 0,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_content}],
                }
            ],
        }
        response = self.client.invoke_model(
            modelId=self.model,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        )
        payload = _load_response_body(response["body"])
        return _extract_text(payload)


def _load_response_body(body: Any) -> dict[str, Any]:
    raw = body.read() if hasattr(body, "read") else body
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        parsed = json.loads(raw)
    elif isinstance(raw, dict):
        parsed = raw
    else:
        raise TypeError(f"Unsupported Bedrock response body type: {type(raw).__name__}")
    if not isinstance(parsed, dict):
        raise ValueError("Bedrock returned a non-object response.")
    return parsed


def _extract_text(payload: dict[str, Any]) -> str:
    content = payload.get("content")
    if isinstance(content, list):
        text_parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        text = "".join(text_parts).strip()
        if text:
            return text

    output_text = payload.get("outputText")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    raise ValueError("Bedrock returned no text content.")
