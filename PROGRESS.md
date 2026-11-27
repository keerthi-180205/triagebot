# Progress

Last updated: 2026-11-27

## Current stage

Skeleton complete. No application code yet.

## Done

- ✅ Python 3.11 virtual environment (`.venv`)
- ✅ `requirements.txt` with pinned versions, installed (`pip check` clean)
- ✅ Project skeleton (empty files)
- ✅ README, PROGRESS and docs outlines
- ✅ [Implementation guide](IMPLEMENTATION.md)

## Roadmap

Proposed build order. Adjust as we go. Each section matches the step with the same number in [IMPLEMENTATION.md](IMPLEMENTATION.md).

### 1. Foundation
- [ ] Settings and logging (`common/`)
- [ ] `.env.example`
- [ ] Docker Compose for Postgres (pgvector) and Redis
- [ ] Database models and first migration

### 2. Webhook service
- [ ] `/health`
- [ ] Signature verification
- [ ] `/webhook` with dedupe by delivery ID
- [ ] Enqueue job
- [ ] Tests

### 3. Worker and GitHub
- [ ] GitHub App and client
- [ ] Worker with retry and backoff
- [ ] Fallback comment

### 4. Retrieval
- [ ] Clone and chunk
- [ ] Embed and index
- [ ] Search

### 5. Agent
- [ ] State and structured outputs
- [ ] classify, retrieve, decide, act nodes
- [ ] Tools and prompts
- [ ] Step limit and timeout
- [ ] Run, tool call, token, cost and latency logging
- [ ] `/runs` endpoints

### 6. Evaluation
- [ ] Collect issues
- [ ] Label by hand (developer)
- [ ] Dev / held-out test split
- [ ] Runner and scorers
- [ ] Ablation and error analysis

### 7. Ship
- [ ] Dockerfile
- [ ] Deploy, demo repository, demo video or GIF
- [ ] Final README with measured results

## Open decisions

| Decision | Current state |
| --- | --- |
| LLM provider and model | Anthropic SDK installed as a provisional choice |
| Embedding model | Not chosen; no embedding library installed |
| Chunking strategy | Not chosen |
| Vector index type | Not chosen |
| Issue categories | bug, feature, question, docs, spam (to confirm) |
| Queue library | arq installed (to confirm) |

## Log

- 2026-11-27: Environment, dependencies and skeleton created.
- 2026-11-27: Implementation guide written.
