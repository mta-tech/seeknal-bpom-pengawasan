# seeknal-bpom-neo: Context Simplification & Follow-up Protocol

**Date:** 2026-06-24
**Reference documents:**
- `docs/planning/2026-06-09-decision-operating-system.md` — Decision OS architecture; paradigm shift from lookup engine to reasoning framework
- `docs/planning/2026-06-11-follow-up-inheritance-refinement.md` — "Inherit ANSWERS, re-derive METHODS"; multiturn regression root cause
- `docs/planning/2026-06-19-execution-discipline-and-trust-transparency.md` — Execution discipline, source precedence, proportionality rule
- `docs/planning/2026-06-22-clarification-gate-and-grounded-disambiguation.md` — Clarification Gate, Grounded Disambiguation Policy, CLARIFY_FIRST vs DIRECT_EXECUTION

**Principle (unchanged, non-negotiable):** we do **not** hardcode answers or question-specific SQL.
The system must be taught a **general reasoning method**: when to clarify, what to clarify, which
authoritative source to consult, how to choose a path, when to stop, and how to state assumptions
honestly. The goal is an agent that generalizes to unseen phrasing, larger schemas, and future
tables without turning the context into a static catalog.

**Flow (unchanged at the top level):** `SEEKNAL_ASK.md` (orchestrator) → loads `context/*.md`
on demand → invokes `seeknal/skills/*`; docs live in `docs/`. What changes in this rework is
**the size and organization of the orchestrator and skill files** — not the architectural shell.

---

## 1. Why This Rework Is Needed

All prior planning documents introduced the correct ideas: Decision OS, semantic commitment,
inheritance rule, ambiguity gate, dictionary-grounded code translation. The improvements were
real and measurable.

However, **each rework added content without removing content**. The consequence is that
`SEEKNAL_ASK.md` and `seeknal/skills/bpom-analyst/SKILL.md` have grown through accretion to a
combined 918 lines — before a single context file is loaded. Including context files, the
agent reads approximately **3,540 lines** per conversation turn.

At this scale, the model cannot attend equally to all instructions. Critical rules get the same
weight as footnotes, and early-loaded content dominates over later-loaded content. The
**ambiguity gate** — one of the most important behavioral controls — is currently at line 151
of SEEKNAL_ASK.md, after 150 lines of decision layer text. By the time the model reaches it,
it is already cognitively committed to "answer mode."

### 1.1 Evidence From Test Runs (2026-06-23)

Multiturn test run with scenario `CLARIF-KOMITMEN-1`:
- Turn 1: prompt "berapa produk MR yang sudah selesai proses komitmennya?" → agent returned
  19,729 immediately (status IN 4, 7, 5). No clarification was issued. `passed=True` because
  `assert_contains: ["komitmen"]` is too weak to detect this failure mode.
- Root cause: the agent read PHASE 1 CAPTURE (seven sub-steps + decomposition), loaded three
  context files, entered RESOLVE, ran dict lookups — and by the time PHASE 1.5 CLARIFY was
  encountered, the method for the turn was already committed.
- The ambiguity gate instruction was present and correct. It was not followed because its
  **position** in the reading order made it arrive too late.

### 1.2 The Specific Structural Problems

| Problem | Location | Impact |
|---|---|---|
| §2 Behavioral Contracts (word→entity table) | `SEEKNAL_ASK.md` | Duplicates `intent_mapping.md`; adds 28 lines of hardcoded examples |
| §3 Schema State (table definitions, casts) | `SEEKNAL_ASK.md` | Duplicates `data_architecture.md` + `data_quality_rules.md`; 22 lines |
| §4 Product Segment Codes (AMDK, Garam, BTP) | `SEEKNAL_ASK.md` | Duplicates `business_glossary.md`; 35 lines of hardcoded codes |
| §5 Information Need Resolution (long table) | `SEEKNAL_ASK.md` | Already covered in SKILL.md PHASE 2; 30 lines of redundant routing |
| PHASE 1 sub-steps A–D (decomposition) | `SKILL.md` | Over-specification that replaces reasoning with a checklist; 25 lines |
| PHASE 2 (five paragraphs + table + SQL template) | `SKILL.md` | Prose-heavy; key "classify by TYPE" principle buried in narrative |
| PHASE 6 synthesis patterns (7 patterns, detailed) | `SKILL.md` | Each pattern is a paragraph; useful as reference but dilutes the core |

### 1.3 Two New Requirements

**Requirement 1 — Clarification Budget (dynamic, default 0):**
The clarification gate currently exists as a policy but has no runtime counter. The agent has
no formal mechanism to know: "I have already asked once this turn — I must now proceed."
The budget must be: (a) default 0 so the agent never interrupts unnecessarily, (b) set
dynamically when dict lookup detects material ambiguity, (c) maximum 1–2 rounds per question
depending on complexity, and (d) reset to 0 after a final answer is delivered. This is tracked
in the Conversation Ledger, not hardcoded by question type.

**Requirement 2 — PROVENANCE follow-up from user:**
When a user asks "dari mana data ini?", "data tersebut berasal dari mana?", "tampilkan query",
or "bagaimana cara menghitungnya?" — this is a **provenance request**, not a data question.
The system must: (a) recognize it as a distinct gate classification, (b) issue NO new SQL,
(c) show the actual SQL executed + the binding table + active filters from the Conversation
Ledger. The Ledger already stores `(from: <one-line query description>)` for every fact;
the PROVENANCE gate uses this to answer without any new computation.

---

## 2. Current-State Diagnosis

### 2.1 What the System Already Has (Do Not Change)

| File / Component | What it does | Status |
|---|---|---|
| `context/code_translation_protocol.md` | Two-way sumber-aware dict resolution; Path A/B for typo vs semantic family; binding table gate; §3 ambiguity loop with >20% gap rule | **Keep as-is.** This file is correct and should not be shrunk. |
| `context/business_glossary.md` | Business ontology, segment codes, commitment concepts, column purpose guide | **Keep as-is.** Facts belong here, not in the orchestrator. |
| `context/data_quality_rules.md` | Mandatory filters, ERBA casts, date-column rules, jenis_permohonan conditional, Case A/B commitment | **Keep as-is.** The canonical filter authority. |
| `context/data_architecture.md` | Table schema, column types, UNION topology, system handover | **Keep as-is.** Schema facts belong here. |
| `context/intent_mapping.md` | ENTITY/OPERATION/DIMENSION registry, Step 0 normalization, segment discovery | **Keep as-is.** Word-to-entity resolution belongs here. |
| `context/query_recipes.md` | Adaptive R1–R13 query templates | **Keep as-is.** Not a rigid catalog — agent adapts these. |
| Decision OS architecture | Conversation Gate → Decision Layer → Skill Workflow | **Unchanged.** The layered architecture is correct. |
| "Inherit ANSWERS, re-derive METHODS" | ANSWERS cross turns as trusted facts; METHODS re-derived every turn | **Unchanged.** This is the core anti-drift principle. |
| Conversation Ledger + SCE | SCE compares new intent vs Ledger state | **Unchanged.** The engine is correct; the Ledger format is extended (see §4). |
| PHASE 0–6 workflow in bpom-analyst | Phase structure for CAPTURE → RESOLVE → PLAN → EXECUTE → REFLECT → GENERATE | **Unchanged.** The phases are correct; only the volume of text per phase changes. |
| `seeknal/skills/bpom-forecaster/SKILL.md` | 6-phase forecast pipeline | **Unchanged.** Not in scope for this rework. |
| `seeknal/skills/evidence-auditor/SKILL.md` | Pre-answer audit checklist | **Unchanged.** Already concise. |

### 2.2 What Is Causing the Failures (Remove or Restructure)

| Problem | Root cause | Fix direction |
|---|---|---|
| Ambiguity gate not triggered | Gate arrives too late in reading order; agent already in "answer mode" | Move CLARIFY check to PHASE 1.5 (already there) but ensure PHASE 1 is SHORT so PHASE 1.5 is reached quickly |
| Orchestrator is too long (453 lines) | Content from context files duplicated into SEEKNAL_ASK.md over multiple iterations | Remove §2, §3, §4, §5 from SEEKNAL_ASK.md — those facts live in context files |
| SKILL.md too long (465 lines) | Each iteration added instructions without removing the ones they superseded | Rewrite PHASE 1 and PHASE 2 around principles, not sub-step checklists |
| No Clarification Budget | The gate decision exists but no counter prevents re-asking after budget is used | Add `Clarification Budget: N` to Conversation Ledger |
| No PROVENANCE classification | User asking "dari mana?" falls into DATA_QUESTION → triggers unnecessary SQL | Add PROVENANCE to §0 Conversation Gate |

---

## 3. What This Rework Is (and Is Not)

**This rework IS:**
- A clean rewrite of `SEEKNAL_ASK.md` and `seeknal/skills/bpom-analyst/SKILL.md`
- Removal of content that duplicates what is already authoritative in `context/*.md`
- Addition of two new mechanisms: Clarification Budget and PROVENANCE gate
- Reduction from 918 lines to approximately 340 lines for these two files combined
- Preservation of every working principle from all prior planning documents

**This rework IS NOT:**
- A change to `context/*.md` files (they are correct fact repositories — leave them alone)
- A change to the skill workflow phases (PHASE 0–6 structure is unchanged)
- A change to `seeknal/skills/bpom-forecaster/SKILL.md` or `evidence-auditor/SKILL.md`
- A change to test YAML files, test harness, or `.env` configuration
- Adding new examples, recipes, or hardcoded detection tables — the opposite

### 3.1 Why Context Files Are Not Rewritten

Context files (`context/*.md`) are **fact repositories loaded on demand** — they are NOT loaded
every turn. Only the three files in PHASE 0 mandatory load (`business_glossary.md`,
`data_quality_rules.md`, `code_translation_protocol.md`) are loaded every turn; others are
loaded only when the current turn needs them.

This means the attention-dilution problem that affects SEEKNAL_ASK.md and SKILL.md does NOT
apply to context files. A 476-line `forecast_recipes.md` is only in the model's context when
a forecast turn actually needs it — it does not compete with routing instructions.

The root cause of SEEKNAL_ASK.md's length problem is that it **duplicated** content from
context files (segment codes from `business_glossary.md`, cast rules from `data_quality_rules.md`,
schema tables from `data_architecture.md`). Removing those duplications from the orchestrator —
not shortening the authoritative source — is the correct fix.

### 3.2 Why evidence-auditor and bpom-forecaster Are Not Rewritten

**evidence-auditor (105 lines):** A verification checklist is intentionally granular and
specific. The principle "no hardcoding, teach how to think" applies to *reasoning* instructions,
not to *audit checklists*. A checklist that says "check `COUNT(DISTINCT)`" and "check `sumber`
predicate" is doing exactly what a checklist should do. 105 lines is appropriate for this role.

**bpom-forecaster (391 lines):** The forecaster is a **deterministic mathematical pipeline**
— eligibility check, 24-month backtest, SN+MA3 ensemble, intervals, 7-block output. Its detail
is intentional: the same formula must produce the same number across sessions (determinism
guarantee). This is different from the analyst, where over-specification replaces reasoning.
The forecaster has no "reasoning gap" — its gap would be wrong formulas, not excess examples.
If a forecaster regression is observed in future tests, a targeted rework will follow separately.

---

## 4. Specification: Conversation Ledger Extension

The Ledger currently holds:
```
Active scope:      entity=… · system=… · year=…
Established facts: - <number> = <scope> (from: <one-line query description>)
Pending:           <any unresolved clarification, or none>
```

**New field: `Clarification Budget`**

```
Active scope:         entity=… · system=… · year=…
Established facts:    - <number> = <scope> (from: <one-line query description>)
Pending:              <CLARIFICATION | class=… | term=… | options=[A, B]> or none
Clarification Budget: <N>
```

Rules for `Clarification Budget`:
- Default value: `0` (the agent never interrupts unless dict lookup proves ambiguity)
- Set to `1` when CLARIFY_FIRST is triggered by PHASE 1.5 ambiguity detection
- Set to `2` only for questions with multiple independent ambiguous dimensions
- After the user responds to a clarification → decrement by 1
- When Budget reaches `0` → proceed unconditionally; pick best interpretation; state assumption
- Reset to `0` after the system delivers a complete final answer (number or table)

This is a **maximum**, not a default. The agent does not ask because it *can* — it asks only
because the dict lookup *proved* that the two plausible interpretations would produce materially
different results (>20% gap, per `code_translation_protocol.md §3`).

---

## 5. Specification: PROVENANCE Gate

Add `PROVENANCE` as a new classification in §0 Conversation Gate.

**Trigger signals:** "dari mana data ini?", "data tersebut berasal dari mana?", "tampilkan query",
"query-nya apa?", "show the SQL", "bagaimana cara menghitungnya?", "dihitung bagaimana?",
"darimana angka ini?"

**Action:**
1. Do NOT run any new SQL.
2. Read the Conversation Ledger `Established facts:` section for the most recently established
   number relevant to the question context.
3. If the SQL from the most recent query is still in context (it is for short conversations),
   show it as a fenced ```sql code block.
4. Show the Binding Table used for that query (term → kode mappings).
5. Show the active filters from RESOLVED CONSTRUCTS for that turn.
6. Answer in user's language. Never include credentials or connection strings.

**SCE classification:** EXPLAIN_EVIDENCE (no new query is run; answer is derived from
already-validated Ledger facts and the query history available in context).

This is distinct from the existing guardrail "SQL transparency on request" — PROVENANCE is a
**gate classification** that routes the entire turn before reaching RESOLVE. The existing
guardrail remains as a fallback inside GENERATE for cases not caught at the gate.

---

## 6. Specification: SEEKNAL_ASK.md Structure (v5)

**Target: ~145 lines** (from 453 lines)

### What is removed

| Section | Lines | Reason for removal |
|---|---|---|
| §2 Behavioral Contracts (word→entity table) | 28 | Full duplicate of `context/intent_mapping.md` §ENTITY registry and Step 0 normalization |
| §3 Schema State (table definitions, cast rules) | 22 | Full duplicate of `context/data_architecture.md` (tables) and `context/data_quality_rules.md` (casts) |
| §4 Product Segment Codes (AMDK, Garam, BTP, Makloon, Canonical Definitions) | 35 | Full duplicate of `context/business_glossary.md` §Product Segment Codes and §Canonical Definitions |
| §5 Information Need Resolution (long two-column table) | 30 | Overlaps with SKILL.md PHASE 2 resolution table; the Source Precedence list is sufficient here |
| §7 Answer Contracts (long with verbose conditions) | 25 | Condensed into §4 Output Contracts (4-row table) |
| §8 Communication Alignment (long) | 20 | One-liner in §5 Guardrails; detail already in SKILL.md PHASE 6 |

### What is added

| Addition | Lines | Purpose |
|---|---|---|
| `PROVENANCE` classification in §0 Gate | 2 | New gate type for user provenance questions |
| `Clarification Budget: N` in Conversation Ledger | 2 | Runtime counter for clarification rounds |
| §4 Output Contracts (condensed from §7) | 10 | Replaces 25-line verbose version |

### Section map (v5)

```
§0   Conversation Gate          — 15 lines  (SMALL_TALK / META / OUT_OF_SCOPE / PROVENANCE / CLARIFICATION / DATA_QUESTION)
§0.5 Decision Frame             — 35 lines  (Semantic Commitment Block + SCE table + Inheritance Rule)
§0.7 Ambiguity Gate             — 22 lines  (CLARIFY_FIRST vs DIRECT_EXECUTION + Budget + format + Pending format + classes)
§1   Routing                    — 8 lines   (FORECAST → bpom-forecaster; else → bpom-analyst; mixed)
§2   Conversation Ledger        — 12 lines  (format including new Clarification Budget field)
§3   Source Precedence          — 10 lines  (6-priority ordered list)
§4   Output Contracts           — 10 lines  (RINGKAS / ANALITIS / AUDIT_GRADE + COUNT default)
§5   Guardrails                 — 10 lines  (8 one-liner rules including PROVENANCE + language)
────────────────────────────────────────────
Total                           ~122 lines
```

---

## 7. Specification: bpom-analyst SKILL.md Structure (v3)

**Target: ~200 lines** (from 465 lines)

### What is removed

| Section | Lines | Reason for removal |
|---|---|---|
| PHASE 1 sub-steps A–D (Multi-Dimensional Decomposition) | 25 | Over-specification. Replaced by one principle: "classify each dimension as DEPENDENT or INDEPENDENT." |
| PHASE 1 step 3 "Determine DOMAIN first via router" | 5 | Covered by §0 Gate OUT_OF_SCOPE; duplicates routing |
| PHASE 2 five prose paragraphs (re-derive explanation, provenance check, new-number-always-query, coverage check, source selection protocol) | 60 | Correct principles but verbose; condensed to the TYPE→Source table and the RESOLVED CONSTRUCTS block |
| PHASE 2 "what is needed / where to get it" long table | 15 | Condensed into TYPE→Source 6-row table |
| PHASE 2 product segment discovery SQL template | 8 | Moved to one line inside the TYPE→Source table row for "unknown segment" |
| PHASE 4 pre-submit 7-item checklist | 15 | Replaced by "verify against RESOLVED CONSTRUCTS block you wrote in PHASE 2" |
| PHASE 6 verbose synthesis pattern descriptions (7 patterns, paragraph each) | 50 | Condensed to one-liner per pattern |
| PHASE 6 Output Completeness Check verbose list | 12 | Condensed to 3 questions |
| PHASE 6 Communication Alignment prose | 15 | Covered in SEEKNAL_ASK.md §5 Guardrails |
| Honesty principles (long prose) | 10 | Condensed to 4 one-liners |

### What is added

| Addition | Lines | Purpose |
|---|---|---|
| PHASE 1.5 Step 3 explicit Budget = 0 branch | 2 | Previously the "proceed with assumption" path was implicit |
| PHASE 6 PROVENANCE turn handling | 3 | Explicit: if turn = PROVENANCE, show SQL + binding + filters from Ledger, no new query |

### Phase size targets (v3)

```
PHASE 0  Mandatory Context Load   — 12 lines
PHASE 1  CAPTURE                  — 18 lines
PHASE 1.5 CLARIFY                 — 22 lines
PHASE 2  RESOLVE                  — 30 lines  (TYPE table + Binding Table + RESOLVED CONSTRUCTS)
PHASE 3  PLAN                     — 8 lines
PHASE 4  EXECUTE                  — 10 lines
PHASE 5  REFLECT                  — 22 lines
PHASE 6  GENERATE                 — 35 lines  (3 questions + contract + synthesis patterns + ledger update)
Honesty                            — 5 lines
────────────────────────────────────────────
Total                             ~162 lines
```

---

## 8. Implementation Order

| Step | File | Action |
|---|---|---|
| 1 | `SEEKNAL_ASK.md` | Rewrite bersih: remove §2, §3, §4, §5; add PROVENANCE gate + Clarification Budget; condense §6→§5, §7→§4, §8 inline |
| 2 | `seeknal/skills/bpom-analyst/SKILL.md` | Rewrite bersih: trim PHASE 1 (remove A–D decomposition), PHASE 2 (condensed TYPE table), PHASE 4 (remove checklist), PHASE 6 (one-liner patterns); add Budget=0 branch + PROVENANCE handling |
| 3 | Run regression tests | Verify no singleturn UAT regression |
| 4 | Run clarification test | Verify `CLARIF-KOMITMEN-1` scenario now issues clarification in Turn 1 |

---

## 9. Acceptance Criteria

### Primary: Clarification gate fires

Scenario `CLARIF-KOMITMEN-1`, Turn 1: `"berapa produk MR yang sudah selesai proses komitmennya?"`

Expected behavior after this rework:
- Agent runs dict lookup for "selesai" under `STATUS_KOMITMEN`
- Lookup returns 0 exact matches → Path B (semantic family) → enumerate full `STATUS_KOMITMEN` category
- Multiple terminal codes qualify (4, 7, 5) → CLARIFY_FIRST → Budget set to 1
- Agent emits a clarification question naming the specific codes as options
- No SQL is run in Turn 1
- Turn 2: user selects one code → agent proceeds to RESOLVE with bound interpretation

### Secondary: No regression

```bash
# Singleturn UAT (must not regress from current pass rate)
uv run python scripts/test_multiturn_v3.py \
  --path seeknal/tests/v1/singleturn \
  --filter UAT

# Multiturn clarification scenario
uv run python scripts/test_multiturn_v3.py \
  --path seeknal/tests/v1/multiturn/UAT \
  --filter CLARIF-KOMITMEN-1
```

### Tertiary: Manual smoke tests

| Test | Expected result |
|---|---|
| Ask an ambiguous status question | Agent asks clarification (Turn 1), not SQL |
| Ask "dari mana data ini?" after an answer | Agent shows SQL + binding + filters from Ledger; no new query |
| Ask "kalau yang disetujui saja?" as follow-up | Inherit scope (MR, system=ERBA), re-derive method (kode 4 only), new SQL |
| Same question 3× in separate sessions | Identical numbers (Semantic Commitment determinism) |
| Simple scalar question | RINGKAS contract, DIRECT_LANE, ≤2 queries total |

---

## 10. Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Removing §3 Schema State breaks ERBA cast discipline | Low | Casts are authoritative in `data_quality_rules.md` (P2 precedence); SKILL.md PHASE 2 RESOLVED CONSTRUCTS block still lists them |
| Removing §4 Segment Codes breaks AMDK/Garam queries | Low | Codes are authoritative in `business_glossary.md` (P4 precedence); PHASE 0 loads glossary unconditionally |
| Shorter PHASE 2 causes RESOLVE to miss bindings | Medium | RESOLVED CONSTRUCTS block still mandatory before PLAN; its format is unchanged |
| Budget mechanism causes agent to ask when Budget=0 case is ambiguous | Low | Explicit "Budget=0 → pick best + state assumption" in PHASE 1.5 Step 3 |
| PROVENANCE gate misclassifies genuine follow-up data questions | Low | Trigger signals are narrow; ambiguous cases fall through to DATA_QUESTION and behave normally |
