# Code Translation Protocol — Runtime Procedure

This file teaches how coded meanings are resolved at runtime.
It does not store final answers.

---

## 1. Principle

A coded value is never assumed from memory when runtime resolution is required.

The agent must resolve:

- user concept -> candidate code(s)
- code(s) -> answer label(s)

through an authoritative procedure that produces a structured artifact the next step can depend on.

---

## 2. When This Protocol Applies

Use this protocol when the concept is a **coded classification**.

Do not use it as the primary path when the concept is:

- a direct field,
- a master-data attribute,
- a business-semantic rule,
- or a discovery-only segment concept.

Classify the concept type before deciding to use dictionary resolution.

---

## 3. Meaning-Carrier Resolution

Resolve by **meaning**, never by word-to-word synonym tables.

A term's meaning is matched against three meaning-carriers, in order:

1. `data_dictionary.label` — the dictionary's own description of meaning
2. column purpose — name, type, and schema comment of the column that carries the concept
3. value distribution — a small row sample confirming the code actually denotes the concept in real data

A match on any one carrier is a candidate. The carrier that produced a match must be recorded.

Synonym tables as a primary resolution method are disallowed.

---

## 4. Four-Pass Resolver

Every non-trivial term is resolved through four passes. The pass that produces the binding decides whether silent binding is allowed.

| Pass | Method | Result | Permitted action |
|---|---|---|---|
| 1 Exact | exact match on label or column | one candidate | bind silently; `source=exact` |
| 2 Normalize | typo, case, canonical synonym, punctuation | one candidate | bind silently; `source=normalized` |
| 3 Semantic | similarity against all three meaning-carriers | one or more | **never bind silently** -> clarify with recommendation |
| 4 Empty | no candidate | none | open clarification |

A term reaches Pass 3 only when Pass 1 and Pass 2 produced nothing.

---

## 5. TermResolution Artifact

Each resolved term must produce:

```text
term | normalized_term | pass | candidates[] | selected | source | carrier | confidence
```

Each candidate is `{ system, category, code, label, carrier, score }`.

If `source` is not `exact`, the term must be surfaced as a clarification (Section 8).

---

## 6. Binding Matrix

For any concept that may span systems, produce a matrix before any `UNION` or combined query:

```text
system | concept | category | code(s) | meaning-carrier | confidence | equivalence
```

`equivalence` is one of: `equivalent`, `equivalent-after-mapping`, `non-equivalent-granularity`, `partial-overlap`, `single-system-only`.

Rules:

- `UNION` across systems is permitted only after the matrix is complete and the equivalence verdict is recorded.
- A code resolved for one system must not be reused for another system without its own matrix row.
- Non-equivalence must remain visible in the answer; it may not be hidden behind a single combined number.
- The same numeric code must not be assumed equivalent across systems without explicit validation.

---

## 7. Outbound Resolution

Outbound resolution means:

```text
code(s) -> answer label(s)
```

The label captured during inbound binding is reused here. Do not run a separate dictionary query to translate output codes when the binding already captured the label.

A raw code may not appear in user-facing output when an authoritative label is resolvable.

---

## 8. Non-Exact -> Clarify with Recommendation

When resolution reaches Pass 3 or 4, the system must surface the ambiguity to the user with a grounded recommendation.

Fixed format:

```text
I could not resolve "<term>" exactly.
Candidate meanings found in the database, ranked by meaning similarity:

[<SYSTEM>]
  - <column | code> "<label>" (score <n>) — via <meaning-carrier>

Did you mean one of the above, a combination, or something else?
```

Rules:

- show all Pass-3 candidates,
- group by system,
- rank by meaning-similarity score,
- annotate each with the carrier that produced it,
- never ask a bare "what do you mean?".

If the dictionary result is absent or too broad, escalate to `context/source_discovery_protocol.md` instead of forcing a weak mapping.

---

## 9. Cross-System Non-Equivalence

When multiple systems encode the same broad business concept differently, decide whether the concepts are:

- equivalent,
- equivalent only after per-system mapping,
- non-equivalent in granularity,
- or only partially overlapping.

If non-equivalence remains, record it in the Binding Matrix and keep it visible in the answer.

---

## 10. Relationship to Other Sources

This protocol provides the **coded-value procedure** only.

It does not replace:

- stable business semantics from `business_glossary.md`,
- data quality rules from `data_quality_rules.md`,
- structural topology from `data_architecture.md`,
- or execution shape from `query_recipes.md`.

---

## 11. Anti-Hardcode Rule

This file must not evolve into a static code-answer catalog.

Its purpose is to teach the method:

- when to resolve,
- how to resolve,
- how to bind,
- and when clarification is required.

If a concept is discoverable only from real data patterns, dictionary resolution is not enough — escalate to discovery.
