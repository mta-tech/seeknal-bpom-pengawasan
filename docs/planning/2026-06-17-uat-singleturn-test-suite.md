# seeknal-bpom-neo: UAT Singleturn Test Suite — 101 Test Cases

**Document type:** Test Suite Construction Record
**Project:** seeknal-bpom-neo (BPOM RPO Analytics Agent)
**Status:** Complete — 101 UAT files, all validated 2026-06-17
**Date:** 2026-06-17
**Scope:** `seeknal/tests/v1/singleturn/UAT-*.yml` (101 files) · database `rpo_v2` (live, tunnel `localhost:5533`)
**Evidence base:** `docs/outputs/messagearchive/iba_conversations_12h_20260615_full.json` (14 conversations, 57 questions from UAT 15 June 2026) · direct verification against `rpo_v2` 2026-06-17
**Amends / extends:** `docs/planning/2026-06-17-dictionary-grounded-code-translation.md` §11 — the test harness referenced in §10 (acceptance numbers), now fully realized

---

## 1. Background

The UAT of 15 June 2026 produced 57 questions from 14 real user-system conversations.
The audit identified **5 classes of critical failure** (RC-1 through RC-5) — ranging from a
Menengah Tinggi count off by 8× (95,736 vs 11,919) to non-deterministic answers for the same
question asked in different sessions.
`2026-06-17-dictionary-grounded-code-translation.md` documents the root causes
(cached code meanings, ERBA/ERLA source fan-out, hardcoded filter scopes).

To verify those fixes and guard against regression, a test harness is needed that:
1. Reflects how real users actually phrase questions (sourced from recorded conversations, not
   invented scenarios).
2. Uses numbers **verified directly from the DB** as of 2026-06-17 — not from the system's own output.
3. Covers **all relevant business domains**, not only the cases already known to be wrong.
4. Can be re-run at any time via `test_multiturn_v3.py --filter UAT` as a standing regression guard.

Beyond the 57 UAT questions, pattern analysis of the real conversation corpus yielded an
**8-domain business framework** (§2) used as a coverage map to ensure no domain is left untested.

---

## 2. The 8-Domain Business Framework

Analysis of the 57 questions shows that almost every user question falls into one of eight domains.
This framework drove test-case authoring so that coverage gaps are structural decisions, not accidents.

| Domain | File Prefix | Core User Questions |
|---|---|---|
| 1. NIE Lifecycle | `UAT-LC-*` | How many are active? How many revoked? When do they expire? |
| 2. Workflow / Pipeline | `UAT-PIPE-*`, `UAT-PIPELINE-*` | How many are still in process? Where is it stuck? |
| 3. Process Quality / Ops Health | `UAT-OPS-*` | How many were rejected? Supplemental data requests? Bottleneck? |
| 4. Risk Category | `UAT-MT-*`, `UAT-MR-*`, `UAT-RISIKO-*`, `UAT-RISK-*` | MR vs MT vs Tinggi breakdown? Year-on-year trend? |
| 5. Application Type | `UAT-JP-*` | More new registrations or revisions? Major vs minor changes? |
| 6. Compliance / Commitment | `UAT-COM-*`, `UAT-KOMITMEN-*`, `UAT-DRAFT-*` | How many cancelled? Approved? Still in draft? |
| 7. Master Data Quality | `UAT-DQ-*`, `UAT-BELUM-*` | Products missing classification? Missing risk category? |
| 8. Product Characteristics | `UAT-AMDK-*`, `UAT-BTP-*`, `UAT-BAYI-*`, `UAT-CHAR-*`, etc. | Segment? Packaging type? Country of origin? |

The underlying user mental model mapped across all domains: **Monitoring → Anomaly → Root Cause → Action**.
Test cases are designed to probe the system's ability at each stage of that chain.

---

## 3. Data Source and Verification

### 3.1 Question source
- **`iba_conversations_12h_20260615_full.json`** — 14 UAT conversations from 15 June 2026, each
  containing `conv_question` (topic) and `messages` (array of `{question, answer, sqls}`). Questions
  were extracted as prompt seeds and rewritten in natural user phrasing.
- **Pattern-derived questions** — cases outside the 57 UAT originals were authored following the
  same patterns observed in the corpus: short, natural, no table names, no technical code references.

### 3.2 Number verification against the DB
Every number in `description` and `assert_contains` was verified directly against `rpo_v2`
(2026-06-17) via SQL query — never from system output. Numbers on live data (active counts,
year-to-date) are noted with explicit tolerance in the `note` field.

**Test-account exclusion applied to all ERBA queries:**
```sql
trader_id::bigint NOT IN (5, 17, 50, 85)   -- ERBA internal test accounts
```
**ERLA exclusion:**
```sql
trader_id != 3384                            -- ERLA internal test account
```

### 3.3 File format
Every YAML file follows this structure:
```yaml
name: UAT_{FunctionalName}
scenario_id: UAT-{PREFIX}-{N}
description: '{ID} — [Domain X] {description}. DB verified 2026-06-17: {critical number}.'
turns:
- prompt: {natural user-style question, ≥ 10 characters}
  assert_contains:
  - '{specific substring}'   # minimum 2 items, each > 2 characters
  - '{another substring}'
  assert_not_contains:       # optional — for RC cases where the wrong number is already known
  - '{number the old system produced}'
  note: '{SQL context / technical notes for the debugger}'
```

---

## 4. Test Cases by Domain

### Domain 1 — NIE Lifecycle (9 files)

Covers questions about the live status of products registered with BPOM: active, expired, revoked, superseded.

| File | Question tested | Critical number |
|---|---|---|
| `UAT-LC-AKTIF-1` | How many NIE are currently valid? | 140,082 (ERBA status 0999) |
| `UAT-LC-TERMINASI-1` | How many NIE have been revoked or deleted by BPOM? | 5,237 revoked + 246 deleted |
| `UAT-LC-EXP-RISIKO-1` | NIE expiring in 2027, broken down by risk category? | MR=1,048 |
| `UAT-LC-DIUBAH-1` | How many NIE have status "superseded"? | 8,931 (status 9999) |
| `UAT-DICABUT-1` | How many NIE have been revoked? | 5,237 |
| `UAT-EXPIRY-2027-1` | How many NIE expire in 2027? | distribution by risk |
| `UAT-EXPIRY-DIST-1` | NIE expiry distribution by year? | multi-year distribution |
| `UAT-MONITORING-STATUS-1` | What is the current status breakdown of all active NIE? | total 312,337 |
| `UAT-TOTAL-1` | How many processed food products are registered with BPOM right now? | ~312,337 (live data, ±2%) |

**Purpose:** Verify that the system resolves `status_nie` codes to real business states (valid /
revoked / expired / superseded) via `data_dictionary` runtime lookup — never from a hardcoded table.

---

### Domain 2 — Workflow / Pipeline (8 files)

Covers questions about in-progress applications and where the process is congested.

| File | Question tested | Critical number |
|---|---|---|
| `UAT-PIPE-BAYAR-1` | How many applications are waiting for payment? | 6,988 |
| `UAT-PIPE-VERIF2-1` | How many are at the Verifikator 2 stage? | 159 |
| `UAT-PIPE-DRAFT-TOTAL-1` | How many applications are still in draft? | 24,959 |
| `UAT-PIPELINE-TOTAL-1` | Total applications currently in process? | total in-process |
| `UAT-PIPELINE-VERIF-1` | How many are at the verification stage? | verification distribution |
| `UAT-PIPELINE-EVAL-1` | How many are at the evaluation stage? | evaluation distribution |
| `UAT-PIPELINE-DIR-1` | How many are at the director / final approval stage? | director-stage distribution |
| `UAT-PENOLAKAN-1` | How many applications have been rejected? | total rejections |

**Purpose:** Test the system's ability to read workflow state from `status_permohonan` stage codes
and surface them as stage names that business users understand.

---

### Domain 3 — Process Quality / Operational Health (7 files)

Covers investigative questions: process anomalies, supplemental data requests, system rejections, bottleneck identification.

| File | Question tested | Critical number |
|---|---|---|
| `UAT-OPS-DATATAMBAHAN-1` | How many applications had supplemental data requested? | 7,371 |
| `UAT-OPS-DITOLAK-SISTEM-1` | How many were automatically rejected by the system? | 12,278 |
| `UAT-OPS-BOTTLENECK-1` | Which stage has the largest backlog? | draft=24,959 (43% of in-process) |
| `UAT-DRAFT-PROSES-1` | How many applications are still in the commitment fulfillment draft stage? | ~24,959 |
| `UAT-INVESTIGASI-KOMITMEN-1` | Why are so many commitments being cancelled? | distribution analysis |
| `UAT-INVESTIGASI-MAYOR-TREN-1` | Why did major changes spike so sharply? | 2023→2025 trend |
| `UAT-DRAFT-1` | How many MR products are still in the commitment fulfillment draft? | 28,720 |

**Purpose:** Test multi-step investigative capability (monitoring → anomaly → cause) — not just
a COUNT, but distribution analysis and trend reasoning.

---

### Domain 4 — Risk Category (12 files)

**The most critical domain** — contains RC-1, the largest error in the UAT, where the system
returned 95,736 for Menengah Tinggi when the correct answer is 11,919. Root cause: ERBA and ERLA
use different code schemes for risk, and the system was combining them without filtering on `sumber`.

| File | Question tested | Critical number |
|---|---|---|
| `UAT-MT-1` ⚡ RC-1 | How many NIE carry medium-high risk? | ERBA 11,919 (not 95,736) |
| `UAT-MT-2` | How many processed food products have medium-high risk? | 11,919 (alternative phrasing) |
| `UAT-MR-1` | How many NIE carry medium-low risk? | ERBA 41,425 + ERLA 77,949 = 119,374 |
| `UAT-RISK-1` | How does low risk compare to high risk in terms of NIE count? | High 80,394 vs MR 41,425 |
| `UAT-RISIKO-4-KATEGORI-1` | Distribution across all four risk categories? | High 80,394, MR 41,425, MT 11,919, TN 3,500 |
| `UAT-RISIKO-TINGGI-NOTIF-1` | How many NIE carry high-risk notification status? | ERBA 3,500 |
| `UAT-RISIKO-TINGGI-NOTIF-TREN-1` | What is the trend for high-risk notification NIE? | 2024=519, 2025=1,891, 2026=1,531 |
| `UAT-TREN-RISK-1` | Medium-low risk NIE trend year by year? | 2023=9,649, 2024=10,636, 2025=13,729 |
| `UAT-TREN-MT-1` | Medium-high risk NIE trend year by year? | 2023=3,077, 2024=4,007, 2025=3,604 |
| `UAT-MT-JP-MEI26-1` | Medium-high risk NIE by application type in May 2026? | JP breakdown |
| `UAT-MT-MINOR-MEI26-1` | Medium-high risk minor-change NIE in May 2026? | May breakdown |
| `UAT-MEI26-RISK-1` | NIE count by risk category for May 2026? | MR=1,335, MT=165, High=3,298 |

**Expected outcome after RC-1 fix:** `UAT-MT-1` passes with an answer of ~11,919, and
`assert_not_contains: ['95.736']` does not trigger.

---

### Domain 5 — Application Type (7 files)

Covers industry pattern questions: are companies registering more new products or revising existing ones?

| File | Question tested | Critical number |
|---|---|---|
| `UAT-JP-BARU-1` | How many new-registration NIE were issued this year? | new 2025 |
| `UAT-JP-MAYOR-2025-1` | How many major-change applications in 2025? | 6,636 |
| `UAT-JP-MINOR-1` | How many minor-change applications in 2025? | 6,935 |
| `UAT-JP-TREN-1` | Application trend by type, year over year? | 2022→2025 trend |
| `UAT-JP-BARU-VS-REVISI-1` | In 2025, were there more new registrations or revisions? | New 43,142 >> Revisions 13,571 |
| `UAT-JP-MINOR-VS-MAYOR-1` | In 2025, were there more minor or major changes? | Minor 6,935 vs Major 6,636 |
| `UAT-JP-PERMOHONAN-BARU-NOTIF-1` | How many new notification applications in 2025? | 2,132 |

**Purpose:** Test business-analysis capability — not just a per-code COUNT, but synthesizing
two or more numbers to answer a comparative question ("which is more?").

---

### Domain 6 — Compliance / Commitment (9 files)

Contains **RC-4** — the old system answered 254 for "MR commitments cancelled" because it
incorrectly applied a NIE status filter. The correct answer is 5,198. Most cancelled applications
never reached NIE issuance, so the NIE status filter silently eliminates the majority of cases.

| File | Question tested | Critical number |
|---|---|---|
| `UAT-COM-1` ⚡ RC-4 | How many MR products had their commitment cancelled by BPOM? | 5,198 (not 254) |
| `UAT-COM-2` | How many active MR NIE have a "cancellation validation" commitment status? | 42 |
| `UAT-DRAFT-1` | How many MR products are still in commitment fulfillment draft? | 28,720 |
| `UAT-KOMITMEN-DIBATALKAN-1` | How many MR products were cancelled? | 5,198 |
| `UAT-KOMITMEN-DISETUJUI-1` | How many MR products had their commitment approved by BPOM? | N approved |
| `UAT-KOMITMEN-DISETUJUI-CATATAN-1` | How many were approved with conditions? | N with conditions |
| `UAT-KOMITMEN-DRAFT-MR-1` | How many MR products still have draft commitment fulfillment status? | 28,720 |
| `UAT-KOMITMEN-PROSES-1` | How many MR commitments are under re-evaluation? | N in process |
| `UAT-KOMITMEN-VARIASI-1` | How many MR products have variation commitment status? | N variation |

**Two cases the system must distinguish:**
- **Case A (NIE already issued):** active products *that also* carry a given commitment status → apply NIE status filter.
- **Case B (application cancelled before NIE issuance):** do *not* apply NIE status filter — the filter hides the majority of the population.

---

### Domain 7 — Master Data Quality (3 files)

Covers completeness questions: are there products missing classification or risk assignment?

| File | Question tested | Critical number |
|---|---|---|
| `UAT-BELUM-KATEGORI-1` | How many products have not yet been categorized? | 28,667 (`kategori_dokumen` NULL) |
| `UAT-DQ-BELUM-KLASIFIKASI-1` | Are there products with no food-type classification? | 0 (none missing) |
| `UAT-DQ-BELUM-RISIKO-1` | How many ERBA products have no risk category assigned? | 28,667 |

**Purpose:** Test **early-warning data quality** capability — including the ability to answer "0"
honestly when nothing is wrong, rather than fabricating a number. `UAT-DQ-BELUM-KLASIFIKASI-1`
is an explicit zero-check.

---

### Domain 8 — Product Characteristics (28 files)

The largest domain — covers product segments (AMDK, food additives/BTP, infant formula, iodized
salt), packaging type, country of origin, industry scale, and intended use. Contains **RC-3**
(Iodized Salt 2023: sub-type code returns 190, parent code returns 199 — the correct scope).

#### 8.1 AMDK — Packaged Drinking Water (4 files)

| File | Question tested | Critical number |
|---|---|---|
| `UAT-AMDK-1` | How many AMDK NIE were issued in 2023? | ERBA 1,743 + ERLA 423 = 2,166 |
| `UAT-AMDK-2` | How many AMDK NIE from ERBA only in 2023? | 1,743 |
| `UAT-AMDK-3` | AMDK trend 2024–2025 (ERBA + ERLA combined)? | 2024=2,514, 2025=2,140 |
| `UAT-AMDK-4` | How many packaged drinking water NIE were issued in 2023? | 2,166 (alternative phrasing) |

#### 8.2 BTP — Food Additives (7 files)

| File | Question tested | Critical number |
|---|---|---|
| `UAT-BTP-1` | How many BTP NIE were issued in ERBA in 2023? | 950 (regression anchor) |
| `UAT-BTP-TREN-1` | Year-on-year BTP trend? | 2023=950, 2024=1,089, 2025=1,523 |
| `UAT-BTP-PEWARNA-1` | How many colourant BTP products? | colourant distribution |
| `UAT-BTP-ANTIOKSIDAN-1` | How many antioxidant BTP products? | antioxidant distribution |
| `UAT-BTP-CAIR-1` | How many liquid BTP products? | liquid distribution |
| `UAT-BTP-SERBUK-1` | How many powder BTP products? | powder distribution |
| `UAT-BTP-CAMPURAN-1` | How many mixed/compound BTP products? | mixed distribution |

#### 8.3 Infant Formula (5 files)

| File | Question tested | Critical number |
|---|---|---|
| `UAT-BAYI-1` | How many infant formula products have a NIE? | ERBA 102 + ERLA 814 = 916 |
| `UAT-BAYI-2` | Of those, how many are still active? | ERBA 60 + ERLA 235 = 295 |
| `UAT-BAYI-3` | Total infant formula products authorized by BPOM? | 916 (alternative phrasing) |
| `UAT-BAYI-DICABUT-1` | How many infant formula NIE have been revoked? | 0 (none in ERBA or ERLA) |
| `UAT-BAYI-JP-BREAKDOWN-1` | Infant formula breakdown by application type? | JP distribution |

#### 8.4 Iodized Salt (2 files)

| File | Question tested | Critical number |
|---|---|---|
| `UAT-GARAM-1` ⚡ RC-3 | How many iodized salt NIE were issued in 2023? | 199 (not 190 from sub-type code) |
| `UAT-GARAM-2` | How many active iodized salt NIE are in BPOM? | 1,241 |

#### 8.5 Packaging Type (5 files)

| File | Question tested | Critical number |
|---|---|---|
| `UAT-KEMASAN-PLASTIK-1` | How many products use plastic packaging? | plastic distribution |
| `UAT-KEMASAN-KACA-1` | How many products use glass packaging? | glass distribution |
| `UAT-CHAR-KOMPOSIT-1` | How many products use composite or laminate packaging? | 40,683 |
| `UAT-CHAR-GANDA-1` | How many products use double / multi-layer packaging? | 29,495 |
| `UAT-CHAR-LOGAM-1` | How many products use metal or can packaging? | 4,568 |

#### 8.6 Other Characteristics (6 files)

| File | Question tested | Critical number |
|---|---|---|
| `UAT-CHAR-PANGAN-BAYI-ERLA-1` | How many infant food products are in the ERLA system? | 81 products |
| `UAT-ORGANIK-1` | How many organic food products are registered? | organic distribution |
| `UAT-PANGAN-BERKLAIM-1` | How many food products carry a health claim? | claimed distribution |
| `UAT-PANGAN-DIET-1` | How many dietary food products are registered? | diet distribution |
| `UAT-PERUNTUKAN-1` | Which intended-use category has the most products? | intended-use distribution |
| `UAT-MAKLOON-1` | How many products are manufactured under a makloon (contract) arrangement? | contract-mfg distribution |

---

### Cross-domain / Regression (18 files)

These files do not belong to a single domain — they test system capability across wider data ranges
or anchor numbers that are already known to be correct and must not regress.

| File | Category | Question / Purpose | Critical number |
|---|---|---|---|
| `UAT-NIE25-1` ⚡ RC-5 | Determinism | Total NIE issued in 2025? | ERBA 53,535 + ERLA 3,671 = 57,206 |
| `UAT-NIE25-2` | Baseline | ERBA-only NIE in 2025? | 53,535 |
| `UAT-MD-1` ⚡ RC-5 | Determinism | How many domestic (MD) products in 2025? | 39,389 (not 30,760) |
| `UAT-SINGLE-MD-1` | Baseline | Example of a single MD product? | `MD ` number prefix format |
| `UAT-ERLA-1` | Baseline | Total ERLA applications across all periods? | 400,784 |
| `UAT-TREN-ERBA-1` | Trend | ERBA application trend year by year? | 2023=42,329, 2024=46,444, 2025=69,964 |
| `UAT-MEI26-1` | Period | Total NIE issued in May 2026? | ERBA 5,085 + ERLA 192 = 5,277 |
| `UAT-MEI-MR-1` | Period × Risk | Medium-low risk NIE issued in any May across all years? | ERBA 3,261 + ERLA 7,295 = 10,556 |
| `UAT-SUSU-1` ⚡ zero-check | Regression | "Sekolah"-brand milk products approved in May 2026? | 0 (system must answer honestly) |
| `UAT-IMPOR-1` | Master data | How many imported products are registered with BPOM? | import distribution |
| `UAT-IMPORTIR-1` | Master data | How many registered importers are there? | importer distribution |
| `UAT-NEGARA-1` | Master data | Which countries of origin appear most frequently? | country distribution |
| `UAT-PRODUSEN-1` | Master data | Where are most manufacturers located? | manufacturer distribution |
| `UAT-TOP-PERUSAHAAN-1` | Master data | Which companies hold the most NIE? | top-N companies |
| `UAT-DAERAH-1` | Region | Which region has the most NIE? | region distribution |
| `UAT-SKALA-1` | Industry scale | Product distribution by industry scale? | UMKM vs Large distribution |
| `UAT-SKALA-2` | Industry scale | Industry scale in ERBA vs ERLA? | cross-system scale comparison |
| `UAT-KLASIFIKASI-1` | Classification | Product distribution by food classification? | top classifications |

---

## 5. Validation Rules Enforced

All 101 files were automatically validated with Python before being declared complete.
Three mandatory rules:

1. **Prompt ≥ 10 characters** — ensures the question is real, not a placeholder.
2. **`assert_contains` ≥ 2 items** — at least one number and one conceptual keyword; a single item
   is not sufficient to distinguish a correct answer from a coincidental substring match.
3. **No item ≤ 2 characters** — items like `'0'` or `'5.'` are too ambiguous (they match almost
   any answer). Zero-result cases use `'tidak ada'` or `'tidak ditemukan'`; short numbers appear
   in context (`'81 produk'` not `'81'`).

```bash
# Run format validation only:
python3 - <<'EOF'
import os, yaml, glob
files = sorted(glob.glob("seeknal/tests/v1/singleturn/UAT-*.yml"))
issues = []
for fpath in files:
    data = yaml.safe_load(open(fpath))
    for t in data.get("turns", []):
        prompt = t.get("prompt", "")
        ac = t.get("assert_contains", [])
        if len(prompt.strip()) < 10: issues.append(f"SHORT PROMPT: {fpath}")
        if len(ac) < 2:             issues.append(f"TOO FEW ASSERT: {fpath}")
        for item in ac:
            if len(str(item).strip()) <= 2: issues.append(f"VAGUE ITEM '{item}': {fpath}")
print(f"{len(files)} files, {len(issues)} issues")
for i in issues: print(" !", i)
EOF
```

---

## 6. Critical Regression Cases (RC Guard)

These five cases are the **first line of defense** — if any one fails, there is a serious regression.

| ID | File | Wrong answer (before fix) | Correct answer (after fix) | Root cause |
|---|---|---|---|---|
| RC-1 | `UAT-MT-1` | 95,736 | **~11,919** | ERBA MT combined with ERLA medium risk — `sumber` fan-out |
| RC-3 | `UAT-GARAM-1` | 190 | **199** | Sub-type code used instead of parent `jenis_pangan=1204` |
| RC-4 | `UAT-COM-1` | 254 | **~5,198** | NIE status filter applied to applications that pre-date NIE issuance |
| RC-5a | `UAT-NIE25-1` | 3 different answers | **~57,206 (consistent)** | "Total NIE 2025" definition was not deterministic |
| RC-5b | `UAT-MD-1` | 30,760 | **~39,389** | Wrong number prefix (`BPOM RI MD%` instead of `MD %`) |

---

## 7. How to Run

```bash
cd seeknal-bpom-neo

# Full UAT suite (101 files):
uv run python scripts/test_multiturn_v3.py \
  --path seeknal/tests/v1/singleturn \
  --filter UAT

# Critical RC cases only:
uv run python scripts/test_multiturn_v3.py \
  --path seeknal/tests/v1/singleturn \
  --filter UAT-MT-1,UAT-GARAM-1,UAT-COM-1,UAT-NIE25-1,UAT-MD-1

# Single domain (example — Risk Category):
uv run python scripts/test_multiturn_v3.py \
  --path seeknal/tests/v1/singleturn \
  --filter UAT-MT,UAT-MR,UAT-RISIKO,UAT-RISK,UAT-TREN-RISK,UAT-TREN-MT
```

---

## 8. Expected Outcomes

### 8.1 Quantitative expectations (static data — these numbers will not drift)

| Case | Expected |
|---|---|
| NIE Menengah Tinggi, all-time | ~11,919 from ERBA; system states ERLA cannot isolate MT from MR |
| Commitment Cancelled MR | ~5,198; no NIE status filter suppressing pre-NIE cases |
| Iodized Salt 2023 | 199; system uses parent scope `jenis_pangan=1204`, not sub-type code |
| Total NIE 2025 (3 consecutive runs) | ~57,206, results identical — no scope variation across sessions |
| Domestic (MD) products 2025 | ~39,389; number prefix `MD ` not `BPOM RI MD` |
| BTP ERBA 2023 | 950 (regression anchor — must not move) |
| "Sekolah" milk, May 2026 | 0 (system answers honestly, does not fabricate) |
| AMDK combined 2023 | ~2,166 (ERBA 1,743 + ERLA 423) |

### 8.2 Qualitative expectations

- **All packaging questions** are answered using `KEMASAN_ID` resolved against `data_dictionary`
  with `sumber='ERBA'` — no row fan-out.
- **All risk questions** distinguish ERBA (4 levels) from ERLA (3 levels; ERLA cannot separate MT
  from MR). The system must **never** add them together without stating the limitation.
- **Zero-result cases** are answered with "not found" or "0" — not a fabricated number.
- **Comparative questions** ("which is more?") are answered by stating both numbers and a
  conclusion ("new registrations outnumber revisions 3-to-1").
- **Investigative questions** ("why did it spike?") are answered with trend data, not opinion.

---

## 9. Deliberate Gaps

- **Multi-turn questions** — this suite is singleturn only. Follow-up inheritance is tested in
  `seeknal/tests/v1/multiturn/`.
- **Typo / misspelling resilience** — no cases for "menengh tnggi" or similar. That behavior is
  owned by `code_translation_protocol.md` §typo-path, not by this suite.
- **Open-ended / recommendation questions** — "which products should be prioritized?" is out of
  scope; the system is a reporting assistant, not a decision engine.
- **Deep ERLA coverage** — most cases focus on ERBA because ERLA has a more limited data structure
  (no `kategori_dokumen`, no `status_komitmen`). ERLA-specific cases are included where ERLA is the
  only source or a meaningfully different scope applies.
