---
name: bpom-analyst
description: "Analytical skill for factual data questions — counting, historical trends, breakdowns, rankings, comparisons, and lists. Queries registration data with verified SQL."
tags: [bpom, text-to-sql, analyst]
version: "4.0.1"
---

# BPOM Analyst — minimal flow

1. **UNDERSTAND** — identify entity · operation · conditions · time scope · system scope.
   Missing system scope on NIE/permohonan/produk/BTP → clarify first (`SEEKNAL_ASK.md`).
2. **RESOLVE** — read `context/predikat.md` (counting entity, date column, status sets,
   jenis_permohonan rule, Case A/B, exclusions, casts, UNION template) and
   `context/filter_code_reference.md` (concept → column + code, pipeline stages, risk, decoys).
   Only then, if a code is still unknown: `data_dictionary` exact-category lookup.
   Two plausible columns/code families → ask the user.
3. **EXECUTE** — write the final query from the resolved bindings. One statement per call.
   ERBA casts mandatory. Separate WHERE per UNION side.
4. **CHECK** before answering: correct counting entity (`nomor` vs `produk_id` vs `trader_id`) ·
   status filter matches the population asked · exclusions applied · scope matches the question
   **and equals the clarified/stated scope** (never silently narrow to one system after a
   gabungan clarification). Wrong → fix once; still wrong → state the limitation honestly.
5. **EXPORT** — the single CSV Store Contract upload happens NOW: after CHECK passes, after the
   last evidence query, immediately before writing the answer (rules in the section below).
6. **ANSWER** — user's language, scope stated (system, produk vs +BTP, time range), following
   the Answer Contract (`predikat.md` §12): lead with the canonical interpretation; label every
   number with its code + dictionary description; show the per-code split and a period ×
   category table. Build that table with ONE closing `GROUP BY` query shaped like the answer —
   choose the right evidence among ALL results this turn, never assemble the headline number by
   hand from scattered results. Numbers only from SQL executed this conversation. Apply internal
   hygiene (test-account exclusions, casts, normalization) silently — never a standalone
   bolded line ("**Eksklusi:** ..."). If a short *Catatan/Metodologi* bullet list is already
   given (scope, method, filter), the exclusion fact may ride along as one plain bullet in
   that list — never its own heading, never volunteered outside such a list.

## Discovery bounds

- Free-text product search (nama/merk): ONE combined query
  `(nama ILIKE '%kw1%' OR merk ILIKE '%kw1%') AND (... kw2 ...)` with a LIMIT, max 2 probes
  total; still 0 rows → answer "tidak ditemukan" honestly — never fabricate, never keep
  permuting keyword variants.
- Clarification goes through `request_clarification`/`ask_user` ONLY — a clarifying question
  typed as plain answer text is never answered and kills the turn.

## CSV Store Contract (one store per question — the turn's FINAL act)

Applies to tabular, forecast, anomaly, and data-bearing descriptive answers alike. "Carries
data" includes a descriptive answer that still conveys data values; only a purely conceptual
answer (e.g. "apa itu NIE") skips the export entirely.

The export is the LAST tool call of the turn: after the final evidence query and after CHECK
passes, immediately before writing the answer. Needing another query after uploading means the
upload was premature — plan so this never happens.

**Self-check before calling `upload_to_s3` (do this every time, it takes one look):** scan this
turn's own tool calls so far. Does `upload_to_s3` already appear — any filename, any SQL? If
yes → do NOT call it again, go straight to the answer; the export already happened. If
`run_forecast`/`detect_anomaly` ran this turn, that call is treated as the export too — count it
before adding another. Never an exploratory query, never `data=`/`columns=`, never more than
one per turn. Never paste the raw URL; the frontend renders a Download button.
