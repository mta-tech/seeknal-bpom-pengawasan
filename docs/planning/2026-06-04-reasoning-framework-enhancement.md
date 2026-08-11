# seeknal-bpom-neo: Reasoning Framework Enhancement

**Document type:** Implementation Plan
**Project:** seeknal-bpom-neo (BPOM RPO Analytics Agent)
**Status:** Ready for Implementation
**Date:** 2026-06-04
**Scope:** `seeknal/skills/bpom-analyst/SKILL.md` · `context/intent_mapping.md` · `context/business_glossary.md`

---

## 1. Background

Following the QA test run on 03 June 2026 (38 test cases, scope SC-2: ERBA + ERLA),
the system achieved a 96.8% data accuracy rate. The failure pattern, however, was not
about wrong data — it was about **how the agent reasons** when a question requires combining
patterns it has not seen together before.

This plan addresses the root cause: the current system is a **lookup + rule engine**,
not a **reasoning framework**. When a question matches a known pattern, the agent performs
well. When a question introduces novel combinations or requires synthesis across multiple
dimensions, the agent falls back to the most familiar known pattern — producing incomplete
or incorrectly structured answers.

The objective of this plan is to add **thinking patterns** inside the existing reasoning
phases, so the agent can handle any question — including ones it has never seen — by
reasoning from principles rather than matching to templates.

---

## 2. Current State Analysis

### 2.1 What the Existing System Already Gets Right

The system already has a sound architecture. The following files and components are **correct
and should not be modified**:

| File / Component | Role | Why It Is Correct |
|---|---|---|
| `SEEKNAL_ASK.md` behavioral contracts | Absolute rules active from session start | Non-negotiable mappings (registrasi→PERMOHONAN) must be enforced before any skill loads |
| `context/query_recipes.md` R1–R11 | 1D SQL template examples | Sufficient as reference for single-dimension queries; adding more recipes creates rigid hardcoding |
| `context/data_quality_rules.md` | Mandatory filter rules | Cast rules, date range patterns, status filters are already correct and complete |
| `context/code_resolution.md` | Code-to-label mappings | Region conversion formula and dictionary join patterns are accurate |
| `seeknal/skills/evidence-auditor/SKILL.md` | Pre-answer audit checklist | Scope match, filter validation, honesty checks are comprehensive |
| CAPTURE → RESOLVE → PLAN → EXECUTE → REFLECT → GENERATE workflow | Core reasoning pipeline | The phase structure itself is correct; what is missing is the **reasoning content** within phases |

### 2.2 How the Existing System Teaches the Agent

Every file in the current system teaches the agent through **pattern matching**:

```
intent_mapping.md   → "if user says X, map to Y"         (lookup table)
query_recipes.md    → "for question type Z, use this SQL" (template catalog)
business_glossary   → "NIE = COUNT(DISTINCT nomor)"       (fixed definition)
data_quality_rules  → "always apply these filters"        (checklist)
bpom-analyst SKILL  → "pick the matching recipe, adapt"   (match + adapt)
```

This works correctly when the user's question maps cleanly to an existing entry.
It breaks when:

1. A question combines two dimensions that have no combined recipe
2. A question asks "which" (requires naming a category) but the agent maps it to "how many" (total count)
3. A question involves multi-aspect analysis requiring synthesis across query results

### 2.3 Three Concrete Failure Cases from QA Results

#### Failure Case 1 — Test 8 (FAILED): 2D Query Split into Two 1D Queries

**Question:** "Bagaimana tren izin edar berdasarkan lokasi pabrik dan tahun penerbitannya?"

**Expected output:** One table — per location × per year (2D result set)

**Actual output:** Two separate tables:
- Table 1: NIE per year (total trend, 1D)
- Table 2: Top locations all-time (ranking, 1D)

**Root cause traced to current files:**

`SEEKNAL_ASK.md` and `intent_mapping.md` both contain the rule:
> `tren per [dimension]` → `GROUP BY year, dimension — ONE query, not two`

The rule **exists as prose** but the agent violated it. Why? Because in the PLAN phase,
the agent opens `query_recipes.md` and finds no SQL example for a 2D query with
`GROUP BY date_trunc('year', tanggal), daerah_pabrik` combined with LEFT JOIN for
region name resolution. Without a concrete anchor to build from, the agent falls back
to two known 1D patterns — producing the wrong output.

The issue is not the rule; it is the absence of **reasoning guidance** that explains
*why* two dependent dimensions must be in one query and *how to derive that structure
from first principles* for any dimension combination.

#### Failure Case 2 — Test 34 (Passed with Notes): "Which Product" Answered as "How Many"

**Question:** "Produk risiko menengah rendah apa yang paling sering mengalami pembatalan?"

**Expected output:** Ranked list of product categories (names + cancellation counts)

**Actual output:** "Terdapat 2.515 produk dengan status Dicabut/Dibatalkan (0009)" — a total
count with no product names

**Root cause traced to current files:**

`intent_mapping.md` ENTITY registry maps `PRODUK` to:
> `PRODUK → LIST/SEARCH operation (row detail), not aggregation`

When the user asks "produk apa yang paling banyak X", the agent identifies the entity
as PRODUK and assigns it the LIST operation. No mapping exists that teaches:

> "produk apa yang paling banyak X" = RANKING operation → `GROUP BY nama_kategori ORDER BY COUNT DESC`

The gap is that `PRODUK` as an entity (individual product row) and `nama_kategori` as a
grouping dimension (category label for ranking) are treated as the same thing. The agent
does not know that "what product" in a ranking context means "which category" at the
aggregation level.

#### Failure Case 3 — Test 36 (Passed with Notes): Workflow Column Confused with Reason Column

**Question:** "Apa alasan pembatalan izin edar yang paling sering terjadi?"

**Actual output (partially correct):** The agent correctly retrieved top 5 reasons from
`jenis_penolakan_komitmen`. But also reported: "kode 0999 (183.830 baris) dan 9999
(205.497 baris) tidak memiliki label alasan yang ditemukan" — treating valid NIE status
codes as if they were cancellation reason codes.

**Root cause traced to current files:**

`business_glossary.md` defines the commitment status section and mentions
`jenis_penolakan_komitmen`, but does not explain the **purpose difference** between:

- `status` = workflow stage of a NIE record (in-process, issued, revoked)
- `jenis_penolakan_komitmen` = the reason why a commitment was rejected

The agent searched multiple columns for "reasons" and found code `0999` in the `status`
column, then tried to find its label in `data_dictionary` under a "cancellation reason"
context. No guidance existed saying: "`status` is a workflow tracker, not a reason field.
Do not use it to answer 'why' questions."

---

## 3. Gap Summary

| Gap | Located In | Affected Phase | Test Cases |
|---|---|---|---|
| **G1** — No decomposition pattern for multi-dimensional questions | `bpom-analyst/SKILL.md` CAPTURE | PLAN phase falls back to multiple 1D queries | Test 8 (FAILED), Tests 14, 22 |
| **G2** — "Which entity" not distinguished from "how many entities" | `intent_mapping.md` ENTITY registry | CAPTURE misclassifies ranking questions as list/count | Tests 34, 31, 30 |
| **G3** — Column purpose not taught (workflow vs reason vs risk) | `business_glossary.md` | RESOLVE selects wrong column for "why/reason" questions | Test 36 |
| **G4** — No synthesis guidance for multi-aspect questions | `bpom-analyst/SKILL.md` GENERATE | Agent produces N separate tables instead of integrated insight | Tests 17, 20, 24 |

---

## 4. Expected State After Changes

The agent should be able to reason as follows, without relying on a pre-existing recipe:

| Situation | Expected reasoning | Expected output |
|---|---|---|
| "Tren NIE per daerah dan tahun" | "2 dependent dimensions → 1 query with GROUP BY tahun, daerah" | One table: daerah × tahun matrix |
| "Produk apa yang paling banyak dibatalkan?" | "Subject is 'produk' in ranking context = GROUP BY nama_kategori" | Ranked list: category name + cancellation count |
| "Alasan pembatalan izin edar?" | "User asks 'why' → use reason column (`jenis_penolakan_komitmen`), not workflow column (`status`)" | Top reasons with counts, no status code noise |
| "Wilayah prioritas pengawasan berdasarkan risiko, pertumbuhan, dan pembatalan" | "3 independent dimensions → 3 queries → find categories appearing in multiple results" | Integrated priority list: entities at intersection of high risk + high cancellation + high growth |

The key shift: **from "find the matching recipe" to "derive the query structure from what the
question is asking for"**.

---

## 5. Proposed Changes

### 5.1 `seeknal/skills/bpom-analyst/SKILL.md`

**Type of change:** ADD content to three existing phases

---

#### 5.1.1 Addition to PHASE 1 — CAPTURE: Multi-Dimensional Decomposition Pattern

**Where to add:** After step 3 (identify ENTITY · OPERATION · DIMENSION · CONDITION)

**What to add:** A thinking pattern that teaches the agent how to decompose any
multi-dimensional question into a query strategy.

**Design note — intentional overlap with `intent_mapping.md` §5.2:**
The "Subject Determines Granularity" principle appears in both SKILL.md CAPTURE and
in `intent_mapping.md`. This is intentional but with a clear division of responsibility:

- **SKILL.md CAPTURE** (here): states the principle *concisely* as a thinking anchor,
  so it is always active when the skill runs — even if the agent skips loading
  `intent_mapping.md` in RESOLVE.
- **`intent_mapping.md`** (§5.2): provides the *full mapping table with examples*
  as the authoritative reference.

SKILL.md does NOT duplicate the mapping table. It states the principle and
cross-references intent_mapping.md for the details.

**Content:**

```
Multi-Dimensional Decomposition (apply after identifying all dimensions):

Step A — Count the dimensions the user is asking for simultaneously.
  A dimension is anything that requires a separate GROUP BY column:
  time (tahun/bulan), location (daerah), risk (risiko), scale (skala),
  category (kategori pangan), system (ERBA/ERLA), etc.

Step B — Classify the relationship between dimensions:

  DEPENDENT dimensions: the user wants a result that crosses both at once.
    Signals: "per X dan Y", "tren per X", "X berdasarkan Y per tahun"
    → One query with GROUP BY dim1, dim2 (multi-column GROUP BY)
    → One row in the result = one combination of (dim1, dim2)

  INDEPENDENT dimensions: the user wants each dimension reported separately.
    Signals: "berdasarkan risiko, skala, dan tren" (three separate aspects)
    → N queries, one per dimension
    → Synthesize results in GENERATE phase

Step C — Determine granularity from the question's SUBJECT noun.

  The subject noun determines what one row of output represents — and therefore
  what the GROUP BY column must be.

  Core principle:
  - "Berapa" / scalar questions → no GROUP BY name column needed
  - "Apa" / "Mana" in a ranking or listing context → GROUP BY the label column
    of the named entity (the subject is what the user wants to see as output rows)

  Rule: "Produk apa yang paling X" → the subject is "produk" as a category →
  GROUP BY nama_kategori (not COUNT total, not individual product rows)

  For the full mapping table (subject noun → GROUP BY column for each entity type),
  see `context/intent_mapping.md` §Question Decomposition — Subject Determines Granularity.

Step D — Determine if one query can satisfy all dependent dimensions.

  YES — one query is possible if:
  - All dimensions come from the same table source (e.g., both from ERBA+ERLA UNION)
  - Dimensions do not require contradictory filter logic

  NO — split into multiple queries if:
  - One dimension requires ERBA-only (e.g., risiko via kategori_dokumen)
    while another requires ERBA+ERLA combined (e.g., skala industri)
  - The incompatible scopes cannot be combined in a single WHERE clause
  → Write one query per dimension, then synthesize in GENERATE
```

**Why this fixes the problem:** The agent no longer depends on finding a recipe that
covers the exact dimension combination. It derives the GROUP BY structure from the
question's subject and dimension count — which generalizes to any combination.

---

#### 5.1.2 Addition to PHASE 2 — RESOLVE: Column Purpose Reasoning

**Where to add:** After the information taxonomy table, before the RESOLVED CONSTRUCTS block

**Design note — separation of concerns between SKILL.md and business_glossary.md:**

The content for this section divides into two distinct types:

| Type | What it is | Where it belongs |
|---|---|---|
| **Reasoning pattern** (generic) | "WHY questions → reason column; STATUS questions → workflow column" | `bpom-analyst/SKILL.md` RESOLVE (here) |
| **Domain knowledge** (specific) | "jenis_penolakan_komitmen = alasan; status = workflow stage" | `business_glossary.md` §Column Purpose Guide (§5.3) |

SKILL.md carries only the **general principle**. When the agent needs to know *which
specific column* stores the reason or the workflow stage, it references `business_glossary.md`
(already loaded in Phase 0). This keeps SKILL.md free of domain-specific column lists that
change as the schema evolves.

**What to add to SKILL.md RESOLVE (general principle only):**

```
Column Purpose Check (apply before writing any SQL):

Before selecting a column, ask: "What kind of information is this column storing?"
The same column can look relevant to a question but serve a different purpose.

Three column purpose categories:

  PURPOSE: WORKFLOW STATE — answers "What stage is this record in?"
    These columns track where a record is in a process.
    Use for: filtering by current status, counting by stage
    Do NOT use for: answering "why" or "what reason"

  PURPOSE: REASON / DESCRIPTION — answers "Why did this happen?"
    These columns store the explanation or rejection reason.
    Use for: answering "alasan", "mengapa", "penyebab" questions
    Do NOT confuse with: workflow state columns (different purpose entirely)

  PURPOSE: CLASSIFICATION — answers "What category/level is this?"
    These columns classify a record into a business taxonomy (risk, scale, type).
    Use for: filtering by risk level, grouping by category
    Note: the same column name can carry different codes in ERBA vs ERLA

To find which specific column serves which purpose for BPOM domain:
→ load `context/business_glossary.md` §Column Purpose Guide

CRITICAL for "alasan/mengapa" questions: the `status` column is a WORKFLOW STATE
column. Status code values (0999, 9999, 0009) are processing stages, NOT reasons.
When the user asks "what is the most common reason", never report status codes as
"uncategorized reason codes" — they are irrelevant to the answer.
```

**Why this fixes the problem:** The SKILL.md teaches the reasoning principle (how to
classify column purposes), while business_glossary.md teaches the domain facts (which
columns belong to which category). Together they prevent the agent from mixing workflow
columns with reason columns — without requiring the skill to hardcode every column name.

---

#### 5.1.3 Addition to PHASE 6 — GENERATE: Synthesis Patterns + Output Completeness Check

**Where to add:** At the beginning of Phase 6, before formatting rules

**What to add:** Two components — an output completeness check and synthesis patterns.

**Content:**

```
Output Completeness Check (answer these before writing):

1. "Does the output directly answer the question?"
   - If user asked "which" or "what" → output must NAME the entity, not just count it
   - If user asked "tren per X" → output must show X and time together, not separately
   - If user asked about "prioritas" / "what to focus on" → output must name the priority,
     not just present raw numbers for the user to interpret

2. "Are all requested dimensions represented in the output?"
   - Count the dimensions in the question
   - Verify each dimension appears as a column or grouping in the output
   - If a dimension is missing → the answer is incomplete

3. "For multi-query results: is there a synthesis?"
   - If N queries were run for N independent dimensions → combine results into one answer
   - Apply the synthesis pattern below before presenting separate tables

Synthesis Patterns (for multi-query, multi-dimension results):

Pattern A — Priority / Pengawasan questions:
  After obtaining N result sets for N dimensions (e.g., risiko, skala, pembatalan):
  1. Identify entities (daerah, kategori pangan) that appear prominently in ≥ 2 result sets
  2. These intersections are the highest-priority findings — present them first
  3. Example: "Kabupaten Bantul appears in top-5 by risiko tinggi AND top-3 by pembatalan →
     highest priority for supervision"
  4. Follow with per-dimension breakdown tables for completeness

Pattern B — Ranking questions ("X yang paling banyak Y"):
  Output must be a ranked list: entity name, count, rank position.
  Format: 1. Entity A — N occurrences · 2. Entity B — M occurrences · ...
  Never summarize to a single total when the user asked for a ranking.

Pattern C — Trend × Dimension questions ("tren X per Y"):
  Output must show Y as rows and time as a nested breakdown, OR use a table
  where rows = Y values and columns = years.
  Never present the trend total and the dimension top-N as separate tables;
  they must be one integrated result.

Pattern D — Comparison questions ("X dibanding Y", "naik atau turun"):
  Present both values side by side, compute the difference, and state the direction.
  Format: "X: [value] · Y: [value] · Selisih: [delta] · [naik/turun N%]"
```

**Why this fixes the problem:** The agent has explicit guidance on what "complete" means
for different question types, and knows how to merge multiple query results into a single
coherent answer rather than presenting N separate tables.

---

### 5.2 `context/intent_mapping.md`

**Type of change:** ADD one section before existing Step 0

**Where to add:** Before "Step 0 — Normalize informal language & typos"

**What to add:** A "Question Decomposition" section that teaches how to read any business
question structurally before mapping individual words.

**Content:**

```markdown
## Question Decomposition — Read the Structure Before the Words

Before normalizing typos or mapping entities, identify the four structural
components of the question. This determines what the query must produce.

| Component | Identifies | Determines |
|---|---|---|
| **Subject** | What entity is being asked about | Granularity of GROUP BY and output rows |
| **Predicate** | What the user wants to know about the subject | Metric column and aggregation function |
| **Modifier** | Conditions that restrict the scope | WHERE clause and filters |
| **Scope dimensions** | Additional axes the result must cover | Extra GROUP BY columns |

### Decomposition Examples

| Question | Subject | Predicate | Modifier | Scope dims |
|---|---|---|---|---|
| "Berapa NIE risiko tinggi?" | NIE | count | risiko tinggi | none → scalar |
| "Tren NIE per daerah dan tahun" | NIE trend | change over time | none | daerah + tahun |
| "Produk apa yang paling banyak dibatalkan?" | produk (=kategori) | dibatalkan count | paling banyak (TOP) | none → GROUP BY nama_kategori |
| "Daerah mana UMKM terbanyak?" | daerah | UMKM count | paling banyak | GROUP BY daerah |
| "Distribusi NIE risiko dan skala 10 tahun?" | NIE | distribution | 10 tahun terakhir | risiko + skala (independent) |

### Key Principle: Subject Determines Granularity

The subject noun controls what one row of output represents:

- "berapa" / "jumlah" → answer is a number (no GROUP BY name needed)
- "daerah mana" / "wilayah apa" → GROUP BY daerah_pabrik → resolve code to name
- "produk apa" / "kategori apa" → GROUP BY nama_kategori
- "perusahaan mana" → GROUP BY trader_id or nama_trader
- "tren" → GROUP BY date_trunc('year', col) — always, no exceptions

If the subject is "produk" in a ranking context ("produk apa yang paling X"):
→ the answer must name categories, not count total products.
→ USE: GROUP BY nama_kategori ORDER BY COUNT DESC LIMIT N
→ NOT: COUNT(*) as a single scalar, or a list of individual product rows

This decomposition runs BEFORE Step 0 typo normalization because it determines
what kind of answer the question requires — which shapes all subsequent steps.
```

**Why this fixes the problem:** The agent has an explicit framework for reading the
*structure* of any question, not just matching individual keywords. This generalizes
across all question types, including ones not previously seen.

---

### 5.3 `context/business_glossary.md`

**Type of change:** ADD one section about column purpose

**Where to add:** New section after the existing "Column distinctions to avoid confusion"
section, or merged into it as an extension

**What to add:** A "Column Purpose Guide" that teaches the purpose-vs-name distinction
for the most commonly confused columns.

**Content:**

```markdown
## Column Purpose Guide — What Question Does Each Column Answer

Columns are often confused because their names overlap semantically. This section
defines the *question each column answers* to prevent cross-purpose queries.

### Columns That Answer "What Stage Is This Record In?" (Workflow)

| Column | Table | Answers the question | Does NOT answer |
|---|---|---|---|
| `status` | ERBA + ERLA | "What is the current processing stage of this NIE?" | Why it was cancelled, or what kind of document it is |
| `status_komitmen` | ERBA only (MR) | "What is the current commitment stage for this MR product?" | Why the commitment was rejected |
| `status_produk` | ERBA | "What production type is this product?" (producer/makloon) | Risk level or document quality |

`status` is a workflow tracker. Values like `0999`, `9999`, `0906` are processing
stage codes. When a user asks about **reasons for cancellation**, the `status` column
is irrelevant — it tells you the *current state*, not the *reason*.

### Columns That Answer "Why?" (Reason / Description)

| Column | Table | Answers the question |
|---|---|---|
| `jenis_penolakan_komitmen` | ERBA only (MR) | "Why was this commitment rejected / cancelled?" |
| `jenis_penolakan_komitmen` + data_dictionary lookup | — | Resolves code to human-readable reason label |

When the user asks "apa alasan pembatalan" or "mengapa izin dibatalkan":
→ USE `jenis_penolakan_komitmen` + JOIN with `data_dictionary WHERE kategori = 'JENIS_PENOLAKAN_KOMITMEN'`
→ DO NOT explore `status` column values as potential reason codes
→ `status` values (0999, 9999, 0009) are NOT reason labels — they are stage codes

### Columns That Answer "What Is the Risk Level?" (Classification)

| Column | Table | Answers the question | WARNING |
|---|---|---|---|
| `kategori_dokumen` | ERBA | "What is the risk classification of this product?" (T / MT / MR) | ERBA code 301 = Tinggi |
| `jenis_dokumen` | ERLA | "What is the risk classification?" (via different codes) | ERLA code 301 = MR (opposite!) |

ERBA `kategori_dokumen = '301'` means **Risiko Tinggi**.
ERLA `jenis_dokumen = '301'` means **Risiko Menengah Rendah**.
The same code means the opposite across systems. Never use the same filter on both.

### Columns That Answer "What Type of Document Was Submitted?" (Document Routing)

| Column | Table | Answers the question |
|---|---|---|
| `jenis_dokumen` | ERBA + ERLA | "What document type was submitted for this application?" |

`jenis_dokumen` in ERBA is used for document routing (not risk level).
`jenis_dokumen` in ERLA carries risk information (different codes).
Do NOT use `jenis_dokumen` when the user asks about risk level in ERBA — use `kategori_dokumen`.
```

**Why this fixes the problem:** The agent learns the *purpose* of each column, not just
its name. When it encounters a "why/reason" question, it knows to use `jenis_penolakan_komitmen`
and knows that `status` codes are not relevant — without needing an explicit rule for every
possible question phrasing.

---

## 6. Files Not Modified

| File | Reason |
|---|---|
| `SEEKNAL_ASK.md` | Behavioral contracts already correct and enforced; modifying would risk breaking working rules |
| `context/query_recipes.md` | R1–R11 are sufficient 1D examples; adding 2D recipes creates hardcoded patterns that do not scale |
| `context/data_quality_rules.md` | Mandatory filter rules and cast rules are already correct |
| `context/code_resolution.md` | Region code conversion and dictionary join patterns are accurate |
| `context/forecast_guide.md` | Forecast table schema documentation is accurate |
| `context/data_architecture.md` | ERD, join rules, and UNION topology are correct |
| `seeknal/skills/evidence-auditor/SKILL.md` | Audit checklist is comprehensive and correct |
| `seeknal/skills/business-question-answering/SKILL.md` | Out of scope; synthesis patterns added directly to bpom-analyst |
| Test case files (`seeknal/tests/v1/`) | Oracle verification is a separate activity |

---

## 7. Design Decisions

### Why Thinking Patterns, Not More Recipes

Adding more recipes to `query_recipes.md` (R12 for 2D, R13 for ranking, etc.) would solve
individual cases but would not generalize. Business users ask questions in infinitely many
combinations. A recipe catalog that covers 20 patterns is still helpless in front of a novel
combination of those patterns.

Thinking patterns generalize because they operate on the *structure* of a question, not its
*specific words*. A pattern that says "subject noun determines GROUP BY column" works for any
subject — daerah, kategori, perusahaan, skala, or any future entity. A recipe for "top daerah
by NIE" only works for that exact question.

### Why These Three Files, Not Others

- `bpom-analyst/SKILL.md` owns the reasoning workflow; thinking patterns belong inline
  with the phase instructions so they are always active
- `intent_mapping.md` is the schema-linking layer — decomposition logic belongs here
  as it precedes the entity/dimension/operation mapping
- `business_glossary.md` is the domain knowledge anchor; column purpose is domain knowledge

The other context files (`data_quality_rules.md`, `code_resolution.md`) teach the agent
*what filters to apply* and *what codes mean* — they are data facts, not reasoning patterns.
Mixing reasoning patterns into those files would blur the distinction between "what is true"
and "how to reason about it".

### Why SEEKNAL_ASK.md Behavioral Contracts Are Not Changed

The behavioral contracts in `SEEKNAL_ASK.md` (registrasi→PERMOHONAN, no-year→all-time) are
absolute rules that must be active before any skill or context file loads. They are correctly
placed. Reasoning patterns, by contrast, are applied *within* skill phases after the session
has started. These two categories are architecturally separate.

---

## 8. Verification Approach

After implementation, verify by checking the reasoning quality (not just result correctness)
against three representative cases:

| Test case | What to verify | Signal of correct reasoning |
|---|---|---|
| "Tren NIE per lokasi pabrik dan tahun" | Agent derives GROUP BY tahun, daerah_pabrik as one query | PLAN phase shows one RESOLVED CONSTRUCTS with Shape: 2D year×daerah |
| "Produk MR apa yang paling banyak dibatalkan?" | Agent maps subject "produk" to GROUP BY nama_kategori | CAPTURE output shows OPERATION=RANKING, GROUP BY=nama_kategori |
| "Alasan pembatalan izin edar terbanyak?" | Agent uses jenis_penolakan_komitmen only; no mention of status codes as reasons | RESOLVE output identifies jenis_penolakan_komitmen as the reason column; no status column exploration |
| "Wilayah prioritas pengawasan berdasarkan risiko, pertumbuhan, dan pembatalan" | Agent identifies entities appearing across multiple dimensions | GENERATE output names intersecting entities before per-dimension tables |

The change is validated when the agent's **reasoning trace** (CAPTURE decomposition,
RESOLVE column selection, GENERATE synthesis) reflects the thinking patterns added —
not just when the final number is correct.

---

## 9. Summary of Changes

| File | Type | Section | What is Added |
|---|---|---|---|
| `seeknal/skills/bpom-analyst/SKILL.md` | ADD | CAPTURE Phase 1 | Multi-Dimensional Decomposition Pattern (Steps A–D) |
| `seeknal/skills/bpom-analyst/SKILL.md` | ADD | RESOLVE Phase 2 | Column Purpose Reasoning Check |
| `seeknal/skills/bpom-analyst/SKILL.md` | ADD | GENERATE Phase 6 | Output Completeness Check + 4 Synthesis Patterns |
| `context/intent_mapping.md` | ADD | Before Step 0 | Question Decomposition section (4-component framework + examples) |
| `context/business_glossary.md` | ADD | After column distinctions | Column Purpose Guide (workflow vs reason vs risk classification) |
