# Testing Guide — seeknal-bpom-neo

This guide covers everything you need to write, run, and extend test cases for the seeknal-bpom-neo agent system.

---

## Table of Contents

1. [How the Test System Works](#1-how-the-test-system-works)
2. [Prerequisites & Environment Setup](#2-prerequisites--environment-setup)
3. [Running Tests](#3-running-tests)
4. [YAML Scenario Format](#4-yaml-scenario-format)
5. [Adding New Test Cases](#5-adding-new-test-cases)
6. [Extending the Test Runner](#6-extending-the-test-runner)
7. [Reading Test Output](#7-reading-test-output)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. How the Test System Works

```
YAML scenario file
      │
      ▼
test_multiturn_v3.py        ← loads all .yml files from --path
      │
      ▼
Agent (bpom-analyst skill)  ← receives prompt, runs SQL, generates answer
      │
      ▼
Oracle string matching      ← checks assert_contains against answer text
      │
      ▼
JSON result file            ← saved to seeknal/tests/outputs/<date>/<version>/
```

**Test types:**

| Prefix | Location | Purpose | Typical oracle |
|--------|----------|---------|----------------|
| `CB-*` | `v1/singleturn/` | Capability Benchmark — numeric answers | Specific numbers (`"40.716"`) |
| `NIE-*` | `v1/singleturn/` | Concept/definition questions | Keywords (`"Nomor Izin Edar"`) |
| `MT-*` | `v1/multiturn/` | Multi-turn dialogs with state retention | Mix of numbers and phrases |

**Oracle matching** uses case-insensitive substring search — every string in `assert_contains` must appear somewhere in the agent's answer. A turn passes only when all strings match.

```python
# internal logic
for expected in turn.assert_contains:
    if expected.lower() not in answer.lower():
        failures.append(f"missing: '{expected}'")
passed = len(failures) == 0
```

---

## 2. Prerequisites & Environment Setup

### 2a. SSH Tunnel

The database is a read-only PostgreSQL instance on a remote BPOM server. Access requires an SSH tunnel.

```
your machine:5533  ──SSH──►  10.59.2.29  ──►  postgres:5433
```

**Option 1 — Use the helper script (recommended):**

```bash
bash scripts/start_tunnel.sh
```

Keep this terminal open. The tunnel stays alive via `ServerAliveInterval`.

**Option 2 — Manual command:**

```bash
sshpass -p "CBN25*pom" ssh \
  -L 5533:localhost:5433 \
  -o ServerAliveInterval=60 \
  -N \
  cbnpom@10.59.2.29
```

| Flag | Meaning |
|------|---------|
| `-L 5533:localhost:5433` | Forward local port 5533 to remote postgres on port 5433 |
| `-o ServerAliveInterval=60` | Send keepalive every 60s so the tunnel doesn't drop |
| `-N` | No remote shell — tunnel only |

### 2b. Environment File

```bash
cp .env.example .env
```

Required variables in `.env`:

```bash
# Database — points to the SSH tunnel
WAREHOUSE_URL=postgresql://readonly_user:read_only_seeknal@localhost:5533/rpo_v2

# LLM provider
GOOGLE_API_KEY=<your-key>
SEEKNAL_ASK_LLM_PROVIDER=google
SEEKNAL_ASK_MODEL=gemini-3-flash-preview

# Test output versioning (controls output subdirectory)
TEST_DATA_VERSION=v1
```

### 2c. Verify the Connection

```bash
uv run python scripts/test_db_conn.py
```

Expected output: `COUNT(DISTINCT nomor)` result for `t_produk_3_erba` (should return tens of thousands). If you see `Catalog "warehouse" does not exist`, the tunnel is not active.

---

## 3. Running Tests

### Quick Start

```bash
# All singleturn scenarios (61 total: CB + NIE groups)
uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/singleturn

# All multiturn scenarios (13 total: MT-001 through MT-013)
uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/multiturn

# Everything under v1/ (default)
uv run python scripts/test_multiturn_v3.py
```

### CLI Reference

```
uv run python scripts/test_multiturn_v3.py [OPTIONS]

  --path PATH           Directory to load YAML scenarios from.
                        Default: seeknal/tests/v1

  --scenario TEXT       Run only scenarios whose name or scenario_id contains
                        this substring (case-insensitive).
                        Example: --scenario CB-1   (exact match)
                                 --scenario MT     (all MT-* scenarios)
                                 --scenario nie    (all NIE-* scenarios)

  --workers N           Number of parallel workers.
                        Default: 1 (sequential — recommended for debugging).
                        Use N > 1 only when the DB connection is stable.

  --turn-timeout N      Per-turn timeout in seconds via SIGALRM.
                        Only works in sequential mode (--workers 1).
                        Default: 0 (no limit).

  --timeout N           Per-scenario wall-clock timeout for parallel mode.
                        Default: 300 seconds.

  --version VERSION     Override the output subdirectory version tag.
                        Default: reads TEST_DATA_VERSION from .env.

  --hide-sql            Suppress SQL statements from console output
                        (parallel mode only).
```

### Common Invocations

```bash
# Run a single scenario by ID
uv run python scripts/test_multiturn_v3.py --scenario CB-1

# Run all CB group scenarios
uv run python scripts/test_multiturn_v3.py --scenario CB --path seeknal/tests/v1/singleturn

# Run with 4 parallel workers (faster, harder to debug)
uv run python scripts/test_multiturn_v3.py --workers 4

# Run sequentially with a 5-minute per-turn limit
uv run python scripts/test_multiturn_v3.py --workers 1 --turn-timeout 300

# Tag output with a custom version
uv run python scripts/test_multiturn_v3.py --version v2
```

### Other Scripts

| Script | Purpose | Requires tunnel? |
|--------|---------|-----------------|
| `scripts/test_db_conn.py` | Verify DB connectivity | Yes |
| `scripts/test_smoke.py` | 4-turn smoke test (light infra check) | Yes (T4 only) |
| `scripts/bench.py` | Performance benchmarking with metrics | Yes |
| `scripts/test_multiturn_v2.py` | Previous runner with hardcoded scenarios | Yes |

---

## 4. YAML Scenario Format

All scenario files live under `seeknal/tests/v1/` and are picked up recursively by `rglob("*.yml")`.

### 4a. Singleturn Scenario

One prompt, one answer, one set of assertions.

**File path:** `seeknal/tests/v1/singleturn/<ID>_<descriptive_name>.yml`

```yaml
name: 01_Berapa izin edar produk pangan olahan risiko menengah rendah
scenario_id: CB-1
description: "Optional longer description of what this scenario tests"
turns:
  - prompt: "Berapa izin edar produk pangan olahan risiko menengah rendah?"
    assert_contains:
      - "40.716"     # all-time total (dot as thousands separator)
    note: "CB-1"     # metadata only — not executed by the runner
```

### 4b. Multiturn Scenario

Multiple turns sharing the same conversation history. Each turn's answer is informed by all previous turns.

**File path:** `seeknal/tests/v1/multiturn/<ID>_<short_name>.yml`

```yaml
name: nie_definisi_ke_eksplorasi
scenario_id: "MT-001"
description: "From NIE definition to data exploration: total, risk, scale, UMKM"
turns:
  - prompt: "apa itu NIE?"
    assert_contains:
      - "Nomor Izin Edar"
      - "izin edar"
    note: "T1 — Basic definition, agent must explain the concept"

  - prompt: "berapa total NIE pangan olahan di sistem ERBA yang terbit tahun 2023?"
    assert_contains:
      - "30.276"
      - "2023"
      - "ERBA"
    note: "T2 — Baseline number, agent must use tanggal (issue date), not tanggal_bayar"

  - prompt: "kalau per kategori risiko bagaimana?"
    assert_contains:
      - "Risiko Tinggi"
      - "Risiko Menengah Tinggi"
      - "Risiko Menengah Rendah"
      - "17.504"
    note: "T3 — Must retain ERBA + 2023 context from T2 without being re-stated"

  - prompt: "dari situ, yang UMKM berapa?"
    assert_contains:
      - "UMKM"
      - "12.407"
    note: "T4 — 'Dari situ' is an implicit reference to T3 data. UMKM = Mikro+Kecil+Menengah"
```

### 4c. Field Reference

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | ✓ | string | Human-readable scenario name. Convention: `{number}_{description}` |
| `scenario_id` | ✓ | string | Unique identifier used in `--scenario` filter and JSON output |
| `description` | ✗ | string | Extended description of what the scenario tests |
| `turns[].prompt` | ✓ | string | The user question sent to the agent |
| `turns[].assert_contains` | ✗ | list[string] | All strings must appear (case-insensitive) in the answer |
| `turns[].note` | ✗ | string | Human annotation — never read by the runner |

### 4d. Writing Good Assertions

**Numbers** — use the Indonesian thousands separator (dot, not comma):
```yaml
assert_contains:
  - "40.716"    # correct
  - "40,716"    # wrong — will never match
  - "40716"     # wrong — will never match
```

**Keywords** — use substrings, not full phrases:
```yaml
assert_contains:
  - "Risiko Tinggi"              # good — substring match
  - "Risiko Tinggi (kode 301)"   # too strict — fragile
```

**Official abbreviations** — use the short form exactly as the agent produces it:
```yaml
assert_contains:
  - "NIE MR"    # correct
  - "NIE MT"
  - "NIE T"
  # Not: "NIE Risiko Menengah Rendah" — the agent may abbreviate differently
```

**Trend assertions** — include the phrase `"per tahun"` for year-over-year questions:
```yaml
assert_contains:
  - "per tahun"   # confirms the agent produced a yearly breakdown
```

**Scope assertions** — for all-time questions, verify scope is stated:
```yaml
assert_contains:
  - "40.716"      # the all-time total
  - "all-time"    # or "keseluruhan" — confirms agent reported full scope
```

**Keep assertions minimal** — only assert what is core to the scenario. Over-specifying causes false failures from phrasing variation.

### 4e. Naming Conventions

```
singleturn CB:   CB-{number}_{descriptive_name}.yml
singleturn NIE:  NIE-{number}_{descriptive_name}.yml
multiturn:       MT-{zero_padded_number}_{short_name}.yml

Examples:
  CB-1_nie_risiko_mr.yml
  NIE-5_definisi_erba_erla.yml
  MT-014_permohonan_vs_nie.yml
```

Numbers must be unique within each prefix group. Check existing IDs before adding a new one.

---

## 5. Adding New Test Cases

### Step 1 — Choose the type

| Question type | Use |
|--------------|-----|
| Single factual/numeric question | `CB-*` singleturn |
| Single definition/concept question | `NIE-*` singleturn |
| Dialog with follow-ups that build on each other | `MT-*` multiturn |

### Step 2 — Find the correct oracle value

Run the query directly to verify the number before writing the assertion. Never guess.

```bash
# Quick connectivity + sample query
uv run python scripts/test_db_conn.py

# Or write a standalone DuckDB script to check
```

For an all-time query the result should be several times larger than a single year's count. If your all-time result equals the 2023 result, the date filter is probably wrong.

### Step 3 — Create the YAML file

```bash
# For a new singleturn CB test
touch seeknal/tests/v1/singleturn/CB-40_my_new_scenario.yml

# For a new multiturn test
touch seeknal/tests/v1/multiturn/MT-014_my_dialog_scenario.yml
```

Fill in the file following the format in Section 4. Use the verified oracle value in `assert_contains`.

### Step 4 — Run it in isolation

```bash
uv run python scripts/test_multiturn_v3.py --scenario CB-40 --workers 1
```

### Step 5 — Inspect the JSON output

Open the result file in `seeknal/tests/outputs/<date>/<version>/` and verify:
- `"passed": true`
- The `sqls` array shows the correct query with proper date ranges and filters
- The `answer` text contains the expected strings
- `elapsed_s` is reasonable (under 600s)

If the scenario fails with `"missing: '...'` but the answer looks correct, the assertion string may not match the agent's exact phrasing — adjust `assert_contains` to use a shorter substring.

---

## 6. Extending the Test Runner

The runner is `scripts/test_multiturn_v3.py`. Key extension points:

### Add a new CLI flag

Add an `add_argument` call in the `argparse` block (around line 580) and thread the value through to `run_all()` or `run_all_parallel()`.

### Add a new assertion type

Currently only `assert_contains` (substring match) is supported. To add `assert_not_contains` or `assert_regex`:

1. Add the new field to the YAML schema (the `Turn` dataclass or TypedDict)
2. Add evaluation logic in the turn-checking loop alongside the existing `assert_contains` loop
3. Populate `failures` with a descriptive message on mismatch

### Add a new scenario group

Create a new subdirectory under `seeknal/tests/v1/` (e.g., `v1/regression/`). The runner picks up all `.yml` files recursively, so no changes to the runner are needed — just pass `--path seeknal/tests/v1/regression`.

---

## 7. Reading Test Output

Results are saved as JSON to:
```
seeknal/tests/outputs/<YYYY-MM-DD>/<TEST_DATA_VERSION>/multiturn_results_<HHMMSStz>.json
```

### Top-level summary

```json
{
  "project_path": "/home/mta/projects/seeknal_audit/seeknal-bpom-neo",
  "timestamp": "2026-05-26T07:20:00.621943+00:00",
  "mode": "multiturn-v3",
  "version": "v1",
  "filter": null,
  "scenarios": [...],
  "summary": {
    "total_scenarios": 61,
    "passed_scenarios": 53,
    "failed_scenarios": 8,
    "total_turns": 61,
    "passed_turns": 53,
    "failed_turns": 8
  }
}
```

### Per-turn detail

```json
{
  "turn_num": 1,
  "prompt": "Berapa izin edar produk pangan olahan risiko menengah rendah?",
  "passed": true,
  "timed_out": false,
  "elapsed_s": 262.26,
  "llm_requests": 27,
  "tool_calls": 32,
  "sqls": [
    "SELECT COUNT(DISTINCT nomor) FROM t_produk_3_erba WHERE ..."
  ],
  "failures": [],
  "answer": "Total all-time: 40.716 NIE ..."
}
```

### Interpreting failures

| Symptom | Likely cause |
|---------|-------------|
| `"failures": ["missing: '40.716'"]` | The number is absent from the answer — year-bias or wrong query |
| `elapsed_s > 400` + `tool_calls > 40` | Cold-start discovery loop — warehouse not connected |
| `llm_requests: 0`, `tool_calls: 0`, `elapsed_s > 100` | Tool-level infrastructure error (max retries exceeded) |
| Answer contains `"Catalog \"warehouse\" does not exist"` | SSH tunnel is down |
| Answer gives 2023 value instead of all-time | Agent fell back to reference values from `data_quality_rules.md` — tunnel was down |

### Performance benchmarks (typical)

| Metric | Expected range |
|--------|---------------|
| `elapsed_s` per turn | 250–500 s |
| `tool_calls` per turn (DB connected) | 25–45 |
| `tool_calls` per turn (DB not connected) | 40–75 (discovery loop) |
| `llm_requests` per turn | 25–60 |

---

## 8. Troubleshooting

### "Catalog 'warehouse' does not exist"

The DuckDB–PostgreSQL bridge is not initialized. Every agent session starts cold — the ATTACH command must succeed before any SELECT can run.

```bash
# 1. Confirm the tunnel is active
ss -tlnp | grep 5533         # Linux
netstat -an | grep 5533      # macOS/Windows

# 2. Re-start the tunnel
bash scripts/start_tunnel.sh

# 3. Verify
uv run python scripts/test_db_conn.py
```

### Agent returns 2023 value instead of all-time

The agent cannot reach the database and falls back to reference values embedded in `context/data_quality_rules.md` (e.g., "46 MR dibatalkan in 2023"). This is a known risk: reference values used as sanity-check examples become hallucination fuel when the DB is offline.

Fix: ensure the tunnel is active before running tests.

### "Tool 'execute_sql' exceeded max retries count of 1"

Infrastructure-level failure — the tool itself crashed, not just a SQL error. The entire scenario produces 0 results.

```bash
# Re-run the failing scenario individually
uv run python scripts/test_multiturn_v3.py --scenario MT-005 --workers 1
```

If it fails consistently, check whether the issue reproduces with `test_db_conn.py`. If the DB is reachable but the tool still fails, there may be a connection pool conflict — reduce to `--workers 1`.

### Tests are slow (>400s per scenario)

This is normal. Each scenario starts a cold agent session that must re-discover the DB schema (30–50 tool calls). Total wall time for all 74 scenarios at `--workers 1` is 5–8 hours.

To run a focused subset quickly:
```bash
uv run python scripts/test_multiturn_v3.py --scenario CB-1 --workers 1
```

Parallel mode (`--workers 4`) reduces total clock time but makes individual failures harder to trace and is sensitive to connection pool limits.

### Assertion mismatch on a correct-looking answer

The oracle uses exact substring matching. Common causes:

- **Number format**: agent wrote `40716` instead of `40.716` — the assertion `"40.716"` fails.
- **Abbreviation mismatch**: agent wrote "NIE Risiko Menengah Rendah" but oracle checks for `"NIE MR"`.
- **Scope phrase missing**: oracle checks `"per tahun"` but agent skipped the yearly breakdown.

Resolution: open the JSON output, read the `answer` field for the failing turn, and adjust `assert_contains` to match what the agent actually produces — or update the agent's context to produce the expected phrasing consistently.
