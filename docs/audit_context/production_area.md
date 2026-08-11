# Production Area — Audit Context

**keyword:** `production_area`  
**environment:** `https://alpha.keycenter.ai/api`  
**domain_id:** `bbc5a1a3-dcdd-4684-9e6c-6134f0583005`  
**date:** 2026-06-14  
**worker:** `seeknal-worker-bpom-neo` (max_concurrency: 20)

---

## System Under Test

```
User → Keycloak (auth.keycenter.ai) → Bearer token
     → POST /v6/chat (IBA service)  → message_id + sse_token
     → GET  /v6/sse  (SSE stream)   → tool_call events + final answer
     → Temporal task queue          → Seeknal worker (Gemini + SQL)
     → PostgreSQL BPOM database     → structured query results
```

**LLM:** `gemini-3-flash-preview`  
**Database:** BPOM pangan olahan (ERBA, ERLA registration systems)

---

## Test Runs — 2026-06-14

### Run 1 — Multi-User Parallel (single-turn, 24 users)

**Command:**
```bash
uv run python scripts/test_concurrency_production.py \
  --config scripts/iba_test_config_production.yml \
  --multi-user --stagger 500
```

**Results:**

| Metric | Value |
|--------|-------|
| Total requests | 24 |
| Assertions PASS | **20 / 24 (83%)** |
| Gemini 503 errors | 3 |
| Empty answers | 0 |
| Error rate | 12.5% |
| Latency p50 | 36.6s |
| Latency p95 | 60.8s |
| Latency avg | 35.6s |
| Latency max | 70.7s |

**Key finding:** All 24 SSE connections delivered answers (0 empty). The 3 failures
were HTTP 503 from Gemini under concurrent load — the LLM provider rate-limited
requests when all 24 users hit it nearly simultaneously. Temporal retried these
internally; the SSE client captured the answer from the retry because it no longer
breaks on `error` events (see Bug Fix below).

---

### Run 2 — Multi-User Multiturn Burst (24 users, 4–5 turns each)

**Command:**
```bash
uv run python scripts/test_concurrency_production.py \
  --config scripts/iba_test_config_production.yml \
  --multiturn \
  --path seeknal/tests/v1/production/multiturn \
  --stagger 500 --version multiturn-production
```

**Results:**

| Metric | Value |
|--------|-------|
| Total requests | 99 (24 users × 4.1 avg turns) |
| Assertions PASS | **94 / 99 (94.9%)** |
| Gemini 503 errors | 3 |
| Empty answers | 0 |
| Error rate | 3.0% |
| Latency p50 | 14.4s |
| Latency p95 | 47.2s |
| Latency avg | 19.6s |
| Latency max | 70.6s |

**Latency per turn:**

| Turn | n | Avg | p50 | Max | Observation |
|------|---|-----|-----|-----|-------------|
| T1 (fresh query) | 24 | 29.1s | 26.0s | 67.5s | Agent runs 4–14 SQL tool calls |
| T2 (follow-up) | 24 | 20.8s | 13.8s | 70.6s | Mixed — some queries, some recall |
| T3 | 24 | 13.0s | 13.2s | 21.6s | Mostly context recall |
| T4 | 22 | 17.8s | 12.9s | 47.2s | Mostly context recall |
| T5 | 5 | 7.6s | 7.1s | 12.8s | Almost no SQL needed |

**Key finding:** Context retention confirmed working — T3/T4/T5 frequently
`tools=0` because the agent recalls data from earlier turns without re-querying.

---

### Run 3 — Multi-User Multiturn Realistic (24 users, organic arrival, 8s think-time)

**Command:**
```bash
uv run python scripts/test_concurrency_production.py \
  --config scripts/iba_test_config_production.yml \
  --multiturn \
  --path seeknal/tests/v1/production/multiturn \
  --stagger 30000 --turn-delay-ms 8000 --random-arrival \
  --version realistic-load
```

**Configuration:**
- Users arrive at random times within a 12-minute window (720 seconds)
- 8 seconds wait between turns (simulates reading the response)
- No two users guaranteed to be on the same turn at the same time

**Results:**

| Metric | Value |
|--------|-------|
| Total requests | 94 |
| Assertions PASS | **91 / 94 (96.8%)** |
| Gemini 503 errors | 2 |
| Empty answers | 0 |
| Error rate | 2.1% |
| Latency p50 | **8.7s** |
| Latency p95 | **30.2s** |
| Latency avg | **13.1s** |
| Latency max | 61.6s |

**Latency per turn (realistic vs burst comparison):**

| Turn | Burst avg | Realistic avg | Improvement |
|------|-----------|---------------|-------------|
| T1 | 29.1s | **21.1s** | -27% |
| T2 | 20.8s | **11.9s** | -43% |
| T3 | 13.0s | **6.8s** | -48% |
| T4 | 17.8s | **13.4s** | -25% |

**Latency by tool-call count:**

| Tool calls | Burst avg | Realistic avg | Improvement |
|------------|-----------|---------------|-------------|
| 0 tools | 9.2s | **4.4s** | -52% |
| 1–3 tools | 16.8s | **9.8s** | -42% |
| 4–7 tools | 30.7s | **20.0s** | -35% |
| 8+ tools | 56.4s | **46.1s** | -18% |

**Key finding:** Organic arrival reduces Gemini contention significantly.
When users are spread over time instead of bursting simultaneously, each
T1 request gets full Gemini capacity → latency drops 27–48% per turn.
This confirms the bottleneck is **Gemini API concurrency**, not IBA/Seeknal/Temporal infrastructure.

---

## Bug Fixes Applied During Session

### SSE Client: `error` event was terminating the stream prematurely

**File:** `scripts/iba_test_client/chat.py`

**Problem:** When the Seeknal worker failed a Gemini call, it published an
`error` SSE event. The client was calling `break` on that event, disconnecting
immediately. If Temporal retried the activity and the worker then published
a successful `message + done`, the client had already left — missing the answer.
This caused ~80% empty answers in early runs.

**Fix:** Removed the `break` after `error` events. The client now waits for
`done` as the sole terminal signal. If a `message` event arrives after a
previous `error`, the error is cleared (retry succeeded).

```python
# Before (broken):
elif event_type == "error":
    result.error = payload.get("error_message", "unknown error")
    break  # ← missed the retry answer

# After (fixed):
elif event_type == "error":
    result.error = payload.get("error_message", "unknown error")
    # stream stays open — Temporal may retry and send message+done

elif event_type == "message":
    result.answer = payload.get("answer", result.answer)
    result.error = None  # retry succeeded after earlier error event
```

**Impact:** Improved pass rate from 4/24 → 17/24 → 20/24 across successive
runs. Empty answer rate dropped from 80%+ to 0%.

---

## Observations and Constraints

### What works well
- IBA service, Temporal task queue, Seeknal worker, and SSE delivery are stable
- Context retention across multiturn conversations is reliable (follow-up turns
  use conversation history correctly, often with `tools=0`)
- 24 concurrent users can be handled without infrastructure failures

### Bottlenecks identified
- **Gemini API rate limit:** Under burst load (24 simultaneous T1 requests),
  approximately 2–3 requests receive HTTP 503 from `gemini-3-flash-preview`.
  Temporal retries recover these within the same SSE session.
- **Sequential tool calls:** Each LLM reasoning cycle (think → SQL → result → think)
  takes 3–10 seconds. Complex questions requiring 10+ tool calls can take 60–70s.
  This is inherent to the ReAct agent pattern, not an infrastructure issue.
- **Gemini contention under burst:** All 24 T1 requests hitting Gemini simultaneously
  causes visible latency increase (avg 29s) vs organic load (avg 21s).

### Not a bottleneck
- IBA POST /v6/chat endpoint (non-blocking, returns in <1s)
- Redis SSE delivery (per-message channels, independent streams)
- Temporal queueing (visible from logs: all tasks enqueued and processed)
- Keycloak authentication (parallel login for 24 users in ~15s)

---

## Test Users

24 accounts used for multi-user tests:

| Account | Password |
|---------|---------|
| `user-test@pom.go.id` | `12345678` |
| `user-test-1@pom.go.id` … `user-test-24@pom.go.id` | `BPOM@2026` |

Note: `user-test-3@pom.go.id` was skipped (account not available).
