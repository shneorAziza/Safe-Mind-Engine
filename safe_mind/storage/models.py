from pydantic import BaseModel


class StoredSignal(BaseModel):
    stored: bool
    vector_id: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
