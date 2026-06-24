# SafeMind Backend Docs

These docs are the durable project memory for humans and AI agents.

Use them to understand:

- what has already been built,
- what architectural decisions were made,
- what privacy constraints must not be broken,
- how to run and evaluate the pipeline,
- how the alert engine works,
- what to update when a stage is completed.

`AI_AGENT_CONTEXT.md` is the source of truth. Keep secondary docs short and delete them when they become stale.

## Start Here

1. [AI_AGENT_CONTEXT.md](AI_AGENT_CONTEXT.md) - source of truth for product intent, runtime flow, storage rules, and operational workflows.
2. [architecture.md](architecture.md) - system boundaries and architecture.
3. [pipeline.md](pipeline.md) - current ingestion and closed-day finalization walkthrough.
4. [eval-ui.md](eval-ui.md) - internal visual evaluation UI.

## Docs Policy

Do not update docs for every tiny edit.

Do update docs when:

- a pipeline stage is completed,
- a meaningful architecture decision changes,
- storage/privacy behavior changes,
- a new operational or evaluation workflow is added,
- a seeded evaluation dataset becomes part of the standard debugging flow.
