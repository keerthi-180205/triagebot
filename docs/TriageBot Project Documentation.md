# TriageBot: Project Documentation

Draft built from the project plan. Everything in **\[TODO\]** must be replaced with your real results once the project works. Do not publish numbers you have not measured, and delete any sentence that describes something you did not build.

---

# 1. README (copy into README.md)

## TriageBot

LLM agent that triages GitHub issues: it classifies each new issue, retrieves relevant code from the repository, and posts a labeled, helpful comment. Built with FastAPI, LangGraph, Redis, and Postgres/pgvector, with an eval harness and a live demo.

**Live demo:** \[TODO: URL\] **Demo repo where it is installed:** \[TODO: URL\] **Demo video/GIF:** \[TODO\]

### Problem

Maintainers of active repositories spend time sorting issues: labeling them, spotting duplicates and spam, and pointing reporters to the right files. TriageBot automates the first pass and logs every decision so its quality can be measured.

### Features

- Receives GitHub webhooks with HMAC signature verification and idempotent handling (duplicate deliveries are ignored)
- Queues work in Redis so the webhook responds quickly; a worker processes jobs asynchronously
- LangGraph agent with steps: classify, retrieve, decide, act
- Tools: `search_code`, `get_issue_history`, `post_comment_and_labels` \[TODO: match to what you built\]
- Safeguards: step limit, timeout, retry with backoff, fallback comment on failure \[TODO: confirm each\]
- Every run logged to Postgres: input, tool calls, tokens, cost, latency, outcome
- Eval harness with a hand-labeled dataset and reported metrics

### Results

Evaluated on \[TODO: N\] hand-labeled issues from \[TODO: repos\]. Prompts were tuned on \[TODO: n\_dev\] issues; results below are on the held-out \[TODO: n\_test\].

| Metric | Value |
| --- | --- |
| Classification accuracy | \[TODO\]% |
| Macro F1 | \[TODO\] |
| Retrieval hit rate@5 | \[TODO\]% |
| Tool-call success rate | \[TODO\]% |
| Avg cost per run | $\[TODO\] |
| p50 / p95 latency | \[TODO\] s / \[TODO\] s |
| Fallback rate | \[TODO\]% |

Ablation: \[TODO: e.g. with vs without retrieval: accuracy X% vs Y%\]. Details in the evaluation section below.

### Architecture (overview)

```
GitHub webhook
  -> FastAPI /webhook (verify signature, dedupe by delivery ID)
  -> Redis queue
  -> Worker
       -> LangGraph agent: classify -> retrieve -> decide -> act
       -> GitHub API (labels, comment)
       -> Postgres (runs, tool_calls, cost, latency, outcome)
```

### Quickstart

```
git clone [TODO: repo URL]
cd triagebot
cp .env.example .env   # add GitHub app credentials, webhook secret, LLM API key
docker-compose up --build
```

Then point your GitHub App webhook to `[TODO: public URL]/webhook`. \[TODO: add steps for creating the GitHub App and exposing localhost for local testing\]

### Project structure

```
triagebot/
  app/            # FastAPI app, webhook, routes
  worker/         # queue consumer
  agent/          # LangGraph graph, nodes, tools, prompts
  retrieval/      # chunking, embedding, indexing, search
  db/             # models, migrations
  evals/          # dataset, runner, scorers, results
  docs/           # architecture, decisions, evaluation
  tests/
```

&#91;TODO: match to your real structure\]

### Limitations

- &#91;TODO: be honest, e.g. tested on English issues from Python repos only\]
- &#91;TODO: e.g. retrieval quality drops on very large repos\]
- &#91;TODO: e.g. no multi-tenant support\]

### Future work

- Duplicate-issue detection with a similarity threshold
- Human-approval mode
- Per-repo configuration file

---

# 2. Architecture (docs/architecture.md)

## Request flow, step by step

1. **GitHub sends a webhook** when an issue or PR is opened.
2. **FastAPI `/webhook`** verifies the HMAC signature using the shared secret and a constant-time comparison. Invalid signatures get a 401 and are dropped.
3. **Idempotency check:** the delivery ID is stored with a unique constraint. If it already exists, the request returns 200 and does nothing. This handles GitHub retries.
4. **Enqueue:** the handler pushes a job (repo, issue number, event type) to Redis and returns quickly, so GitHub does not time out.
5. **Worker** pulls the job and starts the agent run.
6. **Agent** runs the graph: classify, retrieve, decide, act.
7. **Act** posts labels and a comment via the GitHub API.
8. **Logging:** the run, each tool call, token counts, cost, latency, and outcome are written to Postgres.
9. **Failure path:** if the agent errors, times out, or hits the step limit, the worker posts a generic fallback comment and records the failure.

## Components

### Webhook service

FastAPI app. Responsibilities: signature verification, dedupe, enqueue. No LLM work happens in the request path. \[TODO: note response time you measured\]

### Queue and worker

&#91;TODO: Redis with RQ / Celery / arq: name what you used.\] Retry policy: \[TODO: attempts, backoff\]. Jobs that fail permanently are marked failed in Postgres.

### Agent graph

| Node | Purpose | Output |
| --- | --- | --- |
| classify | Label the issue (bug, feature, question, docs, spam) | Structured JSON: category, confidence |
| retrieve | Search repo code and past issues for context | Top-k chunks with file paths |
| decide | Choose action: label only, ask for more info, point to files | Action plan |
| act | Post labels and comment | GitHub API result |

Limits: max \[TODO\] steps, timeout \[TODO\] s, max \[TODO\] retries per tool call.

### Retrieval

Repository is cloned, files chunked by \[TODO: strategy and size\], embedded with \[TODO: model\], and stored in pgvector. Search uses \[TODO: cosine similarity, top-k, any reranking\].

### Database schema

| Table | Key columns | Notes |
| --- | --- | --- |
| runs | id, repo, issue\_number, delivery\_id (unique), status, category, tokens, cost, latency\_ms, created\_at | Index on (repo, created\_at) |
| tool\_calls | id, run\_id, tool, input, output, success, latency\_ms | Index on run\_id |
| chunks | id, repo, path, content, embedding | Vector index: \[TODO: type\] |

&#91;TODO: replace with your real schema\]

---

# 3. Evaluation (docs/evaluation.md)

## Dataset

- &#91;TODO: N\] real issues collected from \[TODO: which public repos and why\]
- Labeled by hand by me into: bug, feature, question, docs, spam \[TODO: confirm categories\]
- For retrieval: ground truth is the file(s) changed in the PR that closed the issue, where available (\[TODO: how many issues have this\])
- Split: \[TODO: n\_dev\] development issues for prompt tuning, \[TODO: n\_test\] held-out test issues never used for tuning

## Metrics

- Classification: accuracy, per-class precision and recall, macro F1
- Retrieval: hit rate@5
- Reliability: tool-call success rate, failure rate, fallback rate
- Efficiency: average cost per run, p50 and p95 latency

## Results

| Metric | Value |
| --- | --- |
| Accuracy | \[TODO\] |
| Macro F1 | \[TODO\] |
| Hit rate@5 | \[TODO\] |
| Tool-call success | \[TODO\] |
| Cost per run | \[TODO\] |
| p95 latency | \[TODO\] |

### Per-class results

| Class | Precision | Recall | Support |
| --- | --- | --- | --- |
| bug | \[TODO\] | \[TODO\] | \[TODO\] |
| feature | \[TODO\] | \[TODO\] | \[TODO\] |
| question | \[TODO\] | \[TODO\] | \[TODO\] |
| docs | \[TODO\] | \[TODO\] | \[TODO\] |
| spam | \[TODO\] | \[TODO\] | \[TODO\] |

## Ablation

Compared: \[TODO: e.g. with retrieval vs without, or prompt A vs prompt B, or model A vs model B\]

| Variant | Accuracy | Hit rate@5 | Cost per run |
| --- | --- | --- | --- |
| \[TODO\] | \[TODO\] | \[TODO\] | \[TODO\] |
| \[TODO\] | \[TODO\] | \[TODO\] | \[TODO\] |

Conclusion: \[TODO: one or two sentences on what changed and why you think so\]

## Error analysis

Five failures, with what went wrong and what I changed:

1. &#91;TODO: issue, expected, got, root cause, fix or reason left unfixed\]
2. &#91;TODO\]
3. &#91;TODO\]
4. &#91;TODO\]
5. &#91;TODO\]

---

# 4. Design decisions (docs/decisions.md)

Format for each entry: Decision, Alternatives, Why, Tradeoff. Starter entries below. Rewrite the "Why" in your own words based on what you actually experienced.

### Queue and worker instead of processing in the request

- **Alternatives:** FastAPI BackgroundTasks, synchronous handling
- **Why:** GitHub expects a fast response and retries on timeout; the agent run takes seconds. \[TODO: add what you observed\]
- **Tradeoff:** extra infrastructure (Redis, worker process) and more moving parts to deploy

### Idempotency by delivery ID

- **Alternatives:** dedupe by issue number, no dedupe
- **Why:** GitHub can redeliver the same webhook; without dedupe the bot would comment twice. \[TODO: describe the bug if you hit it\]
- **Tradeoff:** one more DB write per webhook

### Postgres with pgvector for retrieval

- **Alternatives:** separate vector DB (Qdrant, Pinecone), FAISS in memory
- **Why:** one database for runs and vectors keeps deployment simple. \[TODO: confirm\]
- **Tradeoff:** less tuning and scale than a dedicated vector store

### Structured output for classification

- **Alternatives:** free-text answers parsed with regex
- **Why:** predictable fields make evaluation and fallbacks easier
- **Tradeoff:** occasional schema failures that need retries

### Step limit, timeout, and fallback comment

- **Alternatives:** unbounded agent loop
- **Why:** prevents runaway cost and silent failures. \[TODO: add a real case where it triggered\]
- **Tradeoff:** some hard issues get a generic reply instead of a full answer

### &#91;TODO: add 2 more from your real choices, e.g. chunk size, model choice, prompt versioning\]

---

# 5. API reference (docs/api.md)

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| POST | /webhook | Receive GitHub events | HMAC signature header `X-Hub-Signature-256` |
| GET | /health | Liveness check | None |
| GET | /runs | List recent runs | \[TODO\] |
| GET | /runs/{id} | Run details with tool calls | \[TODO\] |

### POST /webhook

- **Headers:** `X-GitHub-Event`, `X-GitHub-Delivery`, `X-Hub-Signature-256`
- **Body:** GitHub event payload (JSON)
- **Responses:** 200 accepted or duplicate; 401 invalid signature; 422 invalid payload

### GET /runs/{id}

&#91;TODO: paste a real example response from your running service\]

---

# 6. Interview cheat sheet (not for the repo)

Fill in answers from your own experience building it. Starter hints are below.

1. **What happens if GitHub retries a webhook?** Delivery ID is unique in the DB, so the second delivery is acknowledged and ignored.
2. **Why a queue?** The webhook must respond fast; the agent run is slow and can fail. \[TODO: your measured numbers\]
3. **How do you stop the agent looping or burning money?** Step limit, timeout, retry cap, fallback comment, cost logged per run.
4. **How did you choose chunk size?** \[TODO: what you tried and compared\]
5. **What was your worst failure?** \[TODO: pick from bugs.md\]
6. **How did you evaluate it, and could you be fooling yourself?** Held-out test set never used for tuning; labeled by hand; limitations noted. \[TODO\]
7. **What did the ablation show?** \[TODO\]
8. **How would you scale to 1,000 repos?** \[TODO: e.g. per-repo queues, worker autoscaling, index refresh strategy\]
9. **How do you verify the webhook signature?** HMAC-SHA256 of the raw body with the shared secret, compared in constant time.
10. **What would you do differently with more time?** \[TODO: honest answer\]

---

# Still to fill before this is publishable

- [ ] All metrics and result tables (run the eval first)
- [ ] Real repo structure, schema, and tool list
- [ ] Demo URL, repo URL, GIF or video
- [ ] Five real error-analysis cases
- [ ] Two to three more decisions from your own experience
- [ ] Limitations section written honestly
- [ ] Read every sentence and delete anything you did not actually build
