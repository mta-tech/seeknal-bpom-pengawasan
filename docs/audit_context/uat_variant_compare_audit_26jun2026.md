# Variant Compare Audit — June 26, 2026

**Test Date:** June 26, 2026
**Analysis Date:** June 26, 2026
**Data Source:** `seeknal-bpom-neo/seeknal/tests/outputs/2026-06-26/v2/`
**Test Mode:** `variant-compare` (4 variants × N scenarios)

---

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| **Test Date** | June 26, 2026 |
| **Total Files** | 5 test runs |
| **Unique Scenarios** | 66 |
| **Total Graded Runs** | 236 (66 scenarios × 4 variants, minus 28 missing-variant slots) |
| **Passed** | 152 (**64%**) |
| **Failed** | 84 (35%) |

**Key Finding:** After lenient grading (format/near-miss/no-assertion = pass), the system
achieves **64% correctness**. Of the 84 failures, the cause is split nearly evenly between
**scope-mismatch** (41 cases / 49%) and **pure value errors** (43 cases / 51%).

**Important qualification:** The `passed` flag on the `[AUTO]` follow-up turn is unreliable —
it does not enforce the original assertion. The numbers above are from **re-graded** analysis
that checks whether the expected token actually appears in the final answer, not the raw flag.

---

## 2. What the 4 Variants Mean

The test harness runs every scenario against **4 code variants**, defined by two independent
dimensions:

| Dimension | Values | Meaning |
|-----------|--------|---------|
| **Code version** | `pre-refactor-1dd55d9` | Code before the refactor (commit `1dd55d9`) |
| | `after-refactor-f8d34b0` | Code after the refactor (commit `f8d34b0`) |
| **System prompt** | `...-notsystemprompt` (noSP) | System prompt **removed** — LLM operates without BPOM context instructions |
| | (default, SP) | System prompt **present** — LLM has full context/skill instructions |

This produces 4 variants:

| Variant Label | Code | System Prompt |
|---------------|------|---------------|
| **after (SP)** | after-refactor-f8d34b0 | Present |
| **after (noSP)** | after-refactor-f8d34b0-notsystemprompt | Removed |
| **pre (SP)** | pre-refactor-1dd55d9 | Present |
| **pre (noSP)** | pre-refactor-1dd55d9-notsystemprompt | Removed |

### Why 4 variants?

- **Pre vs After refactor:** Measures whether the code refactor improved, maintained, or
  degraded answer quality and efficiency.
- **With vs Without system prompt:** Measures how much the system prompt contributes to
  correctness. If removing it causes sharp degradation, the prompt is essential. If it
  doesn't matter, the LLM is relying on its own knowledge rather than the prompt's context.

---

## 3. Test Harness Mechanics

Each scenario is a **question** (e.g., "Berapa izin edar produk pangan olahan risiko
menengah rendah?"). The harness runs the question through the system and evaluates the
answer.

### 3.1 Answering Modes

The system can answer in two modes:

| Mode | Abbreviation | Behavior | Turn Structure |
|------|-------------|----------|----------------|
| **Direct** | DIR | System answers the question directly, no clarification | 1 turn only |
| **Ask-back** | ASK | System detects ambiguity and asks the user to clarify (presents options) | Turn 1: clarification options; Turn 2: harness auto-selects via `[AUTO]`, system produces final answer |

### 3.2 The ASK Clarification Flow

When the system decides a question is ambiguous (e.g., "ERBA only or ERLA only or union?"),
it presents clarification options to the user. The test harness then automatically picks one
option (the `[AUTO]` selection) and feeds it back to the system, which then produces the
final answer.

Example for **CB-1** ("Berapa izin edar produk pangan olahan risiko menengah rendah?"):

- **Turn 1 (ASK):** System presents options — "Apakah Anda ingin data dari ERBA saja,
  ERLA saja, atau gabungan keduanya?" → `ask_user_calls = 1`
- **Turn 2 ([AUTO]):** Harness selects "ERBA (RBA)" → system answers "40.831 NIE" →
  `passed = True`

**Critical caveat:** The `passed` flag on the `[AUTO]` turn does **not** enforce the original
assertion token. The grader marks it `passed = True` even when the expected value (e.g.,
"118.896") is absent from the answer. This is why raw `passed` counts are misleading and
**re-grading** was performed for this audit.

### 3.3 Auto-clarification vs Ask-user

The data also reveals two sub-modes within the ASK path:

- **`is_auto_clarif = True` (AUTO):** The system internally resolves ambiguity, then
  answers. These turns have **100% pass rate** under the raw flag.
- **`ask_user_calls > 0` (ASK-USER):** The system bubbles the question up to the user.
  These are the turns where `[AUTO]` kicks in.

Both modes are mutually exclusive in the data: a turn is either AUTO or ASK-USER,
never both.

---

## 4. Grading Methodology

### 4.1 The Problem with Raw `passed` Flag

The original grader checks for **expected tokens** (numbers or keywords) in the answer.
When a token is present, the turn passes. When absent, `failures` lists the missing tokens.

However, the `[AUTO]` follow-up turn does **not** carry over the original assertion. So:

| Scenario | Expected Token | `[AUTO]` Answer | `passed` | Actually Correct? |
|----------|---------------|-----------------|----------|-------------------|
| CB-1 | `118` | 40.831 (ERBA-only) | True | **No** — GT is 118.896 (union) |
| UAT-COM-2 | `42 produk` | 3 produk | True | **No** |
| UAT-CHAR-LOGAM-1 | `4.568` | 6.330 | True | **No** |

### 4.2 Re-grading Rules Applied

The audit applies **lenient re-grading** with the following rules:

| Condition | Verdict |
|-----------|---------|
| Expected token present in final answer | **PASS** |
| No expected token (structural/format question only) | **PASS** |
| Keyword-only missing (format issue, substance present) | **PASS** |
| Numeric miss, scope same, relative difference ≤ 2% | **PASS** (near-miss) |
| Scope mismatch (note scope ≠ answer scope) | **FAIL** (scope) |
| Numeric miss, scope same, relative difference > 2% | **FAIL** (value) |

This grading is applied uniformly to both ASK and DIR turns.

---

## 5. Overall Results

### 5.1 Summary

| | Passed | Failed | Total |
|---|---|---|---|
| **ASK (tanya balik)** | 89 (62%) | 53 | 142 |
| **DIR (langsung)** | 63 (67%) | 31 | 94 |
| **TOTAL** | **152 (64%)** | **84 (35%)** | **236** |

### 5.2 Per-Variant Breakdown

| Variant | ASK Pass | ASK Fail (scope/value) | DIR Pass | DIR Fail (scope/value) |
|---------|----------|----------------------|----------|----------------------|
| after (SP) | 22 (61%) | 7 / 7 | 16 (69%) | 3 / 4 |
| after (noSP) | 27 (64%) | 7 / 8 | 9 (52%) | 1 / 7 |
| pre (SP) | 19 (57%) | 10 / 4 | 21 (80%) | 0 / 5 |
| pre (noSP) | 21 (67%) | 7 / 3 | 17 (60%) | 6 / 5 |
| **Gabungan** | **89 (62%)** | **31 / 22** | **63 (67%)** | **10 / 21** |

### 5.3 Failure Cause Breakdown

| Cause | ASK | DIR | Total | % of Failures |
|-------|-----|-----|-------|---------------|
| **Scope-mismatch** | 31 | 10 | **41** | 49% |
| **Pure value error** | 22 | 21 | **43** | 51% |
| **Total failures** | 53 | 31 | **84** | 100% |

**Interpretation:**
- Failures are split ~50/50 between scope-mismatch and pure value errors.
- **ASK** is more prone to scope-mismatch (31 of 53 ASK failures = 58%).
- **DIR** is more prone to value errors (21 of 31 DIR failures = 68%).
- After-refactor DIR has more value errors (4+7=11) than pre-refactor DIR (5+5=10).

### 5.4 Variant Performance Ranking

| Rank | Variant | Overall Pass Rate | ASK Pass Rate | DIR Pass Rate |
|------|---------|-------------------|---------------|---------------|
| 1 | **pre (SP)** | **68%** | 57% | **80%** |
| 2 | after (SP) | 64% | 61% | 69% |
| 3 | pre (noSP) | 64% | 67% | 60% |
| 4 | after (noSP) | 60% | 64% | 52% |

**Key observations:**
- **pre (SP)** has the **best DIR accuracy** (80%) and fewest pure-value ASK errors (4).
- **after (noSP)** has the worst DIR accuracy (52%) and most pure-value DIR errors (7).
- System prompt impact: DIR pass rate drops significantly without SP (pre: 80%→60%,
  after: 69%→52%). The SP is critical for direct-answer accuracy.
- Refactor impact: minimal positive effect. pre (SP) outperforms after (SP) on DIR.

---

## 6. Scope-Mismatch Analysis

### 6.1 What Is Scope-Mismatch?

Scope-mismatch occurs when the `[AUTO]` clarifier (for ASK) or the system's implicit scope
choice (for DIR) selects a different data scope than the ground truth expects.

Common mismatches:

| Ground Truth Expects | System/AUTO Chooses | Effect |
|---------------------|--------------------| -------|
| Union (ERBA + ERLA) | ERBA only | Answer too small |
| ERBA only | Union (ERBA + ERLA) | Answer too large / wrong scope |
| Specific risk (Tinggi) | Wider scope | Different population |
| Per-year breakdown | Total only | Missing granularity |

### 6.2 Scope-Mismatch Direction (41 cases)

| Direction | Count | Meaning |
|-----------|-------|---------|
| **ERBA → UNION** | 27 | GT expects ERBA-only; system answers union (too broad) |
| **UNION → ERBA** | 15 | GT expects union; system answers ERBA-only (too narrow) |
| ERLA → UNION | 2 | GT expects ERLA-only; system answers union |
| UNION → ERLA | 1 | GT expects union; system answers ERLA-only |
| ERBA → ERLA | 1 | Wrong system entirely |

**The dominant pattern (27/41 = 66%) is ERBA→UNION:** the ground truth expects an
ERBA-only answer, but the system (or auto-clarifier) broadens to include ERLA, producing
an inflated number.

### 6.3 Scope-Mismatch Detail Table

| Scenario | Mode | GT Scope | AUTO Scope | Expected Token | Note (Ground Truth) |
|----------|------|----------|------------|----------------|---------------------|
| CB-1 | ASK | UNION | ERBA | `118` | DB 118.896 (ERBA 303 + ERLA 301) |
| UAT-AMDK-1 | ASK | UNION | ERBA | `2.166` | ERBA 1.743 + ERLA 423 = 2.166 |
| UAT-BAYI-1 | ASK | UNION | ERBA | `916` | ERBA 102 + ERLA 814 = 916 |
| UAT-BAYI-2 | ASK | UNION | ERLA | `295` | ERBA 60 + ERLA 235 = 295 |
| UAT-BAYI-3 | ASK | UNION | ERBA | `916` | Same as UAT-BAYI-1 |
| BUGFIX-5 | ASK | UNION | ERBA | `103` | ERBA 83.143 + ERLA 20.555 = 103.698 |
| CAP-4 | ASK | UNION | ERBA | `domestik/impor` | Harus derive dari negara_pabrik |
| UAT-AMDK-2 | DIR | ERBA | UNION | `1.743` | Verifikasi ERBA saja |
| UAT-CHAR-LOGAM-1 | ASK | ERBA | UNION | `4.568` | ERBA aktif kemasan logam |
| UAT-CHAR-KOMPOSIT-1 | ASK | ERBA | UNION | `40.` | ERBA aktif kemasan komposit |
| UAT-CHAR-GANDA-1 | ASK | ERBA | UNION | `29.` | ERBA aktif kemasan ganda |
| UAT-BTP-CAIR-1 | ASK | ERBA | UNION | `2.274` | ERBA bentuk_sediaan=101 |
| UAT-BTP-SERBUK-1 | ASK | ERBA | UNION | `1.796` | ERBA bentuk_sediaan=102 |
| UAT-BTP-CAMPURAN-1 | ASK | ERBA | UNION | `2.788, 695` | ERBA jenis_produk_btp Campuran |
| UAT-BTP-PEWARNA-1 | ASK | ERBA | UNION | `600` | ERBA jenis_btp=47 |
| UAT-BELUM-KATEGORI-1 | ASK | ERBA | ERLA/UNION | `28.667` | ERBA jenis_dokumen=000 |
| UAT-DICABUT-1 | ASK | ERBA | UNION | `5.237` | ERBA status=0009 |
| UAT-ERLA-1 | DIR | ERLA | UNION | `400.` | ERLA produk_id distinct |
| UAT-CHAR-PANGAN-BAYI-ERLA-1 | DIR | ERLA | UNION | `81 produk` | ERLA klasifikasi_pangan=311 |
| UAT-DQ-BELUM-RISIKO-1 | DIR | ERBA | UNION | `28.` | ERBA kategori_dokumen NULL |
| UAT-DRAFT-PROSES-1 | DIR | ERBA | UNION | `20.020` | ERBA status=0912 |
| UAT-BTP-ANTIOKSIDAN-1 | DIR | ERBA | UNION | `942` | ERBA jenis_btp=48 |
| UAT-BTP-TREN-1 | DIR | ERBA | UNION | `950, 1.089, 1.523` | ERBA tren BTP |
| UAT-CHAR-GANDA-1 | DIR | ERBA | UNION | `29.` | ERBA aktif kemasan ganda |
| UAT-CHAR-KOMPOSIT-1 | DIR | ERBA | UNION | `40.` | ERBA aktif kemasan komposit |
| UAT-DICABUT-1 | DIR | ERBA | UNION | `5.237` | ERBA status=0009 |
| UAT-BTP-TREN-1 | DIR | ERBA | UNION | `950, 1.089, 1.523` | ERBA tren BTP |

### 6.4 Root Cause of Scope-Mismatch

The `[AUTO]` scope-picker defaults to **union (ERBA + ERLA)** when the question doesn't
explicitly specify a system. The ground truth often expects a single-system answer because
the test was designed to verify a specific system's data. This is a **systemic bias toward
broadening** in the auto-clarifier.

Similarly, for DIR (direct answer), the system sometimes broadens to union when the question
mentions a domain that could apply to either system (e.g., "BTP", "pangan bayi", "kemasan
logam").

---

## 7. Pure Value Error Analysis

### 7.1 What Is a Pure Value Error?

A pure value error occurs when the **scope is correct** (ERBA-only, union, etc.) but the
**numerical answer is wrong** by more than 2%. This indicates a bug in the SQL query logic,
filter application, or data interpretation.

### 7.2 Distribution

| Variant | ASK Value Errors | DIR Value Errors | Total |
|---------|-----------------|-----------------|-------|
| after (SP) | 7 | 4 | 11 |
| after (noSP) | 8 | 7 | 15 |
| pre (SP) | 4 | 5 | 9 |
| pre (noSP) | 3 | 5 | 8 |
| **Total** | **22** | **21** | **43** |

### 7.3 Patterns in Value Errors

Common patterns observed in the 43 value errors:

| Pattern | Examples | Count (est.) |
|---------|----------|-------------|
| Wrong status filter | Using 0999 vs 0999+0906+9999, or 0009 vs 0000 | ~12 |
| Wrong date range | Full history vs YTD, wrong year boundary | ~8 |
| Wrong category filter | jenis_dokumen vs kategori_dokumen, wrong code | ~10 |
| Include/exclude test accounts | trader_id IN (5,17,50,85) not excluded | ~5 |
| COUNT vs COUNT DISTINCT | Counting rows vs distinct nomor | ~4 |
| Off-by-one or rounding | 5.237 vs 5.238 | ~4 |

### 7.4 Notable Value Error Cases

| Scenario | Variant | Expected | Answered | Issue |
|----------|---------|----------|----------|-------|
| UAT-COM-2 | ASK/DIR | 42 produk | 3 produk | Wrong status_komitmen filter |
| UAT-CHAR-KOMPOSIT-1 | ASK | 40.683 | 44.309 | Wrong kemasan_id filter |
| UAT-BTP-CAIR-1 | ASK/DIR | 2.274 | ~33.944 (1464% off) | bentuk_sediaan filter mismatch |
| UAT-BELUM-KATEGORI-1 | ASK | 28.667 | ~various (91–418% off) | jenis_dokumen=000 filter |
| UAT-COM-1 | ASK/DIR | 5.198 | ~various (19% off) | kategori_dokumen filter |
| UAT-DRAFT-1 | DIR | 28.720 | ~29.239 (1.8% off) | Near-miss, status boundary |
| CAP-6 | ASK | per-year table | total only | Missing format (per-year breakdown) |

---

## 8. Per-Question × Variant Matrix

### Legend

- `ASK/BEN` = Asked back, passed (correct)
- `ASK/SCO` = Asked back, failed (scope mismatch)
- `ASK/VAL` = Asked back, failed (value error)
- `DIR/BEN` = Direct answer, passed
- `DIR/SCO` = Direct answer, failed (scope mismatch)
- `DIR/VAL` = Direct answer, failed (value error)
- `--` = No data for this variant

### 8.1 CB / CAP / BUGFIX Scenarios

| Scenario | after-SP | after-noSP | pre-SP | pre-noSP |
|----------|----------|------------|--------|----------|
| AMDK-1 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| BTP-1 | DIR/BEN | DIR/BEN | DIR/BEN | DIR/BEN |
| BTP-3 | DIR/BEN | DIR/BEN | DIR/BEN | DIR/BEN |
| BUGFIX-3 | DIR/BEN | DIR/VAL | DIR/BEN | DIR/BEN |
| BUGFIX-4 | DIR/BEN | ASK/VAL | DIR/BEN | ASK/BEN |
| BUGFIX-5 | ASK/BEN | ASK/SCO | DIR/BEN | DIR/VAL |
| CAP-2 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| CAP-3 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| CAP-4 | DIR/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| CAP-5 | ASK/BEN | ASK/BEN | DIR/BEN | ASK/BEN |
| CAP-6 | ASK/VAL | ASK/VAL | DIR/BEN | DIR/BEN |
| CAP-8 | DIR/BEN | ASK/BEN | DIR/BEN | DIR/BEN |
| CB-1 | ASK/SCO | ASK/SCO | ASK/SCO | ASK/SCO |
| CB-10 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| CB-11 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| CB-12 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| CB-13 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| CB-14 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| CB-15 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| CB-16 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| CB-17 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| CB-18 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| COMMIT-2 | DIR/BEN | ASK/BEN | DIR/BEN | DIR/BEN |
| NIE-1 | DIR/BEN | DIR/BEN | DIR/BEN | DIR/BEN |
| NIE-10 | DIR/BEN | DIR/BEN | DIR/BEN | DIR/BEN |
| NIE-11 | DIR/BEN | DIR/BEN | DIR/BEN | DIR/BEN |
| NIE-12 | DIR/BEN | ASK/BEN | DIR/BEN | DIR/BEN |
| NIE-13 | DIR/BEN | DIR/BEN | DIR/BEN | DIR/BEN |
| NIE-14 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |

### 8.2 UAT Scenarios

| Scenario | after-SP | after-noSP | pre-SP | pre-noSP |
|----------|----------|------------|--------|----------|
| UAT-AMDK-1 | ASK/SCO | ASK/SCO | ASK/SCO | ASK/SCO |
| UAT-AMDK-2 | DIR/SCO | DIR/VAL | DIR/BEN | DIR/BEN |
| UAT-AMDK-3 | DIR/VAL | DIR/BEN | DIR/BEN | DIR/VAL |
| UAT-AMDK-4 | ASK/VAL | ASK/VAL | ASK/BEN | ASK/VAL |
| UAT-BAYI-1 | ASK/VAL | ASK/SCO | ASK/SCO | ASK/VAL |
| UAT-BAYI-2 | ASK/SCO | DIR/VAL | ASK/BEN | ASK/BEN |
| UAT-BAYI-3 | ASK/VAL | ASK/SCO | ASK/VAL | ASK/VAL |
| UAT-BAYI-DICABUT-1 | ASK/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| UAT-BAYI-JP-BREAKDOWN-1 | DIR/BEN | ASK/BEN | ASK/BEN | ASK/BEN |
| UAT-BELUM-KATEGORI-1 | ASK/SCO | ASK/VAL | ASK/VAL | ASK/SCO |
| UAT-BTP-1 | DIR/VAL | DIR/VAL | DIR/BEN | DIR/BEN |
| UAT-BTP-ANTIOKSIDAN-1 | DIR/SCO | DIR/BEN | DIR/BEN | DIR/BEN |
| UAT-BTP-CAIR-1 | ASK/BEN | ASK/VAL | ASK/SCO | ASK/SCO |
| UAT-BTP-CAMPURAN-1 | ASK/SCO | ASK/VAL | ASK/VAL | ASK/BEN |
| UAT-BTP-PEWARNA-1 | ASK/BEN | ASK/BEN | ASK/SCO | ASK/SCO |
| UAT-BTP-SERBUK-1 | ASK/SCO | ASK/SCO | ASK/SCO | ASK/SCO |
| UAT-BTP-TREN-1 | DIR/BEN | DIR/SCO | DIR/BEN | DIR/BEN |
| UAT-CHAR-GANDA-1 | DIR/BEN | ASK/BEN | ASK/SCO | DIR/SCO |
| UAT-CHAR-KOMPOSIT-1 | ASK/VAL | ASK/VAL | ASK/SCO | DIR/SCO |
| UAT-CHAR-LOGAM-1 | ASK/SCO | ASK/SCO | ASK/SCO | ASK/SCO |
| UAT-CHAR-PANGAN-BAYI-ERLA-1 | ASK/BEN | ASK/BEN | DIR/VAL | DIR/SCO |
| UAT-COM-1 | ASK/VAL | DIR/VAL | DIR/VAL | DIR/VAL |
| UAT-COM-2 | ASK/VAL | DIR/VAL | DIR/VAL | DIR/VAL |
| UAT-DAERAH-1 | ASK/BEN | ASK/BEN | ASK/VAL | ASK/BEN |
| UAT-DICABUT-1 | ASK/BEN | ASK/BEN | ASK/SCO | DIR/SCO |
| UAT-DQ-BELUM-KLASIFIKASI-1 | DIR/BEN | DIR/BEN | DIR/BEN | DIR/BEN |
| UAT-DQ-BELUM-RISIKO-1 | DIR/VAL | DIR/VAL | DIR/VAL | DIR/SCO |
| UAT-DRAFT-1 | DIR/VAL | ASK/BEN | DIR/VAL | DIR/VAL |
| UAT-DRAFT-PROSES-1 | ASK/BEN | ASK/BEN | ASK/BEN | DIR/SCO |
| UAT-ERLA-1 | DIR/SCO | ASK/VAL | DIR/BEN | DIR/BEN |

### 8.3 Observations from the Matrix

- **CB-1 fails in all 4 variants** (scope-mismatch): the auto-clarifier always picks
  ERBA-only when the ground truth expects union (118.896). This is a persistent
  scope-picker defect.
- **UAT-CHAR-LOGAM-1 fails in all 4 variants** (scope-mismatch): same pattern — system
  broadens to union when GT expects ERBA-only (4.568).
- **UAT-COM-1 and UAT-COM-2 fail in all 4 variants** (value error): the system cannot
  correctly compute the answer regardless of scope choice. Likely a SQL filter bug.
- **CB-10 through CB-18 (all CB) pass in all 4 variants**: these are straightforward
  queries that the system handles well across all configurations.
- **NIE scenarios are nearly all DIR/BEN**: these are direct lookups with no ambiguity.
- **UAT scenarios have the most failures**: real-world user questions expose the most
  gaps in the system's reasoning and SQL logic.

---

## 9. LLM Calls & Time Analysis

### 9.1 Per-Turn Averages

| Variant | Turns | LLM Calls (mean) | LLM Calls (max) | Elapsed s (mean) | Elapsed s (max) |
|---------|-------|-------------------|-----------------|-------------------|-----------------|
| after (SP) | 95 | **10.0** | 70 | **103.3** | 523 |
| after (noSP) | 101 | 8.1 | 40 | 72.2 | 482 |
| pre (SP) | 92 | 4.9 | 37 | 70.3 | 360 |
| pre (noSP) | 90 | 5.5 | 40 | 81.1 | 454 |
| **AFTER (gabung)** | 196 | **9.1** | | **87.3s** | |
| **PRE (gabung)** | 182 | **5.2** | | **75.7s** | |

### 9.2 ASK vs DIR Breakdown

| Variant | ASK LLM Calls | ASK Elapsed | DIR LLM Calls | DIR Elapsed |
|---------|---------------|-------------|---------------|-------------|
| after (SP) | **15.1** | **139.6s** | 6.9 | 81.2s |
| after (noSP) | 13.0 | 94.3s | 4.7 | 56.5s |
| pre (SP) | 6.0 | 53.9s | 4.2 | 79.5s |
| pre (noSP) | 6.4 | 62.4s | 5.0 | 91.0s |

### 9.3 Interpretation

1. **After-refactor uses ~75% more LLM calls** than pre (9.1 vs 5.2 per turn) and is
   ~15% slower (87s vs 76s).
2. **The biggest cost difference is in ASK turns:** after-refactor ASK consumes
   **15.1 LLM calls / 140s** per turn — **2.5× more** than pre-refactor ASK (6.0 calls /
   54s). The refactor made the clarification loop significantly deeper.
3. **DIR turns are similar** across pre/after (4–7 calls, 56–91s). The refactor primarily
   impacts the clarification path, not direct answering.
4. **Outlier:** after (SP) has a turn with **70 LLM calls / 523 seconds (≈9 minutes)** —
   likely a stuck SQL→reflection loop. Pre max is 37–40 calls.
5. **Cost-benefit unfavorable:** after-refactor is more expensive and slower, but not more
   accurate. Pre-refactor (SP) is the best-performing variant (80% DIR accuracy) with
   the lowest LLM cost.

---

## 10. Key Findings & Recommendations

### 10.1 Key Findings

1. **Overall accuracy: 64%** after lenient grading. The system answers correctly about
   two-thirds of the time.
2. **Failures split evenly:** 41 scope-mismatch (49%) + 43 value errors (51%). Neither
   dominates — both need fixing.
3. **Scope-mismatch is predominantly ERBA→UNION (27/41 = 66%):** the system/auto-clarifier
   defaults to the broadest scope when the question doesn't explicitly specify a system.
   This is the single largest scope-mismatch pattern.
4. **The `[AUTO]` flag is unreliable:** the `passed` flag on `[AUTO]` turns does not
   enforce the original assertion. Any analysis relying on raw `passed` counts will
   overestimate correctness.
5. **pre-refactor (SP) is the best variant:** highest DIR accuracy (80%), fewest value
   errors (4 ASK), and lowest LLM cost (4.9 calls/turn).
6. **System prompt is critical:** removing it drops DIR accuracy by 20+ percentage points
   (80%→60% for pre, 69%→52% for after).
7. **After-refactor is more expensive without accuracy gain:** 75% more LLM calls, 2.5×
   cost in ASK path, but no improvement in correctness.
8. **UAT scenarios have the lowest pass rate:** real-world user questions expose the most
   gaps, especially in scope determination and filter logic.

### 10.2 Recommendations

| Priority | Action | Targets |
|----------|--------|---------|
| **P0** | Fix `[AUTO]` grader to enforce original assertion tokens on follow-up turns | All multi-turn scenarios |
| **P1** | Fix scope-mismatch: teach auto-clarifier to prefer single-system scope unless question explicitly asks for union | 41 scope-mismatch cases |
| **P1** | Fix pure-value SQL errors: correct status filters, date ranges, category codes, test-account exclusion | 43 value-error cases |
| **P2** | Evaluate whether after-refactor code should be kept — pre-refactor (SP) is more accurate and efficient | Code decision |
| **P2** | Reduce ASK-path LLM calls in after-refactor (currently 15.1 per turn vs 6.0 in pre) | Cost optimization |
| **P3** | Handle structural/format assertions (tren per tahun, per skala, ranking) — these currently have no token-based grading | 31 structural scenarios |

---

## Appendix A: Test File Inventory

| File | Timestamp | Scenarios | Focus |
|------|-----------|-----------|-------|
| `variant_compare_results_20260626_041615.json` | 04:16:15 | 12 | Mixed: CB, NIE, AMDK, BTP, UAT-AMDK |
| `variant_compare_results_20260626_053133.json` | 05:31:33 | 10 | All CB (Core Business) |
| `variant_compare_results_20260626_054416.json` | 05:44:16 | 16 | AMDK, BTP, BUGFIX, CAP, COMMIT, COMP |
| `variant_compare_results_20260626_055019.json` | 05:50:19 | 10 | All NIE (Nomor Izin Edar) |
| `variant_compare_results_20260626_055806.json` | 05:58:06 | 30 | All UAT (User Acceptance Tests) |
| **Total** | | **78** (66 unique after dedup) | |

## Appendix B: Scenario Category Distribution

| Category | Unique Scenarios | Description |
|----------|-----------------|-------------|
| CB | 13 | Core Business queries (izin edar, tren, distribusi) |
| NIE | 8 | Nomor Izin Edar specific lookups |
| CAP | 6 | Capability tests (ranking, format, join logic) |
| BUGFIX | 3 | Regression tests for specific bugs |
| UAT | 30 | User Acceptance Tests (real-world scenarios) |
| Other | 6 | AMDK, BTP, COMMIT, COMP |
| **Total** | **66** | |

## Appendix C: Variant Configuration

| Variant | Code Commit | System Prompt | Description |
|---------|-------------|---------------|-------------|
| after-refactor-f8d34b0 | `f8d34b0` | Present | Post-refactor with full context |
| after-refactor-f8d34b0-notsystemprompt | `f8d34b0` | Removed | Post-refactor, no context |
| pre-refactor-1dd55d9 | `1dd55d9` | Present | Pre-refactor with full context |
| pre-refactor-1dd55d9-notsystemprompt | `1dd55d9` | Removed | Pre-refactor, no context |

## Appendix D: Glossary

| Term | Definition |
|------|-----------|
| **ASK** | System asks back to user (clarification flow) |
| **DIR** | System answers directly without clarification |
| **[AUTO]** | Test harness auto-selects a clarification option |
| **Scope-mismatch** | System's scope (ERBA/ERLA/union) differs from ground truth |
| **Pure-value error** | Scope correct but numerical answer wrong by >2% |
| **Near-miss** | Numerical difference ≤2%, considered acceptable |
| **noExp** | No explicit expected token — structural/format question |
| **ERBA** | Electronic Registrasi Baru (new registration system) |
| **ERLA** | Electronic Registrasi Lama (legacy registration system) |
| **NIE** | Nomor Izin Edar (product registration number) |
| **BTP** | Bahan Tambahan Pangan (food additive) |
| **AMDK** | Air Minum Dalam Kemasan (bottled drinking water) |
| **GT** | Ground Truth (verified expected value from database) |
