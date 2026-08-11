# Intent Mapping — Decomposition and Concept Typing

This file teaches the agent how to break a user turn into analytical structure.
It is a schema-linking and reasoning-support file, not an answer catalog.

---

## 1. Decompose Before You Resolve

Before resolving codes, fields, or tables, decompose the turn into:

- **Entity** — what is being counted, listed, compared, or described
- **Operation** — what the user wants done
- **Dimensions** — which axes the result must cover
- **Conditions** — what narrows or qualifies the scope
- **Time Scope** — explicit or implicit temporal scope

This decomposition should be stable across paraphrases.

---

## 2. Subject Controls Altitude

The subject of the question determines what one output row represents.

| Subject form | Likely altitude |
|---|---|
| scalar total | one number |
| trend | one period per row |
| breakdown by dimension | one category per row |
| ranking | one ranked category/entity per row |
| comparison | one compared bucket per row |
| list/search | one record per row |

The system must not answer a ranking question as a scalar total or a scalar question as an arbitrary list.

---

## 3. Dimension Relationship

If multiple dimensions are present, determine whether they are:

- **dependent** — must appear together in one crossed result,
- or **independent** — separate analyses that must later be synthesized.

Do not split a dependent question into unrelated one-dimensional answers.

---

## 4. Concept Type Model

Every important user concept must be classified before resolution.

| Concept type | Meaning | Typical resolution path |
|---|---|---|
| Business Event | defines what business state is being counted | business semantics first |
| Coded Classification | meaning depends on runtime code resolution | dictionary-grounded resolution |
| Direct Field | already represented by an explicit field | direct field |
| Master-Data Attribute | requires join to reference/master data | master-data join |
| Segment Discovery Concept | may require controlled discovery | discovery path |
| Cross-System Asymmetric Concept | differs across systems in code or granularity | per-system resolution |
| Conversation-Scope Reference | refers to prior scope or result | ledger/state |

This classification is required before SQL planning.

---

## 5. Normalization Rules

Normalize phrasing before interpretation:

- structural punctuation and bracket content do not change meaning,
- obvious typos should be normalized if meaning is clear,
- synonyms should map to the same conceptual slot,
- implicit references should be resolved from conversation state rather than guessed fresh.

Do not inject raw user phrasing directly into SQL as a substitute for meaning resolution.

---

## 6. Resolution Order

For a data question:

1. Decompose the turn
2. Lock the business event
3. Classify each major concept by type
4. Determine whether clarification is required
5. Choose the authoritative source path
6. Only then plan the query

---

## 7. Time Scope Rules

Time words affect scope and shape, not entity identity.

General rules:

- explicit year or range overrides defaults,
- no year stated means all available data,
- trend requests imply time breakdown,
- month-level requests use month-level granularity,
- follow-up references such as "that year" or "same period" resolve from the active topic.

---

## 8. Follow-Up Interpretation

A follow-up must be classified as one of:

- same topic, modified scope
- same topic, extended scope
- provenance/explanation request
- new topic

Do not assume every short follow-up continues the same interpretation.

### Follow-up stop rule

Not every follow-up needs another clarification.

Stop follow-up questioning when:

- entity is already locked,
- business event is already locked,
- source path is already singular,
- the remaining ambiguity changes wording only, not the data result,
- or the user has already confirmed the needed binding in the active topic.

Ask one more follow-up only when the remaining ambiguity still changes:

- the counted entity,
- the business event,
- the authoritative system/path,
- or the final result meaning.

If the same ambiguity persists after two clarification rounds in one topic, stop and answer with a limitation instead of looping.

---

## 9. Anti-Pattern

Do not teach the agent with:

- giant banks of named-question mappings,
- product-by-product shortcut lists as the main operating method,
- or examples that silently bypass concept typing.

The purpose of this file is to support generalizable decomposition and classification.
