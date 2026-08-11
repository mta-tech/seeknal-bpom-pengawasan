# iba_test_client — Library Reference

Python library in `scripts/iba_test_client/`. Provides authentication,
HTTP chat, and latency tracking for all IBA test scripts.

---

## `auth.py` — KeycloakClient

Authenticates users against Keycloak using the Resource Owner Password
Credentials (ROPC) grant. Caches tokens per email address and
automatically re-acquires them before they expire.

### Class: `KeycloakClient`

```python
from iba_test_client.auth import KeycloakClient

kc = KeycloakClient(
    url="https://auth.keycenter.ai/auth",
    realm="keycenter",
    client_id="web",
    client_secret="<secret>",
)
token = kc.get_valid_token("user@pom.go.id", "password")
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `login(email, password)` | `TokenPair` | Authenticates and caches the token |
| `get_valid_token(email, password)` | `str` | Returns cached token or re-authenticates |
| `get_user_pool(users)` | `list[str]` | Pre-authenticates a list of users |
| `decode_claims(token)` | `dict` | Decodes JWT payload (no signature check) |
| `get_account_id(token)` | `str` | Extracts `sub` claim from JWT |

**Token caching:** tokens are cached per email with a 60-second safety margin.
If a token expires within 60 seconds, `get_valid_token` triggers re-authentication.

---

## `chat.py` — IBAChatClient

Implements the IBA v6 two-phase chat protocol.

### Two-phase flow

```
Phase 1: POST /v6/chat
  → returns message_id + sse_token immediately
  → backend queues work to Seeknal worker via Temporal (non-blocking)

Phase 2: GET /v6/sse?message_id=...&sse_token=...
  → opens SSE stream
  → receives events: token | tool_call | tool_result | message | done | error | heartbeat
  → stream ends on "done" event
```

### Class: `IBAChatClient`

```python
from iba_test_client.chat import IBAChatClient

client = IBAChatClient(
    token="<bearer_token>",
    base_url="https://alpha.keycenter.ai/api",
    service_path="",          # leave empty for production
)

# Full request in one call
answer = client.ask(
    query="Berapa total NIE pangan olahan di ERBA 2024?",
    domain_id="bbc5a1a3-dcdd-4684-9e6c-6134f0583005",
    stream_timeout=300,
)
print(answer.answer)
print(answer.tool_calls)      # number of SQL tool calls made
```

**Key behaviors:**

- **`error` event is not terminal.** The Seeknal worker retries failed Gemini
  calls internally via Temporal. If an `error` event arrives followed later by
  a `message` event, the error is cleared and the answer is captured. The
  client only disconnects on `done`.

- **Inactivity timeout** resets on every event including heartbeats (every 15s),
  so the stream stays alive during long worker processing.

- **`sse_token` is single-use.** It is consumed atomically in Redis on first
  connection. Reconnecting after a disconnect is not supported.

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `send_message(query, domain_id, conversation_id)` | `ChatResponse` | Phase 1: POST /v6/chat |
| `stream_response(message_id, sse_token, timeout)` | `StreamResult` | Phase 2: GET /v6/sse |
| `ask(query, domain_id, ...)` | `Answer` | Combined Phase 1 + Phase 2 |

### SSE Event Types

| Event | Payload | Effect |
|-------|---------|--------|
| `token` | `answer` (partial) | Appended to streaming answer buffer |
| `tool_call` | `tool_name`, `tool_args` | Increments tool call counter, extracts SQL |
| `tool_result` | — | Ignored (tracked via `tool_call`) |
| `message` | `answer` (final) | Sets the definitive answer; clears any prior error |
| `done` | — | Terminal: closes stream |
| `error` | `error_message` | Recorded but stream stays open |
| `heartbeat` | — | Resets inactivity deadline; no data effect |

---

## `metrics.py` — Latency Tracking

### Class: `LatencyTracker`

Measures elapsed time for named phases. Phases: `auth`, `init`, `ttft`
(time-to-first-token), `stream`, `total`.

```python
from iba_test_client.metrics import LatencyTracker

tracker = LatencyTracker()
tracker.start("total")
tracker.start("init")
resp = client.send_message(query, domain_id)
tracker.stop("init")
tracker.start("stream")
result = client.stream_response(resp.message_id, resp.sse_token)
tracker.stop("stream")
tracker.stop("total")
tracker.set_tool_calls(result.tool_call_count)
metrics = tracker.build()     # → RequestMetrics
```

### `compute_aggregate(metrics_list)`

Takes a list of `RequestMetrics` and returns aggregate statistics:

```python
from iba_test_client.metrics import compute_aggregate

agg = compute_aggregate(all_metrics)
# Keys: total_requests, successful, failed,
#       latency_p50_ms, latency_p95_ms, latency_p99_ms,
#       latency_min_ms, latency_max_ms, latency_avg_ms,
#       throughput_req_per_sec, error_rate_percent
```

### `RequestMetrics` Fields

| Field | Unit | Description |
|-------|------|-------------|
| `auth_latency_ms` | ms | Time spent on Keycloak token acquisition |
| `init_latency_ms` | ms | Time for POST /v6/chat response |
| `time_to_first_token_ms` | ms | SSE latency until first `token` event |
| `stream_duration_ms` | ms | Total SSE stream duration |
| `total_latency_ms` | ms | End-to-end request duration |
| `tool_calls` | count | Number of SQL tool calls made by agent |
| `sqls` | list[str] | Extracted SQL query strings |
| `status_code` | int | HTTP status of POST /v6/chat |
| `error` | str\|None | Error message if request failed |
