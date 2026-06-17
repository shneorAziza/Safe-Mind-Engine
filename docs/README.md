# SafeMind Backend Docs

These docs are the durable project memory for humans and AI agents.

Use them to understand:

- what has already been built,
- what architectural decisions were made,
- what privacy constraints must not be broken,
- how to run and evaluate the pipeline,
- how the alert engine works,
- what to update when a stage is completed.

## Start Here

1. [AI_AGENT_CONTEXT.md](AI_AGENT_CONTEXT.md) - main context file for a new AI agent.
2. [handoff.md](handoff.md) - older handoff summary.
3. [architecture.md](architecture.md) - system boundaries and architecture.
4. [pipeline.md](pipeline.md) - current pipeline walkthrough.
5. [psychological-analyzer.md](psychological-analyzer.md) - signal analyzer stage.
6. [embedding-vector-store.md](embedding-vector-store.md) - embeddings and vector storage.
7. [eval-ui.md](eval-ui.md) - internal visual evaluation UI.
8. [evaluation.md](evaluation.md) - first-stage filter dataset evaluation.

## Docs Policy

Do not update docs for every tiny edit.

Do update docs when:

- a pipeline stage is completed,
- a meaningful architecture decision changes,
- storage/privacy behavior changes,
- a new operational or evaluation workflow is added,
- a seeded evaluation dataset becomes part of the standard debugging flow.
