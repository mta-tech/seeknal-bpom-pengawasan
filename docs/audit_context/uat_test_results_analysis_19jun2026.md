# UAT Test Results Analysis — June 19, 2026

**Test Date:** June 19, 2026
**Analysis Date:** June 19, 2026
**Data Source:** `seeknal-bpom-neo/seeknal/tests/outputs/2026-06-19/v1/`
**Database:** `rpo_v2` via SSH tunnel (localhost:5533)

---

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| **Test Date** | June 19, 2026 |
| **Total Scenarios** | 238 |
| **Passed** | 143 (60.1%) |
| **Failed** | 95 (39.9%) |
| **UAT Scenarios** | 101 |
| **UAT Passed** | 18 (17.8%) |
| **UAT Failed** | 83 (82.2%) |

**Key Finding:** The system performs well on canonical queries (CB: 86.8%, NIE: 95.6%) but struggles significantly with real-world user acceptance tests (UAT: 17.8%).

**Important qualification:** the UAT problem is not explained by infrastructure alone. In the UAT
run, only 1 of 83 failures was a runtime/orchestrator issue. The rest are reasoning failures that
still produced answers.

---

## 2. Test Results by Category

| Category | Total | Passed | Failed | Pass Rate |
|----------|-------|--------|--------|-----------|
| **CB** (Core Business) | 38 | 33 | 5 | **86.8%** |
| **CAP/BUGFIX/FORECAST** | 54 | 49 | 5 | **90.7%** |
| **NIE** (Nomor Izin Edar) | 45 | 43 | 2 | **95.6%** |
| **UAT** (User Acceptance) | 101 | 18 | 83 | **17.8%** |
| **TOTAL** | **238** | **143** | **95** | **60.1%** |

**Interpretation:**
- CB/NIE/CAP tests are **well-handled** by the system
- UAT tests reveal **critical gaps** in real-world reasoning

---

## 3. Detailed Test Run Breakdown

| File | Timestamp | Scenarios | Passed | Failed | Pass Rate |
|------|-----------|-----------|--------|--------|-----------|
| `073456` | 07:34:56 | 38 | 33 | 5 | **86.8%** |
| `074940` | 07:49:40 | 54 | 49 | 5 | **90.7%** |
| `075716` | 07:57:16 | 45 | 43 | 2 | **95.6%** |
| `082737` | 08:27:37 | 101 | 18 | 83 | **17.8%** |
| **TOTAL** | | **238** | **143** | **95** | **60.1%** |

---

## 4. Root Cause Classification Summary

| Root Cause Class | Count | Percentage | Description |
|------------------|-------|------------|-------------|
| application_type_filter_drift | 16 | 19.3% | Wrong jenis_permohonan filter logic |
| lifecycle_status_family | 13 | 15.7% | Wrong status family grouping |
| direct_field_mishandled | 12 | 14.5% | Direct field treated as discovery |
| commitment_case_or_status_family | 12 | 14.5% | Wrong Case A/B or status collapse |
| code_mapping_cross_system | 10 | 12.0% | Wrong ERBA/ERLA code mapping |
| master_data_identity_semantics | 8 | 9.6% | Wrong identity key selection |
| scope_over_broadening | 7 | 8.4% | Scope expanded without request |
| other | 4 | 4.8% | Mixed/minor issues |
| runtime_orchestrator | 1 | 1.2% | Infrastructure failure |
| **TOTAL** | **83** | **100%** | |

### 4.1 How to Read This Table

These classes represent the **primary** failure selected for each scenario so the 83 failures can be
partitioned cleanly. They do not capture every secondary symptom. In practice, many scenarios also
show:

- over-exploration,
- scope broadening,
- or polished-but-wrong presentation

after the primary reasoning error has already happened.

---

## 5. Complete List of 83 Failed UAT Scenarios

### 5.1 Class A: application_type_filter_drift (16 scenarios)

| Scenario ID | Name | Expected | Got | Gap | Root Cause |
|-------------|------|----------|-----|-----|------------|
| UAT-JP-BARU-1 | Permohonan Baru 2023 | 29,888 | 31,xxx | ~2% | Wrong JP filter scope |
| UAT-JP-BARU-VS-REVISI-1 | JP Baru vs Revisi 2025 | "43." | MISSING | - | Missing keyword |
| UAT-JP-MAYOR-2025-1 | Permohonan Mayor 2025 | 6,636 | 8,154 | +23% | All statuses, not just approved |
| UAT-JP-MINOR-1 | Permohonan Minor 2023 | 1,327 | 10,882 | +8x | All statuses, not just approved |
| UAT-JP-MINOR-VS-MAYOR-1 | JP Minor vs Mayor 2025 | 6,935/6,636 | MISSING | - | Missing comparison |
| UAT-JP-TREN-1 | Tren JP ERBA | "43.142"/"2025" | MISSING | - | Missing trend data |
| UAT-MD-1 | Produk MD 2025 | "39.389"/"nomor MD" | MISSING | - | Wrong scope |
| UAT-MEI-MR-1 | Mei MR 2026 | ? | ? | ? | Wrong filter |
| UAT-NIE25-1 | Total NIE 2025 | "57.206" | MISSING | - | Missing total |
| UAT-NIE25-2 | NIE RBA 2025 | "53.535" | MISSING | - | Missing total |
| UAT-TREN-ERBA-1 | Tren ERBA | ? | ? | ? | Wrong scope |
| UAT-ERLA-1 | ERLA Permohonan Total | "400." | MISSING | - | Missing total |
| UAT-MEI26-1 | Total NIE Mei 2026 | ? | ? | ? | Wrong scope |
| UAT-MEI26-RISK-1 | Mei 2026 per Risiko | ? | ? | ? | Wrong scope |
| UAT-LC-DIUBAH-1 | NIE Sudah Diubah | "8.931" | MISSING | - | Missing count |

**Root Cause:** Agent treats `jenis_permohonan` as entity definition rather than scope modifier.

**Problem-solving hypothesis:** the system is still locking administrative type too early, before it
has fully locked the business event and counted entity.

**Example:**
```
Scenario: UAT-JP-MINOR-1
Expected: 1,327
Got: 10,882
Gap: 8x overcount

Problem: Agent applied jenis_permohonan='303' (minor) but counted ALL statuses, not just approved
```

---

### 5.2 Class B: lifecycle_status_family (13 scenarios)

| Scenario ID | Name | Expected | Got | Gap | Root Cause |
|-------------|------|----------|-----|-----|------------|
| UAT-DICABUT-1 | NIE Dicabut/Dibatalkan | "5.237" | MISSING | - | Wrong revoked scope |
| UAT-LC-AKTIF-1 | NIE Masih Berlaku | ~140,000 | 237,438 | +70% | Over-included |
| UAT-LC-DIUBAH-1 | NIE Sudah Diubah | "8.931" | MISSING | - | Missing count |
| UAT-LC-TERMINASI-1 | Terminasi Breakdown | "5.237"/"246" | MISSING | - | Missing breakdown |
| UAT-MONITORING-STATUS-1 | Monitoring Status | ? | ? | ? | Wrong status family |
| UAT-OPS-BOTTLENECK-1 | Bottleneck | ? | ? | ? | Wrong pipeline scope |
| UAT-OPS-DATATAMBAHAN-1 | Data Tambahan | ? | ? | ? | Wrong status scope |
| UAT-OPS-DITOLAK-SISTEM-1 | Ditolak Sistem | ? | ? | ? | Wrong status scope |
| UAT-PIPE-BAYAR-1 | Pipeline Bayar | ? | ? | ? | Wrong status scope |
| UAT-PIPE-DRAFT-TOTAL-1 | Pipeline Draft Total | ? | ? | ? | Wrong status scope |
| UAT-PIPE-VERIF2-1 | Pipeline Verif 2 | ? | ? | ? | Wrong status scope |
| UAT-PIPELINE-DIR-1 | Pipeline Direktur | ? | ? | ? | Wrong status scope |
| UAT-PIPELINE-EVAL-1 | Pipeline Evaluasi | ? | ? | ? | Wrong status scope |
| UAT-PIPELINE-TOTAL-1 | Pipeline Total | ? | ? | ? | Wrong pipeline scope |
| UAT-PIPELINE-VERIF-1 | Pipeline Verifikasi | ? | ? | ? | Wrong status scope |

**Root Cause:** Agent thinks per-code, not per-family-state.

**Problem-solving hypothesis:** the system lacks an explicit step that groups raw status codes into
business families before query construction.

**Example:**
```
Scenario: UAT-LC-AKTIF-1
Expected: ~140,000
Got: 237,438
Gap: 70% overcount

Problem: Agent counted ALL non-expired NIE, not just "currently active" (issued + valid + not revoked)
```

---

### 5.3 Class C: direct_field_mishandled (12 scenarios)

| Scenario ID | Name | Expected | Got | Gap | Root Cause |
|-------------|------|----------|-----|-----|------------|
| UAT-BAYI-2 | Formula Bayi Aktif | 295 | MISSING | - | Missing count |
| UAT-BELUM-KATEGORI-1 | Produk Belum Dikategorikan | "28.667" | 9 | -3000x | Wrong scope |
| UAT-BTP-PEWARNA-1 | BTP Pewarna NIE | "600" | 5,888 | +10x | Wrong scope |
| UAT-CHAR-PANGAN-BAYI-ERLA-1 | Pangan Bayi ERLA | "81 produk" | 401 | +5x | Wrong scope |
| UAT-DQ-BELUM-KLASIFIKASI-1 | Belum Klasifikasi | "klasifikasi" | MISSING | - | Missing keyword |
| UAT-DQ-BELUM-RISIKO-1 | Belum Risiko | "28." | MISSING | - | Missing prefix |
| UAT-EXPIRY-2027-1 | Kadaluarsa 2027 | "kadaluarsa" | 33,289 | - | Missing keyword + wrong number |
| UAT-EXPIRY-DIST-1 | Distribusi Kadaluarsa | "44.758" | MISSING | - | Missing count |
| UAT-KLASIFIKASI-1 | Makanan vs Minuman | "57.972"/"37.366" | MISSING | - | Missing breakdown |
| UAT-PANGAN-BERKLAIM-1 | Pangan Berklaim | ? | ? | ? | Wrong scope |
| UAT-PANGAN-DIET-1 | Pangan Diet | ? | ? | ? | Wrong scope |
| UAT-PERUNTUKAN-1 | Peruntukan | ? | ? | ? | Wrong scope |

**Root Cause:** Agent doesn't distinguish direct-field vs coded/discovery concept.

**Problem-solving hypothesis:** when the wording feels specific, the agent escalates into discovery
too early instead of first deciding whether the concept is already anchored to one authoritative
field.

**Example:**
```
Scenario: UAT-EXPIRY-2027-1
Expected: "kadaluarsa" keyword
Got: 33,289 (wrong number + missing keyword)

Problem: Agent treated expiry as discovery problem instead of direct field (tanggal_exp)
```

---

### 5.4 Class D: commitment_case_or_status_family (12 scenarios)

| Scenario ID | Name | Expected | Got | Gap | Root Cause |
|-------------|------|----------|-----|-----|------------|
| UAT-COM-1 | Komitmen Dibatalkan MR | "5.198" | 5,215 | +0.3% | Near-miss |
| UAT-DRAFT-1 | Draft Pemenuhan Komitmen | "28.720" | 17,221 | -40% | Wrong draft scope |
| UAT-DRAFT-PROSES-1 | Draft Belum Bayar | "20.020" | 25,129 | +25% | Wrong scope |
| UAT-INVESTIGASI-KOMITMEN-1 | Investigasi Komitmen MR | "28.720"/"11.688"/"10.233"/"5.198" | MISSING | - | Missing breakdown |
| UAT-KOMITMEN-DIBATALKAN-1 | Komitmen Dibatalkan MR | "5.198" | 5,216 | +0.3% | Near-miss |
| UAT-KOMITMEN-DISETUJUI-1 | Komitmen Disetujui MR | "2.717" | 14,322 | +5x | Collapsed 4+7 |
| UAT-KOMITMEN-DISETUJUI-CATATAN-1 | Komitmen Disetujui Catatan | "11.688" | 11,693 | +0.04% | Near-miss |
| UAT-KOMITMEN-DRAFT-MR-1 | Komitmen Draft MR | "28." | 17,221 | - | Missing prefix |
| UAT-KOMITMEN-PROSES-1 | Komitmen Proses MR | "10.233" | 10,278 | +0.4% | Near-miss |
| UAT-KOMITMEN-VARIASI-1 | Komitmen Variasi MR | "4.099" | 3,994 | -2.5% | Near-miss |

**Root Cause:** Agent collapses status 4 (Disetujui) and 7 (Disetujui Catatan) when user asks for exact state.

**Important nuance:** several commitment failures are numerically close, but they are still
substantive semantic failures. "Near miss" here does not mean the reasoning is safe; it means the
agent landed near the right answer while still taking the wrong logical path.

**Example:**
```
Scenario: UAT-KOMITMEN-DISETUJUI-1
Expected: 2,717
Got: 14,322
Gap: 5x overcount

Problem: Agent combined status 4 (Disetujui) + status 7 (Disetujui Catatan), user only wanted 4
```

---

### 5.5 Class E: code_mapping_cross_system (10 scenarios)

| Scenario ID | Name | Expected | Got | Gap | Root Cause |
|-------------|------|----------|-----|-----|------------|
| UAT-BAYI-1 | Formula Bayi Total | 916 | 94 | -10x | Wrong ERLA code |
| UAT-BAYI-3 | Formula Bayi Natural | 916 | 175 | -5x | Wrong ERLA code |
| UAT-BTP-ANTIOKSIDAN-1 | BTP Antioksidan NIE | 942 | 943 | +0.1% | Near-miss |
| UAT-BTP-CAIR-1 | BTP Cair/Pasta | "2.274" | 5,179 | +2x | Wrong scope |
| UAT-BTP-CAMPURAN-1 | BTP Campuran vs Tunggal | "2.788"/"695" | MISSING | - | Missing breakdown |
| UAT-BTP-SERBUK-1 | BTP Serbuk | "1.796" | 4,023 | +2x | Wrong scope |
| UAT-KEMASAN-KACA-1 | Kemasan Kaca ERBA | "14.154" | MISSING | - | Missing count |
| UAT-KEMASAN-PLASTIK-1 | Kemasan Plastik ERBA | "44.631" | MISSING | - | Missing count |
| UAT-MT-1 | Risiko Menengah Tinggi | ? | ? | ? | ERLA 303 = ALL medium |
| UAT-RISK-1 | Risiko | ? | ? | ? | Wrong code mapping |

**Root Cause:** Agent uses ERBA codes for ERLA queries.

**Problem-solving hypothesis:** source-aware binding may exist in context, but the runtime agent is
not consistently enforcing it before composing UNION queries.

**Example:**
```
Scenario: UAT-BAYI-1
Expected: 916
Got: 94
Gap: 10x undercount

Problem: Agent used ERBA codes (1301/1302) for ERLA query, but ERLA uses 622/604/624
```

---

### 5.6 Class F: master_data_identity_semantics (8 scenarios)

| Scenario ID | Name | Expected | Got | Gap | Root Cause |
|-------------|------|----------|-----|-----|------------|
| UAT-DAERAH-1 | Produk Jakarta Timur | "17.544" | 40,282 | +2x | Wrong location field |
| UAT-IMPOR-1 | Produk Impor | "44.127" | 109,739 | +2.5x | Wrong scope |
| UAT-IMPORTIR-1 | Perusahaan Importir | "1.300" | MISSING | - | Missing count |
| UAT-NEGARA-1 | Produk dari China | ? | ? | ? | Wrong country field |
| UAT-PRODUSEN-1 | Perusahaan Produsen | ? | ? | ? | Wrong identity |
| UAT-SKALA-1 | Skala Usaha | ? | ? | ? | Wrong scope |
| UAT-SKALA-2 | Skala Usaha 2 | ? | ? | ? | Wrong scope |
| UAT-TOP-PERUSAHAAN-1 | Top Perusahaan | ? | ? | ? | Wrong scope |

**Root Cause:** Agent confuses company identity vs display label, trader location vs factory location.

**Problem-solving hypothesis:** the system does not yet force an explicit choice between:
- identity key,
- display label,
- company location,
- and factory location
before writing grouping SQL.

**Example:**
```
Scenario: UAT-DAERAH-1
Expected: 17,544
Got: 40,282
Gap: 2x overcount

Problem: Agent used daerah_pabrik instead of daerah_trader
```

---

### 5.7 Class G: scope_over_broadening (7 scenarios)

| Scenario ID | Name | Expected | Got | Gap | Root Cause |
|-------------|------|----------|-----|-----|------------|
| UAT-CHAR-GANDA-1 | Kemasan Ganda | "29." | 57,643 | +2x | All systems + all-time |
| UAT-CHAR-KOMPOSIT-1 | Kemasan Komposit | "40." | MISSING | - | Missing prefix |
| UAT-CHAR-LOGAM-1 | Kemasan Logam | "4.568" | 11,537 | +2.5x | Wrong scope |
| UAT-DRAFT-PROSES-1 | Draft Belum Bayar | "20.020" | 25,129 | +25% | Wrong scope |
| UAT-MAKLOON-1 | Produk Makloon | "2.133" | 7,192 | +3.4x | All-time scope |
| UAT-TREN-MT-1 | Tren MT | ? | ? | ? | Wrong scope |
| UAT-TREN-RISK-1 | Tren Risk | ? | ? | ? | Wrong scope |

**Root Cause:** Agent has bias "more complete answer = safer answer".

**Problem-solving hypothesis:** the answer contract is not constraining source-path selection early
enough, so the system broadens scope when uncertain instead of stopping at the smallest sufficient
answer.

**Example:**
```
Scenario: UAT-CHAR-GANDA-1
Expected: ~29,000
Got: 57,643
Gap: 2x overcount

Problem: Agent counted all "ganda" packaging across all systems and time, not just requested scope
```

---

### 5.8 Class H: runtime_orchestrator (1 scenario)

| Scenario ID | Name | Issue |
|-------------|------|-------|
| UAT-MR-1 | Risiko Menengah Rendah | ConnectError — infrastructure failure |

---

### 5.9 Other (4 scenarios)

| Scenario ID | Name | Expected | Got | Gap | Root Cause |
|-------------|------|----------|-----|-----|------------|
| UAT-BTP-TREN-1 | BTP Tren ERBA | 1,089/1,523 | 1,107/1,542 | +2% | Minor scope drift |
| UAT-ERLA-1 | ERLA Total | "400." | MISSING | - | Missing prefix |
| UAT-GARAM-2 | Garam All Time | "1.241" | MISSING | - | Missing count |
| UAT-MT-2 | MT Gabungan | ? | ? | ? | ERLA code issue |

---

## 6. Cross-cutting Patterns

| Pattern | Description | Affected Scenarios |
|---------|-------------|-------------------|
| **over_exploration_no_authoritative_stop** | Agent makes 20-30 queries without improving quality | 14 scenarios |
| **scope_drift_to_all_time_combined** | Agent defaults to all-time + ERBA+ERLA when unsure | 20+ scenarios |
| **presentation_oracle_mismatch** | Answer format doesn't match expected | 6 scenarios |
| **runtime_failure** | Infrastructure/connection issues | 1 scenario |

### 6.1 Key Interpretation

These cross-cutting patterns are usually **amplifiers**, not primary causes. For example,
over-exploration often appears only after the system has already failed to classify concept type or
lock the correct event.

---

## 7. What the System Does Right

| Capability | Status | Evidence |
|------------|--------|----------|
| Canonical segment queries (AMDK, Garam, BTP) | ✅ Strong | High pass rate on CB/NIE tests |
| Dual-system UNION pattern | ✅ Strong | Consistently applied |
| COUNT DISTINCT awareness | ✅ Strong | Always uses COUNT(DISTINCT nomor) |
| Date range discipline | ✅ Strong | Proper >= and < filters |
| Test account exclusion | ✅ Strong | Correct trader_id exclusions |
| Zero-result honesty | ✅ Strong | Correctly reports "not found" |

### 7.1 What This Means

The foundation is not empty. The system already has:
- valid SQL mechanics,
- distinct-count discipline,
- correct canonical filters in many simple cases,
- and some honest zero-result behavior.

That is why the repair strategy should focus on **decision quality before SQL**, not on rewriting the
entire SQL layer.

---

## 8. What the System Fails At

| Capability | Status | Evidence |
|------------|--------|----------|
| Business-event disambiguation | ❌ Weak | 16 scenarios fail |
| Lifecycle status family reasoning | ❌ Weak | 13 scenarios fail |
| Direct-field vs coded-field discrimination | ❌ Weak | 12 scenarios fail |
| Commitment Case A vs Case B | ❌ Weak | 12 scenarios fail |
| Cross-system code mapping | ❌ Weak | 10 scenarios fail |
| Master-data identity semantics | ❌ Weak | 8 scenarios fail |
| Scope discipline | ❌ Weak | 7 scenarios fail |

---

## 9. Key Insights

### 9.1 "Almost Right" vs "Totally Wrong"

| Pattern | Count | Description |
|---------|-------|-------------|
| **Almost Right** (<5% gap) | ~10 | Agent on right track, minor drift |
| **Totally Wrong** (>100% gap) | ~73 | Agent on wrong path entirely |

**Important nuance:** "Almost Right" failures should not be dismissed as harmless. They usually
indicate unstable event-locking or family collapse. In production, that kind of instability will
still erode trust because the same user question can move between adjacent answers across runs.

### 9.2 "Missing" vs "Wrong Number"

| Pattern | Count | Description |
|---------|-------|-------------|
| **Missing** | ~60 | Agent didn't include expected information |
| **Wrong Number** | ~23 | Agent included information but wrong value |

### 9.3 Query Efficiency

| Scenario Type | Avg SQL Count | Avg Time |
|---------------|---------------|----------|
| **Passing** | 10.89 | 50-150 seconds |
| **Failing** | 9.98 | 200-900 seconds |

**Interpretation:** More queries ≠ better answers. Over-exploration is a failure precursor.

### 9.4 Why UAT Is So Different from CB/NIE

CB/NIE tests usually give the agent the concept type almost for free:
- the entity is explicit,
- the scope is explicit,
- the filter family is explicit.

UAT prompts often do not. They require the agent to infer:
- what kind of concept is being asked,
- which business event is being counted,
- whether the concept is direct-field, coded, or master-data,
- and whether the answer should stay narrow or broaden.

So the UAT gap is primarily a **problem-solving gap**, not a raw SQL template gap.

---

## 10. Recommendations

### 10.1 Immediate Actions (Priority 1)

| Action | File | Root Cause |
|--------|------|------------|
| Add commitment Case A vs Case B rules | data_quality_rules.md | Class D |
| Add application type filter decision tree | data_quality_rules.md | Class A |
| Add lifecycle status family ontology | business_glossary.md | Class B |
| Add concept-type routing before SQL | SEEKNAL_ASK.md / SKILL.md | Cross-class |

### 10.2 Short-term Actions (Priority 2)

| Action | File | Root Cause |
|--------|------|------------|
| Add direct-field vs coded-field classification | business_glossary.md | Class C |
| Add source-aware cross-system binding rules | code_translation_protocol.md | Class E |
| Add master-data identity semantics | business_glossary.md | Class F |

### 10.3 Medium-term Actions (Priority 3)

| Action | File | Root Cause |
|--------|------|------------|
| Add authoritative-path stop rule | SKILL.md | Cross-cutting |
| Add scope discipline rules | SEEKNAL_ASK.md | Class G |
| Upgrade REFLECT from SQL-audit to semantic gate | evidence-auditor / SKILL.md | Cross-class |

### 10.4 Recommendation Guardrail

The recommendations above should not be implemented as:
- a memorized list of UAT questions,
- a frozen answer sheet,
- or a giant context block that enumerates every future phrasing.

They should be implemented as runtime teaching:
- how to classify concepts,
- how to pick authoritative sources,
- how to bind per-system codes,
- and how to stop when the right path is found.

---

## 11. Conclusion

The system is **not broken** — it handles canonical queries well (86-95% pass rate). However, it **fails on real-world UAT scenarios** (17.8% pass rate) because:

1. **Concept typing is not strong enough** — agent can't reliably distinguish coded vs direct vs master-data vs lifecycle concepts
2. **Source-path selection is not decisive enough** — agent explores too many paths instead of committing to one authoritative path
3. **Business-event locking is not early enough** — agent applies filters before fully understanding what event is being counted
4. **Reflection gate is not strict enough** — technically valid SQL passes even when business scope is wrong

**The fix is NOT to hardcode answers**, but to:
- Teach agent the concept taxonomy (6 types)
- Teach agent the decision tree for source-path selection
- Teach agent when to stop exploring
- Teach agent when to be narrow vs broad

---

*Report generated from UAT session data (June 19, 2026) and live database verification. All SQL evidence is reproducible against the `rpo_v2` database.*
