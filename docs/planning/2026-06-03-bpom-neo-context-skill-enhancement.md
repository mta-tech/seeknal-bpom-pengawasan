# seeknal-bpom-neo: Context, Skill & Architecture Enhancement Plan

**Document type:** Implementation Plan  
**Project:** seeknal-bpom-neo (BPOM RPO Analytics Agent)  
**Status:** Pending Implementation  
**Date:** 2026-06-03  
**Scope:** SEEKNAL_ASK.md · context/*.md · seeknal/skills/*.md  

---

## 1. Background

This plan documents all findings from a comprehensive audit of the seeknal-bpom-neo
agent system, conducted June 2026. The audit covered:

- Direct database queries against production (`rpo_v2` via SSH tunnel)
- Review of all context files (`context/*.md`)
- Review of all skill files (`seeknal/skills/*/SKILL.md`)
- Analysis of 13 multiturn and 61 singleturn test cases
- Two real agent output samples showing inconsistent entity resolution

The audit identified 11 distinct problems causing agent inconsistency, incorrect
SQL, and misleading answers. This document specifies every change required to
resolve them, the file it targets, the reason it is needed, and the expected
outcome after the fix is applied.

---

## 2. Current State

### 2.1 Database State (Production — June 2026)

| Table | Rows | `tanggal` type | `trader_id` type | Date range |
|---|---|---|---|---|
| `t_produk_3_erba` | 245,049 | **TEXT** | **TEXT** | Sep 2022 → Jun 2026 |
| `t_produk_3_rilis_erla` | 412,607 | TIMESTAMP | BIGINT | 2012 → Jun 2026 |
| `t_btp_3_erba` | 6,696 | TEXT | TEXT | 2023 → Jun 2026 |
| `t_btp_3_erla` | 9,782 | TIMESTAMP | BIGINT | 2018 → 2024 |
| `m_trader_rba` | 14,642 | — | — | — |
| `m_trader_rla` | 10,284 | — | — | — |
| `data_dictionary` | 1,141 | — | — | 21 categories |
| `forecast_permohonan` | 111 | — | — | Feb 2022 → Apr 2031 (51 actual + 60 predicted) |

**Key facts confirmed from direct database queries:**

- ERBA stores ALL columns as TEXT — `tanggal`, `tanggal_bayar`, `trader_id`, `status_komitmen`, etc.
- ERLA stores `tanggal`/`tanggal_bayar` as TIMESTAMP, `trader_id` as BIGINT
- ERBA and ERLA `nomor` values do NOT overlap — UNION ALL is safe; COUNT DISTINCT is accurate
- 55,528 ERBA rows (22.7%) have `tanggal = NULL` — products still in evaluation, no NIE issued
- `status_komitmen` in ERBA has mixed format: both `'5'` and `'5.0'` exist in the same column
- ERBA/ERLA handover happened in 2022–2023; both systems were active in that period
- NIE ERBA 2023 valid = 30,230 (test oracle 30,276 — delta 46, essentially valid)
- Permohonan ERBA 2023 = 42,329 (test oracle exact match)

### 2.2 ERBA Data Distribution

**kategori_dokumen (risk):**

| Code | Label | Count | % |
|---|---|---|---|
| 301 | Risiko Tinggi | 154,381 | 63.0% |
| 303 | Risiko Menengah Rendah | 63,089 | 25.7% |
| 302 | Risiko Menengah Tinggi | 18,612 | 7.6% |
| 304 | Risiko Tinggi Notifikasi | 7,809 | 3.2% |

**status_komitmen for MR rows (kategori_dokumen = '303'):**

| Code | Label | Count | % |
|---|---|---|---|
| 0 | Draft Pemenuhan Komitmen | 27,806 | 44.1% |
| 7 | Komitmen Disetujui Dengan Catatan | 11,561 | 18.3% |
| 1 | Proses Penilaian Kembali | 9,287 | 14.7% |
| 5 | Komitmen Dibatalkan | 4,952 | 7.8% |
| 4 | Komitmen Disetujui | 2,732 | 4.3% |

### 2.3 Risk Code Mapping — Critical Cross-System Difference

| User intent | ERBA column | ERBA code | ERLA column | ERLA code |
|---|---|---|---|---|
| Risiko Tinggi (T) | `kategori_dokumen` | `301`, `304` | `jenis_dokumen` | `302` |
| Risiko Menengah Tinggi (MT) | `kategori_dokumen` | `302` | `jenis_dokumen` | `303` |
| Risiko Menengah Rendah (MR) | `kategori_dokumen` | `303` | `jenis_dokumen` | `301` |

> ERBA `301` = Tinggi. ERLA `301` = Low Risk (MR equivalent). Same code, opposite meaning.

### 2.4 AMDK Product Codes

| System | Filter |
|---|---|
| ERBA | `jenis_pangan = '1401'` |
| ERLA | `jenis_pangan IN ('651', '652', '655')` |

AMDK handover mirrors the system handover: pre-2023 AMDK data is in ERLA
(codes 651/652/655), 2023+ AMDK data is in ERBA (code 1401).

### 2.5 Current Architecture State

```
SEEKNAL_ASK.md
  → injected at session start (always loaded)
  → references: skill bpom-analyst, skill evidence-auditor
  → contains: workflow, metric routing, data architecture, filters, guardrails
  → problem: too large; contains knowledge that belongs in context files

seeknal/skills/bpom-analyst/SKILL.md
  → loaded when agent calls the skill
  → contains: CAPTURE → PLAN → EXECUTE → REFLECT → GENERATE
  → problem: no mandatory context loading step; no RESOLVE phase

seeknal/skills/evidence-auditor/SKILL.md
  → loaded at REFLECT phase
  → contains: audit checklist (scope, filters, consistency, honesty)
  → problem: no data availability check (0 rows ≠ no data)

seeknal/skills/database-analyst/SKILL.md
  → generic analyst skill; loads context explicitly
  → contains: step 1 "load business context first — this step is not optional"
  → status: correct pattern; should be adopted by bpom-analyst

context/*.md
  → domain knowledge files
  → problem: loaded inconsistently; agent often skips because SEEKNAL_ASK.md
             already contains enough to proceed
```

---

## 3. Problems Identified

### P01 — "Registrasi" Resolves to Different Entities Across Sessions

**Symptom:** Two nearly identical questions produce different metrics.

- "Bagaimana tren registrasi AMDK" → Permohonan (correct per glossary)
- "Bagaimana tren registrasi AMDK setiap tahun?" → NIE (wrong — different entity)

**Root cause:** The word "registrasi" is non-deterministic in the current context.
Adding "setiap tahun" changed the agent's entity interpretation. The business
glossary defines the difference correctly, but there is no enforcement rule that
prevents the mapping from being overridden by adjacent keywords.

**Files to change:** `SEEKNAL_ASK.md`

---

### P02 — ERBA TEXT Columns Cause UNION Query Runtime Errors

**Symptom:** UNION queries between ERBA and ERLA fail with:
`UNION types text and timestamp cannot be matched`

**Root cause:** ERBA stores `tanggal`, `tanggal_bayar`, and `trader_id` as TEXT.
ERLA stores them as TIMESTAMP and BIGINT. No context file documents this
difference. Agent writes UNION queries without explicit cast and they fail.

**Files to change:** `context/data_quality_rules.md`

---

### P03 — status_komitmen Float/Integer Mix Causes Undercounting

**Symptom:** Commitment cancellation queries return fewer results than the
database actually contains for that filter.

**Root cause:** ERBA stores `status_komitmen` as TEXT with inconsistent
formatting. Some rows contain `'5'`, others contain `'5.0'`. A filter
`status_komitmen = '5'` silently misses all `'5.0'` rows. Confirmed in
production: `'0.0'`, `'1.0'`, `'4.0'`, `'5.0'` variants all exist.

**Files to change:** `context/data_quality_rules.md`

---

### P04 — AMDK Code Only Documented for ERLA; ERBA Code Missing

**Symptom:** AMDK queries for 2023 onwards return 0 rows when using only ERLA codes.

**Root cause:** Context only documents ERLA codes (651/652/655). ERBA uses a
different code (1401). Since ERBA is the primary system for 2023+ data, any
AMDK query without the ERBA code is silently incomplete for recent years.

**Files to change:** `SEEKNAL_ASK.md`, `context/business_glossary.md`

---

### P05 — "Tren" Keyword Does Not Reliably Trigger GROUP BY Year

**Symptom:** "Tren registrasi AMDK" sometimes returns a total-only count.
"Tren per daerah" sometimes returns a ranked list of daerah with no year
breakdown — the agent drops the time dimension.

**Root cause:** The rule "tren = GROUP BY year" exists as narrative prose in
`intent_mapping.md`. It is not enforced as a deterministic pre-SQL rule.
For multi-dimension questions (tren × daerah), the agent drops one dimension
instead of producing a single 2D GROUP BY query.

**Files to change:** `SEEKNAL_ASK.md`, `context/intent_mapping.md`

---

### P06 — Data State in Context Files Is Outdated

**Symptom:** Context references ERBA as a new system that may be empty. The
agent occasionally skips ERBA or warns users about ERBA data availability.

**Root cause:** ERBA was empty during an earlier period of the project. It is
now populated with 245,049 rows (Sep 2022 → Jun 2026) and is the primary system
for recent product registrations. Three files still carry the old state.

**Files to change:** `SEEKNAL_ASK.md`, `context/data_architecture.md`,
`context/business_glossary.md`

---

### P07 — Risk Code Inversion Between Systems Not Flagged as Danger

**Symptom:** Cross-system risk queries silently produce wrong risk attribution.
ERBA code `301` means Tinggi; ERLA code `301` means Low Risk (MR equivalent).
Applying the same filter to both in a UNION mixes risk levels.

**Root cause:** The inversion is mentioned in `business_glossary.md` but is not
formatted as a prominent warning. The agent may apply the same risk code to both
systems in a UNION, producing incorrect results without any visible error.

**Files to change:** `context/business_glossary.md`, `context/intent_mapping.md`

---

### P08 — bpom-analyst Skill Has No RESOLVE Phase and No Mandatory Context Load

**Symptom:** Agent jumps from CAPTURE directly to writing SQL without first
resolving all unknown terms to concrete constructs. This produces AMDK queries
via text search (`nama ILIKE '%air minum%'`), queries without required casts,
and queries where the wrong column or code is used.

**Root cause:** The bpom-analyst workflow is `CAPTURE → PLAN → EXECUTE →
REFLECT → GENERATE`. There is no mandatory step to resolve unknown terms before
SQL, and no enforced context file loading. In contrast, `database-analyst/SKILL.md`
mandates: "Load business context first — this step is not optional."

**Files to change:** `seeknal/skills/bpom-analyst/SKILL.md`

---

### P09 — Evidence Auditor Does Not Check Data Availability

**Symptom:** Agent declares "data tidak tersedia" (data not available) when a
query returns 0 rows, without verifying whether a filter error caused the
empty result rather than genuine absence of data.

**Root cause:** `evidence-auditor/SKILL.md` checks scope match, mandatory
filters, consistency, and honesty — but has no checklist item for verifying
that the queried table contains data and that 0 rows is not caused by a missing
cast or wrong filter before concluding unavailability.

**Files to change:** `seeknal/skills/evidence-auditor/SKILL.md`

---

### P10 — Test Oracle Values Need Verification Against Current DB State

**Symptom:** Test cases reference values written against an earlier database
state (e.g., "NIE ERBA 2023 = 30,276"). After ERBA was populated, these values
require verification.

**Audit finding:** NIE ERBA 2023 actual = 30,230 (delta 46 from oracle — within
acceptable range). Permohonan ERBA 2023 actual = 42,329 (exact oracle match).
Test cases are substantially valid. The delta of 46 in NIE is likely a minor
difference in cast handling of `trader_id` for the NOT IN filter.

**Files to change:** `seeknal/tests/v1/` (verification run only, not rewrite)

---

### P11 — SEEKNAL_ASK.md as Knowledge Monolith Causes Context Files to Be Skipped

**Symptom:** The agent consistently proceeds without opening context files
(`data_architecture.md`, `code_resolution.md`, etc.), missing details that
only exist there: daerah code conversion formula, ERBA cast rules, BTP-specific
filters, risk code inversion warning.

**Root cause:** SEEKNAL_ASK.md contains enough information for the agent to
form a plan and write SQL without opening any other file. The bpom-analyst
workflow does not mandate specific file loading before each phase. Context
files become decorative rather than authoritative references.

**Solution approach:** Redesign SEEKNAL_ASK.md as a thin process guide with
behavioral contracts and a pointer table (information taxonomy). Move all
domain knowledge detail into context files. Redesign bpom-analyst SKILL.md
to explicitly mandate context loading before SQL — mirroring the database-analyst
pattern which already works correctly.

**Files to change:** `SEEKNAL_ASK.md`, `seeknal/skills/bpom-analyst/SKILL.md`

---

## 4. Changes Per File

### 4.1 `SEEKNAL_ASK.md` — Refactor to Thin Process Guide

**Solves:** P01, P04, P05, P06, P11

**Why:** Currently a knowledge monolith (workflow + codes + rules + mapping all
in one file). Agent uses it as the single source of truth and skips context
files because SEEKNAL_ASK.md already has enough to proceed.

**What is removed (moved to context files):**

- Detailed mandatory filter checklist → stays in `data_quality_rules.md`
- Detailed metric routing table (NIE vs Permohonan columns) → stays in `intent_mapping.md`
- ERBA/ERLA detailed comparison → stays in `business_glossary.md`

**What is kept:**

- Instruction to use skill `bpom-analyst` (skill routing)
- Instruction to use `evidence-auditor` at REFLECT phase
- Behavioral contracts (must be active before any skill loads)
- Guardrails (honesty, anti-hallucination, test oracle prohibition)

**What is added:**

```markdown
## BEHAVIORAL CONTRACTS (active from session start — no exceptions)

| User word | Always resolves to | Never changes because of |
|---|---|---|
| registrasi, pengajuan, daftar | PERMOHONAN — COUNT(DISTINCT produk_id), tanggal_bayar | other keywords in the sentence |
| izin edar, NIE, terbit, diterbitkan | NIE — COUNT(DISTINCT nomor), tanggal | other keywords |
| tren, per tahun, setiap tahun, perkembangan | GROUP BY date_trunc('year', col) | adding a second dimension |
| tren per [dimension] | GROUP BY year, dimension — ONE query | — |
| no year stated | ALL-TIME: range 2000–2030 + GROUP BY year | — |

## CRITICAL DATA STATE (June 2026)

| Table | Rows | Column types | Date range |
|---|---|---|---|
| t_produk_3_erba | 245,049 | ALL TEXT — cast required | Sep 2022 → now |
| t_produk_3_rilis_erla | 412,607 | TIMESTAMP / BIGINT | 2012 → now |

ERBA mandatory casts: tanggal::timestamp · tanggal_bayar::timestamp · trader_id::bigint
status_komitmen normalization: ROUND(status_komitmen::numeric)::int::text
ERBA is the primary system for 2023+ registrations. ERLA covers 2012–2022.
UNION ERBA + ERLA for ALL-TIME queries. Nomor values do not overlap.

## PRODUCT SEGMENT CODES (both systems)

| Segment | ERBA | ERLA |
|---|---|---|
| AMDK | jenis_pangan = '1401' | jenis_pangan IN ('651','652','655') |
| Garam Beryodium | kategori_pangan = '120101000001' | kategori_pangan = '12010103' |
| BTP | table t_btp_3_erba | table t_btp_3_erla |
| Makloon | status_produk = '304' (ERBA only) | — |

Unknown segment: query nama_kategori (see business_glossary.md §Product Segment Codes)

## INFORMATION TAXONOMY (load the file that contains the type of information needed)

| When agent needs to know... | Load this file |
|---|---|
| Concept definition (NIE, permohonan, ERBA, UMKM, commitment) | context/business_glossary.md |
| Which table / column / relationship | context/data_architecture.md |
| What a code value means | context/code_resolution.md + data_dictionary SQL |
| Which filters are mandatory / ERBA cast rules | context/data_quality_rules.md |
| Product segment code not in SEEKNAL_ASK.md | context/business_glossary.md §Product Segment Codes |
| SQL structure or query pattern | context/query_recipes.md |
| Forecast / prediction data | context/forecast_guide.md |
| Word → entity / dimension / operation mapping | context/intent_mapping.md |

RULE: Load the relevant file before writing SQL. Do not proceed on memory alone.
```

**New file structure:**

```
§0  Mandatory: use skill bpom-analyst
§1  Behavioral Contracts
§2  Critical Data State
§3  Product Segment Codes
§4  Information Taxonomy
§5  Guardrails
```

**Expected outcome:**

- File becomes ~60% shorter
- Agent opens context files because SEEKNAL_ASK.md no longer contains full detail
- Behavioral contracts enforced from session start before any skill is called
- AMDK queries always include both ERBA and ERLA codes

---

### 4.2 `context/data_quality_rules.md` — Add ERBA Cast Rules + status_komitmen Normalization

**Solves:** P02, P03

**Why:** Every UNION query touching ERBA fails without a cast. The undercounting
in commitment queries is silently wrong without normalization.

**What to add:**

```markdown
## ERBA Schema: All Columns Are TEXT — Mandatory Cast

ERBA stores all critical columns as TEXT. Always apply explicit cast for ERBA:

| Column | Cast required | Usage example |
|---|---|---|
| tanggal | ::timestamp | tanggal::timestamp >= '2022-01-01' |
| tanggal_bayar | ::timestamp | tanggal_bayar::timestamp |
| trader_id | ::bigint | trader_id::bigint NOT IN (5,17,50,85) |
| status_komitmen | see normalization below | — |

UNION ERBA + ERLA — always cast on the ERBA side:

  SELECT nomor, tanggal::timestamp AS tanggal, trader_id::bigint AS trader_id
  FROM warehouse.public.t_produk_3_erba
  WHERE tanggal IS NOT NULL AND tanggal != ''
    AND status IN ('0999','0906','9999')
    AND jenis_permohonan IN ('301','305')
    AND trader_id::bigint NOT IN (5,17,50,85)
    AND tanggal::timestamp >= '{Y}-01-01' AND tanggal::timestamp < '{Y+1}-01-01'

  UNION ALL

  SELECT nomor, tanggal, trader_id
  FROM warehouse.public.t_produk_3_rilis_erla
  WHERE status IN ('0099','0999','0906','9999')
    AND jenis_permohonan IN ('301','304','305')
    AND trader_id != 3384
    AND tanggal >= '{Y}-01-01' AND tanggal < '{Y+1}-01-01'

## status_komitmen: Float/Integer Normalization

ERBA status_komitmen is TEXT with inconsistent formatting.
Both '5' and '5.0' exist in the same column for the same logical value.

NEVER:  WHERE status_komitmen = '5'
        — silently misses '5.0' rows

ALWAYS: WHERE ROUND(status_komitmen::numeric)::int::text = '5'
     OR: WHERE status_komitmen LIKE '5%'   — simpler alternative

Apply this normalization for ALL status_komitmen filters.

## NULL tanggal in ERBA (22.7% of rows)

55,528 ERBA rows have tanggal = NULL or tanggal = ''.
These are products still in evaluation (no NIE has been issued yet).
Date range filters exclude them automatically (NULL::timestamp fails the comparison).
For safety in GROUP BY queries: add WHERE tanggal IS NOT NULL AND tanggal != ''
```

**Expected outcome:**

- UNION ERBA+ERLA runs without type errors
- Commitment queries correctly count all cancelled MR rows including `'5.0'` variants
- Agent has a ready-to-use UNION template with correct casts

---

### 4.3 `context/data_architecture.md` — Update Table Inventory + Add Type Warning

**Solves:** P06

**Why:** Current doc presents ERBA as potentially secondary or empty. It is
now the primary system for 2023+ data.

**What to update/add:**

```markdown
## Table Inventory (June 2026)

| Table | Rows | Date range | Risk column | Commitment |
|---|---|---|---|---|
| t_produk_3_erba | 245,049 | Sep 2022 → now | kategori_dokumen | status_komitmen |
| t_produk_3_rilis_erla | 412,607 | 2012 → now | jenis_dokumen | ✗ not available |
| t_btp_3_erba | 6,696 | 2023 → now | — | — |
| t_btp_3_erla | 9,782 | 2018 → 2024 | — | — |
| m_trader_rba | 14,642 | — | — | — |
| m_trader_rla | 10,284 | — | — | — |

System handover: 2022–2023 (both systems active; use UNION for that period).
ERBA is the primary system for 2023+ product registrations.
ERLA covers historical data 2012–2022.
For ALL-TIME queries: UNION ERBA + ERLA.
nomor values do NOT overlap between systems — UNION ALL + COUNT(DISTINCT nomor) is accurate.

## ERBA Column Type Difference (see data_quality_rules.md for cast rules)

ERBA (t_produk_3_erba): ALL columns are stored as TEXT
ERLA (t_produk_3_rilis_erla): tanggal = TIMESTAMP, trader_id = BIGINT

ERBA UNION queries will fail without explicit cast.
55,528 ERBA rows have tanggal = NULL (products still in evaluation).
```

**Expected outcome:**

- Agent no longer warns about ERBA availability
- Agent always includes ERBA in queries for 2023+ scope
- Queries correctly cast ERBA columns before UNION

---

### 4.4 `context/business_glossary.md` — Update ERBA/ERLA Comparison + Risk Warning + Segment Codes

**Solves:** P04, P06, P07

**Why:** Outdated ERBA state, missing ERBA AMDK code, and the risk code
inversion is not prominently flagged as a dangerous pitfall.

**What to update — ERBA/ERLA comparison table:**

```markdown
## ERBA / ERLA System Comparison (June 2026)

| Aspect | ERBA | ERLA |
|---|---|---|
| Rows | 245,049 | 412,607 |
| Date range | Sep 2022 → now | 2012 → now |
| Column types | ALL TEXT | TIMESTAMP / BIGINT |
| Risk column | kategori_dokumen | jenis_dokumen |
| Commitment | status_komitmen ✓ | ✗ not available |
| Valid NIE status | 0999, 0906, 9999 | 0099, 0999, 0906, 9999 |
| NIE jenis_permohonan | 301, 305 | 301, 304, 305 |
| Test account exclude | trader_id::bigint NOT IN (5,17,50,85) | trader_id != 3384 |
```

**What to add — risk code inversion warning:**

```markdown
## ⚠️ RISK CODE INVERSION WARNING

ERBA and ERLA use DIFFERENT columns AND DIFFERENT codes for risk level.
The same code number has OPPOSITE meaning in the two systems.

| Risk level | ERBA: kategori_dokumen | ERLA: jenis_dokumen |
|---|---|---|
| Risiko Tinggi (T) | '301', '304' | '302' |
| Risiko Menengah Tinggi (MT) | '302' | '303' |
| Risiko Menengah Rendah (MR) | '303' | '301' |

ERBA code '301' = Tinggi (high risk).
ERLA code '301' = Low Risk (MR equivalent).
NEVER apply the same risk code filter to both tables in a UNION.

For combined risk queries, write separate WHERE per UNION side:

  -- Risiko Tinggi (combined ERBA + ERLA):
  FROM t_produk_3_erba WHERE kategori_dokumen IN ('301','304')
  UNION ALL
  FROM t_produk_3_rilis_erla WHERE jenis_dokumen = '302'

  -- Risiko MR (combined):
  FROM t_produk_3_erba WHERE kategori_dokumen = '303'
  UNION ALL
  FROM t_produk_3_rilis_erla WHERE jenis_dokumen = '301'
```

**What to add — product segment codes:**

```markdown
## Product Segment Codes (ERBA and ERLA codes differ)

| Segment | ERBA filter | ERLA filter |
|---|---|---|
| AMDK | `jenis_pangan = '1401'` | `jenis_pangan IN ('651','652','655')` |
| Garam Beryodium | `kategori_pangan = '120101000001'` | `kategori_pangan = '12010103'` |
| BTP / food additives | table `t_btp_3_erba` | table `t_btp_3_erla` |
| Makloon (contract mfg.) | `status_produk = '304'`, use `produsen_*` columns | ERBA only |

For segments NOT listed above, discover via `nama_kategori`:

  SELECT DISTINCT jenis_pangan, nama_kategori, COUNT(*) AS cnt
  FROM warehouse.public.[table]
  WHERE nama_kategori ILIKE '%<keyword>%'
  GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10

Then confirm with a sample:
  SELECT DISTINCT nama FROM warehouse.public.[table]
  WHERE jenis_pangan = '<code>' LIMIT 5

Use `nama_kategori` (standardized category label) for discovery, NOT `nama`
(product name, inconsistent and noisy).
```

**Expected outcome:**

- Agent always uses correct AMDK code per system — no more 0 rows for 2023+
- Agent never applies the same risk code filter to both ERBA and ERLA
- Unknown product segments discoverable via `nama_kategori` without hardcoded lookup

---

### 4.5 `context/intent_mapping.md` — Add Segment Resolution Step + Deterministic Tren Rule

**Solves:** P05, P07

**Why:** Segment resolution is not a distinct step — it is buried after entity
resolution. The "tren = GROUP BY year" rule exists as prose but is not
deterministic enough to prevent the agent from dropping the time dimension.

**What to add — Step 0.5 (before entity resolution):**

```markdown
## Step 0.5 — Product Segment Resolution

If the user mentions a specific product type (AMDK, susu, garam, BTP, dll.):

1. Check `context/business_glossary.md` §Product Segment Codes first
2. If listed: use the `jenis_pangan` filter for each system (they differ)
3. If not listed: run discovery query using `nama_kategori` (see glossary)
4. NEVER use `nama ILIKE '%keyword%'` as the primary segment filter
   — `nama` is product-level and inconsistent; `nama_kategori` is standardized
```

**What to add — deterministic tren rule:**

```markdown
## Time Dimension: Deterministic Rules (no exceptions)

| Keyword present | SQL shape — always |
|---|---|
| tren, per tahun, setiap tahun, perkembangan | `GROUP BY date_trunc('year', col)` |
| tren per [dimension] | `GROUP BY year, dimension` — ONE query, not two |
| distribusi [A] dan [B] | `GROUP BY col_A, col_B` — ONE query |
| no year stated | range 2000–2030 + `GROUP BY year` (all-time) |

Adding "setiap tahun", "tren", or "per bulan" to a question does NOT change
the entity (NIE vs permohonan). Entity is resolved in CAPTURE and stays fixed.
Time keywords affect only the SQL shape, not the entity.
```

**Expected outcome:**

- "Tren registrasi AMDK" and "Tren registrasi AMDK setiap tahun" always produce
  identical entity resolution (Permohonan)
- "Tren per daerah" produces a single 2D query: GROUP BY year, daerah — not two
  separate queries joined manually in the answer text

---

### 4.6 `seeknal/skills/bpom-analyst/SKILL.md` — Add RESOLVE Phase + Mandatory Context Load

**Solves:** P08, P11

**Why:** This is the most fundamental change in the plan. Without a mandatory
context loading step enforced inside the skill workflow, all other improvements
are unreliable — the agent can bypass them by proceeding from SEEKNAL_ASK.md
alone. The model for this change is `database-analyst/SKILL.md` step 1, which
already works: "load business context first — this step is not optional."

**New workflow:** `CAPTURE → RESOLVE → PLAN → EXECUTE → REFLECT → GENERATE`

**What to add:**

```markdown
## PHASE 0 — MANDATORY CONTEXT LOAD (runs before CAPTURE)

Load these two files unconditionally before any other action:

  read_project_file('context/business_glossary.md')
  read_project_file('context/data_quality_rules.md')

These files contain: entity definitions, ERBA TEXT cast rules, mandatory NIE
filters, product segment codes for ERBA and ERLA, risk code inversion warning,
and status_komitmen normalization.

This step is NOT optional. Proceeding without it produces wrong SQL.

## PHASE 2 — RESOLVE (new, between CAPTURE and PLAN)

After CAPTURE, identify every piece of information still needed before SQL can
be written. For each gap, use the information taxonomy below:

  Need to understand a TERM or CONCEPT?
  → read_project_file('context/business_glossary.md')

  Need to know WHICH TABLE or COLUMN?
  → read_project_file('context/data_architecture.md')

  Need to know what a CODED VALUE means?
  → read_project_file('context/code_resolution.md')
  → execute_sql: SELECT kode, deskripsi FROM data_dictionary WHERE kategori = '...'

  Need to confirm MANDATORY FILTERS or CAST RULES?
  → re-read relevant section of context/data_quality_rules.md (loaded in Phase 0)

  Need PRODUCT SEGMENT CODE (AMDK, susu, garam, etc.)?
  → check business_glossary.md §Product Segment Codes (loaded in Phase 0)
  → if not listed: run discovery query:
      SELECT DISTINCT jenis_pangan, nama_kategori, COUNT(*) AS cnt
      FROM warehouse.public.[table]
      WHERE nama_kategori ILIKE '%<keyword>%'
      GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10
  → confirm: SELECT DISTINCT nama FROM [table] WHERE jenis_pangan = '<code>' LIMIT 5

  Need SQL STRUCTURE?
  → read_project_file('context/query_recipes.md')

  Need FORECAST data?
  → read_project_file('context/forecast_guide.md')

Write RESOLVED CONSTRUCTS before moving to PLAN (mandatory output):

  Table  : [which table(s) — both ERBA and ERLA if scope is ALL-TIME or 2023+]
  Shape  : [scalar | 1D-time | 1D-dim | 2D: year×dim]
  Segment: [jenis_pangan or kategori_pangan codes, one per system if they differ]
  Cast   : [ERBA columns needing ::timestamp or ::bigint]
  Risk   : [ERBA: kategori_dokumen codes | ERLA: jenis_dokumen codes — NOT the same]
  Filters: [every mandatory filter listed explicitly]

Never write SQL before RESOLVED CONSTRUCTS are complete.

## PHASE 4 — EXECUTE (additions to existing)

Before submitting any query:
- ERBA + ERLA UNION: confirm ERBA side has ::timestamp on tanggal/tanggal_bayar
  and ::bigint on trader_id
- Query includes status_komitmen: use ROUND(status_komitmen::numeric)::int::text
- Risk filter present: confirm ERBA uses kategori_dokumen and ERLA uses
  jenis_dokumen — they are NOT interchangeable across systems
```

**Expected outcome:**

- Agent always loads glossary and quality rules before the first SQL
- Product segment codes are resolved before SQL, not guessed
- 2D tren queries produce a single GROUP BY year, dimension query
- ERBA cast is always present in UNION queries
- Context files are always consulted — not bypassed

---

### 4.7 `seeknal/skills/evidence-auditor/SKILL.md` — Add Data Availability Check

**Solves:** P09

**Why:** Agent declares "data tidak tersedia" on 0 rows without first verifying
whether a filter error or missing cast caused the empty result rather than
genuine absence of data.

**What to add (new checklist section E):**

```markdown
### E. Data availability check (run before declaring "data is not available")

When a query returns 0 rows or an unexpectedly small count:

- [ ] Is the queried table non-empty?
      ERBA: 245,049 rows | ERLA: 412,607 rows — both have substantial data
- [ ] ERBA query: are TEXT columns cast correctly?
      tanggal::timestamp · tanggal_bayar::timestamp · trader_id::bigint
- [ ] status_komitmen filter: uses ROUND(status_komitmen::numeric)::int::text,
      NOT a plain string comparison like = '5'?
- [ ] Risk filter: correct column per system?
      ERBA uses kategori_dokumen | ERLA uses jenis_dokumen — codes differ
- [ ] Mandatory NIE filters present?
      status IN (...) AND jenis_permohonan IN (...) AND test account exclusion
- [ ] ALL-TIME query: does the UNION include both ERBA and ERLA?
- [ ] AMDK filter: uses the correct code per system?
      ERBA: jenis_pangan = '1401' | ERLA: jenis_pangan IN ('651','652','655')

If all checks pass and result is still 0: conclude data is absent for this scope.
If any check fails: fix and re-run. Do NOT declare data unavailability before
exhausting all filter checks.
```

**Expected outcome:**

- Questions like "Daerah mana yang paling sering mengalami pembatalan komitmen?"
  no longer return "0 baris, data tidak tersedia" due to a missing cast
- Agent correctly distinguishes between a filter error and genuine data absence

---

## 5. Implementation Order

Changes 1–7 can all be completed in a single session. P10 (test verification)
requires a live agent run and is a separate session.

| # | Change | File | Problems solved | Effort |
|---|---|---|---|---|
| 1 | ERBA cast rules + status_komitmen normalization | `context/data_quality_rules.md` | P02, P03 | Low |
| 2 | Behavioral contracts + data state + segment codes + taxonomy | `SEEKNAL_ASK.md` | P01, P04, P05, P06, P11 | Low |
| 3 | Risk inversion warning + segment codes + ERBA state | `context/business_glossary.md` | P04, P06, P07 | Low |
| 4 | Updated table inventory + column type note | `context/data_architecture.md` | P06 | Low |
| 5 | Segment resolution step + tren deterministic rule | `context/intent_mapping.md` | P05, P07 | Low |
| 6 | RESOLVE phase + Phase 0 mandatory load | `seeknal/skills/bpom-analyst/SKILL.md` | P08, P11 | Medium |
| 7 | Data availability checklist section E | `seeknal/skills/evidence-auditor/SKILL.md` | P09 | Low |
| 8 | Test oracle verification run | `seeknal/tests/v1/` | P10 | Medium (separate) |

---

## 6. Expected Outcomes

| Problem | Root cause | After fix | How to verify |
|---|---|---|---|
| P01 — "registrasi" ambiguity | Non-deterministic entity resolution | "registrasi" always = Permohonan regardless of adjacent keywords | Run original two samples; both must return Permohonan with identical counts |
| P02 — UNION type error | ERBA TEXT vs ERLA TIMESTAMP | UNION queries run without runtime errors | NIE all-time UNION ERBA+ERLA executes and returns ~350K NIE |
| P03 — Commitment undercount | Float/int mix in status_komitmen TEXT | Commitment filters count all rows including '5.0' variants | MR dibatalkan count increases to match expected range |
| P04 — AMDK 0 rows 2023+ | Missing ERBA AMDK code | AMDK queries include ERBA (1401) + ERLA (651/652/655) | AMDK 2023 returns ~1,743 NIE (ERBA dominant) |
| P05 — Tren without GROUP BY | Non-enforced keyword rule | Every "tren" question produces a year-breakdown table | "Tren AMDK" returns one row per year, not a total |
| P06 — Outdated ERBA state | Stale documentation | Agent treats ERBA as active primary system for 2023+ | Agent does not warn about ERBA emptiness |
| P07 — Risk code inversion | Undocumented cross-system pitfall | Agent uses different codes per system in all UNION risk queries | "NIE risiko tinggi gabungan" uses 301/304 for ERBA and 302 for ERLA |
| P08 — No RESOLVE phase | Missing workflow step | Agent resolves all constructs before first SQL | No AMDK text search; no missing casts in any query |
| P09 — False "no data" | Missing availability check | Agent re-checks filters before declaring data unavailable | Commitment + daerah + skala query runs with correct results |
| P10 — Test oracles | Earlier DB state | Oracles verified against current production DB | Test suite re-run passes at ≥88% multiturn pass rate |
| P11 — Context files skipped | SEEKNAL_ASK.md too complete | Context files consistently opened per skill workflow | Agent opens at least 2 context files per session |

---

## 7. What Is NOT Changed

The following files are out of scope — either already correct or not part of
this plan's change boundary.

| File | Reason |
|---|---|
| `context/forecast_guide.md` | Already accurate; no issues found |
| `context/query_recipes.md` | Kept as adaptive framework; RESOLVE phase makes new recipes unnecessary |
| `context/code_resolution.md` | Daerah conversion formula and dictionary pattern already correct |
| `seeknal/skills/business-question-answering/SKILL.md` | Out of scope |
| `seeknal/skills/database-analyst/SKILL.md` | Already has the correct pattern; used as model |
| `seeknal_agent.yml` | No changes needed |
| `seeknal_project.yml` | No changes needed |
| Test case questions and assertions | Content not rewritten; values verified only |

---

## 8. Design Decisions

### Need-Based Routing vs Question-Based Routing

The information taxonomy in the new SEEKNAL_ASK.md and bpom-analyst SKILL.md
uses **need-based routing**: the agent loads a file when it needs a specific
*type of information*, not when the user asked about a specific *topic*.

A question-based routing table ("user asks about AMDK → load business_glossary.md")
is still hardcoded. It fails on questions that do not match a listed pattern.
Need-based routing is general: any question generates information needs (concept
understanding, table structure, code values, filter rules), and those needs always
map to the same set of source files regardless of how the question is worded.

### Query Recipes Are Not Expanded

Adding more entries to `query_recipes.md` creates a lookup system that does not
scale. It also does not teach the agent to handle queries it has never seen. The
RESOLVE phase teaches the agent to derive correct SQL from resolved constructs
(table + shape + segment codes + casts + filters). A recipe is what the agent
*produces*, not what it *reads*. The existing recipes remain as adaptive
frameworks — not rigid templates.

### Behavioral Contracts Stay in SEEKNAL_ASK.md, Not Context Files

Behavioral contracts (registrasi = permohonan, tren = GROUP BY year) must remain
in SEEKNAL_ASK.md because they must be active from the first moment of the
session, before any skill is called or any context file is loaded. Placing them
in a context file that requires a skill to load creates a bootstrapping gap where
the agent can violate the contract before the file containing it is read.
