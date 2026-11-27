# API reference

Planned endpoints. None are implemented yet.

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| POST | /webhook | Receive GitHub events | HMAC signature header `X-Hub-Signature-256` |
| GET | /health | Liveness check | None |
| GET | /runs | List recent runs | To be decided |
| GET | /runs/{id} | Run details with tool calls | To be decided |
