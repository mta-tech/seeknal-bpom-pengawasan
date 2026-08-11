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
- Free-text product search (nama/merk): try a coded column first; only then ONE combined query
  `(nama ILIKE '%kw1%' OR merk ILIKE '%kw1%') AND (... kw2 ...)` with a LIMIT, max 2 probes total
  (they count against the budget). Use ILIKE to discover a code, then count on the code — do not
  count repeatedly through ILIKE. Still 0 rows → answer "tidak ditemukan" honestly, never keep
  permuting keyword variants.
- Clarification goes through `request_clarification`/`ask_user` ONLY — a clarifying question
  typed as plain answer text is never answered and kills the turn.
- A count question on a populated concept expects at least one counting query — if the plan ends
  with none, re-check the entity and population once before answering rather than stopping short.
- On a follow-up, read the earlier turns first: carry over the settled subject, system/scope, time
  range, and resolved codes, and change only what this turn names — never rebuild from a blank
  question or drift to a different concept than the one under discussion.

## CHECK before answering (Gate 5)
Run these as a list, not as a feeling — each one has failed a real case:

- **Counting entity = question subject**, and the same rule holds for every code family; there is
  no table-specific exception (`predikat.md` §1).
- **The code set is closed.** Compound concepts — "X atau Y", "disetujui", "perubahan",
  "logam atau kaleng" — take every member from the §4 closure table or from a full category read.
  Never the first single-keyword ILIKE hit: the sibling it drops is invisible in the result
  (`filter_code_reference.md` §0, §4).
- **Headline total came from its OWN global DISTINCT query**, never summed from a partitioned
  breakdown — per-year, per-status and per-system rows double-count revisions (`predikat.md` §12-C).
- **Status filter = the asked population.** Never stack the issued-NIE set on a population that is
  already defined by another workflow state; that erases what was asked about.
- **Exclusions applied** — test accounts, and the NULL-date guard when grouping without a date
  range.
- **The final SQL touches exactly the tables the settled scope implies** — the clarified scope for
  a new question, the carried-over scope for a follow-up. A side left out on purpose is named in
  the answer; a side left out by accident is the largest undercount available here.
- **Codes resolved to labels**, with the business term spelled out at least once.

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
Shape the answer per the Answer Contract (`predikat.md` §12): canonical interpretation first,
every number labelled with its code + description, per-code split, and a period × category table
from ONE closing `GROUP BY` — hygiene applied silently.
