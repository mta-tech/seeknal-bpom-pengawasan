---
name: bpom-pengawasan-analyst
description: "Analytical skill for factual data questions — counting, historical trends, breakdowns, rankings, comparisons, and lists. Enforces the gated procedure and the answer contract."
tags: [bpom, pengawasan, text-to-sql, analyst, gated]
version: "2.0.0"
---

# BPOM Pengawasan Analyst — gated executor

Follow `SEEKNAL_ASK.md` Gates 0-5 literally. This skill adds the enforcement details; the data
rules themselves live in the `context/` pages the map opens.

## Query ledger (keep mentally, per turn)

Count **logical steps**, not raw calls:

| Step | Typical spend |
|---|---|
| Resolve values (Gate 2 path P2/P3) | 1, only when the page has no anchor |
| Discovery / verification | 1, only when a binding is genuinely unknown |
| Final query | 1 |
| Corrected retry | 1, on error only |

Opening context pages costs nothing; open every component's page at once. **Reading is cheap,
querying is not.** TOTAL SQL ceiling per turn: **6**. Reaching the ceiling without a defensible
number = STOP and report honestly (what resolved, what failed, which single decision is missing).

## Stop rules (these override the urge to keep querying)

- **The same query shape already ran this turn** -> the answer is already in hand. A different
  `LIMIT`, alias, or `GROUP BY` order is the same shape. Re-running never adds information.
- **Two consecutive probes did not change the plan** -> the binding is settled; go to the final
  query. Doubt is a reason to state an assumption, not to spend another query.
- A probe returning 0 rows twice for the same concept -> the binding is wrong; go back to
  Gate 2/Gate 1, do not brute-force variations.
- An error on the final query -> ONE corrected retry, informed by the error text. A second error
  -> STOP honestly.
- If the expected magnitude and the result differ wildly, do not "search" for a number that
  feels right — re-check the counting entity and population filter once, then either stand by
  the result or stop honestly. **Never tune filters toward an expected number.**
- Free-text search (`nama_produk`, `pendaftar`, `lokasi_iklan`): try a coded column first; only
  then ONE combined query with `ILIKE` and a `LIMIT`, max 2 probes total. Still 0 rows -> answer
  "tidak ditemukan" honestly. **Zero rows on a name search is an answer, not a failure.**
  `pendaftar` carries duplicated-string artefacts, so use a short fragment that also catches them.
- Clarification goes through `request_clarification`/`ask_user` ONLY — a clarifying question
  typed as plain answer text is never answered and kills the turn.
- A count question on a populated concept expects at least one counting query — if the plan ends
  with none, re-check the entity and population once before answering rather than stopping short.
- On a follow-up, read the earlier turns first: carry over the settled subject, scope, time
  range, and resolved codes, and change only what this turn names. **Re-derive the METHOD from the
  pages each turn** — never reuse a column or filter from recall.

## CHECK before answering (Gate 5)

Run these as a list, not as a feeling — each one has failed a real case:

- **Counting entity = question subject.** Baris produk, event, and surat are three different
  counts (`00-menghitung.md`).
- **Cross-komoditi comparison uses the event count**, never the row count — some komoditi carry
  several products per event and would win on row count alone.
- **Verdict column is the one the question asked about**, and the TMK family is matched by prefix,
  not by equality — its members differ between the balai and pusat columns (`30-vonis.md`).
- **The code set is closed.** Compound concepts take every member from a full category read.
  Never the first single-keyword `ILIKE` hit. Value families in this domain vary in spelling
  (spaces, hyphens, case) — one spelling is rarely the whole family.
- **Column chosen by MEANING.** The three verdict columns are not interchangeable and do not share
  a value set (`30-vonis.md`).
- **Joins to log or timeline start from the fact table**, never the other way round — those tables
  contain ids the fact table does not (`45-status-dan-alur.md`).
- **A "duration" column with only a couple of distinct values is a flag, not a number of days**;
  check the spread before averaging (`60-waktu-dan-durasi.md`).
- **Headline total came from its OWN global query**, never summed from a partitioned breakdown.
  Joining a companion table multiplies parent rows; count `DISTINCT` on the parent id after a join.
- **Status filter = the asked population.** Never stack filters that erase what was asked about.
- **Verdict filter present ONLY if the question asks about it.**
- **Every `WHERE` clause traces to a word in the question.** Ones that do not — especially column
  fill-guards — are unrequested narrowing: drop them unless listed as a mandatory exclusion in
  `00-menghitung.md`. The reverse also holds: a clause carrying the subject (sarana, komoditi,
  jenis pangan, period) must NOT be dropped — dropping it answers a wider question.
- **Exclusions applied** — central units on per-balai counts; sentinels removed before any
  `COUNT(DISTINCT ...)`.
- **Sentinel handled by its actual shape.** The fact table has **no SQL NULL at all** — every
  "empty" is a text value, so `IS NULL` there always returns nothing (`90-kualitas-data.md`).
- **The final SQL touches exactly the tables the settled scope implies.**
- **Coverage stated** when the column used is sparsely filled on the asked population — say which
  slice the answer covers before presenting a ranking or a percentage.
- **Current period flagged as partial.**
- **Codes resolved to labels**, with the business term spelled out at least once.
- **Every figure and every example row comes from `execute_sql` this turn.** No query this turn ->
  no facility names, no product names, no numbers.

## Two failure modes specific to this domain

**1. An anti-join that returns nothing is usually the wrong question shape.** "UPT yang tidak
melaporkan X" tends to be empty because nearly every balai reports something. Say so, then answer
what the user meant: a ranking by share, lowest first.

**2. `SELECT *` is not an answer to a recap question.** The answer shape comes from the question's
verb — "berapa" takes an aggregate, "tren" takes a grouping by period, "tampilkan data" takes a
recap over the named dimension. A raw row dump runs fine and answers nothing.

## CSV Store Contract (one store per question — the turn's FINAL act)

Applies to tabular, forecast, anomaly, and data-bearing descriptive answers alike.

The export is the LAST tool call of the turn: after the final evidence query and after Gate 5
passes, immediately before the answer.

**Self-check before calling `upload_to_s3`:** scan this turn's own tool calls so far — does
`upload_to_s3` already appear (any filename)? If yes -> do NOT call it again, the export already
happened, go straight to the answer. If `run_forecast`/`detect_anomaly` ran this turn, that
call IS the export — count it before adding another. Never an exploratory query, never
`data=`/`columns=`, never more than one per turn. Never paste the raw URL.

**The export is the final-answer SQL itself** — not an exploratory query, not a narrowed one.
Its `ORDER BY` follows the question: ranking -> metric DESC; trend -> period ASC; list -> entity id.

## Presentation

User's language. The Gate 3 commitment block is INTERNAL — never print it. Bullets use `-`.
Failed/empty/timed-out query -> report the failure plainly.

Shape the answer as: canonical interpretation first, then the headline number, then the breakdown.
Every number labelled with its code + description; hygiene (sentinel handling, exclusions) applied
silently but **stated in one line when it changes what is being counted** — naming which verdict
column was used, and which komoditi it covers, is the case where it always does (`30-vonis.md`).

**A markdown table needs each row on its own line**, with a blank line before it; written inline in
a bullet it renders as raw pipe text. Never restate a chart's rows as a table.
