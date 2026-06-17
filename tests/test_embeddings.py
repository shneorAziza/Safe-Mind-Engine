from safe_mind.embeddings.openai_embeddings import OpenAIEmbeddingService


class FakeEmbeddingData:
    embedding = [0.1, 0.2, 0.3]


class FakeEmbeddingResponse:
    data = [FakeEmbeddingData()]


class FakeEmbeddings:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeEmbeddingResponse()


class FakeClient:
    def __init__(self):
        self.embeddings = FakeEmbeddings()


def test_openai_embedding_service_returns_vector_metadata() -> None:
    service = OpenAIEmbeddingService(
        api_key="test-key",
        model="text-embedding-test",
        client=FakeClient(),
    )

    result = service.embed("temporary summary")

    assert result.vector == [0.1, 0.2, 0.3]
    assert result.model == "text-embedding-test"
    assert result.provider == "openai"
    assert result.dimensions == 3
