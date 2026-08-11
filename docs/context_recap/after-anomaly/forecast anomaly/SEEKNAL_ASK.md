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

- Equivalent phrasings should produce the same decision frame.
- Implicit references such as "that year", "same scope", or "the previous result" are resolved from the Conversation Ledger, not from raw transcript memory.
- For factual answers, context is reasoning guidance only. The answer itself must come from database evidence or validated ledger facts that originally came from database evidence.

### 1.2 State Comparison Engine

Compare the new frame against the active topic in the ledger.

| Result | Meaning | Action |
|---|---|---|
| `NEW_QUESTION` | different core topic or event | full workflow from scratch |
| `MODIFY_SCOPE` | same topic, changed scope | reuse validated facts only where still relevant; re-derive method |
| `EXTEND_SCOPE` | same topic, broader view or extra axis | keep topic; re-resolve method for the expanded question |
| `EXPLAIN_EVIDENCE` | user wants explanation from existing validated facts | no new SQL unless evidence is missing |

### 1.3 Inheritance rule

| Thing | May inherit? | Rule |
|---|---|---|
| Validated fact | yes | may reuse without recomputing |
| Confirmed user binding | yes | may reuse within the same topic |
| Column choice | no | re-derive |
| Filter logic | no | re-derive |
| Code mapping | no | re-resolve unless explicitly confirmed and still topic-valid |
| Query shape | no | re-derive |

**Inherit ANSWERS, re-derive METHODS.**

---

## 2. Clarification Gate

Clarification is a runtime decision, not a style preference.

The system must clarify before SQL when materially different interpretations remain possible.

Minimum ambiguity classes:

- `ENTITY`
- `BUSINESS_EVENT`
- `SOURCE_PATH`
- `EXACT_VS_FAMILY`
- `CONCEPT_TYPE`
- `CONVERSATION_SCOPE`

### 2.1 Mandatory clarification cases

Clarify when:

- more than one entity interpretation is plausible,
- more than one business event is plausible,
- more than one authoritative source path remains,
- time scope is missing and different periods would materially change the answer,
- source scope is missing and `ERBA` / `ERLA` / combined would materially change the answer,
- an exact state may be confused with a family of states,
- it is unclear whether the concept is direct-field, coded, discovery-based, or master-data based,
- or it is unclear whether the user is continuing the same topic.

### 2.2 Clarification exceptions

Skip clarification only when:

- the user already gave an exact literal or exact code-like value,
- the interpretation is unambiguous from the question,
- or the same binding was explicitly confirmed in the active topic and is still valid.

### 2.3 Clarification behavior

Use the clarification tool that matches the runtime:

- interactive CLI/TUI -> `ask_user`
- gateway / worker / headless -> `request_clarification`

When clarification is emitted:

- present grounded options,
- bind the result,
- stop execution for the turn,
- resume resolution only after the user answer arrives.

No data SQL may run while pending clarification exists.

For coded or segment-like concepts, a light discovery pass from
`context/source_discovery_protocol.md` may be used first to build grounded clarification options.

### 2.4 Follow-up stop rule

Clarification must not become an open-ended conversation loop.

Apply these rules:

- ask only the most blocking ambiguity first,
- keep only one active clarification at a time,
- do not ask again for a binding already confirmed in the active topic,
- after each clarification answer, re-resolve before deciding whether another clarification is still needed,
- if the scope is already sufficient to execute, stop clarifying and continue to SQL.

### 2.5 Clarification budget

Per topic, use at most:

- round 1 -> resolve the primary ambiguity,
- round 2 -> resolve one residual ambiguity only if it still changes the answer materially.

After two clarification rounds:

- execute if the scope is already sufficient,
- otherwise stop and state the exact missing choice needed from the user,
- never re-ask the same ambiguity in different wording.

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

1. `SEEKNAL_ASK.md` — conversation decisions and global gate logic
2. `context/data_quality_rules.md` — mandatory correctness rules
3. `context/source_discovery_protocol.md` — runtime discovery before binding or combining
4. `context/code_translation_protocol.md` — coded value resolution procedure
5. `context/business_glossary.md` — stable business semantics
6. `context/intent_mapping.md` — turn decomposition and concept typing
7. `context/data_architecture.md` — topology and structure
8. `context/query_recipes.md` — post-resolution execution frameworks

Lower-precedence guidance must not override higher-precedence rules.

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
- Never collapse unresolved ambiguity into a confident answer.
- Never show raw coded values when an authoritative label can be resolved.
- Never recompute a prior answer for a pure provenance request unless execution evidence is missing.
- Never rely on automatic per-query CSV upload — export happens at most once per turn, from the SQL
  behind the final answer, decided after the answer is resolved (see `bpom-analyst/SKILL.md`).
