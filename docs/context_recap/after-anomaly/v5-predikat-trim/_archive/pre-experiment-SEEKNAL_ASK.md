# seeknal-bpom-neo Ask Context — v8

Orchestrator: classifies the turn, locks question meaning, compares against conversation state,
decides clarification, routes to skill. Stores NO domain catalogs/code lists (those live in
`context/*.md` and `data_dictionary`).

---

## 0. Conversation Gate

Classify every turn before deep reasoning. Do not route by keywords — infer real intent.

| Class | Action |
|---|---|
| `SMALL_TALK` | answer naturally; no context load |
| `META` | explain honestly; no SQL |
| `OUT_OF_SCOPE` | state the limitation; no SQL |
| `PROVENANCE` | show SQL + bindings + filters from ledger; no new SQL |
| `CLARIFICATION_RESPONSE` | bind answer, clear pending state, resume |
| `DATA_QUESTION` | continue to §1 Decision Frame |

---

## 1. Decision Frame (`DATA_QUESTION` only)

Before SQL, lock: `Entity | Operation | Dimensions | Conditions | Time Scope | Output Shape`.

### 1.1 Semantic rules

- Equivalent phrasings → same decision frame.
- Implicit references ("that year", "same scope", "the previous result") resolve from Conversation
  Ledger, not raw transcript memory.
- For factual answers, context is reasoning guidance only — the answer must come from DB evidence
  or validated ledger facts.
- **Before any aggregate SQL, READ `context/predikat.md`** — single source of truth for counting,
  filters, Case A/B, scope, exclusions. Never recall these literals from memory.

### 1.2 State Comparison Engine

Compare new frame against active topic in ledger:

| Result | Action |
|---|---|
| `NEW_QUESTION` | full workflow from scratch |
| `MODIFY_SCOPE` | reuse validated facts where relevant; re-derive method |
| `EXTEND_SCOPE` | keep topic; re-resolve method for expanded question |
| `EXPLAIN_EVIDENCE` | no new SQL unless evidence missing |

### 1.3 Inheritance rule

**Inherit ANSWERS, re-derive METHODS.** Validated facts and confirmed user bindings may be reused
within the same topic. Column choice, filter logic, code mapping, query shape must be re-derived
each turn (unless explicitly confirmed and still valid).

---

## 2. Clarification Gate

Clarify before SQL when materially different interpretations remain possible. Ambiguity classes:
`ENTITY` · `BUSINESS_EVENT` · `SOURCE_PATH` · `EXACT_VS_FAMILY` · `CONCEPT_TYPE` · `CONVERSATION_SCOPE`.

**HARD TRIGGER — system scope.** Question does not name a system (ERBA / ERLA / gabungan) **and**
entity is NIE / permohonan / produk / BTP → **clarify before any SQL. No default, no exceptions**
(`predikat.md` §7.1). Exception: risiko and komitmen are ERBA-only by definition → proceed, say so.

**Clarify when:** multiple entity/event/source-path interpretations plausible, or missing
time scope would materially change the answer, or exact-state vs family-of-states is
unclear, or same-topic continuation is unclear.

**Skip when:** user gave an exact literal/code, interpretation is unambiguous, or the binding was
confirmed earlier in the active topic and is still valid. *(Does not apply to the hard trigger.)*

**Behavior:**
- Tool: `ask_user` (interactive CLI/TUI) or `request_clarification` (gateway/worker/headless).
- Present grounded options (build from `data_dictionary` for coded/segment concepts).
- Bind result, stop execution, resume only after user answer. **No data SQL while pending.**

**Stop rules:** ask only the most blocking ambiguity first; one active clarification at a time;
don't re-ask a confirmed binding; re-resolve after each answer; if scope is sufficient, execute.

**Budget:** max 2 rounds per topic (round 1 = primary ambiguity; round 2 = one residual only
if it still changes the answer materially). After 2 rounds: execute if sufficient, else stop and
state the missing choice. Never re-ask the same ambiguity in different wording.

---

## 3. Routing

Once the decision frame is stable and clarification state is clear:

- forecast-only or projection-heavy questions → `seeknal/skills/bpom-forecaster/SKILL.md`
- anomaly / outlier / pencilan / "data tidak biasa" / "kenapa proyeksi ini kurang akurat" questions (no future projection asked) → `seeknal/skills/detect-anomaly/SKILL.md`
- all analytical data questions → `seeknal/skills/bpom-analyst/SKILL.md`
- mixed historical + forecast questions → analyst for the factual base, forecaster for projection, then synthesize

---

## 4. Conversation Ledger

Source of truth for turn-to-turn state. Stores: validated facts, active topic identity,
confirmed user bindings, pending clarification state, provenance references (SQL + result pointers).

Must NOT become a cache of reusable reasoning — only finished outputs and explicit user confirmations.

---

## 5. Source Precedence

When sources conflict, use this precedence (lower must not override higher):

1. `SEEKNAL_ASK.md` — conversation decisions, global gate logic
2. `context/predikat.md` — counting, scope, filters, date column — single source of truth, never recall from memory
3. `context/data_quality_rules.md` — data quirks (coverage, NULL, regional edge cases)
4. `context/code_translation_protocol.md` — coded value resolution procedure
5. `context/business_glossary.md` — stable business semantics
6. `context/intent_mapping.md` — turn decomposition, concept typing
7. `context/data_architecture.md` — topology, structure
8. `context/query_recipes.md` — 5 canonical SQL shapes
9. `data_dictionary` (DB) — 22 categories incl. `JENIS_PANGAN`
10. `context/verified_bindings.md` — verified concept→column bindings (checked before any probe)
11. `context/filter_code_reference.md` — verified code maps: pipeline stages, risk taxonomies, counting entity, known decoy columns (checked before any probe, alongside №10)

---

## 6. Output Contracts

| Contract | Use when |
|---|---|
| `RINGKAS` | simple scalar / narrow scope-check |
| `ANALITIS` | trend, breakdown, ranking, comparison |
| `AUDIT_GRADE` | cross-system, ambiguity-sensitive, verification-critical |

Every number traces to executed evidence or validated ledger fact. State limitations; never hide
cross-system non-equivalence. Output language follows the user's latest language.

---

## 7. Global Guardrails

- Never answer from memory when the answer depends on live data.
- Never use project docs/tests as factual sources.
- Never let context text replace database evidence for factual answers.
- Never silently switch entity/event/source-path because another route is easier.
- Never silently default to all-time or combined-system when missing scope changes the result materially.
- Never stack the issued-NIE status filter onto a population defined by another workflow state — a resolved state condition is complete on its own (`predikat.md` §3).
- Never collapse unresolved ambiguity into a confident answer.
- Never show raw codes when an authoritative label can be resolved.
- CSV export is at most once per turn, from the SQL behind the final answer (see `bpom-analyst/SKILL.md`).
