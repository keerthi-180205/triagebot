# TriageBot implementation guide

Build TriageBot yourself, one step at a time. Each step lists the goal, the files, what to write, the parts that are easy to get wrong, and a "done when" check. Snippets cover only the tricky parts; the rest is yours to write.

## Contents

- [How to work](#how-to-work)
- [Before you start](#before-you-start)
- [Step 1: Foundation](#step-1-foundation)
- [Step 2: Webhook service](#step-2-webhook-service)
- [Step 3: Worker and GitHub](#step-3-worker-and-github)
- [Step 4: Retrieval](#step-4-retrieval)
- [Step 5: Agent](#step-5-agent)
- [Step 6: Evaluation](#step-6-evaluation)
- [Step 7: Ship](#step-7-ship)
- [Corrections to the project draft](#corrections-to-the-project-draft)

---

## How to work

1. Do the steps in order. Do not start the next one until "done when" passes.
2. One branch and at least one commit per step.
3. Write the tests in the same step as the code.
4. After each step, mark the items ✅ in [PROGRESS.md](PROGRESS.md), update the matching file in `docs/`, and record what went wrong in [docs/bugs.md](docs/bugs.md).
5. When you make a choice (chunk size, model, retry policy), add it to [docs/decisions.md](docs/decisions.md) while you still remember why.
6. Never write a number you have not measured.

### Who does what

| The AI in the app | Plain code | You |
| --- | --- | --- |
| Classify the issue | Verify signatures, dedupe, queue | Build everything |
| Write the comment | Retrieval search, retries, timeouts | Label the evaluation data by hand |
| Choose an action | Validate model output before acting | Measure, analyze failures, explain decisions |

---

## Before you start

You need:

- Python 3.11 and the project `.venv`
- Docker Desktop, **running** (check with `docker info`)
- A GitHub account and an empty demo repository for testing
- An LLM API key (needed from step 5)

Activate the environment from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run every command in this guide from the project root.

### Open decisions

| Decision | Needed by | Notes |
| --- | --- | --- |
| LLM provider and model | Step 5 | This project uses Google Gemini through the installed `google-genai` SDK (the §5.2 snippet below is still the original Anthropic example and will be replaced by a Gemini one). Keep all SDK calls in `agent/llm.py` so a swap touches one file. |
| Embedding model | Step 4 | Fixes the vector column size. |
| Chunking strategy | Step 4 | Start simple, compare later. |
| Issue categories | Step 5 | Draft: bug, feature, question, docs, spam. |

---

## Step 1: Foundation

**Goal:** settings load, Postgres and Redis run, tables exist.

**Files:** `pyproject.toml`, `.gitignore`, `.env.example`, `common/config.py`, `common/logging.py`, `docker-compose.yml`, `db/models.py`, `db/session.py`, `db/migrations/`

### 1.1 Tool configuration

`pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

[tool.ruff]
line-length = 100
target-version = "py311"
```

### 1.2 Protect secrets

`.gitignore` already ignores `.env`, but **not** private keys. Add this line before you create the GitHub App:

```gitignore
*.pem
```

### 1.3 Settings

`.env.example` (commit this; copy it to `.env` and fill in real values there):

```dotenv
DATABASE_URL=postgresql+asyncpg://triagebot:triagebot@localhost:5432/triagebot
REDIS_URL=redis://localhost:6379/0
GITHUB_WEBHOOK_SECRET=change-me
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY_PATH=
GEMINI_API_KEY=
LLM_MODEL=gemini-3.8-flash
DRY_RUN=true
AGENT_TIMEOUT_S=120
AGENT_MAX_STEPS=10
JOB_MAX_TRIES=3
RUNS_API_TOKEN=
```

The timeout, step and retry values are starting points. Tune them after you have measurements.

`common/config.py`:

```python
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    # Required and non-empty: an empty secret would let anyone sign requests.
    github_webhook_secret: SecretStr = Field(min_length=1)
    github_app_id: str = ""
    github_private_key_path: str = ""
    gemini_api_key: SecretStr = SecretStr("")
    llm_model: str = "gemini-3.8-flash"
    dry_run: bool = True
    agent_timeout_s: int = 120
    agent_max_steps: int = 10
    job_max_tries: int = 3
    runs_api_token: SecretStr = SecretStr("")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`DRY_RUN=true` means "log what you would post, post nothing". Keep it on until step 3 works.

`common/logging.py`: one `setup_logging()` function. Include the delivery ID or run ID in log lines. Never log secrets or tokens.

### 1.4 Postgres and Redis

`docker-compose.yml` (ports are bound to your machine only):

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_USER: triagebot
      POSTGRES_PASSWORD: triagebot
      POSTGRES_DB: triagebot
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U triagebot"]
      interval: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    ports:
      - "127.0.0.1:6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 10

volumes:
  pgdata:
```

```powershell
docker compose up -d
```

If a port is already in use, change the left-hand port and the matching URL in `.env`.

### 1.5 Database models

`db/models.py`, using SQLAlchemy 2 `DeclarativeBase`, `Mapped` and `mapped_column`:

| Table | Columns |
| --- | --- |
| `runs` | id, delivery_id (**unique**), repo, issue_number, installation_id (BigInteger), status, input (JSONB), category, confidence, model, input_tokens, output_tokens, cost_usd (Numeric), latency_ms, error, created_at, finished_at |
| `tool_calls` | id, run_id (foreign key, indexed), tool, input (JSONB), output (JSONB), success, latency_ms, created_at |

Add an index on `(repo, created_at)`. Run statuses: `received`, `queued`, `running`, `succeeded`, `fallback`, `failed`. The `chunks` table comes in step 4.

`db/session.py`: `create_async_engine(url)` and `async_sessionmaker(engine, expire_on_commit=False)`.

### 1.6 Migrations

Alembic refuses to initialise over the empty placeholder files, so delete them first:

```powershell
Remove-Item alembic.ini
```

```powershell
Remove-Item -Recurse db\migrations
```

```powershell
alembic init -t async db/migrations
```

In the generated `db/migrations/env.py`, set the URL from your settings and point Alembic at your models:

```python
from common.config import get_settings
from db.models import Base

config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
target_metadata = Base.metadata
```

The generated file already defines `config` and `target_metadata = None`; replace that last line.

```powershell
alembic revision --autogenerate -m "create runs and tool_calls"
```

Read the generated migration, then apply it:

```powershell
alembic upgrade head
```

**Done when:** this lists `runs`, `tool_calls` and `alembic_version`.

```powershell
docker compose exec postgres psql -U triagebot -c "\dt"
```

---

## Step 2: Webhook service

**Goal:** GitHub events are verified, deduplicated and queued, and the response is fast.

**Files:** `app/main.py`, `app/security.py`, `app/schemas.py`, `app/idempotency.py`, `app/routes/health.py`, `app/routes/webhook.py`, `common/queue.py`, `db/repository.py`, `tests/test_signature.py`, `tests/test_webhook.py`, `tests/test_idempotency.py`

### 2.1 App and health check

`app/main.py`: create the FastAPI app with a `lifespan` function that opens the database engine and Redis pool on startup and closes them on shutdown. `GET /health` returns `{"status": "ok"}`.

```powershell
uvicorn app.main:app --reload
```

### 2.2 Signature verification

`app/security.py`:

```python
import hashlib
import hmac


def verify_signature(secret: str, body: bytes, header: str | None) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.encode(), header.encode())
```

Verify against the **raw bytes** (`await request.body()`), before parsing JSON.

Use GitHub's published test values in `tests/test_signature.py`:

| Item | Value |
| --- | --- |
| Secret | `It's a Secret to Everybody` |
| Body | `Hello, World!` |
| Header | `sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17` |

Also test a wrong secret, a changed body and a missing header.

### 2.3 The `/webhook` route

In this order:

1. Read the raw body and check `X-Hub-Signature-256`. Invalid: **401**.
2. Read `X-GitHub-Event` and `X-GitHub-Delivery`.
3. Handle only event `issues` with action `opened`. Anything else (including `ping`): 200, ignored.
4. Ignore events where `sender.type` is `Bot`.
5. Validate the payload with a Pydantic model (repository full name, issue number, title, body, installation ID). The body can be `null`. Invalid: **422**.
6. Record the delivery, enqueue, return 200.

### 2.4 Idempotency without losing jobs

Insert the run and let the unique constraint decide (`db/repository.py`):

```python
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Run


async def create_run_if_new(session: AsyncSession, **values) -> int | None:
    statement = (
        insert(Run)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["delivery_id"])
        .returning(Run.id)
    )
    return (await session.execute(statement)).scalar_one_or_none()
```

A trap: if you insert the row, then Redis is down, a plain "duplicate, ignore" rule drops the issue forever. So:

1. Insert with status `received` and commit.
2. Enqueue, then set status `queued`. If enqueueing fails, return **503**.
3. On a duplicate delivery, enqueue again only if the existing row is still `received`.

### 2.5 Queue

`common/queue.py`: create the pool with `arq.create_pool(RedisSettings.from_dsn(url))` and enqueue like this:

```python
from arq.connections import ArqRedis


async def enqueue_triage(redis: ArqRedis, run_id: int, delivery_id: str) -> None:
    # The same _job_id cannot be queued twice. A None result means it already exists.
    await redis.enqueue_job("triage_issue", run_id, _job_id=delivery_id)
```

### Tests

Use `fastapi.testclient.TestClient` and replace the database and queue dependencies with fakes. Cover: bad signature, ignored event, bot sender, new delivery queued once, duplicate ignored, enqueue failure then redelivery.

**Done when:** tests pass, and sending the same delivery twice creates one row and one job. Measure the response time and note it in `docs/architecture.md`.

---

## Step 3: Worker and GitHub

**Goal:** opening an issue in your demo repo produces a fixed placeholder comment. This proves the whole pipe before any AI.

**Files:** `common/github_client.py`, `worker/main.py`, `worker/jobs.py`, `worker/fallback.py`, `tests/test_worker.py`

### 3.1 Create the GitHub App

1. GitHub: Settings, Developer settings, GitHub Apps, New GitHub App.
2. Webhook URL: your tunnel URL plus `/webhook`. Set a long random webhook secret and put the same value in `.env`.
3. Repository permissions: **Issues: read and write**, **Contents: read-only**.
4. Subscribe to the **Issues** event.
5. Note the App ID, generate a private key, and save the `.pem` file **outside the repository**.
6. Install the app on your demo repository only.

To reach your laptop, use a tunnel that forwards the body unchanged, such as `cloudflared tunnel --url http://localhost:8000` or ngrok (install separately).

### 3.2 GitHub client

Authentication has two stages: sign a short JWT as the app, then exchange it for an installation token.

```python
import time

import jwt


def app_jwt(app_id: str, private_key: str) -> str:
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 540, "iss": app_id}
    return jwt.encode(payload, private_key, algorithm="RS256")
```

| Call | Endpoint |
| --- | --- |
| Installation token (use the app JWT) | `POST /app/installations/{installation_id}/access_tokens` |
| Read an issue | `GET /repos/{owner}/{repo}/issues/{number}` |
| List comments | `GET /repos/{owner}/{repo}/issues/{number}/comments` |
| Add labels | `POST /repos/{owner}/{repo}/issues/{number}/labels` |
| Add a comment | `POST /repos/{owner}/{repo}/issues/{number}/comments` |

- Base URL `https://api.github.com`; send `Accept: application/vnd.github+json`, a `User-Agent`, and `Authorization: Bearer <token>`.
- Use one `httpx.AsyncClient` with a timeout.
- Installation tokens expire after an hour. Cache them and refresh early.
- Raise your own `TransientError` for network errors, 429, 5xx and rate-limit 403 responses. Raise a different error for the rest.
- When `dry_run` is true, log write calls instead of sending them.

### 3.3 Worker and retry policy

How arq behaves (checked in the installed 0.28 source):

| In the job | Result |
| --- | --- |
| `raise Retry(defer=...)` | Retried, up to `max_tries` |
| Any other exception, including `job_timeout` expiring | Marked failed, **not** retried |
| Cancelled because the worker is stopping | Run again |

So the job itself must catch failures and decide:

```python
import asyncio

from arq import Retry

from common.config import get_settings
from common.github_client import TransientError
from worker.fallback import post_fallback


async def triage_issue(ctx: dict, run_id: int) -> None:
    settings = get_settings()
    try:
        async with asyncio.timeout(settings.agent_timeout_s):
            await run_triage(ctx, run_id)  # you write this
    except TransientError as exc:
        if ctx["job_try"] < settings.job_max_tries:
            raise Retry(defer=2 ** ctx["job_try"]) from exc
        await post_fallback(ctx, run_id, exc)
    except Exception as exc:
        await post_fallback(ctx, run_id, exc)
```

`worker/main.py`:

```python
from arq.connections import RedisSettings

from common.config import get_settings
from worker.jobs import shutdown, startup, triage_issue

settings = get_settings()


class WorkerSettings:
    functions = [triage_issue]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    max_tries = settings.job_max_tries
    # Longer than the agent timeout, so your own handler runs first.
    job_timeout = settings.agent_timeout_s + 60
```

```powershell
arq worker.main.WorkerSettings
```

### 3.4 Never comment twice

A retry can happen after the comment was posted. Add a hidden marker such as `<!-- triagebot:run=42 -->` to every comment, and skip posting if a comment with that marker already exists.

`post_fallback` posts a short generic comment, sets status `fallback`, and stores the error. If posting the fallback also fails, set status `failed` and log it.

**Done when:** with `DRY_RUN=false`, a new issue in the demo repo gets exactly one comment, redelivering from the app's "Recent Deliveries" adds none, and a forced error produces the fallback comment.

---

## Step 4: Retrieval

**Goal:** given issue text, return the most relevant code chunks with file paths.

**Files:** `retrieval/cloner.py`, `chunker.py`, `embedder.py`, `indexer.py`, `search.py`, `scripts/index_repo.py`, `db/models.py`, `tests/test_retrieval.py`

### 4.1 Choose the embedding model first

| Option | Plus | Minus |
| --- | --- | --- |
| Hosted API (for example Voyage AI or OpenAI) | Small install, good quality | Cost per call, another key, code leaves your machine |
| Local model (for example sentence-transformers) | Free per call, private | Large download, slower on CPU |

Gemini offers embedding models (for example `gemini-embedding-2`), so one provider can cover both generation and retrieval; a local model is the other option. Pick one, add its library to `requirements.txt`, and record the decision. The model sets the vector size; pgvector's `vector` indexes support at most 2,000 dimensions.

### 4.2 Pipeline

1. **Clone** (`cloner.py`): `git clone --depth 1` into a temporary folder, using `subprocess.run` with a list of arguments (no shell). Accept an optional commit SHA; step 6 needs it. Start with public repos so no token is stored on disk.
2. **Chunk** (`chunker.py`): start with line windows, for example 60 lines with 10 overlapping. Keep path and line numbers. Skip `.git`, vendored folders, binaries, lock files and very large files. Do not follow symlinks.
3. **Embed** (`embedder.py`): expose `embed_documents(texts)` and `embed_query(text)`. Batch requests.
4. **Index** (`indexer.py`): replace the rows for that repo in one transaction. A content hash lets you skip unchanged chunks later.
5. **Search** (`search.py`): cosine distance, top-k.

Add the `Chunk` model, replacing `1024` with your model's size:

```python
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column

EMBEDDING_DIM = 1024


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo: Mapped[str] = mapped_column(index=True)
    commit_sha: Mapped[str]
    path: Mapped[str]
    start_line: Mapped[int]
    end_line: Mapped[int]
    content: Mapped[str]
    content_hash: Mapped[str]
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
```

(`Base` is already defined in `db/models.py`.)

```python
from sqlalchemy import select

from db.models import Chunk


def search_statement(repo: str, query_vector: list[float], k: int = 5):
    distance = Chunk.embedding.cosine_distance(query_vector)
    return (
        select(Chunk, distance.label("distance"))
        .where(Chunk.repo == repo)
        .order_by(distance)
        .limit(k)
    )
```

In the new migration, add `import pgvector.sqlalchemy` at the top and make the first line of `upgrade()`:

```python
op.execute("CREATE EXTENSION IF NOT EXISTS vector")
```

Start **without** a vector index: exact search is fine for one small repo. If search gets slow, add an HNSW index with `vector_cosine_ops` and re-check results, because filtering by repo can then return fewer than k rows.

**Done when:** `python -m scripts.index_repo <repo-url>` fills the table, and a hand-written query about a known feature returns the right file in the top 5. Try ten queries and note the misses.

---

## Step 5: Agent

**Goal:** the worker runs classify, retrieve, decide, act, and logs everything.

**Files:** `agent/schemas.py`, `state.py`, `llm.py`, `limits.py`, `graph.py`, `nodes/`, `tools/`, `prompts/`, `app/routes/runs.py`, `tests/test_agent_graph.py`

### 5.1 Structured outputs and state

`agent/schemas.py`:

```python
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class Category(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    QUESTION = "question"
    DOCS = "docs"
    SPAM = "spam"


class Classification(BaseModel):
    category: Category
    confidence: float
    reason: str


class Decision(BaseModel):
    action: Literal["label_only", "ask_for_info", "point_to_files"]
    files: list[str]
    comment: str
```

`agent/state.py`: a `TypedDict` with the issue fields, `classification`, `chunks`, `decision` and `result`.

### 5.2 LLM client

> **Note:** the snippet and bullets below are the original Anthropic version (`anthropic`, effort setting, fallbacks, price table) and no longer match the installed SDK. Ask for the Gemini boilerplate when you reach Step 5. The structure to keep is the same: one `LLMClient.structured(...)` that returns the parsed object, the token usage and the model name.

`agent/llm.py`:

```python
from typing import TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from common.config import Settings

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        # pydantic-settings does not export .env to os.environ, so pass the key.
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())
        self.model = settings.llm_model
        self.effort = settings.llm_effort

    async def structured(self, *, system: str, user: str, schema: type[T]):
        response = await self.client.beta.messages.parse(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": self.effort},
            output_format=schema,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            raise LLMError(f"no usable output: {response.stop_reason}")
        return response.parsed_output, response.usage, response.model
```

- `fallbacks="default"` lets the API retry a declined request on another model. The returned `response.model` tells you which one answered.
- With the default model, do not send `temperature`, a forced `tool_choice`, or a setting that disables thinking; the API rejects them.
- The SDK already retries rate limits and server errors twice. Map what still fails (`APIConnectionError`, `RateLimitError`, `InternalServerError`) to `TransientError`.
- `parse` raises a validation error if the output is cut off. Treat it as a failed call.
- Cost: keep a price table per model and multiply by `usage.input_tokens` and `usage.output_tokens`. For `claude-opus-5-5` the price was $4 input and $20 output per million tokens in November 2026; check the current price page. If the answering model is not in your table, store no cost instead of a guess. A request that fell back can be billed for more than one attempt (see `usage.iterations`).

### 5.3 Nodes and prompts

| Node | Does | Writes to state |
| --- | --- | --- |
| classify | LLM call with `Classification` | classification |
| retrieve | Search code and past issues | chunks |
| decide | LLM call with `Decision` | decision |
| act | Validate, then post labels and comment | result |

- Keep prompts in `agent/prompts/*.md`. Define each category with one or two examples **written by you, not copied from the test set**.
- Log a hash of the prompt with each evaluation run.
- Spam skips retrieval.

### 5.4 Treat issue text as hostile

Anyone can open an issue and write "ignore your instructions" in it.

- Put issue text and code chunks inside clearly marked tags in the user message, and tell the model they are data, not instructions.
- Labels come only from the `Category` enum.
- Keep only file paths that retrieval actually returned.
- Cap the comment length and neutralise mentions so the bot cannot ping people:

```python
import re


def neutralize_mentions(text: str) -> str:
    return re.sub(r"@(?=[A-Za-z0-9])", "@​", text)
```

- The model never receives secrets, and no tool lets it run commands.

### 5.5 Graph

```python
from functools import partial

from langgraph.graph import END, START, StateGraph

from agent.nodes.act import act
from agent.nodes.classify import classify
from agent.nodes.decide import decide
from agent.nodes.retrieve import retrieve
from agent.schemas import Category
from agent.state import TriageState


def after_classify(state: TriageState) -> str:
    is_spam = state["classification"].category == Category.SPAM
    return "decide" if is_spam else "retrieve"


def build_graph(deps):
    graph = StateGraph(TriageState)
    for name, node in [
        ("classify", classify),
        ("retrieve", retrieve),
        ("decide", decide),
        ("act", act),
    ]:
        graph.add_node(name, partial(node, deps=deps))
    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", after_classify, ["retrieve", "decide"])
    graph.add_edge("retrieve", "decide")
    graph.add_edge("decide", "act")
    graph.add_edge("act", END)
    return graph.compile()
```

Each node is `async def name(state, deps) -> dict` and returns only the keys it changes. `deps` holds the LLM client, search function and GitHub client, so tests can pass fakes.

Run it with `await graph.ainvoke(state, config={"recursion_limit": settings.agent_max_steps})`. The limit raises `GraphRecursionError`; the timeout is the one in the worker job.

### 5.6 Tools: be accurate about what you built

`search_code`, `get_issue_history` and `post_comment_and_labels` live in `agent/tools/`. In the graph above, **your code** calls them in a fixed order. That is a valid, predictable design, but describe it that way: the model is not choosing tools, and the step limit can never trigger.

Once the fixed version works, you may let the model call the two read-only tools in a bounded loop. Keep posting under code control.

For `get_issue_history`, start with the GitHub search API (`GET /search/issues`), and let it accept a "created before" date for step 6.

### 5.7 Logging and `/runs`

- Wrap every tool call to write a `tool_calls` row with input, output, success and latency, including failed calls.
- Update the run with status, category, tokens, cost and latency, including on fallback.
- `GET /runs` and `GET /runs/{id}` require `Authorization: Bearer <RUNS_API_TOKEN>`. Compare with `secrets.compare_digest`, and refuse all requests if the token is empty.

### Tests

Fake the LLM, search and GitHub client. Cover: normal path, spam path, invented file path removed, LLM error leading to fallback, timeout. Tests must not call a paid API.

**Done when:** a real issue gets a sensible label and comment, and `/runs/{id}` shows its tool calls, tokens, cost and latency.

---

## Step 6: Evaluation

**Goal:** measured, honest numbers.

**Files:** `evals/collect.py`, `runner.py`, `scorers.py`, `ablation.py`, `evals/dataset/`, `tests/test_scorers.py`

### 6.1 Collect

- Use closed issues from a few public repositories. `GET /repos/{owner}/{repo}/issues` also returns pull requests; drop items with a `pull_request` key.
- For retrieval ground truth, find the pull request that closed each issue (GraphQL field `closedByPullRequestsReferences`), then its changed files and base commit. Not every issue has one.
- One JSON object per line: repo, number, title, body, created_at, label, relevant_files, base_sha.

### 6.2 Label

1. Write your labeling rules down first.
2. Label by hand, without looking at model output.
3. Split into `dev.jsonl` and `test.jsonl` **before** tuning, keeping every category in both.
4. Tune on dev only. Run test at the end.

How many issues you need depends on your time; 150 to 200 is a reasonable target. Rare classes such as spam will have few examples, so report the count per class.

### 6.3 Avoid leaking the answer

- Index each repository at the commit **before** the fix (`base_sha`).
- Issue history may include only items created before the issue.
- Check bodies for later edits that mention the fix.

### 6.4 Score

| Metric | How |
| --- | --- |
| Accuracy, precision, recall | `sklearn.metrics.classification_report(..., output_dict=True, zero_division=0)` |
| Macro F1 | `f1_score(..., average="macro", labels=all_categories, zero_division=0)` |
| Hit rate@5 | Share of issues with ground truth where any of the top 5 chunks is from a changed file |
| Tool-call success, fallback rate | From `tool_calls` and `runs` |
| Cost per run | Mean of `cost_usd` |
| Latency | p50 and p95 with `numpy.percentile` |

The runner must force dry-run mode, support `--limit` for cheap trials, and save each result to `evals/results/` with the date, git commit, model, effort, prompt hash and chunk settings. Each run costs money, so try a few issues first.

### 6.5 Ablation and errors

Change one thing at a time. In the graph above, classification happens **before** retrieval, so "with or without retrieval" cannot change accuracy. Compare something that can:

| Change | Metric it can move |
| --- | --- |
| Chunking strategy (line windows vs. Python functions) | Hit rate@5 |
| Model or effort level | Accuracy, cost, latency |
| Prompt A vs. prompt B | Accuracy, macro F1 |

Compare on dev, then confirm on test once. Write up five real failures in [docs/evaluation.md](docs/evaluation.md): issue, expected, got, cause, fix or why not.

**Done when:** one command reproduces the results table, and `docs/evaluation.md` contains only measured values.

---

## Step 7: Ship

**Goal:** anyone can run it, and the README matches reality.

### 7.1 Container

`Dockerfile`:

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home appuser
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`.dockerignore`:

```gitignore
.venv
.git
.env
*.pem
**/__pycache__
docs/TriageBot Project Documentation.md
```

Add `api` and `worker` services to `docker-compose.yml`:

```yaml
  api:
    build: .
    env_file: .env
    environment: &internal
      DATABASE_URL: postgresql+asyncpg://triagebot:triagebot@postgres:5432/triagebot
      REDIS_URL: redis://redis:6379/0
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    build: .
    command: arq worker.main.WorkerSettings
    env_file: .env
    environment: *internal
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
```

Mount the private key into both containers as a read-only volume and point `GITHUB_PRIVATE_KEY_PATH` at it.

```powershell
docker compose run --rm api alembic upgrade head
```

```powershell
docker compose up --build
```

### 7.2 Deploy and publish

- Use a host that runs a web process, a worker, Redis and Postgres with pgvector.
- Use new database credentials, real secrets in the host's settings, and HTTPS.
- Set a spending limit with your LLM provider.
- Record a short demo video or GIF.
- Rewrite the README with measured results, honest limitations and the real structure.

**Done when:** a fresh clone starts by following only the README.

---

## Corrections to the project draft

Fix these before you publish or discuss the project.

| The draft says or implies | Actually |
| --- | --- |
| GitHub retries webhooks on timeout | GitHub does **not** redeliver failed deliveries automatically. Redelivery is manual or through the API, and keeps the same delivery ID. It expects a 2XX within 10 seconds. |
| Ablation: accuracy with vs. without retrieval | No effect if classification runs before retrieval (see 6.5). |
| The agent uses tools | Say whether your code or the model calls them (see 5.6). |

Deduplication by delivery ID is still worth having: redeliveries happen, and your own system can receive the same event twice.
