# UAT System Failure Analysis — June 19, 2026

**Test Date:** June 19, 2026
**Analysis Date:** June 19, 2026
**Focus:** System failure modes and root causes
**Data Source:** `seeknal-bpom-neo/seeknal/tests/outputs/2026-06-19/v1/multiturn_results_20260619_082737.json`

---

## 1. Executive Summary

**Core Finding:** The system fails not because it can't write SQL, but because it **chooses the wrong SQL to write**.

| Metric | Value |
|--------|-------|
| **Total UAT Scenarios** | 101 |
| **Passed** | 18 (17.8%) |
| **Failed** | 83 (82.2%) |
| **Failure Type: Substantive** | 77 (92.8%) |
| **Failure Type: Presentation** | 6 (7.2%) |

**Key Insight:** 92.8% of failures are **substantive wrong answers**, not string matching issues.

**Important framing:** the failure modes below are not mutually exclusive buckets. In many UAT cases,
one **primary decision failure** creates several **secondary symptoms** such as over-exploration,
scope broadening, or polished-but-wrong output. This matters because the fix should target the
decision layer first, not isolated SQL fragments.

---

## 2. System Architecture Overview

### 2.1 How the System Works

```
User Question
    ↓
[1] CAPTURE → Extract intent, entity, operation, dimension, time
    ↓
[2] RESOLVE → Fill information gaps from context/dictionary
    ↓
[3] PLAN → Design query plan
    ↓
[4] EXECUTE → Run SQL
    ↓
[5] REFLECT → Audit result
    ↓
[6] GENERATE → Present answer
```

### 2.2 Where the System Fails

| Phase | Failure Mode | Impact |
|-------|--------------|--------|
| **CAPTURE** | Misidentifies business event | High |
| **RESOLVE** | Wrong code mapping | High |
| **PLAN** | Wrong source-path selection | Critical |
| **EXECUTE** | Over-exploration | Medium |
| **REFLECT** | Validates syntax, not semantics | High |
| **GENERATE** | Wrong scope presentation | Medium |

### 2.3 What This Means Operationally

Most failing answers still reach the database and execute valid SQL. The dominant breakdown is:

1. the agent locks the wrong business interpretation,
2. then writes coherent SQL for that wrong interpretation,
3. REFLECT approves the query because the SQL itself is well-formed,
4. GENERATE presents the result confidently.

So the main UAT gap is not "SQL cannot run", but **business-semantic misrouting before SQL is
written**.

---

## 3. Failure Mode 1: Source-Path Selection Failure

### 3.1 Description

The system's most critical failure is **choosing the wrong source path** before writing SQL.

### 3.2 Evidence

| Scenario | Expected Path | Actual Path | Result |
|----------|---------------|-------------|--------|
| UAT-JP-MINOR-1 | ERBA, status=approved, jp=minor | ERBA, all statuses, jp=minor | 8x overcount |
| UAT-LC-AKTIF-1 | ERBA+ERLA, issued+valid+not expired | ERBA+ERLA, all non-expired | 70% overcount |
| UAT-BAYI-1 | ERBA(1301) + ERLA(622) | ERBA(1301) only | 10x undercount |

### 3.3 Root Cause

- Agent doesn't have a strong internal decision tree
- Agent explores multiple paths instead of committing to one
- Agent doesn't distinguish "mandatory filter" vs "optional narrowing"

### 3.4 Current vs Correct Behavior

**Current:**
```
1. Read question
2. Guess scope
3. Explore several possibilities
4. Mix technically valid results
5. Answer with confident narrative
```

**Correct:**
```
1. Read question
2. Lock intent
3. Classify concept type
4. Select single authoritative source path
5. Execute final query
6. Answer with verified result
```

---

## 4. Failure Mode 2: Concept Type Misclassification

### 4.1 Description

The system fails to correctly classify concepts into their proper types.

### 4.2 The 6 Concept Types

| Type | Description | Example | System's Error |
|------|-------------|---------|----------------|
| **A. Coded cross-system** | Codes that differ between ERBA/ERLA | risk, kemasan | Uses ERBA code for ERLA |
| **B. Direct field** | Fields that can be directly filtered | tanggal_exp, klaim | Over-explores instead of direct filter |
| **C. Master-data** | Entity attributes requiring joins | company, location | Wrong identity key |
| **D. Lifecycle/pipeline** | Status families | draft, verifikasi, evaluasi | Thinks per-code, not per-family |
| **E. Segment discovery** | Product categories needing discovery | AMDK, garam, formula bayi | Wrong scope discovery |
| **F. Business-event** | Events that determine counting logic | terbit, aktif, disetujui | Wrong event locking |

### 4.3 Evidence

| Scenario | Concept Type | Expected Behavior | Actual Behavior |
|----------|--------------|-------------------|-----------------|
| UAT-EXPIRY-2027-1 | B (Direct field) | Filter tanggal_exp directly | Over-explored to ERLA/all-time |
| UAT-KOMITMEN-DISETUJUI-1 | D (Lifecycle) | Lock exact status=4 | Collapsed to family (4+7) |
| UAT-BAYI-1 | E (Segment) | Use ERLA code 622 | Used ERBA code 1301 |
| UAT-JP-MAYOR-2025-1 | F (Business event) | Lock "disetujui" event | Applied wrong status filter |

---

## 5. Failure Mode 3: Business-Event Locking Failure

### 5.1 Description

The system fails to correctly identify and lock the business event being counted.

### 5.2 Event Ambiguity Table

| User Says | Possible Events | System's Error |
|-----------|-----------------|----------------|
| "terbit" | Issued NIE / New issuance / Any NIE | Doesn't distinguish |
| "aktif" | Currently valid / Non-expired / Not revoked | Over-includes |
| "disetujui" | Approved application / Approved commitment | Confuses entity |
| "dibatalkan" | Cancelled application / Revoked NIE | Wrong lifecycle stage |
| "dalam proses" | All in-process states / Specific stage | Doesn't know family |

### 5.3 Evidence

| Scenario | User Said | Expected Event | Actual Event | Gap |
|----------|-----------|----------------|--------------|-----|
| UAT-JP-MAYOR-2025-1 | "disetujui" | Approved major changes | All major changes | 23% overcount |
| UAT-KOMITMEN-DIBATALKAN-1 | "dibatalkan" | Cancelled commitments (Case B) | Cancelled commitments with NIE (Case A) | 95% undercount |
| UAT-LC-AKTIF-1 | "masih berlaku" | Currently active NIE | All non-expired NIE | 70% overcount |

---

## 6. Failure Mode 4: Cross-System Code Asymmetry

### 6.1 Description

The system fails to handle the fact that ERBA and ERLA use **different codes for the same concept**.

### 6.2 Known Code Asymmetries

| Concept | ERBA Code | ERLA Code | System's Error |
|---------|-----------|-----------|----------------|
| **Kemasan Plastik** | kemasan_id = 1 | kemasan_id = 31, 32, 33 | Uses 1 for both |
| **Kemasan Logam** | kemasan_id = 5 | kemasan_id = 35 | Uses 5 for both |
| **Kemasan Ganda** | kemasan_id = 7 | kemasan_id = 38 | Uses 7 for both |
| **Kemasan Komposit** | kemasan_id = 4 | kemasan_id = 34, 37 | Uses 4 for both |
| **Formula Bayi** | jenis_pangan = 1301 | jenis_pangan = 622 | Uses 1301 for both |
| **Formula Lanjutan** | jenis_pangan = 1302 | jenis_pangan = 604, 624 | Uses 1302 for both |
| **Risiko Tinggi** | kategori_dokumen = 301 | jenis_dokumen = 302 | Uses 301 for both |
| **Risiko MT** | kategori_dokumen = 302 | jenis_dokumen = 303 (gabungan!) | Treats 303 as MT only |

### 6.3 Evidence

| Scenario | Concept | Expected | Got | Root Cause |
|----------|---------|----------|-----|------------|
| UAT-BAYI-1 | Formula Bayi | 916 | 94 | ERBA code used for ERLA |
| UAT-KEMASAN-KACA-1 | Kemasan Kaca | 14,154 | ? | Wrong ERLA code |
| UAT-MT-1 | Risiko MT | ? | ? | ERLA 303 = ALL medium, not MT only |

### 6.4 Constraint on the Fix

This should **not** be fixed by hardcoding a long catalog of question-specific answers. The system
needs to learn the runtime method:

1. detect that the concept is cross-system,
2. bind code per system from the authoritative source,
3. detect when one system does not expose equivalent granularity,
4. keep the limitation visible instead of forcing a false combined number.

---

## 7. Failure Mode 5: Commitment Domain Confusion

### 7.1 Description

The system fails to correctly handle commitment-related queries.

### 7.2 The Two Cases

| Case | Description | Filter Logic | When to Use |
|------|-------------|--------------|-------------|
| **Case A** | NIE with commitment status | NIE status filter + commitment filter | "NIE yang komitmennya disetujui" |
| **Case B** | Application lifecycle outcome | Commitment filter ONLY (no NIE status) | "Permohonan yang dibatalkan" |

### 7.3 Status Code Confusion

| Status | Code | System's Error |
|--------|------|----------------|
| Draft | 0 | Sometimes includes with "dalam proses" |
| Dalam Proses | 2 | Sometimes excludes from "dalam proses" |
| Disetujui | 4 | Collapses with 7 |
| Dibatalkan | 5 | Correct |
| Disetujui Catatan | 7 | Collapses with 4 |

### 7.4 Evidence

| Scenario | Expected | Got | Root Cause |
|----------|----------|-----|------------|
| UAT-KOMITMEN-DISETUJUI-1 | 2,717 (status=4 only) | 14,322 (status=4+7) | Collapsed family |
| UAT-KOMITMEN-DIBATALKAN-1 | 5,198 (Case B) | 5,216 (Case A?) | Wrong case logic |
| UAT-DRAFT-1 | 28,720 | 17,221 | Wrong draft scope |

---

## 8. Failure Mode 6: Over-Exploration Without Stop Rule

### 8.1 Description

The system makes too many queries without improving quality.

### 8.2 Evidence

| Scenario | SQL Count | Result | Analysis |
|----------|-----------|--------|----------|
| UAT-SUSU-1 | 42 queries | PASS | Wasteful but correct |
| UAT-TOP-PERUSAHAAN-1 | 30 queries | FAIL | Over-exploration led to wrong scope |
| UAT-BTP-PEWARNA-1 | 30 queries | FAIL | Over-exploration led to wrong scope |
| UAT-KLASIFIKASI-1 | 27 queries | FAIL | Over-exploration led to wrong scope |

### 8.3 Statistics

| Scenario Type | Avg SQL Count | Avg Time |
|---------------|---------------|----------|
| **Passing** | 10.89 | 50-150 seconds |
| **Failing** | 9.98 | 200-900 seconds |

**Key Finding:** Failing scenarios actually have **fewer** SQL queries on average, but take **longer**. This suggests the issue is not "not enough exploration" but "exploration in wrong direction".

### 8.4 Root Cause

- Agent doesn't know when to stop exploring
- Agent doesn't have "authoritative path found" signal
- Agent treats exploration as safety net instead of targeted investigation

### 8.5 Interpretation

Over-exploration is usually a **secondary amplifier**, not the first mistake. It tends to appear
after the agent has already failed to:

- classify the concept type,
- lock the business event,
- or choose the authoritative source path.

So lowering query count alone will not fix UAT. The system has to get better at deciding
**which path deserves exploration at all**.

---

## 9. Failure Mode 7: Reflection Validates Syntax, Not Semantics

### 9.1 Description

The REFLECT phase validates SQL correctness but not business scope correctness.

### 9.2 What REFLECT Currently Checks

| Check | Status | Example |
|-------|--------|---------|
| SQL syntax valid | ✅ Checked | All queries execute |
| Filter completeness | ✅ Checked | Status, test exclusion applied |
| COUNT DISTINCT used | ✅ Checked | Always applied |
| Date range correct | ✅ Checked | Proper >= and < |

### 9.3 What REFLECT Doesn't Check

| Check | Status | Example |
|-------|--------|---------|
| Business event correct | ❌ Not checked | "disetujui" vs "all mayor" |
| Concept type correct | ❌ Not checked | Direct field vs coded field |
| Source path correct | ❌ Not checked | ERBA-only vs combined |
| Scope narrow enough | ❌ Not checked | All-time vs specific year |

### 9.4 Evidence

Many failed scenarios have **technically valid SQL** but **wrong business scope**:
- UAT-JP-MINOR-1: SQL valid, but counted all statuses instead of approved
- UAT-LC-AKTIF-1: SQL valid, but included expired NIE
- UAT-CHAR-GANDA-1: SQL valid, but included all systems and time

### 9.5 Missing Semantic Gates

REFLECT is currently closer to a **query auditor** than a **business-semantic gate**. The missing
checks are:

- was the right business event locked before SQL was written?
- is the concept direct-field, coded, master-data, lifecycle, or discovery?
- is the selected source path the narrowest authoritative one?
- did the SQL preserve exact-state vs family-state distinction?
- did the answer broaden to all-time / ERBA+ERLA / BTP without being requested?

---

## 10. Failure Mode 8: Scope Over-Broadening Bias

### 10.1 Description

When uncertain, the agent defaults to **broader scope** (all-time, ERBA+ERLA, include BTP).

### 10.2 Evidence

| Scenario | Expected Scope | Actual Scope | Gap |
|----------|----------------|--------------|-----|
| UAT-CHAR-GANDA-1 | ERBA only, specific time | ERBA+ERLA, all-time | 2x overcount |
| UAT-MAKLOON-1 | Active only | All-time | 3.4x overcount |
| UAT-IMPOR-1 | Status impor only | All imports | 2.5x overcount |

### 10.3 Root Cause

- Agent has bias: "more complete answer = safer answer"
- Agent doesn't have "answer contract" that limits scope
- Agent adds systems/time/breakdown without being asked

### 10.4 Current vs Correct Behavior

**Current:**
> "If unsure, add more data — all-time, both systems, include BTP, add trend"

**Correct:**
> "Answer should be as small as sufficient for the locked intent — don't add what wasn't asked"

---

## 11. Summary: The 8 Failure Modes

| # | Failure Mode | Count | Impact |
|---|--------------|-------|--------|
| 1 | Source-path selection failure | 83 | Critical |
| 2 | Concept type misclassification | 40 | High |
| 3 | Business-event locking failure | 16 | High |
| 4 | Cross-system code asymmetry | 10 | High |
| 5 | Commitment domain confusion | 12 | High |
| 6 | Over-exploration without stop rule | 14 | Medium |
| 7 | Reflection validates syntax, not semantics | 83 | Critical |
| 8 | Scope over-broadening bias | 7 | Medium |

### 11.1 Primary vs Cross-Cutting

These eight modes should be read in two layers.

**Primary decision failures**
- Source-path selection failure
- Concept type misclassification
- Business-event locking failure
- Cross-system code asymmetry
- Commitment domain confusion

**Cross-cutting amplifiers**
- Over-exploration without stop rule
- Reflection validates syntax, not semantics
- Scope over-broadening bias

The amplifiers make answers slower and more misleading, but they usually start **after** the
primary decision failure.

---

## 12. The Fundamental Problem

### 12.1 What the System Is Good At

- Writing syntactically correct SQL
- Applying standard filters (status, test exclusion)
- Using COUNT DISTINCT
- Handling canonical segments (AMDK, Garam, BTP)

### 12.2 What the System Is Bad At

- Choosing the right SQL to write
- Classifying concept types
- Locking business events early
- Stopping exploration when path is found
- Validating business scope in REFLECT

### 12.3 The Core Insight

> **The system is a capable SQL writer but an inadequate business-semantic decision engine.**

It often:
- Finds data
- Writes valid SQL
- Presents polished answers
- But counts the **wrong thing**

This is why many failed answers "look convincing but have wrong numbers".

---

## 13. Detailed Analysis: 6 Concept Types

### 13.1 Type A: Coded Cross-System Concepts

**Definition:** Codes that exist in both ERBA and ERLA but with **different values** for the same concept.

**Examples:**
- Risk levels (kategori_dokumen vs jenis_dokumen)
- Packaging (kemasan_id)
- Formula bayi (jenis_pangan)

**System's Error:** Uses ERBA code for ERLA queries, or assumes codes are identical.

**Fix:** Teach runtime source-aware binding and asymmetry handling, not a frozen answer catalog.

### 13.2 Type B: Direct Field Concepts

**Definition:** Concepts that can be directly filtered from a specific field without dictionary lookup.

**Examples:**
- Expiry date (tanggal_exp)
- Claims (klaim)
- Purpose (peruntukan)

**System's Error:** Treats these as discovery problems, over-explores, or uses proxy fields.

**Fix:** Add direct-field classification to context files.

### 13.3 Type C: Master-Data Concepts

**Definition:** Entity attributes that require JOINs to master tables.

**Examples:**
- Company identity (trader_id, nama_trader)
- Location (daerah_trader, daerah_pabrik)
- Business role (produsen, importir)

**System's Error:** Confuses identity vs label, trader location vs factory location.

**Fix:** Add identity semantics rules to context files.

### 13.4 Type D: Lifecycle/Pipeline Concepts

**Definition:** Status families that represent process stages.

**Examples:**
- Draft (0910)
- Verification (0912, 0918)
- Evaluation (0914)
- Payment (0916)
- Terminal states (0999, 0009, 0000, 0666)

**System's Error:** Thinks per-code, not per-family. Doesn't recognize "dalam proses" = multiple codes.

**Fix:** Add status family ontology to context files.

### 13.5 Type E: Segment Discovery Concepts

**Definition:** Product categories that require discovery or canonical mapping.

**Examples:**
- AMDK (jenis_pangan=1401 for ERBA, 651/652/655 for ERLA)
- Garam (jenis_pangan=1204)
- Formula bayi (jenis_pangan=1301 for ERBA, 622 for ERLA)

**System's Error:** Wrong scope discovery, wrong code mapping, or wrong system coverage.

**Fix:** Teach canonical segment discovery and per-system binding rules, not question-specific outputs.

### 13.6 Type F: Business-Event Concepts

**Definition:** Events that determine what is being counted.

**Examples:**
- "terbit" = issued NIE
- "aktif" = currently valid
- "disetujui" = approved application
- "dibatalkan" = cancelled

**System's Error:** Doesn't lock event early, applies wrong filters.

**Fix:** Add event disambiguation rules to context files.

### 13.7 Why This Taxonomy Matters

Canonical test prompts often already imply the concept type. Real user prompts do not. That is why
CB/NIE tests can pass while UAT collapses: the runtime system is not yet inferring concept type
explicitly enough from natural phrasing.

---

## 14. Recommendations

### 14.0 Recommendation Guardrail

The implementation path should remain aligned with the core principle of this project:

- do **not** fix UAT by memorizing question-answer pairs,
- do **not** freeze broad code tables as if they were final answers,
- do fix UAT by teaching the agent how to classify concepts, select sources, and stop exploration.

### 14.1 Fix Source-Path Selection (Priority 1)

**Action:** Add decision tree for concept classification and source-path selection

**Files:** `SEEKNAL_ASK.md`, `bpom-analyst/SKILL.md`

**Implementation:**
```markdown
## Source-Path Selection Decision Tree

After CAPTURE, before PLAN:

1. Classify concept type:
   - Coded cross-system? → Dictionary lookup (sumber-aware)
   - Direct field? → Direct filter, no discovery
   - Master-data? → JOIN with identity key
   - Lifecycle/pipeline? → Status family mapping
   - Segment discovery? → Canonical map or discovery
   - Business-event? → Event locking first

2. Select authoritative source path:
   - One entity
   - One metric
   - One time column
   - One system scope
   - One coded filter (if needed)

3. Stop after path is selected:
   - Don't explore alternatives
   - Don't add scope without request
   - Don't collapse families without reason
```

### 14.2 Fix Concept Type Classification (Priority 1)

**Action:** Add taxonomy of 6 concept types with classification rules

**Files:** `business_glossary.md`, `intent_mapping.md`

**Implementation:**
```markdown
## Concept Type Taxonomy

### A. Coded Cross-System
- Definition: Codes that differ between ERBA/ERLA
- Examples: risk, kemasan, formula bayi
- Rule: Bind code per system BEFORE query

### B. Direct Field
- Definition: Fields that can be directly filtered
- Examples: tanggal_exp, klaim, peruntukan
- Rule: Filter directly, no discovery needed

### C. Master-Data
- Definition: Entity attributes requiring JOINs
- Examples: company, location, scale
- Rule: Use identity key, not label

### D. Lifecycle/Pipeline
- Definition: Status families
- Examples: draft, verifikasi, evaluasi
- Rule: Map to family, then resolve members

### E. Segment Discovery
- Definition: Product categories needing discovery
- Examples: AMDK, garam, formula bayi
- Rule: Use canonical map or targeted discovery

### F. Business-Event
- Definition: Events that determine counting logic
- Examples: terbit, aktif, disetujui
- Rule: Lock event FIRST, then apply filters
```

### 14.3 Fix Business-Event Locking (Priority 1)

**Action:** Add event disambiguation rules

**Files:** `data_quality_rules.md`, `intent_mapping.md`

**Implementation:**
```markdown
## Business-Event Locking Rules

Before writing SQL, answer:

1. What event is being counted?
   - Issued NIE? → status IN ('0999','0906','9999')
   - Active NIE? → status IN ('0999','0906','9999') + not expired
   - Approved application? → specific status + jenis_permohonan
   - Cancelled commitment? → status_komitmen='5' (Case B)

2. What entity is being counted?
   - NIE? → COUNT(DISTINCT nomor)
   - Application? → COUNT(DISTINCT produk_id)
   - Company? → COUNT(DISTINCT trader_id)

3. Is jenis_permohonan mandatory, optional, or not used?
   - Mandatory: "NIE baru" → filter required
   - Optional: "permohonan" → may narrow scope
   - Not used: "total NIE" → don't filter
```

### 14.4 Fix Cross-System Code Mapping (Priority 2)

**Action:** Add complete ERLA code mapping tables

**Files:** `business_glossary.md`, `code_translation_protocol.md`

**Implementation:**
```markdown
## Cross-System Code Mapping

### Kemasan
| Konsep | ERBA (kemasan_id) | ERLA (kemasan_id) |
|--------|-------------------|-------------------|
| Plastik | 1 | 31, 32, 33 |
| Logam | 5 | 35 |
| Ganda | 7 | 38 |
| Komposit | 4 | 34, 37 |
| Kaca | 6 | 36 |

### Formula Bayi
| Konsep | ERBA (jenis_pangan) | ERLA (jenis_pangan) |
|--------|---------------------|---------------------|
| Formula Bayi | 1301 | 622 |
| Formula Lanjutan | 1302 | 604, 624 |

### Risk
| Konsep | ERBA (kategori_dokumen) | ERLA (jenis_dokumen) |
|--------|-------------------------|----------------------|
| Tinggi | 301 | 302 |
| Menengah Tinggi | 302 | 303 (gabungan MT+MR!) |
| Menengah Rendah | 303 | 301 |
| Tinggi Notifikasi | 304 | - (tidak ada) |

### Rules:
- BIND kode per system SEBELUM query
- Jika satu sistem tidak punya granularity setara → state limitation
- Jangan pakai kode satu sistem ke sistem lain
```

### 14.5 Fix Commitment Domain (Priority 2)

**Action:** Add Case A vs Case B rules with exact status mapping

**Files:** `data_quality_rules.md`

**Implementation:**
```markdown
## Commitment Domain Rules

### Case A: NIE with Commitment Status
- When: "NIE yang komitmennya..."
- Filter: NIE status + commitment status
- Example: "NIE yang komitmennya disetujui" → status IN ('0999','0906','9999') + status_komitmen='4'

### Case B: Application Lifecycle Outcome
- When: "Permohonan yang..."
- Filter: Commitment status ONLY (no NIE status)
- Example: "Permohonan yang dibatalkan" → status_komitmen='5' (no NIE filter)

### Exact Status Mapping
| Code | Status | Family |
|------|--------|--------|
| 0 | Draft | In-Process |
| 2 | Dalam Proses | In-Process |
| 4 | Disetujui | Terminal-Approved |
| 5 | Dibatalkan | Terminal-Cancelled |
| 7 | Disetujui Catatan | Terminal-Approved |

### Rules:
- Jika user minta EXACT state → jangan collapse ke family
- Jika user minta FAMILY → boleh collapse, tapi state dalam jawaban
```

### 14.6 Add Stop Rule (Priority 2)

**Action:** Add authoritative-path stop rule

**Files:** `SKILL.md`, `SEEKNAL_ASK.md`

**Implementation:**
```markdown
## Stop Rule (WAJIB diikuti)

### Rule 1: Maksimal 12 tool calls
Setelah 12 calls, WAJIB jawab dengan data yang ada + state keterbatasan

### Rule 2: Authoritative Path Selection
Setelah SATU path authoritative ditemukan, BLOK query lain

### Rule 3: Query harus punya tujuan eksplisit
Setiap query harus untuk:
- Resolve code
- Verify coverage
- Choose between candidate paths

### Rule 4: Jika ragu, state asumsi
Bukan terus menambah query, tapi state: "Asumsi: [interpretasi]"
```

### 14.7 Fix Reflection Gate (Priority 3)

**Action:** Add semantic validation to REFLECT phase

**Files:** `evidence-auditor/SKILL.md`

**Implementation:**
```markdown
## REFLECT Semantic Validation

Before presenting answer, verify:

1. Business event correct?
   - Did I count the right event?
   - Did I lock the event early?

2. Concept type correct?
   - Did I classify the concept correctly?
   - Did I use the right source path?

3. Source path correct?
   - Did I choose ERBA-only vs combined correctly?
   - Did I apply the right filters?

4. Scope narrow enough?
   - Did I add scope without request?
   - Did I over-broaden the answer?

If any check fails → re-resolve or state limitation
```

### 14.8 Fix Scope Discipline (Priority 3)

**Action:** Add answer contract that limits scope

**Files:** `SEEKNAL_ASK.md`

**Implementation:**
```markdown
## Scope Discipline Rules

### Default Scope (jika user tidak spesifik)
| Pertanyaan | Default Scope |
|------------|---------------|
| "Berapa NIE..." | ERBA + ERLA, all-time, semua status |
| "Berapa NIE baru..." | ERBA + ERLA, all-time, jp IN ('301','305') |
| "Berapa NIE 2025..." | ERBA + ERLA, tahun 2025, semua status |
| "Berapa NIE ERBA..." | ERBA only, all-time, semua status |

### Scope Narrowing (hanya jika user spesifik)
| User Bilang | Scope |
|-------------|-------|
| "tahun 2025" | Filter tahun |
| "ERBA saja" | ERBA only |
| "baru saja" | jp IN ('301','305') |
| "yang aktif" | status IN ('0999','0906','9999') + belum expired |

### Rules:
- Jangan tambah scope tanpa diminta
- Jangan tambah BTP/ERLA/all-time/trend kecuali diminta
- "Jawaban harus sekecil mungkin tapi cukup untuk intent yang terkunci"
```

---

## 15. Conclusion

The system fails at UAT not because it lacks SQL knowledge, but because it lacks **business-semantic decision-making ability**.

**The fix is NOT:**
- Hardcoding SQL answers
- Adding more test cases to context
- Making the system memorize questions

**The fix IS:**
- Teaching the concept taxonomy (6 types)
- Teaching source-path selection decision tree
- Teaching business-event locking discipline
- Teaching when to stop exploring
- Teaching REFLECT to validate semantics, not just syntax

This aligns with the core principle: **"Teach the agent how to think, not what to answer."**

---

*Report generated from UAT session data (June 19, 2026) and live database verification. All SQL evidence is reproducible against the `rpo_v2` database.*
