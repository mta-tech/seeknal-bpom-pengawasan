# Source Discovery Protocol

This file teaches how to discover meaning from the database at runtime.
It does not store business answers.

## 1. Principle

Use this protocol when a concept is not safely locked by:

- a direct literal field,
- an exact dictionary match,
- or an already confirmed binding in the active topic.

The method is:

1. check scope,
2. try dictionary,
3. probe real data per system,
4. compare ERBA and ERLA,
5. clarify before counting if the answer would change materially.

## 2. Clarify before probing deeply when scope is missing

If the user does not specify year, date range, or source scope, clarify first when
those choices would materially change the result.

Do not silently default to all-time or combined-system in that situation.

## 3. Discovery loop

### Stage A — Dictionary

Search `data_dictionary` in the correct `sumber` scope.

Classify the result:

- exact and narrow -> usable binding,
- present but broad -> insufficient,
- absent -> escalate to probing.

### Stage A.5 — Data-Grounded Confirmation

A dictionary label alone is not always trustworthy. Before binding a code that came from a Pass-3 (semantic) match or a broad dictionary hit, confirm it against real rows.

For each candidate code:

1. sample a small number of rows carrying that code,
2. inspect the descriptive columns of those rows,
3. verify the sampled meaning matches the user concept.

If the sample contradicts the dictionary label, treat the binding as unconfirmed and escalate to Stage B.

This step guards against stale, misleading, or empty dictionary labels.

### Stage B — Combined Probe-and-Resolve

For each candidate system separately, run a **single** probe that returns both the candidate codes and their per-system counts. Do not split "find candidates" and "count" into separate steps.

1. inspect likely fact tables,
2. inspect likely descriptive columns,
3. run one probe using text search or distinct-code distribution that also returns row counts,
4. collect candidate codes, row evidence, and per-system counts in the same pass.

The per-system counts produced here are reused to measure divergence between interpretations (Stage D) and to decide whether a clarification is worth surfacing.

### Stage C — Compare systems

Check:

- does the concept exist in both systems,
- do both systems encode it the same way,
- is one broader or narrower,
- is one missing the concept entirely.

Treat ERBA/ERLA equivalence as a runtime hypothesis, not a memory fact.

### Stage D — Decide

Use the per-system counts from Stage B to measure divergence between candidate interpretations.

- one stable interpretation -> execute,
- divergence above the materiality threshold between candidates -> clarify using the recommendation format in `code_translation_protocol.md` Section 8,
- no coverage -> answer honestly,
- partial coverage -> answer with explicit limitation.

Treat a clarification triggered here as net efficiency-positive: one round is cheaper than a wrong answer followed by a correction and a recompute.

## 4. Required artifact

Before final counting SQL on non-trivial concepts, produce:

```text
Source Discovery Record
term:
systems_checked:
dictionary_result:
columns_probed:
candidate_codes:
same_meaning_across_systems?:
verdict:
```

## 5. Anti-hardcode rules

- Do not store product-specific code lists here.
- Do not assume the same code means the same thing across ERBA and ERLA.
- Do not combine systems unless equivalence has been checked.
- Do not answer factual questions from context text alone.
- Every final binding must trace to database evidence or an exact dictionary match.
