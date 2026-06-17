from typing import Any, Protocol

from openai import APIConnectionError, OpenAI

from safe_mind.embeddings.models import EmbeddingResult
from safe_mind.openai_curl_client import post_json


class EmbeddingsClient(Protocol):
    embeddings: Any


class OpenAIEmbeddingService:
    def __init__(self, api_key: str, model: str, client: EmbeddingsClient | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.client = client or OpenAI(api_key=api_key)

    def embed(self, text: str) -> EmbeddingResult:
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            vector = response.data[0].embedding
        except APIConnectionError:
            response_json = post_json(
                "/v1/embeddings",
                api_key=self.api_key,
                payload={
                    "model": self.model,
                    "input": text,
                },
            )
            vector = response_json["data"][0]["embedding"]
        return EmbeddingResult(
            vector=vector,
            model=self.model,
            provider="openai",
            dimensions=len(vector),
        )
