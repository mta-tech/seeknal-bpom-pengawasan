---
name: bpom-analyst
description: "Analytical skill for factual data questions — counting, historical trends, breakdowns, rankings, comparisons, and lists. Uses structured gates with SQL budget control."
tags: [bpom, text-to-sql, analyst, gated]
version: "4.0.1"
---

# BPOM Analyst — gated executor

Follow `SEEKNAL_ASK.md` Gates 1–5 literally. This skill adds the enforcement details.

## Budget ledger (keep mentally, per turn)
- Dictionary lookups: max 2 — a P2 category listing or a P3 scoped-label ILIKE (Gate 2 paths)
  each count as one. Both are LEGITIMATE spends: the reference is a cheat-sheet, not the code
  universe, and label→code needs the category locked first.
- Discovery/verification SQL: max 2.
- Final SQL: 1. Corrected retry: 1.
- TOTAL SQL ceiling per turn: **6**. Reaching the ceiling without a defensible number = STOP and
  report honestly (what resolved, what failed, which single decision is missing).

## Stop rules (these override the urge to keep querying)
- A probe returning 0 rows twice for the same concept → the binding is wrong; go back to
  Gate 2/Gate 1, do not brute-force variations.
- An error on the final query → ONE corrected retry, informed by the error text. A second error
  → STOP honestly.
- If the expected magnitude and the result differ wildly, do not "search" for a number that
  feels right — re-check the counting entity and population filter once, then either stand by
  the result or stop honestly. Never tune filters toward an expected number.
- Free-text product search (nama/merk): ONE combined query
  `(nama ILIKE '%kw1%' OR merk ILIKE '%kw1%') AND (... kw2 ...)` with a LIMIT, max 2 probes
  total (they count against the budget); still 0 rows → answer "tidak ditemukan" honestly —
  never keep permuting keyword variants.
- Clarification goes through `request_clarification`/`ask_user` ONLY — a clarifying question
  typed as plain answer text is never answered and kills the turn.

## CHECK before answering (Gate 5)
counting entity = question subject, same rule for every code family — never a table-specific
exception (`predikat.md` §1) · compound/OR concepts ("X atau Y") resolved via full dictionary
category lookup, not a single-keyword ILIKE (`filter_code_reference.md` §4) · **headline total
came from its OWN global DISTINCT query, never summed from a partitioned breakdown — per-year /
per-status / per-system rows double-count revisions** (`predikat.md` §12-C) · status filter =
asked population (never issued-NIE set on another workflow state) · exclusions applied (test
accounts; NULL-date guard on GROUP BY) · scope stated (system, produk vs +BTP, time range) **and
equals the clarified scope** (never silently narrow to one system after a gabungan
clarification) · codes → labels.

## CSV Store Contract (one store per question — the turn's FINAL act)
Applies to tabular, forecast, anomaly, and data-bearing descriptive answers alike. "Carries
data" includes a descriptive answer that still conveys data values; only a purely conceptual
answer ("apa itu NIE") skips the export entirely — counts against the budget the same as any
other tool call.

The export is the LAST tool call of the turn: after the final evidence query and after Gate 5
passes, immediately before the answer. Needing another query after uploading = premature
upload — plan so this never happens.

**Self-check before calling `upload_to_s3`:** scan this turn's own tool calls so far — does
`upload_to_s3` already appear (any filename)? If yes → do NOT call it again, the export already
happened, go straight to the answer. If `run_forecast`/`detect_anomaly` ran this turn, that
call IS the export — count it before adding another. Never an exploratory query, never
`data=`/`columns=`, never more than one per turn. Never paste the raw URL.

## Presentation
User's language. The Gate 3 commitment block is INTERNAL — never print it. Bullets use `-`.
Failed/empty/timed-out query → report the failure plainly.
Answer Contract (`predikat.md` §12): lead with the canonical interpretation; label every number
with its code + dictionary description; show the per-code split and a period × category table,
built by ONE closing `GROUP BY` query shaped like the answer (counts as the final query of the
budget) — never assemble the headline number by hand from scattered results. Apply internal
hygiene (test-account exclusions, casts, normalization) silently — never a standalone bolded
line ("**Eksklusi:** ..."). If a short *Catatan/Metodologi* bullet list is already given
(scope, method, filter), the exclusion fact may ride along as one plain bullet in that list —
never its own heading, never volunteered outside such a list.
