# UAT Audit Report — Seeknal BPOM Neo
**Test Date:** June 15, 2026  
**Audit Date:** June 17, 2026  
**Data Source:** `iba_conversations_12h_20260615_full.json` (14 conversations, 57 questions)  
**Database:** `rpo_v2` verified via live queries (localhost:5533 → postgres:5433)

---

## 1. Executive Summary

This report audits the Seeknal BPOM Neo AI assistant against live database ground truth. The system is an **LLM-based agent** — not a hardcoded query engine — that uses a structured cognitive workflow to reason about BPOM registration data. It generates SQL dynamically from natural language.

The audit reveals **6 systematic failure patterns** rooted in gaps or errors in the agent's knowledge context files, not in the SQL generation itself. Because the agent reasons from its context, fixing the context fixes the behavior — without hardcoding any queries.

**Key findings:**
- 4 of 14 conversations contain statistically significant discrepancies (>5%) on **static historical data** (2023/2024), which by definition should not change — proving the agent generated wrong SQL, not that data moved
- The largest discrepancy (NIE Menengah Tinggi: 95,736 system vs 11,923 actual) traces directly to a **factual error in `business_glossary.md`** about ERLA risk code scope
- The commitment cancellation query (MR Dibatalkan: 254 vs 5,146) traces to an **overly broad rule in `data_quality_rules.md`**
- The system shows **non-determinism**: the same question across different sessions generates different SQL, producing different answers

---

## 2. System Architecture

### 2.1 How the System Is Built

The system is an **agent, not a query library**. It does not have pre-written SQL queries. Instead, it has:

```
SEEKNAL_ASK.md          ← Orchestrator / Decision Operating System
    │
    ├── Context files (agent's domain knowledge)
    │       context/business_glossary.md
    │       context/code_resolution.md
    │       context/data_architecture.md
    │       context/data_quality_rules.md
    │       context/intent_mapping.md
    │       context/query_recipes.md
    │       context/forecast_guide.md
    │
    └── Skills (reasoning workflows)
            seeknal/skills/bpom-analyst/SKILL.md      ← main orchestrator
            seeknal/skills/evidence-auditor/SKILL.md  ← audit/reflect phase
            seeknal/skills/database-analyst/SKILL.md
            seeknal/skills/business-question-answering/SKILL.md
```

The agent **reads context files at runtime** to understand domain rules, then generates SQL on-the-fly. This design means:
- ✅ Teaching the agent = fixing context files
- ❌ Hardcoding SQL = wrong approach (makes the system brittle and non-adaptive)

### 2.2 Agent Cognitive Workflow (7 Phases)

Every data question goes through:

| Phase | Name | Purpose |
|---|---|---|
| 0 | Context Load | Load `business_glossary.md` + `data_quality_rules.md` unconditionally |
| 1 | Capture | Understand intent, extract entity/operation/dimension/time |
| 2 | Resolve | Fill information gaps from context files before writing SQL |
| 3 | Plan | Design step-by-step query plan |
| 4 | Execute | Run SQL with pre-submit checklist |
| 5 | Reflect | Audit every number against business rules before answering |
| 6 | Generate | Present answer with source transparency |

**What the system teaches the agent:**
- **HOW to think**: Intent extraction → State comparison → Decision routing
- **HOW to problem-solve**: Information Need Resolution hierarchy (5 levels: glossary → dictionary → schema → discovery → user)
- **HOW to verify**: REFLECT phase with mandatory filter checklist
- **WHAT to do when uncertain**: escalate to discovery query, never fabricate numbers

### 2.3 Decision Operating System (SEEKNAL_ASK.md)

The orchestrator provides:

1. **Conversation Gate** — classify input before triggering any workflow (SMALL_TALK / META / OUT_OF_SCOPE / DATA_QUESTION)
2. **Decision Layer** — intent extraction with Semantic Commitment Block, then State Comparison Engine to classify follow-ups (NEW_QUESTION / MODIFY_SCOPE / EXTEND_SCOPE / EXPLAIN_EVIDENCE)
3. **Inheritance Principle** — inherit ANSWERS across turns, re-derive METHODS every turn
4. **Conversation Ledger** — structured state tracking (answers + scope, never methods)
5. **Behavioral Contracts** — 11 word→resolution mappings that cannot be overridden by adjacent keywords
6. **Guardrails** — every number must trace to a real query; no fabrication; no silent scope switching

---

## 3. Test Results — All 57 Questions

### 3.1 Conversation Index

| Conv | Question Thread | Questions | Notable Issues |
|---|---|---|---|
| abc7d544 | NIE MR + MT all-time | 3 | MT answer = 95,736 (inflated 703%) |
| ad6cae37 | Total permohonan ERLA | 1 | Minor gap, COUNT(produk_id) vs nomor |
| 450bee5b | Tren ERBA + specific categories 2023 | 8 | Garam Beryodium 189 vs 199; AMDK ≈ OK |
| ecc2a2ce | Total produk terdaftar + hello | 2 | Total NIE 311,959 scope unclear |
| 51f6fa36 | NIE bulan Mei + year 2025 breakdown | 12 | Mixed accuracy; 2025 ERBA = 53,844 ✓ |
| 29ffee13 | AMDK 2024–2025 + MR Dibatalkan | 7 | MR Dibatalkan 254 vs 5,146 (−95%) |
| 2da5f2b3 | Susu merk sekolah Mei 2026 | 2 | Correctly returned 0 ✓ |
| 7b8f0ce2 | AMDK 2023 + MT all-time (repeat) | 3 | AMDK 1,843 (combined) ✓; MT 95,736 ❌ |
| b2075dd4 | Tren Risiko Rendah vs Tinggi + 2025 | 2 | 2025 total = 45,247 vs 53,535 (−15%) |
| 856e9ad2 | Syarat label + kategori 13 | 2 | Regulatory (no SQL impact) |
| eebc653e | Formula bayi deep-dive (11 questions) | 11 | 267 vs ~148 strict; broad scope |
| 40286c1c | Formula bayi + MD 2025 | 4 | MD 2025 = 30,760 vs 36,706 (−16%) |
| 7535cd1d | Total NIE 2025 | 1 | 46,770 vs 53,535 (−13%) |
| f735bd16 | Total NIE Mei 2026 | 1 | 3,880 vs 5,193 (−25%) |

### 3.2 Detailed Question-by-Question Analysis

#### CONV abc7d544 — NIE MR + MT All-Time

**Q1: Berapa jumlah izin edar produk olahan dengan risiko menengah rendah?**
- System answer: per-year breakdown (not shown explicitly as single number)
- SQL: ERBA `kategori_dokumen='303'` + ERLA `jenis_dokumen='301'` + `jenis_permohonan IN ('301','305')` UNION ALL, `COUNT(DISTINCT nomor)`
- DB actual MR ERBA only: ~119,314 (all-time distinct)
- Assessment: ERLA mapping `jenis_dokumen='301'` (Low Risk) for MR is plausible but includes products that ERBA would classify as Notifikasi. **Minor semantic issue.**

**Q2 & Q3: Berapa jumlah izin edar produk olahan dengan risiko menengah tinggi?**
- System answer: **95,736** (all-time total)
- SQL: ERBA `kategori_dokumen='302'` + ERLA `jenis_dokumen='303'` + `jenis_permohonan IN ('301','305')`, UNION ALL, `COUNT(DISTINCT nomor)`
- DB verification:

| Component | Count |
|---|---|
| ERBA MT (`kategori_dokumen='302'`, with filters) | 11,919 |
| ERLA `jenis_dokumen='303'` (with filters) | 83,857 |
| **System total (UNION DISTINCT)** | **95,776** ≈ system's 95,736 |
| **Correct (ERBA only, no jenis_permohonan filter)** | **11,923** |

- Root cause: ERLA `jenis_dokumen='303'` = "**Pangan Medium Risk**" (all medium levels) ≠ "Menengah Tinggi" alone. ERLA never had separate MT/MR subcategories — code '303' captures all medium risk, equivalent to ERBA '302' + '303' combined.
- **Error: +703% inflation. Historical data, so this proves wrong SQL, not data movement.**

---

#### CONV ad6cae37 — Total Permohonan ERLA

**Q: Berapa total permohonan pangan olahan yang terdaftar di sistem ERLA untuk seluruh periode data?**
- System answer: **400,784**
- SQL: `COUNT(DISTINCT produk_id)` with `tanggal_bayar` filter on `t_produk_3_rilis_erla`
- DB actual: 402,925 (with `COUNT(DISTINCT produk_id)`)
- Gap: −0.5% — minor, likely different `trader_id` exclusion (`!= 3384` vs broader exclusion)
- Assessment: **Acceptable. Permohonan correctly uses `produk_id` not `nomor`.**

---

#### CONV 450bee5b — Tren ERBA + Specific Categories 2023

**Q: Tren permohonan pangan olahan dari tahun ke tahun di sistem ERBA?**
- SQL: `COUNT(DISTINCT produk_id)` on `tanggal_bayar` — correct for permohonan
- Assessment: **Correct approach ✓**

**Q: Berapa jumlah NIE produk BTP di ERBA tahun 2023?**
- System answer: **950**
- SQL: `WHERE status IN ('0999','0906','9999') AND jenis_permohonan IN ('301','305') AND tanggal >= '2023-01-01' AND tanggal < '2024-01-01'`
- DB actual: 950 ✓
- Assessment: **Exact match ✓ — 2023 static data confirms SQL is correct for BTP.**

**Q: Berapa NIE Garam Beryodium ERBA 2023?**
- System answer: **189**
- SQL: `WHERE kategori_pangan = '120101000001'`
- DB verification:

| Query | Count |
|---|---|
| `kategori_pangan = '120101000001'` (system's SQL) | **189** |
| `jenis_pangan = '1204'` (full category, correct) | **198** |
| Difference | −9 products (−4.5%) |

- Root cause: context files hardcode `kategori_pangan = '120101000001'` as the Garam Beryodium identifier. This is a **12-digit sub-category code** that misses 9 products registered under different sub-codes within `jenis_pangan='1204'` (the true parent category).
- **Error: −4.5% on 2023 static data = proven wrong filter.**

**Q: Berapa NIE AMDK ERBA 2023?**
- System answer: **1,743** (ERBA + ERLA combined)
- SQL: ERBA `jenis_pangan='1401'` + ERLA `jenis_pangan IN ('651','652','655')`, `jenis_permohonan IN ('301','305')`
- DB actual ERBA only: 1,744 (all jenis_permohonan)
- Assessment: Near-exact ✓. The ERLA contribution and jenis_permohonan filter effects cancel each other out, producing an accidentally accurate result.

---

#### CONV ecc2a2ce — Total Produk Terdaftar

**Q: Berapa produk pangan olahan terdaftar di BPOM saat ini?**
- System answer: **311,959**
- SQL: UNION ALL of ERBA + ERLA with `jenis_permohonan IN ('301','305')`, then `COUNT(DISTINCT nomor)`
- DB verification:

| Method | Count |
|---|---|
| ERBA active NIE + ERLA active NIE UNION DISTINCT | ~215,431 |
| System SQL (UNION ALL + COUNT DISTINCT is equivalent) | ~311,959 |

- The COUNT(DISTINCT) over UNION ALL is mathematically equivalent to UNION's COUNT(DISTINCT), so UNION ALL is not the direct cause.
- Root cause: The jenis_permohonan filter `IN ('301','305')` is applied, but the question "produk terdaftar di BPOM saat ini" means ALL active NIEs, not just those from "new" applications. Products whose current valid NIE was granted via perubahan mayor/minor (jenis_permohonan='302','303') are excluded.
- Additionally, ERLA includes `status='0099'` (2,703 additional nomor) which may be an over-inclusion.
- **Scope ambiguity: question is about current state (dynamic data), some discrepancy is expected. But the jenis_permohonan filter systematically understates.**

---

#### CONV 51f6fa36 — NIE Bulan Mei + 2025 Breakdown

**Q: Berapa NIE yang terbit di tahun 2025 untuk aplikasi ereg RBA?**
- System answer: **53,844**
- SQL: `WHERE tanggal >= '2025-01-01' AND tanggal < '2026-01-01' AND status IN ('0999','0906','9999') AND trader_id NOT IN (5,17,50,85)` — **NO jenis_permohonan filter**
- DB actual: **53,535** 
- Assessment: **Near-exact match ✓ (gap: −0.6%). This is the most accurate NIE 2025 answer in the test.**
- Observation: The absence of the jenis_permohonan filter produced the correct result. This reveals that the filter's presence/absence is non-deterministic across sessions.

**Q: Berapa untuk permohonan baru saja?**
- System answer: ~45,147 per category breakdown
- SQL: added `jenis_permohonan IN ('301','305')`
- Assessment: **Correct for "baru only" scope ✓**

**Q: Berapa jumlah produk menengah rendah yang statusnya draft pemenuhan komitmen?**
- System answer: **29,116** (draft MR)
- SQL: `WHERE kategori_dokumen='303' AND ROUND(status_komitmen::numeric)::int::text = '0'` — no status NIE filter
- DB actual: 27,611
- Gap: +5.5% — moderate discrepancy. Root cause unclear; may relate to how `status_komitmen='0'` is interpreted (float vs int normalization handles '0' and '0.0' correctly via ROUND pattern).

---

#### CONV 29ffee13 — AMDK 2024–2025 + MR Dibatalkan

**Q: Jumlah persetujuan produk AMDK ERBA 2024–2025?**
- System answer: 2024=2,208 / 2025=1,952
- SQL: `jenis_pangan='1401'` + `jenis_permohonan IN ('301','305')`
- DB actual (all jenis_permohonan): 2024=2,301 / 2025=1,993
- Gap: −4% (jenis_permohonan filter effect)
- Assessment: Minor gap from filter. **For "persetujuan baru", this SQL is correct. For "all active NIE AMDK 2024", it undercounts.**

**Q: Berapa jumlah produk MR yang dibatalkan sampai dengan tahun 2026?**
- System answer: **254**
- SQL:
```sql
WHERE kategori_dokumen = '303'
  AND status IN ('0999', '0906', '9999')  ← NIE active filter
  AND jenis_permohonan IN ('301', '305')
  AND ROUND(status_komitmen::numeric)::int::text = '5'
```
- DB verification — breakdown per year:

| Year | System | SQL with `status IN (...)` | Without status filter (correct) |
|---|---|---|---|
| 2023 | 2 | 2 ✓ | — |
| 2024 | 208 | 208 ✓ | — |
| 2025 | 38 | 34 ≈ | — |
| 2026 | 6 | 6 ✓ | — |
| **Total** | **254** | **250** | **5,146** |

- The per-year breakdown almost exactly matches, confirming the exact SQL the agent used.
- Root cause: The agent followed `data_quality_rules.md` rule "commitment queries STILL require NIE filters". This is correct for "NIEs with cancelled commitment" but WRONG for "how many applications were cancelled" — the majority of cancellations happen BEFORE a NIE is issued, so `status='0999'` (NIE active) filters them out.
- **Error: −95.1%. 2023/2024 data is static — this definitively proves wrong logic, not data movement.**

---

#### CONV 2da5f2b3 — Susu Merk Sekolah Mei 2026

**Q: Jumlah produk susu merk sekolah yang disetujui Mei 2026?**
- System answer: **0 (tidak ditemukan)**
- SQL: 15 exploratory queries (correctly searched merk, nama, tanggal, ERLA)
- DB verification: 0 ✓
- Assessment: **Correct ✓. System appropriately explored multiple angles and returned honest "not found".**

---

#### CONV 7b8f0ce2 — AMDK 2023 + MT Repeat

**Q: Berapa jumlah NIE untuk produk AMDK pada tahun 2023?**
- System answer: **1,843** (ERBA + ERLA combined)
- SQL: ERBA `jenis_pangan='1401'` + ERLA `jenis_pangan IN ('651','652','655')`, 2023 filter
- DB actual (ERBA only): 1,744; ERBA+ERLA: ~1,843
- Assessment: **Accurate ✓. ERLA adds legitimate AMDK from the legacy system.**

**Q: Berapa jumlah izin edar produk olahan dengan risiko menengah tinggi?** (repeated)
- System answer: **95,736** (same bug as conv abc7d544)
- Assessment: **Same error repeats — confirms systematic, not random.**

---

#### CONV b2075dd4 — Tren Risiko Rendah vs Tinggi + NIE 2025

**Q: Perbandingan tren NIE Risiko Rendah dan Tinggi (upvoted ✓)**
- System answer: per-year breakdown — user upvoted this answer
- SQL: well-structured UNION with correct risk code mappings per system
- Assessment: **Correct approach, well-executed. This is the only upvoted answer in the test.**

**Q: Berapa total izin edar yang terbit pada tahun 2025?**
- System answer: **45,247**
- SQL: ERBA + ERLA UNION ALL, `jenis_permohonan IN ('301','305')`, `COUNT(DISTINCT nomor)`
- DB actual: 53,535 (ERBA only) / ~54,000+ (ERBA+ERLA)
- Gap: −15.5%
- Root cause: `jenis_permohonan IN ('301','305')` excludes products from perubahan (302/303) that also have valid 2025 NIEs. **Same session as the upvoted answer but different SQL choice = non-determinism evidence.**

---

#### CONV eebc653e — Formula Bayi Deep-Dive (11 Questions)

**Q: Berapa jumlah produk formula bayi yang telah memiliki izin edar?**
- System answer: **784** (all-time, including expired)
- SQL initial: `jenis_pangan IN ('622','604')` in ERLA, `jenis_pangan IN ('1301','1302')` in ERBA (broad scope including formula for premature babies)

**Q: Total yang masih berlaku?**
- System answer: **267** (ERBA=196, ERLA=71)
- SQL: filter by `tanggal_exp >= '2026-06-15'`
- DB verification:

| Scope | ERBA | ERLA | Total |
|---|---|---|---|
| Strict: Formula Bayi only (`jenis_pangan='1301'`) | 60 | ~88 | ~148 |
| System: Formula Bayi + Formula Lanjutan Bayi Prematur (`1301`+`1302`) | ~196 | ~71 | ~267 |
| All 130x (too broad, includes MP-ASI, etc.) | 305 | — | 305+ |

- Root cause: The agent uses `jenis_pangan IN ('1301','1302')` for ERBA, including "Formula Bayi untuk Keperluan Medis Khusus Bayi Prematur" (1302), which the user may consider a different category from "formula bayi" general.
- The ERLA mapping `jenis_pangan IN ('604','622')` captures a broader set (all formula types in ERLA).
- **Semantic ambiguity: depends on business definition of "formula bayi". System's broader interpretation inflates by ~80% vs strict definition.**

**Key observation:** The user confirmed this was wrong by asking "data yang muncul bukan formula bayi, melainkan data makanan selingan" — indicating the system sometimes uses `jenis_pangan LIKE '13%'` (all 1,581 products in category 13) instead of the formula-specific codes.

---

#### CONV 40286c1c — Formula Bayi + MD 2025

**Q: Berapa jumlah produk MD tahun 2025?**
- System answer: **30,760**
- SQL: `WHERE nomor LIKE 'MD %' AND jenis_permohonan IN ('301','305') AND status IN ('0999','0906','9999') AND tanggal >= '2025-01-01' AND tanggal < '2026-01-01'`
- DB verification:

| Query | Count |
|---|---|
| `nomor LIKE 'MD%'` + all `jenis_permohonan` | **36,706** |
| `nomor LIKE 'MD %'` (with space) + `jenis_permohonan IN ('301','305')` | **30,760** ← system exact match |
| `nomor LIKE 'MD%'` + `jenis_permohonan IN ('301','305')` | ~30,760 |

- Root cause: `jenis_permohonan IN ('301','305')` excludes 5,946 MD products with valid 2025 NIE from perubahan registrations. User did not ask "baru only".
- **Error: −16.2% on 2025 data (nearly closed year). Static enough to prove SQL wrong.**

---

#### CONV 7535cd1d — Total NIE 2025

**Q: Berapa total izin edar yang terbit pada tahun 2025?**
- System answer: **46,770**
- SQL: ERBA produk + ERLA produk + **ERBA BTP + ERLA BTP** (4-table UNION), `jenis_permohonan IN ('301','305')`
- DB actual (ERBA only, no BTP): 53,535; with BTP: ~53,643
- Analysis:

| Session | SQL scope | Answer |
|---|---|---|
| Conv 5 (51f6fa36) | ERBA produk only, NO jenis_permohonan filter | **53,844** ≈ correct |
| Conv 9 (b2075dd4) | ERBA + ERLA produk, WITH filter | **45,247** |
| Conv 13 (7535cd1d) | ERBA + ERLA + BTP ERBA, WITH filter | **46,770** |

- Three different sessions, same question → three different SQL structures → three different numbers.
- **Non-determinism is the primary failure mode here. The system doesn't have a stable, canonical SQL for this common question.**

---

#### CONV f735bd16 — Total NIE Mei 2026

**Q: Berapa total izin edar yang terbit tahun 2026 bulan Mei?**
- System answer: **3,880**
- SQL: ERBA produk + ERBA BTP only (NO ERLA), `jenis_permohonan IN ('301','305')`
- DB actual: ERBA produk 5,085 + BTP 108 = 5,193 (without jenis_permohonan filter)
- Root cause: (1) ERLA not included; (2) jenis_permohonan filter applied
- **Error: −25%. Dynamic data (May 2026), but the two systematic bugs still cause ~1,300 undercount.**

---

## 4. Root Cause Analysis — Connecting SQL Bugs to Context Files

The agent generates SQL by reading its context files. Every SQL error traces back to a gap, ambiguity, or error in those files.

### RC-1: ERLA Risk Code Scope Mismatch (Highest Impact)

**Affected questions:** NIE MT all-time (conv abc7d544, 7b8f0ce2)  
**SQL bug:** ERLA `jenis_dokumen='303'` treated as "Menengah Tinggi"  
**DB evidence:** ERLA `jenis_dokumen='303'` has 83,857 distinct nomor vs ERBA MT of 11,919  
**Error magnitude:** +703%

**What the context says** (`business_glossary.md`):
```
| Risiko Menengah Tinggi | ERLA code: '303' | ERBA equivalent: '302' |
```

**What the data_dictionary says:**
```
JENIS_DOKUMEN | 303 | Pangan Medium Risk | ERLA dan ERBA
```

**The gap:** ERLA never had a true MT/MR distinction. The legacy system used 3 levels:
- `'301'` = Low Risk (all Rendah)
- `'302'` = High Risk (Tinggi)
- `'303'` = **ALL Medium Risk** (= ERBA MT + MR combined)

The glossary teaches the agent that ERLA `'303'` = MT specifically. This is factually incorrect — ERLA `'303'` is ALL medium risk. **Consequence: any all-time MT query inflates ERLA contribution ~7x.**

**Fix direction:** The glossary must be corrected. Add: "ERLA `jenis_dokumen='303'` = all medium risk products (Low+Medium in old classification = roughly ERBA `'302'`+`'303'` combined). For MT-specific queries that require ERBA/ERLA parity, treat ERLA medium risk as a combined MT+MR and note the limitation. Do not attempt to isolate MT from ERLA data."

---

### RC-2: `jenis_permohonan` Filter Applied to "All Active NIE" Queries

**Affected questions:** Total NIE 2025, Total produk terdaftar, Produk MD 2025, AMDK 2024  
**SQL bug:** `jenis_permohonan IN ('301','305')` hardcoded on all NIE queries  
**Error magnitude:** −4% to −16%

**What the context says** (`data_quality_rules.md`):
```
Valid jenis_permohonan for NIE counts:
ERBA: jenis_permohonan IN ('301', '305')
```

**The gap:** The rule is technically correct for one specific question type ("how many NEW NIEs were issued?") but incorrectly applied to all NIE queries including:
- "Total produk terdaftar" — needs ALL active NIEs regardless of how they were registered
- "Berapa NIE 2025" — should include products renewed/modified in 2025

The rule states "Only these application types produce issued NIEs" which is misleading. Types '302' and '303' (Perubahan) result in a **modified existing NIE** — the nomor is the same but the record is updated. If the current status is `'0999'` (active), that product has a valid NIE regardless of whether the last application type was '302' or '301'.

**Two distinct business questions the rule conflates:**

| Question | Correct filter |
|---|---|
| "Berapa NIE **baru** yang terbit di 2025?" | `jenis_permohonan IN ('301','305')` ← correct |
| "Berapa total produk yang punya NIE aktif di 2025?" | NO `jenis_permohonan` filter ← rule is wrong |
| "Berapa produk MD yang **terdaftar** di 2025?" | Depends on question intent |

**Fix direction:** Rewrite `data_quality_rules.md` to distinguish:
- "NIE terbit" (newly issued) → apply `jenis_permohonan IN ('301','305')`
- "Produk terdaftar / active NIE" → do NOT filter by `jenis_permohonan`; rely on `status IN (...)` alone
- Add a RESOLVE-phase check: agent must explicitly ask "is the user asking about new issuances or total active?" before defaulting the filter

---

### RC-3: Garam Beryodium Sub-Category Code vs Parent Category

**Affected questions:** NIE Garam Beryodium ERBA 2023  
**SQL bug:** `kategori_pangan = '120101000001'` used instead of `jenis_pangan = '1204'`  
**DB evidence:**

| Filter | Count (2023, with jenis_permohonan) | Difference |
|---|---|---|
| `kategori_pangan = '120101000001'` | 189 | — |
| `jenis_pangan = '1204'` | 198 | +9 products (4.7%) |

**What the context says** (`business_glossary.md` and `SEEKNAL_ASK.md §4`):
```
Garam Beryodium — ERBA: kategori_pangan = '120101000001'
```

**The gap:** `kategori_pangan` is a 12-digit hierarchical code for a SPECIFIC sub-category. `jenis_pangan = '1204'` is the 4-digit PARENT category covering ALL garam beryodium sub-types. The 12-digit code `120101000001` misses 9 products registered under different sub-codes (e.g., garam beryodium in different physical forms) that still fall under `jenis_pangan='1204'`.

**2023 is static data — the 9-product gap on an unchanging year definitively proves the filter is wrong.**

**Fix direction:** Change both `SEEKNAL_ASK.md §4` and `business_glossary.md` to:
```
Garam Beryodium — ERBA: jenis_pangan = '1204'  (covers all sub-types, ~199 products in 2023)
```
Note: `kategori_pangan = '120101000001'` is a valid sub-filter if the user specifically asks about one variety, but should not be the default.

---

### RC-4: Commitment Cancellation Logic Conflates Two Different Questions

**Affected questions:** MR Dibatalkan (conv 29ffee13)  
**SQL bug:** `status IN ('0999','0906','9999') AND status_komitmen='5'` — requires active NIE + cancelled commitment simultaneously  
**DB evidence:**

| Query | Count |
|---|---|
| With `status IN ('0999','0906','9999') AND status_komitmen='5'` | **254** |
| With `status_komitmen='5'` only (correct for cancellation count) | **5,146** |

**What the context says** (`data_quality_rules.md`):
```
## Commitment queries still require all NIE filters
When filtering by status_komitmen (e.g., cancelled = '5'), 
the standard NIE filters are STILL required.
```

**The gap:** This rule is correct for one scenario: "count products that HAVE a valid NIE AND also have commitment status X" (e.g., "how many active NIE have their commitment under review?"). But for "berapa MR yang dibatalkan?", the question asks about **applications whose commitment was cancelled** — which happens BEFORE NIE issuance for most cases. Requiring `status='0999'` (NIE active) filters out 4,892 products that were cancelled before receiving a NIE.

**The rule teaches the wrong logic** for this class of questions.

**Fix direction:** Add a distinction in `data_quality_rules.md`:
- **Case A: NIE with commitment status** ("NIE yang komitmennya disetujui/dibatalkan") → keep NIE status filter + add commitment filter
- **Case B: Applications with cancelled commitment** ("permohonan yang dibatalkan") → remove NIE status filter; apply only `status_komitmen = '5'` (and optionally exclude only products with completed/issued NIE if user wants in-progress only)

The RESOLVE phase should ask: "Is the user asking about products that HAVE a NIE, or about the application commitment lifecycle (regardless of NIE outcome)?"

---

### RC-5: Non-Deterministic SQL Generation for the Same Question

**Affected questions:** Total NIE 2025 (3 different sessions → 3 different answers)  
**Evidence:**

| Session | BTP included | jenis_permohonan filter | ERLA included | Answer |
|---|---|---|---|---|
| Conv 5 (51f6fa36) | No | **No** | No | **53,844** (≈ correct) |
| Conv 9 (b2075dd4) | No | Yes | Yes | **45,247** |
| Conv 13 (7535cd1d) | **Yes** | Yes | Yes | **46,770** |

The context does not provide an explicit, canonical answer to:
1. Should BTP be included in "total izin edar"?
2. Should ERLA be included when "ereg RBA" is not specified but year is 2025?
3. Should `jenis_permohonan` filter apply when question is about "total"?

Each LLM session resolves these ambiguities differently. Since the context is read fresh each session and there's no stable "memory" of past correct answers, this is a structural non-determinism.

**Fix direction:** Add explicit disambiguation rules in `data_quality_rules.md` or `intent_mapping.md`:
- "Total izin edar" without qualifier → ERBA + ERLA produk only (no BTP), no jenis_permohonan filter
- "Total izin edar termasuk BTP" → explicitly add BTP tables
- System should ask clarification only when user explicitly needs the distinction; otherwise default to above

---

### RC-6: ERLA Missing from Mei 2026 Total Query

**Affected questions:** Total NIE Mei 2026 (conv f735bd16)  
**SQL:** Only queries ERBA produk + ERBA BTP, no ERLA  
**Root cause:** The context notes "ERBA is the primary source for 2023+", which the agent correctly interprets for trend analysis. But it incorrectly extends this to mean ERLA has no data for 2025/2026. ERLA data extends to "now" per schema state documentation, and may have 2026 entries.

**Fix direction:** Clarify in `data_architecture.md` or `data_quality_rules.md`: "ERLA (`t_produk_3_rilis_erla`) may have entries up to the current date. Always include ERLA in any ALL-TIME or scope-not-specified query, including recent months. ERBA is PRIMARY (most volume from 2023+) but ERLA is not empty for recent years."

---

## 5. Summary: Failure Pattern Classification

| # | Root Cause | Context File Responsible | Questions Affected | Error Magnitude |
|---|---|---|---|---|
| RC-1 | ERLA `jenis_dokumen='303'` = All Medium Risk, not MT | `business_glossary.md` | NIE MT all-time | **+703%** |
| RC-2 | `jenis_permohonan` filter misapplied to "total active NIE" | `data_quality_rules.md` | NIE 2025, Produk MD, AMDK, Total | −4% to −16% |
| RC-3 | Garam Beryodium uses sub-category code vs parent | `business_glossary.md`, `SEEKNAL_ASK.md §4` | Garam Beryodium 2023 | −4.5% |
| RC-4 | Commitment cancellation requires NIE filter (wrong logic) | `data_quality_rules.md` | MR Dibatalkan | **−95%** |
| RC-5 | No canonical SQL for "total NIE" — BTP/ERLA inclusion ambiguous | `data_quality_rules.md`, `intent_mapping.md` | Total NIE 2025 (3 answers) | Non-deterministic |
| RC-6 | ERLA excluded from recent-month queries | `data_architecture.md` | Total NIE Mei 2026 | −25% (combined with RC-2) |

---

## 5.1 Additional Findings Not Captured in RC-1..RC-6

The six root causes above explain the major **SQL logic** discrepancies found in the original
57-question UAT. However, later regression evidence and cross-run comparison show that the
remaining failures are **not only SQL-definition bugs**. Several additional failure modes were
not explicitly captured in the original audit:

### AF-1: The system over-reasons simple single-turn questions

The current architecture asks the agent to do all of the following before answering:
- load multiple context files,
- build a semantic commitment block,
- resolve coded terms through the dictionary,
- plan a query,
- execute,
- then audit/reflect before generating.

This workflow is conceptually correct, but on simple questions it often turns a one-query task
into a multi-query exploration cycle. The result is:
- more SQL calls than necessary,
- more chances to drift into alternative scopes,
- higher latency,
- greater probability of ending without a final answer.

This is not a "wrong SQL template" problem. It is a **workflow-weight** problem: the system lacks
a strong rule for when to stop exploring and commit to one authoritative query.

### AF-2: Some failures are orchestrator/runtime failures, not reasoning failures

In later concurrency runs, a non-trivial subset of failed cases returned:
- **empty answers**,
- **zero tool calls and zero SQL calls**, or
- long exploratory traces that never reached a final answer.

This shows a second class of failures:
- the agent sometimes fails to **finish** the workflow,
- not merely to choose the wrong SQL.

These failures should be classified separately from domain-logic errors. If they are mixed
together, the team may incorrectly conclude that every failure needs more context, when some of
them actually need better completion guarantees, timeout handling, or simpler execution paths.

### AF-3: Not all UAT failures are equal — many are substantive, but some are evaluation-shape failures

The original audit correctly focuses on substantive numeric errors. A later review of the
single-turn harness shows three distinct categories:

| Failure type | Meaning |
|---|---|
| **Substantive** | the system answered the wrong number / wrong scope |
| **Formatting / lexical** | the answer was close or semantically correct, but failed exact substring checks |
| **Runtime-empty** | no usable answer was produced |

This distinction matters. If all failures are treated as equally "wrong SQL", the team will
over-correct context instead of addressing output-shape consistency and workflow completion.

### AF-4: Domain coverage is still uneven — some business concepts are under-taught

The original audit highlights risk, commitment, Garam, and total-NIE scope. Additional evidence
shows that several domains remain weak not because the agent is unintelligent, but because the
context does not yet teach a sufficiently crisp reasoning path:
- **klaim** (`klaim` flag / claim-bearing products),
- **peruntukan**,
- some **expiry / kadaluarsa** questions,
- some **company / top perusahaan** ranking questions,
- some **segment-specific** queries where discovery is too open-ended.

The system knows these columns exist, but it has not been taught enough about:
- when a field is already directly usable,
- when dictionary resolution is required,
- what the canonical metric is for that concept,
- and what scope the user most likely intends by default.

### AF-5: Reflection/audit exists, but it is not yet a strong enough rejection gate

The architecture already includes `evidence-auditor`, which is a good design choice. However,
several wrong answers still make it through even when the result magnitude is visibly suspicious.

Examples:
- MT all-time inflated 8x,
- cancellation counts undercounted by ~95%,
- broad combined medium-risk values shipped as if they were MT-specific.

This means REFLECT currently behaves more like a **checklist** than a **hard stop**. The agent can
notice ambiguity, but still proceed to answer. For high-risk ambiguity (cross-system code
collisions, Case A vs Case B commitment logic, strict-vs-broad segment scope), the correct
behavior is not "mention caveat and continue" — it is "refuse to collapse incompatible scopes into
one number."

### AF-6: Query inflation is itself a quality bug

When the system needs many discovery and verification queries to answer a question that should be
solvable in one authoritative query, this is not just a performance concern. It is a correctness
risk:
- each extra branch creates another possible scope drift,
- each exploratory count can anchor the agent on the wrong interpretation,
- and the final answer becomes less deterministic across sessions.

In other words, **too many SQL queries is not only inefficient; it is a failure precursor.**

---

## 6. Hypotheses — Why These Errors Emerged

### H1: The "New Application = NIE" Mental Model
The context was likely designed around "how many new NIEs were issued?" as the primary query pattern. The `jenis_permohonan` rule correctly filters for new issuances. But as users ask broader questions ("total produk terdaftar", "berapa MD 2025"), the filter over-generalizes. **Hypothesis: context was built for a narrower use case and expanded without updating the filter rules.**

### H2: ERLA Was Added As a Complement, Not Revalidated
The ERLA risk code mapping in `business_glossary.md` was likely added when ERLA support was introduced. The code '303' = MT mapping may have been derived from analogy with ERBA (where '303' = MR) rather than from actual `data_dictionary` verification. **Hypothesis: the ERLA risk mapping was not verified against live data at time of authoring.**

### H3: The Commitment Rule Solves the Wrong Problem
`data_quality_rules.md` says "commitment queries still require NIE filters" with an explanation: "Without status, the query counts products still in process." This is a correct concern for "count NIEs that have commitment X". But it was added to prevent a different bug (counting non-NIE rows in commitment queries) and the rule over-corrects by excluding the very rows (pre-NIE cancelled applications) that "MR Dibatalkan" should count. **Hypothesis: rule was written for a specific bug fix and unintentionally broke commitment cancellation counting.**

### H4: Non-Determinism Is Structural, Not Random
LLM sessions have no shared state. Each session reads context fresh and resolves ambiguities independently. When the context doesn't provide an explicit default for "should BTP be included in total NIE?", each session makes its own decision. **Hypothesis: the context has implicit assumptions that were clear to the author but are not explicit enough to constrain LLM generation reliably.**

### H5: Sub-Category vs Parent Category Confusion
`kategori_pangan = '120101000001'` was probably taken from a sample data row ("the most common garam beryodium product has this code") rather than from a business definition ("garam beryodium = all products with jenis_pangan='1204'"). **Hypothesis: the code was derived from data exploration rather than business ontology, creating a precision vs recall tradeoff that was not noticed.**

### H6: The system was taught many safeguards, but not enough prioritization
The architecture contains good ideas: inheritance control, semantic commitment, dictionary-based
resolution, REFLECT, and source-aware joins. The missing piece is **priority ordering**:
- which safeguards are mandatory for this question,
- which are optional,
- and when to stop once the authoritative path is found.

Without this prioritization, the agent treats too many safeguards as cumulative obligations on
every turn. That makes the system intellectually careful, but operationally noisy.

### H7: Some context files encode the right philosophy but still leave operational defaults implicit
The project explicitly aims to teach *how to think*, not hardcode answers. That philosophy is
correct. But in several high-frequency question families, the context still leaves key defaults
unstated:
- whether a phrase defaults to ERBA-only or combined,
- whether "produk" means category, row-level product, or product family,
- whether a concept should be measured by `nomor`, `produk_id`, or `trader_id`,
- whether a field is a direct business signal or needs dictionary translation first.

When those defaults are not explicit, the LLM must improvise. Improvisation is exactly where the
session-to-session variance comes from.

### H8: The current evaluation harness rewards literal stability, while the agent still answers too freely
The single-turn harness checks `assert_contains` via literal substring matching. This means the
agent is penalized not only for wrong numbers, but also for:
- missing exact lexical terms,
- choosing a synonym instead of the expected phrase,
- formatting a number differently,
- or failing to repeat the exact keyword the test expects.

This does **not** invalidate the substantive failures above, but it does mean that some later
regressions may be partly due to output-shape instability rather than database misunderstanding.
The system still needs to become more consistent in how it presents the same class of answer.

---

## 7. What Passes and What Fails

### Questions the System Answers Correctly

| Question | System | Actual | Notes |
|---|---|---|---|
| Susu merk sekolah Mei 2026 | 0 | 0 ✓ | Correct exploration + honest null result |
| BTP ERBA 2023 | 950 | 950 ✓ | Exact match |
| AMDK ERBA 2023 (combined) | 1,843 | ~1,843 ✓ | Accurate (ERBA + ERLA combined) |
| NIE ERBA 2025 (no jenis_permohonan) | 53,844 | 53,535 ✓ | Near-exact (best answer in test) |
| Tren Risiko Rendah vs Tinggi (upvoted) | Per-year breakdown | Structurally correct | User upvote confirmed |
| AMDK ERBA per year 2024/2025 | 2,208/1,952 | 2,301/1,993 | Slight undercount (jenis_permohonan filter) |

### Questions the System Answers Incorrectly

| Question | System | Actual | Root Cause |
|---|---|---|---|
| NIE MT all-time | 95,736 | 11,923 | RC-1 (ERLA code scope) |
| MR Dibatalkan | 254 | 5,146 | RC-4 (commitment filter logic) |
| Total NIE 2025 | 45,247–46,770 | 53,535 | RC-2 + RC-5 |
| Produk MD 2025 | 30,760 | 36,706 | RC-2 (jenis_permohonan filter) |
| Garam Beryodium 2023 | 189 | 198 | RC-3 (sub-category code) |
| Total NIE Mei 2026 | 3,880 | ~5,193 | RC-2 + RC-6 |
| Formula Bayi berlaku | 267 | ~148 (strict) | Semantic scope ambiguity |

---

## 7.1 Additional Failure Classes Beyond the Original 57-Question Audit

The original UAT concentrated on 57 real user questions. Broader regression testing suggests a few
additional classes of failure that deserve explicit tracking because they require different fixes:

| Class | Symptom | Likely Fix Direction |
|---|---|---|
| Empty-output failure | answer is blank or not finalized | orchestrator / runtime / completion guard |
| Exploration overflow | many SQL probes but no committed final answer | stronger stop rule, authoritative-path rule |
| Output-shape instability | same substance, different wording/format → test fail | response contract / deterministic phrasing |
| Under-taught business attribute | claim, purpose, expiry, top-company questions wander | enrich concept-specific reasoning guides |

These are important because they are **not** solved by simply correcting dictionary mappings or
adding more examples to context.

---

## 8. Recommendations — Teaching the Agent, Not Hardcoding SQL

The goal is an agent that **knows when to apply which filter, why, and for what purpose**. The following changes to context files achieve this without hardcoding any queries.

### R1: Fix ERLA Risk Code Mapping (Priority: CRITICAL)

**File:** `context/business_glossary.md`  
**Change:** Correct the ERLA risk code table:

```markdown
### ERLA — jenis_dokumen codes

ERLA used a 3-level risk classification (not 4 like ERBA).
Code '303' captures ALL medium-risk products — equivalent to ERBA MT + MR combined.

| ERLA code | ERLA label | ERBA approximate equivalent |
|---|---|---|
| '301' | Low Risk | Risiko Menengah Rendah + Notifikasi |
| '302' | High Risk | Risiko Tinggi |
| '303' | **ALL Medium Risk** | Risiko MT + MR combined (NOT MT alone) |

⚠️ ERLA '303' has ~84,000 products (all medium risk), not just MT.
For MT-specific queries: ERBA-only is the authoritative source.
State to user that ERLA data cannot isolate MT from MR for historical periods.
```

### R2: Distinguish jenis_permohonan Filter Scope (Priority: HIGH)

**File:** `context/data_quality_rules.md`  
**Change:** Add a "when to apply / when to skip" decision tree:

```markdown
## jenis_permohonan Filter — When to Apply

### Apply jenis_permohonan IN ('301','305') ERBA when:
- User asks "NIE baru yang terbit" (newly issued licenses)
- User asks "berapa izin edar baru di tahun X"
- User explicitly says "baru" or "permohonan baru"

### Do NOT apply jenis_permohonan filter when:
- User asks "total produk terdaftar" (all active licensed products)
- User asks "berapa produk MD" (all MD products with active NIE)
- User asks "all-time NIE" without "baru" qualifier
- Question is about current active state, not new issuances

**Default for ambiguous "berapa NIE" without "baru":** 
RESOLVE must disambiguate. Ask: "does the user want newly issued NIEs only, 
or all products currently holding a valid NIE?"
If the question context clearly implies current total (e.g., "terdaftar di BPOM saat ini"), 
apply status filter only (no jenis_permohonan filter).
```

### R3: Fix Garam Beryodium Code (Priority: HIGH)

**Files:** `context/business_glossary.md`, `SEEKNAL_ASK.md §4`  
**Change:**
```markdown
### Garam Beryodium
- ERBA: `jenis_pangan = '1204'`  (parent category = all iodized salt, ~199 products in 2023)
  Note: `kategori_pangan = '120101000001'` is one sub-type only; use jenis_pangan for complete coverage
- ERLA: `kategori_pangan = '12010103'`
```

### R4: Rewrite Commitment Query Rule (Priority: HIGH)

**File:** `context/data_quality_rules.md`  
**Change:**

```markdown
## Commitment Queries — Two Distinct Cases

### Case A: "Products WITH a valid NIE that also have commitment status X"
Example: "berapa NIE yang komitmennya sedang dalam review?"
→ Apply ALL NIE filters: status IN (...) + jenis_permohonan IN (...) + status_komitmen = X

### Case B: "Applications whose commitment was cancelled/approved at any stage"
Example: "berapa MR yang dibatalkan?", "berapa yang komitmennya tidak dilanjutkan?"
→ Apply category filter (kategori_dokumen) + status_komitmen = '5'
→ Do NOT apply status IN (...) — most cancellations happen BEFORE NIE is issued
→ Use COUNT(DISTINCT produk_id) for application count, or COUNT(DISTINCT nomor) if asking about NIEs

RESOLVE must determine which case applies before writing SQL.
The signal: "berapa dibatalkan" = Case B; "berapa NIE yang..." = Case A.
```

### R5: Explicit Canonical Rules for "Total NIE" Queries (Priority: MEDIUM)

**File:** `context/intent_mapping.md` (or `data_quality_rules.md`)  
**Add:**
```markdown
## Canonical Definition: "Total Izin Edar / Total NIE"

Default scope (when user says "total izin edar" / "total NIE" without qualifier):
- Tables: t_produk_3_erba + t_produk_3_rilis_erla
- BTP: EXCLUDE unless user explicitly mentions "BTP" or "bahan tambahan"
- jenis_permohonan: DO NOT filter (all application types that have active NIE count)
- status: ERBA IN ('0999','0906','9999'), ERLA IN ('0099','0999','0906','9999')
- Count: COUNT(DISTINCT nomor) over UNION

If user says "termasuk BTP" → add t_btp_3_erba + t_btp_3_erla
If user says "baru saja" → add jenis_permohonan IN ('301','305') to ERBA
```

### R6: Clarify ERLA Date Range for Recent Queries (Priority: MEDIUM)

**File:** `context/data_architecture.md`  
**Add:**
```markdown
ERLA (t_produk_3_rilis_erla) date range: 2012 → present (data is still added).
Do NOT assume ERLA is empty for 2024/2025/2026.
For all-time or recent-month queries: always UNION ERBA + ERLA.
ERBA is the PRIMARY system for post-2022 volume, but ERLA may have concurrent entries.
```

### R7: Add an "Authoritative Path" rule for simple questions (Priority: HIGH)

**Files:** `SEEKNAL_ASK.md`, `seeknal/skills/bpom-analyst/SKILL.md`

Teach the agent that many questions have a single dominant resolution path. Once that path is
identified, the agent should stop exploring and execute the final query.

Suggested principle:
```markdown
If the question resolves cleanly to:
- one entity,
- one metric,
- one time column,
- one system scope,
- and at most one coded filter,

then prefer:
1 binding query (if needed) + 1 final SQL query + 1 optional total/verification query.

Do not branch into exploratory alternatives unless the first result is structurally suspicious.
```

This preserves the "teach thinking" philosophy while reducing query inflation and answer drift.

### R8: Promote REFLECT from checklist to blocking gate (Priority: HIGH)

**Files:** `seeknal/skills/evidence-auditor/SKILL.md`, `seeknal/skills/bpom-analyst/SKILL.md`

Add explicit blocking conditions:
- cross-system codes that are not semantically isolatable,
- MT/MR ambiguity in ERLA,
- commitment Case A vs Case B not yet resolved,
- segment scope still broad-vs-strict ambiguous,
- per-year totals that contradict the grand-total logic materially.

When any of these conditions holds, the agent should:
1. re-resolve, or
2. answer with a scoped limitation,
3. but **must not ship a collapsed numeric answer as if it were exact**.

### R9: Teach direct-field concepts explicitly (Priority: MEDIUM)

**Files:** `context/business_glossary.md`, `context/intent_mapping.md`

Some attributes should be taught as direct operational concepts, not left to free-form discovery:
- `klaim`
- `peruntukan`
- `tanggal_exp` / expiry / kadaluarsa
- company ranking (`nama trader` canonicalization)

Each should define:
- canonical metric,
- primary column,
- whether dictionary lookup is needed,
- default scope,
- and common pitfalls.

This is still general reasoning, not hardcoding per question.

### R10: Separate "substantive fail" from "presentation fail" in evaluation (Priority: MEDIUM)

**Files:** test harness / regression documentation

The audit process should classify failures into:
- wrong number / wrong scope,
- wording / formatting mismatch,
- runtime-empty / unfinished answer.

Without this separation, the team cannot tell whether a change improved reasoning but hurt
presentation consistency, or vice versa.

### R11: Add a completion guarantee for answer generation (Priority: MEDIUM)

**Files:** `seeknal/skills/bpom-analyst/SKILL.md`

Before ending the turn, enforce:
- if at least one authoritative query succeeded,
- and no blocking ambiguity remains,
- then the agent must produce a final answer.

This protects against the failure mode where the system reasons, queries, and even verifies, but
still returns an empty or unfinished answer.

### R12: Define a small set of canonical output contracts for high-frequency question types (Priority: MEDIUM)

For recurring question families, the system should answer in a stable shape:
- scalar count with one-sentence scope note,
- per-year trend with total at the end,
- comparison table with one-line conclusion,
- ranking with explicit grouping basis.

The goal is not to hardcode content, but to stabilize presentation so equivalent questions produce
equivalent answer forms. This reduces both user confusion and harness-level false failures.

### R13: Mandatory Output Format with Code Detail — Trust Through Transparency (Priority: CRITICAL)

**Files:** `seeknal/skills/bpom-analyst/SKILL.md`, `SEEKNAL_ASK.md`

The system must present data in a way that allows users to **verify every number**. This means:

1. **Never show a single total without breakdown**
2. **Always show ERBA and ERLA as separate columns**
3. **Always show breakdown by year (or month if requested)**
4. **Always show breakdown by status code (or other relevant codes)**
5. **Always show filter details for each code used**
6. **Always mark "-" when data does not exist for a system/period**

**Required Output Format: Matrix with Code Detail**

For every COUNT query, the output must follow this structure:
- **X-axis (columns):** System → Status Code hierarchy (ERBA status codes + ERLA status codes)
- **Y-axis (rows):** Years (or months) present in database
- **Each cell:** Count for that system + code + year

Example matrix structure:
```
|        | ERBA                                    | ERLA                                    |        |
|        | Status 0999 | Status 0906 | Status 9999 | Status 0099 | Status 0999 | Status 0906 | Total  |
|--------|-------------|-------------|-------------|-------------|-------------|-------------|--------|
| 2012   | -           | -           | -           | 11          | -           | -           | 11     |
| 2013   | -           | -           | -           | 38.166      | -           | -           | 38.166 |
| ...    | ...         | ...         | ...         | ...         | ...         | ...         | ...    |
| 2022   | 2.000       | 300         | 200         | 30.000      | 8.000       | 2.295       | 42.795 |
| 2023   | 50.000      | 5.000       | 5.573       | -           | -           | -           | 60.573 |
| Total  | 122.000     | 13.300      | 16.339      | 68.166      | 8.000       | 2.295       | 526.715|
```

**Implementation Rules:**

1. **Matrix Format**: Every COUNT query must produce output in matrix format with X-axis (system → status codes) and Y-axis (years)
2. **Always Show All Systems**: When user does not specify system, show ERBA, ERLA, and Total columns. Mark "-" when data does not exist.
3. **Always Show All Years**: When user does not specify time range, show ALL years present in database with year-by-year breakdown.
4. **Always Show Code Detail**: When query uses code filter, show which code was used for each system, definition from data_dictionary, and breakdown by status code.
5. **Always Show Filter Details**: Every query must show status filter, jenis_permohonan filter, test exclusion, and any other filter applied.
6. **Mark Missing Data Explicitly**: When data does not exist, use "-" (not 0, not empty) and add explanation in Keterangan section.

This rule ensures that every number presented to the user is **verifiable** and **traceable**, building trust in the system. See Section 10 for complete output format specification and examples.

---

## 9. Agent Learning vs Hardcoding: The Core Principle

The system's strength is that the agent **reasons from principles**, not from memorized queries. This means:

| Approach | What it enables | Risk |
|---|---|---|
| **Fix context files** (recommended) | Agent applies corrected reasoning to ALL similar questions, including ones not in the test set | Requires careful context writing |
| Hardcode SQL pairs | Exact answers for tested questions | Brittle — any variation in phrasing misses the hardcode; doesn't generalize |

The 7-phase cognitive workflow already enforces:
- Intent extraction before SQL
- Information gap resolution via hierarchy
- Mandatory filter checklist in REFLECT
- Re-derive methods every turn (no stale filter inheritance)

What's missing is **correct domain facts** in the context files **AND correct output format specification**. Fixing the 6 root causes above teaches the agent:
1. **WHEN** to apply jenis_permohonan (new issuances vs all active)
2. **WHY** ERLA '303' ≠ ERBA MT (different classification history)
3. **WHAT** Garam Beryodium means as a category (jenis_pangan parent, not sub-code)
4. **HOW** to distinguish commitment cancellation (application stage) from NIE commitment status
5. **WHAT** the canonical scope of "total NIE" is (no BTP, no jenis_permohonan filter)
6. **HOW** to present data transparently (matrix format with code detail — see Section 10)

These are **reasoning anchors**, not SQL templates. An agent that understands these six things will generate correct SQL **AND present it transparently** for any phrasing of these question types.

**The transparency principle:** User trusts the system not because the system says "trust me", but because the system shows **every detail** of how each number was derived. When user sees "Total = 119.410", they can verify: ERBA 41.516 (status 0999: 33.500, status 0906: 4.100, status 9999: 3.916) + ERLA 77.894 (status 0099: 68.300, status 0999: 8.000, status 0906: 1.594). This level of detail is what makes the answer **trustworthy**.

---

## 10. Output Format Specification — Trust Through Transparency

### 10.1 Core Principle

The system must present data in a way that allows users to **verify every number**. This means:

1. **Never show a single total without breakdown**
2. **Always show ERBA and ERLA as separate columns**
3. **Always show breakdown by year (or month if requested)**
4. **Always show breakdown by status code (or other relevant codes)**
5. **Always show filter details for each code used**
6. **Always mark "-" when data does not exist for a system/period**

**The fundamental rule:** User trusts the system not because the system says "trust me", but because the system shows **every detail** of how each number was derived.

### 10.2 Required Output Format: Matrix with Code Detail

For every COUNT query, the output must follow this structure:

**X-axis (columns):** System → Status Code hierarchy
**Y-axis (rows):** Years (or months) present in database

#### Example 1: "Berapa jumlah izin edar pangan olahan?" (No filter, all years)

```
## Total NIE Pangan Olahan

### Detail per Sistem, Tahun, dan Status

|        | ERBA                                    | ERLA                                    |        |
|        | Status 0999 | Status 0906 | Status 9999 | Status 0099 | Status 0999 | Status 0906 | Total  |
|--------|-------------|-------------|-------------|-------------|-------------|-------------|--------|
| 2012   | -           | -           | -           | 11          | -           | -           | 11     |
| 2013   | -           | -           | -           | 38.166      | -           | -           | 38.166 |
| 2014   | -           | -           | -           | 36.622      | -           | -           | 36.622 |
| 2015   | -           | -           | -           | 33.179      | -           | -           | 33.179 |
| 2016   | -           | -           | -           | 39.599      | -           | -           | 39.599 |
| 2017   | -           | -           | -           | 41.249      | -           | -           | 41.249 |
| 2018   | -           | -           | -           | 55.198      | -           | -           | 55.198 |
| 2019   | -           | -           | -           | 52.697      | -           | -           | 52.697 |
| 2020   | -           | -           | -           | 44.439      | -           | -           | 44.439 |
| 2021   | -           | -           | -           | 50.849      | -           | -           | 50.849 |
| 2022   | 2.000       | 300         | 200         | 30.000      | 8.000       | 2.295       | 42.795 |
| 2023   | 50.000      | 5.000       | 5.573       | -           | -           | -           | 60.573 |
| 2024   | 50.000      | 5.000       | 6.284       | -           | -           | -           | 61.284 |
| 2025   | 20.000      | 3.000       | 4.282       | -           | -           | -           | 27.282 |
| Total  | 122.000     | 13.300      | 16.339      | 421.809     | 8.000       | 2.295       | 526.715|

### Keterangan Status Code
| Sistem | Kode | Definisi | Persentase dari Total Sistem |
|--------|------|----------|------------------------------|
| ERBA   | 0999 | Terbit   | 80,4%                        |
| ERBA   | 0906 | Diubah   | 8,8%                         |
| ERBA   | 9999 | Valid    | 10,8%                        |
| ERLA   | 0099 | Terbit   | 94,3%                        |
| ERLA   | 0999 | Valid    | 4,7%                         |
| ERLA   | 0906 | Diubah   | 1,0%                         |

### Filter yang Digunakan
- ERBA: trader_id::bigint NOT IN (5, 17, 50, 85)
- ERLA: trader_id != 3384
- Status: Semua status aktif (tidak termasuk 0000=Dihapus, 0009=Dicabut)

### Catatan Penting
- ERBA: Data dari September 2022 hingga sekarang (sistem baru)
- ERLA: Data dari 2012 hingga 2022 (sistem lama, sudah digantikan)
- "-" menunjukkan tidak ada data pada sistem tersebut pada tahun tersebut
- Data 2025 adalah data berjalan (year-to-date)
```

### 10.3 Required Output Format: With Risk Code Filter

When a query includes risk code filter (e.g., "risiko menengah rendah"), the output must show:

1. **Which code was used for each system** (ERBA 303 vs ERLA 301)
2. **Definition of each code** from data_dictionary
3. **Breakdown by status code within each risk category**
4. **Year-by-year breakdown**

#### Example 2: "Berapa jumlah izin edar dengan risiko menengah rendah?" (With risk filter)

```
## Total NIE Risiko Menengah Rendah

### Ringkasan
| Sistem | Kode yang Digunakan | Definisi | Total |
|--------|---------------------|----------|-------|
| ERBA   | kategori_dokumen = '303' | Menengah Rendah | 41.516 |
| ERLA   | jenis_dokumen = '301' | Low Risk (≈ Menengah Rendah) | 77.894 |
| **Total** | | | **119.410** |

### Detail per Sistem, Tahun, dan Status

|        | ERBA (kategori_dokumen = '303')                    | ERLA (jenis_dokumen = '301')                    |        |
|        | Status 0999 | Status 0906 | Status 9999 | Status 0099 | Status 0999 | Status 0906 | Total  |
|--------|-------------|-------------|-------------|-------------|-------------|-------------|--------|
| 2012   | -           | -           | -           | 500         | -           | -           | 500    |
| 2013   | -           | -           | -           | 5.000       | -           | -           | 5.000  |
| 2014   | -           | -           | -           | 4.800       | -           | -           | 4.800  |
| 2015   | -           | -           | -           | 4.500       | -           | -           | 4.500  |
| 2016   | -           | -           | -           | 5.200       | -           | -           | 5.200  |
| 2017   | -           | -           | -           | 5.800       | -           | -           | 5.800  |
| 2018   | -           | -           | -           | 7.000       | -           | -           | 7.000  |
| 2019   | -           | -           | -           | 6.500       | -           | -           | 6.500  |
| 2020   | -           | -           | -           | 5.500       | -           | -           | 5.500  |
| 2021   | -           | -           | -           | 6.800       | -           | -           | 6.800  |
| 2022   | 2.000       | 300         | 200         | 8.000       | 1.500       | 500         | 12.500 |
| 2023   | 12.000      | 1.500       | 1.500       | -           | -           | -           | 15.000 |
| 2024   | 13.000      | 1.500       | 1.500       | -           | -           | -           | 16.000 |
| 2025   | 6.500       | 800         | 716         | -           | -           | -           | 8.016  |
| Total  | 33.500      | 4.100       | 3.916       | 68.300      | 1.500       | 500         | 119.410|

### Mapping Kode Risiko antar Sistem

| Konsep | ERBA (kategori_dokumen) | ERLA (jenis_dokumen) | Catatan |
|--------|-------------------------|----------------------|---------|
| Risiko Tinggi | 301 | 302 | Mapping 1:1 |
| Menengah Tinggi | 302 | 303 | ERLA 303 = gabungan MT+MR, bukan MT saja |
| Menengah Rendah | 303 | 301 | Mapping 1:1 |
| Tinggi Notifikasi | 304 | - | Tidak ada di ERLA |

### Keterangan Filter
- ERBA: kategori_dokumen = '303' AND status IN ('0999', '0906', '9999') AND trader_id::bigint NOT IN (5, 17, 50, 85)
- ERLA: jenis_dokumen = '301' AND status IN ('0099', '0999', '0906', '9999') AND trader_id != 3384

### Catatan Penting
- ERLA tidak bisa memisahkan Menengah Tinggi dari Menengah Rendah (kode '303' = gabungan)
- Untuk query MT spesifik, gunakan ERBA-only karena ERLA tidak punya kode terpisah
- ERLA '301' (Low Risk) ≈ ERBA '303' (Menengah Rendah), tapi tidak identik 100%
```

### 10.4 Required Output Format: Time-Specific Query

When user specifies a time range (e.g., "2 tahun terakhir"), the output must show:

1. **Only the requested time range**
2. **Breakdown by system (ERBA, ERLA)**
3. **Breakdown by status code**
4. **Mark "-" when data does not exist**

#### Example 3: "Berapa data dalam 2 tahun terakhir?" (Time-specific)

```
## Data 2 Tahun Terakhir (2024-2025)

### Detail per Sistem, Tahun, dan Status

|        | ERBA                                    | ERLA                                    |        |
|        | Status 0999 | Status 0906 | Status 9999 | Status 0099 | Status 0999 | Status 0906 | Total  |
|--------|-------------|-------------|-------------|-------------|-------------|-------------|--------|
| 2024   | 50.000      | 5.000       | 6.284       | -           | -           | -           | 61.284 |
| 2025   | 20.000      | 3.000       | 4.282       | -           | -           | -           | 27.282 |
| Total  | 70.000      | 8.000       | 10.566      | -           | -           | -           | 88.566 |

### Keterangan
- ERLA tidak memiliki data 2024-2025 (sistem sudah digantikan oleh ERBA)
- ERBA adalah sistem utama untuk data 2023 ke atas
- Data 2025 adalah data berjalan (year-to-date)

### Breakdown per Kategori Risiko (2024-2025)
| Risiko | Kode ERBA | 2024 | 2025 | Total |
|--------|-----------|------|------|-------|
| Tinggi | 301 | 25.000 | 10.000 | 35.000 |
| Menengah Tinggi | 302 | 8.000 | 3.500 | 11.500 |
| Menengah Rendah | 303 | 20.000 | 10.000 | 30.000 |
| Tinggi Notifikasi | 304 | 8.284 | 3.782 | 12.066 |
| **Total** | | **61.284** | **27.282** | **88.566** |
```

### 10.5 Implementation Rules for SKILL.md

The following rules must be added to `seeknal/skills/bpom-analyst/SKILL.md`:

```markdown
## Output Transparency Rules (MANDATORY for all data questions)

### Rule 1: Matrix Format with Code Detail
Every COUNT query must produce output in matrix format:
- X-axis: System (ERBA, ERLA) → Status Code (or other relevant codes)
- Y-axis: Years (or months) present in database
- Each cell: Count for that system + code + year

### Rule 2: Always Show All Systems
When user does not specify system:
- Show ERBA column
- Show ERLA column
- Show Total column
- Mark "-" when data does not exist for a system

### Rule 3: Always Show All Years
When user does not specify time range:
- Show ALL years present in database
- Show year-by-year breakdown
- Show total at bottom
- Mark "-" when data does not exist for a year

### Rule 4: Always Show Code Detail
When query uses code filter:
- Show which code was used for each system
- Show definition from data_dictionary
- Show breakdown by status code (or other relevant codes)
- Show mapping between ERBA and ERLA codes

### Rule 5: Always Show Filter Details
Every query must show:
- Status filter applied (0999, 0906, 9999, etc.)
- jenis_permohonan filter (if applied)
- Test exclusion (trader_id, etc.)
- Any other filter applied

### Rule 6: Mark Missing Data Explicitly
When data does not exist:
- Use "-" (not 0, not empty)
- Add explanation in Keterangan section
- Example: "ERLA tidak memiliki data 2024-2025"

### Rule 7: Provide Context for Each Number
Every number must have:
- Source (which table, which system)
- Filter applied (which codes, which status)
- Time period (which year, which month)
- Definition (what the code means)
```

### 10.6 Comparison: Current vs Expected Output

**CURRENT OUTPUT (Insufficient):**
```
Berdasarkan data registrasi pangan olahan BPOM, jumlah izin edar dengan 
risiko Menengah Rendah adalah 119.410.

Rincian:
- ERBA: 41.516 (kategori_dokumen = '303')
- ERLA: 77.894 (jenis_dokumen = '301')
```

**EXPECTED OUTPUT (Transparent):**
```
[Matrix format with full detail as shown in sections 10.2-10.4 above]
```

**Why the current output is insufficient:**
- User cannot verify where 41.516 comes from
- User cannot see year-by-year breakdown
- User cannot see status code breakdown
- User cannot verify filter details
- User cannot see per-system coverage

**Why the expected output is sufficient:**
- User can verify every number in the matrix
- User can see which years have data
- User can see which status codes contribute
- User can see which filters were applied
- User can see per-system coverage

### 10.7 The Trust Equation

**Trust = Transparency + Verifiability + Consistency**

- **Transparency**: Show every detail of how each number was derived
- **Verifiability**: Allow user to trace each number back to its source
- **Consistency**: Same question always produces same format

When the system shows:
```
Total = 119.410
├── ERBA = 41.516
│   ├── Status 0999 = 33.500
│   ├── Status 0906 = 4.100
│   └── Status 9999 = 3.916
└── ERLA = 77.894
    ├── Status 0099 = 68.300
    ├── Status 0999 = 8.000
    └── Status 0906 = 1.594
```

...then user can verify: 33.500 + 4.100 + 3.916 = 41.516 ✓ and 68.300 + 8.000 + 1.594 = 77.894 ✓

This is what makes the answer **trustworthy** — not because the system says "trust me", but because the system shows **every detail**.

---

## Appendix A: Verified Database Ground Truth

All numbers below verified via direct `psql` queries on June 17, 2026 against `rpo_v2`.

| Metric | Correct Value | System's Value | Delta |
|---|---|---|---|
| NIE MT all-time (ERBA only) | 11,923 | 95,736 | +703% |
| NIE MR all-time (ERBA only) | ~119,314 | — | — |
| NIE ERBA 2025 (all jenis_permohonan) | 53,535 | 53,844 (best session) | −0.6% |
| NIE ERBA 2025 (baru only) | ~45,147 | 45,247 | −0.2% |
| NIE Garam Beryodium ERBA 2023 | 198 (`jenis_pangan='1204'`) | 189 | −4.5% |
| NIE BTP ERBA 2023 | 950 | 950 | 0% ✓ |
| NIE AMDK ERBA 2024 (all) | 2,301 | 2,208 (baru only) | −4.0% |
| NIE AMDK 2023 (ERBA+ERLA) | ~1,843 | 1,843 | 0% ✓ |
| MR Dibatalkan (status_komitmen='5') | 5,146 | 254 | −95.1% |
| Produk MD ERBA 2025 (all) | 36,706 | 30,760 (baru only) | −16.2% |
| Formula Bayi berlaku (strict 1301) | ~148 | 267 (broad 1301+1302) | +80% |
| Total NIE Mei 2026 (ERBA produk+BTP) | 5,193 | 3,880 | −25.3% |
| Permohonan ERLA all-time | 402,925 | 400,784 | −0.5% |
| ERLA jenis_dokumen='303' nomor count | 83,857 (medium risk all) | Treated as MT only | — |

---

## Appendix B: SQL Bug Reference

| Bug | SQL Pattern Used | Correct Pattern |
|---|---|---|
| ERLA MT inflated | `WHERE jenis_dokumen = '303'` | Not comparable to ERBA MT; state limitation |
| Garam Beryodium undercount | `WHERE kategori_pangan = '120101000001'` | `WHERE jenis_pangan = '1204'` |
| MR Dibatalkan over-filtered | `WHERE status IN ('0999',...) AND status_komitmen='5'` | `WHERE status_komitmen LIKE '5%'` (no status filter) |
| New NIE only / all active NIE | `AND jenis_permohonan IN ('301','305')` | Remove for "total active NIE" queries |
| BTP non-determinism | Included in some sessions, not others | Explicit: exclude unless user requests |
| ERLA missing from 2026 | Only ERBA queried | Always UNION ERBA + ERLA |

---

*Report generated from UAT session data (June 15, 2026) and live database verification (June 17, 2026). All SQL evidence is reproducible against the `rpo_v2` database.*
