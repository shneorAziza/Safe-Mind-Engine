from typing import Literal

from pydantic import BaseModel, Field

EmbeddingProvider = Literal["openai"]


class EmbeddingResult(BaseModel):
    vector: list[float] = Field(min_length=1)
    model: str
    provider: EmbeddingProvider = "openai"
    dimensions: int

