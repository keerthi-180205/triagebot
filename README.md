# TriageBot

LLM agent that triages GitHub issues: it classifies each new issue, retrieves relevant code from the repository, and posts a labeled, helpful comment.

> **Status: skeleton only.** The folder structure and dependencies exist; no application code has been written yet. Everything below describes the plan. See [PROGRESS.md](PROGRESS.md) for what is done.

## Problem

Maintainers of active repositories spend time sorting issues: labeling them, spotting duplicates and spam, and pointing reporters to the right files. TriageBot automates the first pass and logs every decision so its quality can be measured.

## Planned features

- GitHub webhooks with HMAC signature verification and idempotent handling
- Redis queue so the webhook responds quickly, with an asynchronous worker
- LangGraph agent: classify, retrieve, decide, act
- Tools: `search_code`, `get_issue_history`, `post_comment_and_labels`
- Safeguards: step limit, timeout, retry with backoff, fallback comment
- Every run logged to Postgres: input, tool calls, tokens, cost, latency, outcome
- Eval harness with a hand-labeled dataset

## Planned architecture

```
GitHub webhook
  -> FastAPI /webhook (verify signature, dedupe by delivery ID)
  -> Redis queue
  -> Worker
       -> LangGraph agent: classify -> retrieve -> decide -> act
       -> GitHub API (labels, comment)
       -> Postgres (runs, tool_calls, cost, latency, outcome)
```

More detail: [docs/architecture.md](docs/architecture.md).

## Tech stack

| Area | Choice |
| --- | --- |
| Language | Python 3.11 |
| Web | FastAPI, Uvicorn |
| Queue | Redis, arq |
| Agent | LangGraph |
| LLM | Anthropic SDK (provisional) |
| Embeddings | Not chosen yet |
| Database | Postgres with pgvector, SQLAlchemy, Alembic |
| Evaluation | scikit-learn |
| Tests and lint | pytest, Ruff |

## Local setup

Requires Python 3.11. From the project root, in PowerShell:

```powershell
py -3.11 -m venv .venv
```

```powershell
.\.venv\Scripts\Activate.ps1
```

```powershell
pip install -r requirements.txt
```

Running the app is not possible yet. Instructions for environment variables, Docker Compose and the GitHub App will be added as those parts are built.

## Project structure

```
triagebot/
  app/                  FastAPI service
    main.py             application entry point
    security.py         webhook HMAC signature verification
    idempotency.py      duplicate-delivery detection
    schemas.py          request and response models
    routes/             webhook, health, runs endpoints
  worker/               queue consumer
    main.py             worker entry point
    jobs.py             job handlers, retry policy
    fallback.py         fallback comment on failure
  common/               shared by app, worker, agent and retrieval
    config.py           settings from environment variables
    logging.py          logging setup
    github_client.py    GitHub App auth and API calls
    queue.py            Redis connection and enqueue
  agent/                LangGraph agent
    graph.py            graph wiring
    state.py            graph state
    schemas.py          structured LLM outputs
    llm.py              LLM client, token and cost tracking
    limits.py           step limit and timeout
    nodes/              classify, retrieve, decide, act
    tools/              search_code, get_issue_history, post_comment_and_labels
    prompts/            prompt files
  retrieval/            clone, chunk, embed, index, search
  db/                   models, session, queries, migrations
  evals/                data collection, runner, scorers, ablation
    dataset/            dev and held-out test sets
    results/            evaluation outputs
  scripts/              command-line helpers (index a repository)
  tests/                tests and fixtures
  docs/                 architecture, decisions, evaluation, API, bugs
  Dockerfile            (empty placeholder)
  docker-compose.yml    (empty placeholder)
  alembic.ini           (empty placeholder)
  pyproject.toml        (empty placeholder)
  .env.example          (empty placeholder)
  requirements.txt      pinned dependencies
  IMPLEMENTATION.md     step-by-step build guide
  PROGRESS.md           build progress
```

## Documentation

- [Implementation guide](IMPLEMENTATION.md)
- [Architecture](docs/architecture.md)
- [Design decisions](docs/decisions.md)
- [Evaluation](docs/evaluation.md)
- [API reference](docs/api.md)
- [Bug log](docs/bugs.md)

## Results

None yet. Numbers are added only after they have been measured.

## License

See [LICENSE](LICENSE).
