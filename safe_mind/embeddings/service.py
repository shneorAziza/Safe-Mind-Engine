from safe_mind.core.config import settings
from safe_mind.embeddings.models import EmbeddingResult
from safe_mind.embeddings.openai_embeddings import OpenAIEmbeddingService


def create_embedding(text: str) -> EmbeddingResult:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to create embeddings.")

    return OpenAIEmbeddingService(
        api_key=settings.openai_api_key,
        model=settings.openai_embedding_model,
    ).embed(text)

