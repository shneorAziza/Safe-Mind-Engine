# SafeMind Backend

Pilot backend for receiving child-device message events, processing emotional signals, and eventually sending parent-device alerts.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn safe_mind.main:app --reload
```

## Current scope

- Receive message events from the child Android app.
- Keep API keys server-side only.
- Prepare a privacy-first processing pipeline before model calls.
- Persist vectors and numeric signal features without storing text.
- Build a fixed 10-day vector baseline and evaluate a 3-of-5 day alert gate.
- Inspect the pipeline and alert engine through the internal Eval UI dashboard.

## What Exists Today

- `POST /v1/ingest/messages` processes a single message through privacy, emotional filtering, psychological analysis, embeddings, storage, and alert evaluation.
- `GET /eval` exposes an internal dashboard for:
  - running pipeline simulations
  - selecting a child user from the local DB
  - viewing 30-day alert timelines
  - inspecting vector baseline, daily distance scores, deviations, and push decisions
- Local SQLite stores:
  - vectors
  - numeric and enumerated features
  - parent alert decisions

## Evaluation Seeds

- `scripts/seed_alert_demo_data.py`
  Seeds direct numeric signal data for alert-engine inspection only.

- `scripts/seed_message_pipeline_demo_data.py`
  Seeds a 30-day synthetic message dataset through the real pipeline.
  By default this uses the configured providers, including OpenAI when enabled.

## Docs

Start with [docs/handoff.md](docs/handoff.md) when continuing this project from a new context window.
