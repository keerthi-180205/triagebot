# Architecture

Planned design. Not built yet.

## Request flow

1. GitHub sends a webhook when an issue or PR is opened.
2. `/webhook` verifies the HMAC signature in constant time; invalid requests get a 401.
3. The delivery ID is stored under a unique constraint; duplicates return 200 and do nothing.
4. A job is pushed to Redis and the request returns.
5. The worker pulls the job and starts an agent run.
6. The agent runs classify, retrieve, decide, act.
7. Act posts labels and a comment through the GitHub API.
8. The run, tool calls, tokens, cost, latency and outcome are written to Postgres.
9. On error, timeout or step limit, a fallback comment is posted and the failure recorded.

## Components

### Webhook service

To be written.

### Queue and worker

To be written.

### Agent graph

| Node | Purpose | Output |
| --- | --- | --- |
| classify | Label the issue | Category and confidence |
| retrieve | Find relevant code and past issues | Top-k chunks with file paths |
| decide | Choose an action | Action plan |
| act | Post labels and comment | GitHub API result |

Limits: to be decided.

### Retrieval

To be written.

### Database schema

| Table | Key columns |
| --- | --- |
| runs | id, repo, issue_number, delivery_id (unique), status, category, tokens, cost, latency_ms, created_at |
| tool_calls | id, run_id, tool, input, output, success, latency_ms |
| chunks | id, repo, path, content, embedding |
