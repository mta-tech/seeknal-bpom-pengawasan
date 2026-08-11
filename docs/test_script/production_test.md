# Production Test Scripts

This document describes the production test scripts created for testing the IBA agent system against the live production environment at `alpha.keycenter.ai`.

## Overview

The production test suite validates that the IBA agent can correctly answer BPOM-related questions through the full IBA stack (Keycloak auth → POST /v6/chat → SSE streaming). It measures latency, throughput, and assertion pass/fail rates.

## Files Created

### 1. Test Configuration

**File:** `scripts/iba_test_config_production.yml`

Production-specific configuration for the IBA test client. Contains:
- IBA API endpoint (`https://alpha.keycenter.ai/api`)
- Keycloak credentials (realm `keycenter`, client `web`)
- Test user (`user-test@pom.go.id`)
- Domain ID (`bbc5a1a3-dcdd-4684-9e6c-6134f0583005`)

### 2. Test Script

**File:** `scripts/test_concurrency_production.py`

Main test runner that executes 20 test cases against the production IBA API. Supports sequential execution with smart retry for empty answers.

### 3. Test Cases

**Directory:** `seeknal/tests/v1/production/`

20 YAML test cases covering diverse BPOM domains:

| ID | Domain | Example Prompt |
|----|--------|----------------|
| PROD-001 | NIE count | "Berapa total NIE pangan olahan di sistem ERBA tahun 2024?" |
| PROD-002 | Conceptual | "Apa perbedaan sistem ERBA dan ERLA?" |
| PROD-003 | Time-series | "Tren jumlah permohonan dari tahun 2020 sampai 2025" |
| PROD-004 | Ranking | "10 perusahaan dengan izin edar terbanyak" |
| PROD-005 | BTP | "Berapa produk BTP yang terdaftar di ERBA?" |
| PROD-006 | Risk | "Jumlah NIE per risiko tinggi, sedang, dan rendah" |
| PROD-007 | Import/Domestic | "Berapa produk pangan olahan impor dan dalam negeri tahun 2024?" |
| PROD-008 | Geographic | "Daerah mana yang memiliki pabrik dengan izin edar terbanyak?" |
| PROD-009 | UMKM | "Berapa UMKM yang memiliki izin edar aktif?" |
| PROD-010 | Processing time | "Berapa rata-rata waktu proses penerbitan NIE?" |
| PROD-011 | Application type | "Jenis permohonan apa yang paling banyak diajukan?" |
| PROD-012 | Commitment | "Berapa produk yang memiliki status komitmen menunggu verifikasi?" |
| PROD-013 | Cosmetics | "Tren jumlah NIE produk kosmetik dari tahun ke tahun" |
| PROD-014 | Expired NIE | "Berapa produk yang masa berlaku NIE-nya sudah habis?" |
| PROD-015 | Industrial scale | "Bagaimana distribusi produk berdasarkan skala industri?" |
| PROD-016 | Monthly | "Berapa jumlah NIE yang diterbitkan per bulan di tahun 2025?" |
| PROD-017 | Comparison | "Perbandingan jumlah produk ERBA versus ERLA per tahun" |
| PROD-018 | AMDK | "Berapa produk air minum dalam kemasan yang sudah terdaftar?" |
| PROD-019 | Trader ranking | "Siapa 5 trader dengan jumlah produk terbanyak di ERBA?" |
| PROD-020 | Percentage | "Berapa persen produk yang sudah memiliki nomor NIE dari total permohonan?" |

## How to Use

### Prerequisites

- Python 3.10+
- `uv` package manager
- Network access to `alpha.keycenter.ai` and `auth.keycenter.ai`

### Basic Usage

Run all 20 test cases sequentially with default settings:

```bash
cd seeknal-bpom-neo
uv run python scripts/test_concurrency_production.py
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--concurrency N` | 20 | Number of cases to run |
| `--stream-timeout N` | 3600 | Max seconds per SSE stream |
| `--stagger-ms N` | 10000 | Milliseconds between each request |
| `--max-retries N` | 2 | Max retry attempts for empty answers |
| `--retry-wait N` | 60 | Seconds to wait before retry batch |
| `--no-retry-empty` | false | Disable retry for empty answers |
| `--config PATH` | scripts/iba_test_config_production.yml | Config file path |
| `--path PATH` | seeknal/tests/v1/production | YAML test directory |

### Examples

```bash
# Run only 5 cases
uv run python scripts/test_concurrency_production.py --concurrency 5

# Faster execution (5s between requests)
uv run python scripts/test_concurrency_production.py --stagger-ms 5000

# No retry on empty answers
uv run python scripts/test_concurrency_production.py --no-retry-empty

# Custom retry wait (120s between retry batches)
uv run python scripts/test_concurrency_production.py --retry-wait 120

# Run specific test directory
uv run python scripts/test_concurrency_production.py --path seeknal/tests/v1/singleturn
```

### Output

Results are saved to:
```
seeknal/tests/outputs/<YYYY-MM-DD>/concurrency-production/concurrency_<timestamp>.json
```

The JSON contains:
- Per-request results (prompt, answer, passed, failures, metrics)
- Aggregate statistics (p50/p95/p99 latency, throughput, error rate)

## Architecture

### Request Flow

```
CLI Script
  → Keycloak ROPC login → access_token
  → POST /api/v6/chat → message_id + sse_token
  → GET /api/v6/sse?message_id=...&sse_token=...
  → Parse SSE events (token, tool_call, tool_result, done)
  → Assert expected strings in answer
  → Collect metrics (latency, tool_calls, etc.)
```

### Why Sequential?

The production worker has `max_concurrency=1` (HTTP transport). When multiple requests arrive simultaneously, the worker processes them one at a time. Requests that wait too long in the queue receive empty answers.

**First run (20 concurrent, no stagger):** 6/20 passed
**Second run (20 concurrent, 2s stagger + retry):** 7/20 passed
**Final run (sequential, 10s stagger + smart retry):** 20/20 passed

### Smart Retry

Empty answers occur when the worker is overloaded. The script detects empty answers and retries after a configurable wait period (default: 60s) to let the worker recover.

## Test Case YAML Format

```yaml
name: Human_Readable_Name
scenario_id: UNIQUE-ID
description: "Description of what this test validates"
turns:
- prompt: "The user's question in Indonesian"
  assert_contains:
  - "expected string 1"
  - "expected string 2"
  note: "Developer note about expected behavior"
```

## Related Files

These files were adapted from the existing test framework:

| File | Purpose |
|------|---------|
| `scripts/iba_test_client/auth.py` | Keycloak ROPC authentication client |
| `scripts/iba_test_client/chat.py` | IBA chat API client (POST /v6/chat + SSE) |
| `scripts/iba_test_client/metrics.py` | Latency tracking and aggregation |
| `scripts/test_e2e_iba.py` | Original E2E test (local environment) |
| `scripts/test_concurrency.py` | Original concurrency test (local environment) |
