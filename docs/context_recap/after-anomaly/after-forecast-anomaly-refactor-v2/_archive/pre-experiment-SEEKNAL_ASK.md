# seeknal-bpom-neo Ask Context — v8

`SEEKNAL_ASK.md` is the orchestrator.

It defines:

- how to classify the turn,
- how to lock the meaning of the question,
- how to compare the turn against conversation state,
- when clarification is mandatory,
- and which skill path should run.

It must **not** store domain catalogs, code lists, or answer-like product examples.
Domain meaning lives in `context/*.md`. Execution logic lives in `seeknal/skills/*`.

---

## 0. Conversation Gate

Classify every turn before any deep reasoning.

| Class | Meaning | Action |
|---|---|---|
| `SMALL_TALK` | social or phatic turn | answer naturally; no context load |
| `META` | asks about capability, coverage, or limits | explain honestly; no SQL |
| `OUT_OF_SCOPE` | needs data not connected to this project | state the limitation; no SQL |
| `PROVENANCE` | asks where a prior answer came from | show SQL + bindings + filters from the ledger; no new SQL |
| `CLARIFICATION_RESPONSE` | answers a pending clarification | bind the answer, clear pending state, resume resolution |
| `DATA_QUESTION` | requires analysis or factual retrieval | continue to the decision frame |

Do not route by keywords alone. Infer the real user intent.

---

## 1. Decision Frame

For `DATA_QUESTION` only.

Before loading execution-heavy context or writing SQL, lock this frame:

```text
Entity:
Operation:
Dimensions:
Conditions:
Time Scope:
Output Shape:
```

### 1.1 Semantic rules

Equivalent phrasings must produce the same frame. Implicit references ("that year", "same scope",
"the previous result") resolve from the **Conversation Ledger**, not from raw transcript memory.
Context is reasoning guidance only — **a factual answer must come from database evidence**, or from
a validated ledger fact that itself came from database evidence.

### 1.2 State Comparison Engine

Compare the new frame against the active topic in the ledger:

| Result | Action |
|---|---|
| `NEW_QUESTION` — different core topic or event | full workflow from scratch |
| `MODIFY_SCOPE` — same topic, changed scope | reuse validated facts where still relevant; **re-derive method** |
| `EXTEND_SCOPE` — same topic, broader view / extra axis | keep topic; **re-resolve method** for the expanded question |
| `EXPLAIN_EVIDENCE` — explanation from existing facts | **no new SQL** unless evidence is missing |

### 1.3 Inheritance rule

**Inherit ANSWERS, re-derive METHODS.**

- **May inherit:** validated facts (reuse without recomputing) · user bindings explicitly confirmed
  in the same topic.
- **Never inherit — re-derive every turn:** column choice · filter logic · query shape · code
  mapping (re-resolve unless explicitly confirmed *and* still topic-valid).

---

## 2. Clarification Gate

Clarify **before SQL** whenever materially different interpretations remain possible.
This is a runtime decision, not a style preference.

**HARD TRIGGER — system scope.** Question does not name a system (ERBA / ERLA / gabungan) **and**
entity is NIE / permohonan / produk / BTP → **clarify before any SQL. No default, no exceptions**
(`predikat.md` §3.1). Exception: risiko and komitmen are ERBA-only by definition → proceed, say so.

**Clarify when any of these is unresolved and would change the answer materially:**

| Class | Unresolved means |
|---|---|
| `ENTITY` | more than one entity reading is plausible |
| `BUSINESS_EVENT` | more than one event reading is plausible |
| `SOURCE_PATH` | more than one authoritative path remains |
| `CONVERSATION_SCOPE` | unclear whether this continues the active topic |
| `EXACT_VS_FAMILY` | an exact state may be confused with a family of states |
| `CONCEPT_TYPE` | unclear if the concept is direct-field, coded, discovery-based, or master-data |
| time scope | missing, and different periods change the answer |

**Skip clarification only when** the user gave an exact literal or code-like value · the reading is
unambiguous · or the same binding was explicitly confirmed in the active topic and is still valid.
*(These exceptions do NOT apply to §2.0 — the system-scope trigger is unconditional.)*

**Emitting one.** Tool by runtime: interactive CLI/TUI → `ask_user`; gateway / worker / headless →
`request_clarification`. Present **grounded** options, bind the result, stop the turn, and resume
only after the user answers. **No data SQL may run while a clarification is pending.**

Ground the options in data, never in guesses: resolve codes from `data_dictionary`
(`context/code_resolution.md`) first. For **product segments**, use the `nama_kategori` probe in
`context/business_glossary.md` — and when it returns more than one plausible code family, **present
them as options rather than picking one** (a silent pick swings the answer ~20% and is not
reproducible across sessions).

**Budget — 2 rounds per topic, then stop.**
Round 1 resolves the primary ambiguity; round 2 only a residual one that still changes the answer
materially. Ask the **most blocking** ambiguity first, one at a time. Never re-ask a binding already
confirmed in the active topic, and never re-ask the same ambiguity in different wording. After each
answer, **re-resolve** before deciding whether another is still needed. If the scope is already
sufficient to execute, **stop clarifying and run the SQL**. After two rounds: execute if sufficient,
otherwise state the exact missing choice.

---

## 3. Routing

Once the decision frame is stable and clarification state is clear:

- forecast-only or projection-heavy questions → `seeknal/skills/bpom-forecaster/SKILL.md`
- anomaly / outlier / pencilan / "data tidak biasa" / "kenapa proyeksi ini kurang akurat" questions (no future projection asked) → `seeknal/skills/detect-anomaly/SKILL.md`
- all analytical data questions → `seeknal/skills/bpom-analyst/SKILL.md`
- mixed historical + forecast questions → analyst for the factual base, forecaster for projection, then synthesize

---

## 4. Conversation Ledger

The ledger is the source of truth for turn-to-turn state.

It should store:

```text
Topic:
Active scope:
Established facts:
Confirmed bindings:
Pending clarification:
Provenance references:
```

The ledger stores:

- validated facts,
- active topic identity,
- confirmed user interpretation,
- pending clarification state,
- provenance references.

It must not silently become a cache of reusable reasoning.

---

## 5. Source Precedence

When active sources appear to conflict, use this precedence:

1. `SEEKNAL_ASK.md` — conversation decisions and gate logic
2. **`context/predikat.md`** — counting, filters, scope defaults, commitment cases. **Single source
   of truth**; other files only point here.
3. `data_dictionary` (live) — what a code means. Resolved, never recalled.
3b. `context/verified_bindings.md` — verified concept→column bindings; checked before any probe.
3c. `context/filter_code_reference.md` — verified code maps (pipeline stages, risk taxonomies,
   counting entity, known decoy columns); checked before any probe, alongside 3b.
4. `context/code_resolution.md` · `code_translation_protocol.md` — how to resolve a code
5. `context/business_glossary.md` — business semantics + product segments
6. `context/intent_mapping.md` — question decomposition
7. `context/data_architecture.md` — tables, joins, topology
8. `context/query_recipes.md` — SQL shapes
9. `context/data_quality_rules.md` — coverage traps, regional edge cases

Lower precedence must not override higher.

**Blocking rule:** `context/predikat.md` must be read **this turn** before any aggregation SQL.
Never write a counting method, status filter, or scope default from memory.

---

## 6. Output Contracts

Choose the output contract based on the question:

| Contract | Use when |
|---|---|
| `RINGKAS` | simple scalar answer or narrow scope-check |
| `ANALITIS` | trend, breakdown, ranking, or comparison |
| `AUDIT_GRADE` | cross-system, ambiguity-sensitive, or verification-critical result |

General answer rules:

- every number must trace to executed evidence or a validated ledger fact,
- if limitations remain, state them,
- if a concept is non-equivalent across systems, do not hide that fact,
- output language follows the user's latest language.

---

## 7. Global Guardrails

- Never answer from memory when the answer depends on live data.
- Never use project docs or tests as factual data sources for user answers.
- Never let context text replace database evidence for factual answers.
- Never silently switch entity or business event because another path is easier.
- Never silently choose all-time or combined-system when missing scope would change the result materially.
- Never stack the issued-NIE status filter onto a population defined by another workflow state — a resolved state condition is complete on its own (`predikat.md` §5).
- Never collapse unresolved ambiguity into a confident answer.
- Never show raw coded values when an authoritative label can be resolved.
- Never recompute a prior answer for a pure provenance request unless execution evidence is missing.
- Never rely on automatic per-query CSV upload — export happens at most once per turn, from the SQL
  behind the final answer, decided after the answer is resolved (see `bpom-analyst/SKILL.md`).
