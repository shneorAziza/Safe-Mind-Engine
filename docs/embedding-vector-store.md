# Embedding And Local Vector Store

## Status

Implemented for the pilot backend.

The current implementation uses:

- OpenAI embeddings model: `text-embedding-3-small`
- Local SQLite-backed vector store: `data/safe_mind_vectors.sqlite3`

This is intentionally simple for the pilot. It can later be replaced with Postgres + pgvector or a managed vector database.

## Current Flow

```text
incoming message
  -> privacy redaction
  -> emotional relevance filter
  -> psychological signal analyzer
  -> temporary summary_for_embedding
  -> OpenAI embedding
  -> save vector + numeric features + metadata
  -> compute alert drift from stored vectors
```

## Files

- [safe_mind/embeddings/openai_embeddings.py](../safe_mind/embeddings/openai_embeddings.py)
- [safe_mind/embeddings/service.py](../safe_mind/embeddings/service.py)
- [safe_mind/storage/vector_store.py](../safe_mind/storage/vector_store.py)
- [safe_mind/pipeline.py](../safe_mind/pipeline.py)
- [scripts/run_pipeline_debug.py](../scripts/run_pipeline_debug.py)

## Configuration

```env
SAFE_MIND_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
SAFE_MIND_VECTOR_DB_PATH=data/safe_mind_vectors.sqlite3
SAFE_MIND_PERSIST_SIGNALS=true
SAFE_MIND_PIPELINE_VERSION=v1
```

## What Is Stored

The SQLite vector table stores:

- vector id
- event id
- pseudonymous child user id
- device id
- occurred_at
- source_app
- embedding vector as JSON
- embedding model
- embedding dimensions
- numeric/enumerated signal features as JSON
- pipeline version
- created_at

Current table columns:

```text
id
event_id
child_user_id
device_id
occurred_at
source_app
vector_json
embedding_model
embedding_dimensions
features_json
pipeline_version
created_at
```

The same SQLite database also stores `parent_alert_decisions`. Those decisions are now rebuilt from the stored vectors, not from raw or redacted text and not from `summary_for_embedding`.

## What Is Not Stored

The vector store must not store:

- raw text
- redacted text
- `summary_for_embedding`
- evidence phrases
- direct quotes

`summary_for_embedding` exists only in memory during the pipeline run so the embedding can be created.

## Manual Debugging

Run one message without storing:

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline_debug.py --no-persist --text "אני ממש לחוץ מהמבחן מחר ולא מצליח להירדם"
```

With `--no-persist`, the pipeline still creates the embedding and prints the vector/metadata preview,
but does not write anything to the SQLite store.

Use `--no-vector` only when you want to skip embedding creation entirely.

Run one message and store vector:

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline_debug.py --text "אני ממש לחוץ מהמבחן מחר ולא מצליח להירדם"
```

Run several messages:

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline_debug.py --text "..." --text "..."
```

Or from a UTF-8 text file, one message per line:

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline_debug.py --file .\messages.txt
```

Debug logs may print raw/redacted text and temporary summaries to stdout.
Those logs are for local manual debugging only and are not written to the vector store.

The final debug stage is `embedding_and_storage`.

When running with `--no-persist`, it should include:

```json
{
  "would_store": false,
  "stored": false,
  "stored_text": false,
  "vector_record": {
    "vector_json": {
      "dimensions": 1536,
      "preview_first_8_values": []
    },
    "metadata": {
      "event_id": "...",
      "child_user_id": "...",
      "device_id": "...",
      "occurred_at": "...",
      "source_app": "debug",
      "embedding_model": "text-embedding-3-small",
      "embedding_dimensions": 1536,
      "features": {},
      "pipeline_version": "v1"
    }
  },
  "vector_id": null
}
```

## Next Step

Add vector search/evaluation helpers:

- query by a new text summary,
- compute embedding,
- cosine-search stored vectors,
- return only ids, scores, metadata, and numeric features.
