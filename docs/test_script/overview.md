# IBA Production Test Script — Overview

Test framework for validating the IBA v6 agent system on `alpha.keycenter.ai`
against real BPOM data. It authenticates Keycloak users, sends questions via
`POST /v6/chat`, streams answers via `GET /v6/sse`, and compares results
against expected keyword assertions defined in YAML test cases.

---

## Directory Structure

```
seeknal-bpom-neo/
├── scripts/
│   ├── test_concurrency_production.py   # Main test runner (all modes)
│   ├── iba_test_config_production.yml   # Config: URLs, credentials, test users
│   └── iba_test_client/
│       ├── __init__.py                  # Package exports
│       ├── auth.py                      # Keycloak ROPC auth + token cache
│       ├── chat.py                      # IBA v6 HTTP client (POST + SSE)
│       └── metrics.py                   # Latency tracking + aggregate stats
│
└── seeknal/tests/v1/production/
    ├── PROD-001.yml … PROD-020.yml      # Single-turn production test cases
    └── multiturn/
        ├── PROD-MT-001.yml              # NIE: definition → exploration (5 turns)
        ├── PROD-MT-002.yml              # NIE: year-over-year comparison (4 turns)
        ├── PROD-MT-003.yml              # NIE: ERBA vs all systems (4 turns)
        ├── PROD-MT-004.yml              # NIE: risk category breakdown (4 turns)
        ├── PROD-MT-005.yml              # MR: commitment status drilldown (4 turns)
        ├── PROD-MT-006.yml              # NIE: industry scale + UMKM (4 turns)
        ├── PROD-MT-007.yml              # NIE: specific product comparison (4 turns)
        ├── PROD-MT-008.yml              # BTP: ERBA vs ERLA (4 turns)
        ├── PROD-MT-009.yml              # Permohonan vs NIE concepts (5 turns)
        └── PROD-MT-010.yml              # SQL transparency (3 turns)
```

---

## Files and Purposes

### `scripts/test_concurrency_production.py`

The main entry point. Loads YAML scenarios, authenticates users, and runs
them in one of four modes. Saves JSON results to
`seeknal/tests/outputs/<date>/<version>/`.

**When to use:** Any time you want to validate system behavior against the
production BPOM agent — functional correctness, latency measurement, or
load testing.

See: [test_concurrency_production.md](test_concurrency_production.md)

---

### `scripts/iba_test_config_production.yml`

YAML configuration file. Defines Keycloak connection, IBA base URL, domain
ID, and the pool of test users. Pass it to the runner with `--config`.

**Key fields:**

| Field | Purpose |
|-------|---------|
| `iba.base_url` | IBA API base URL |
| `keycloak.*` | Realm, client credentials for ROPC auth |
| `test_users` | List of `{email, password}` for multi-user tests |
| `domain_id` | Target seeknal domain UUID |
| `seeknal.yaml_path` | Default directory for YAML test cases |

---

### `scripts/iba_test_client/auth.py`

`KeycloakClient` — authenticates users via the ROPC grant and caches tokens
in memory per email. Automatically re-authenticates when a token is within
60 seconds of expiry.

**When to use:** Import this when you need a valid Bearer token for IBA API
calls. You should not need to instantiate this directly; `test_concurrency_production.py`
handles it automatically.

See: [iba_test_client.md](iba_test_client.md)

---

### `scripts/iba_test_client/chat.py`

`IBAChatClient` — sends a question to the IBA v6 API and collects the
streamed response. Implements the two-phase flow:

1. `send_message()` → `POST /v6/chat` → returns `message_id` + `sse_token`
2. `stream_response()` → `GET /v6/sse` → reads SSE events until `done`

The `ask()` convenience method combines both phases.

**Important behavior:** On receiving an `error` SSE event the client does
NOT disconnect — it waits for `done`. This allows capturing the answer when
the Seeknal worker retries a failed Gemini call internally.

See: [iba_test_client.md](iba_test_client.md)

---

### `scripts/iba_test_client/metrics.py`

`LatencyTracker` + `RequestMetrics` + `compute_aggregate()`. Tracks
per-phase timing (auth, POST init, SSE stream, total) and computes p50/p95/p99
latency, throughput, and error rate across a batch of requests.

---

### `seeknal/tests/v1/production/PROD-*.yml`

Twenty single-turn test cases covering the main BPOM data queries:
total NIE counts, registration system comparisons, product categories,
geographic breakdowns, company rankings, and process metrics.

Each file follows this schema:

```yaml
name: Total_NIE_ERBA_2024
scenario_id: PROD-001
turns:
  - prompt: "Berapa total NIE pangan olahan di sistem ERBA tahun 2024?"
    assert_contains:
      - "ERBA"
      - "2024"
    note: "Optional developer annotation"
```

---

### `seeknal/tests/v1/production/multiturn/PROD-MT-*.yml`

Ten multi-turn conversation scenarios (3–5 turns each). Each scenario
tests **context retention**: later turns reference data from earlier turns
without repeating the full context. The agent must carry the
`conversation_id` across all turns within a session.

Use with `--multiturn` mode.

---

## Quick Start

```bash
cd seeknal-bpom-neo

# 1. Validate single-turn — sequential, all 20 cases
uv run python scripts/test_concurrency_production.py \
  --config scripts/iba_test_config_production.yml

# 2. Multi-user burst — 24 users, one case each
uv run python scripts/test_concurrency_production.py \
  --config scripts/iba_test_config_production.yml \
  --multi-user --stagger 500

# 3. Multiturn — 24 users, full conversation each
uv run python scripts/test_concurrency_production.py \
  --config scripts/iba_test_config_production.yml \
  --multiturn \
  --path seeknal/tests/v1/production/multiturn \
  --stagger 500

# 4. Realistic load — organic arrival + think-time between turns
uv run python scripts/test_concurrency_production.py \
  --config scripts/iba_test_config_production.yml \
  --multiturn \
  --path seeknal/tests/v1/production/multiturn \
  --stagger 30000 --turn-delay-ms 8000 --random-arrival \
  --version realistic-load
```

Results are saved to `seeknal/tests/outputs/<date>/<version>/concurrency_<timestamp>.json`.
