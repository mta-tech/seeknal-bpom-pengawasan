# test_concurrency_production.py — CLI Reference

Production load test runner for the IBA v6 API on `alpha.keycenter.ai`.

---

## Execution Modes

### `sequential` (default)

Sends one scenario at a time. After every request, waits `--stagger-ms`
before the next. Automatically retries any request that returned an empty
answer (up to `--max-retries` times, waiting `--retry-wait` seconds between
batches).

Best for: reliable functional validation. Achieves 20/20 pass rate.

```bash
uv run python scripts/test_concurrency_production.py \
  --config scripts/iba_test_config_production.yml
```

---

### `--parallel`

Launches all selected scenarios simultaneously using `asyncio.gather`.
Uses a single Keycloak token. A configurable launch stagger
(`--stagger-ms`) spreads the initial burst.

Best for: measuring burst behavior with a single user account.

```bash
uv run python scripts/test_concurrency_production.py \
  --config scripts/iba_test_config_production.yml \
  --parallel --stagger-ms 500
```

---

### `--multi-user`

Each user in `test_users` authenticates independently and receives one
YAML scenario (distributed round-robin). All users fire simultaneously.

Best for: true multi-user concurrency test — each request carries a
distinct JWT token and user identity.

```bash
uv run python scripts/test_concurrency_production.py \
  --config scripts/iba_test_config_production.yml \
  --multi-user --stagger 500
```

---

### `--multiturn`

Each user runs ALL turns of their assigned scenario sequentially, carrying
`conversation_id` between turns. All users run their full scenario in
parallel with each other.

Two optional sub-flags control the timing model:

| Flag | Default | Effect |
|------|---------|--------|
| `--turn-delay-ms N` | `0` | Wait N ms after each turn (simulates reading time) |
| `--random-arrival` | off | Users arrive at random times within the stagger window instead of linearly |

**Burst mode** (no delay, linear stagger):
```bash
uv run python scripts/test_concurrency_production.py \
  --config scripts/iba_test_config_production.yml \
  --multiturn \
  --path seeknal/tests/v1/production/multiturn \
  --stagger 500
```

**Realistic mode** (organic arrival + reading pause):
```bash
uv run python scripts/test_concurrency_production.py \
  --config scripts/iba_test_config_production.yml \
  --multiturn \
  --path seeknal/tests/v1/production/multiturn \
  --stagger 30000 --turn-delay-ms 8000 --random-arrival \
  --version realistic-load
```

---

## All CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--config` | `scripts/iba_test_config_production.yml` | Path to config YAML |
| `--path` | from config `seeknal.yaml_path` | Override test case directory |
| `--concurrency` | `20` | Max scenarios to run (sequential/parallel mode) |
| `--base-url` | from config | Override IBA base URL |
| `--domain-id` | from config | Override domain UUID |
| `--stream-timeout` | `3600` | Seconds of SSE inactivity before timeout |
| `--stagger-ms` | `10000` | Ms between sequential requests OR user arrival window |
| `--parallel` | off | Run all cases concurrently (single user) |
| `--multi-user` | off | Each test user fires one case in parallel |
| `--multiturn` | off | Each user runs all turns of their scenario |
| `--turn-delay-ms` | `0` | Ms to wait between turns in multiturn mode |
| `--random-arrival` | off | Randomize user arrival within stagger window |
| `--no-retry-empty` | off | Disable automatic retry of empty answers |
| `--max-retries` | `2` | Max retry attempts per empty answer |
| `--retry-wait` | `60` | Seconds to wait before each retry batch |
| `--version` | `concurrency-production` | Output subdirectory label |

---

## Output JSON Schema

Saved to `seeknal/tests/outputs/<YYYY-MM-DD>/<version>/concurrency_<timestamp>.json`.

```json
{
  "mode": "multi-user-multiturn",
  "config": { "base_url": "...", "domain_id": "...", "users": 24, ... },
  "timestamp": "2026-06-14T10:20:06+00:00",
  "per_request": [
    {
      "scenario_id": "PROD-MT-001",
      "user_id": "user-test@pom.go.id",
      "turn": 1,
      "prompt": "apa itu NIE?",
      "answer": "NIE adalah Nomor Izin Edar ...",
      "passed": true,
      "failures": [],
      "attempt": 1,
      "answer_length": 692,
      "metrics": {
        "auth_latency_ms": 0.0,
        "init_latency_ms": 312.4,
        "time_to_first_token_ms": 0.0,
        "stream_duration_ms": 8205.1,
        "total_latency_ms": 8518.0,
        "tool_calls": 2,
        "sqls": ["SELECT ..."],
        "status_code": 200,
        "error": null
      }
    }
  ],
  "aggregate": {
    "total_requests": 99,
    "successful": 96,
    "failed": 3,
    "latency_p50_ms": 14401.8,
    "latency_p95_ms": 47171.1,
    "latency_p99_ms": 67533.1,
    "latency_min_ms": 3310.9,
    "latency_max_ms": 70604.5,
    "latency_avg_ms": 19585.9,
    "throughput_req_per_sec": 0.05,
    "error_rate_percent": 3.0
  }
}
```

---

## YAML Test Case Format

```yaml
name: nie_definisi_ke_eksplorasi        # human-readable name
scenario_id: "PROD-MT-001"             # unique ID used in output and logs
description: "Optional description"    # developer context
turns:
  - prompt: "apa itu NIE?"
    assert_contains:                   # all strings must appear in the answer
      - "Nomor Izin Edar"
      - "izin edar"
    note: "Optional annotation"        # not evaluated, for developer reference
  - prompt: "berapa total NIE ERBA 2024?"
    assert_contains:
      - "ERBA"
      - "2024"
```

Single-turn scenarios use only the first turn. Multi-turn scenarios carry
`conversation_id` across all turns automatically when using `--multiturn`.
