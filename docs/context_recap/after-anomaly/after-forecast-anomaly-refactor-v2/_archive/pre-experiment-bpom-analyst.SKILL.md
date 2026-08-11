---
name: bpom-analyst
description: "Orchestrate BPOM RPO data questions end-to-end: capture intent, resolve constructs from the authoritative sources, execute SQL, audit the evidence, then answer. Use for every quantitative BPOM question (NIE, permohonan, risiko, skala/UMKM, komitmen, produk spesifik, gabungan sistem)."
tags: [bpom, text-to-sql, orchestration, reflection, analyst]
version: "3.0.0"
---

# BPOM Analyst — Orchestrator

**CAPTURE → RESOLVE → EXECUTE → AUDIT → ANSWER**

This skill directs the **thinking flow**. It stores no domain facts. Every fact is **looked up**,
never recalled:

| What you need | Where it lives — read it, do not remember it |
|---|---|
| Counting method · filters · scope defaults · casts · commitment cases | **`context/predikat.md`** |
| What a code means (status, risiko, kemasan, daerah, skala, …) | **`data_dictionary`** (live table) — via `context/code_resolution.md` |
| Which table · how they join | `context/data_architecture.md` |
| SQL shape per operation | `context/query_recipes.md` |
| Word → entity / operation / dimension | `context/intent_mapping.md` |
| Business definitions (NIE, permohonan, ERBA vs ERLA) | `context/business_glossary.md` |

**No blanket preload.** Read a file only when this turn actually needs it — with one exception,
in RESOLVE below.

---

## CAPTURE

1. Start from the `SEEKNAL_ASK.md` decision frame — **inherit ANSWERS, re-derive METHODS**:
   `EXPLAIN_EVIDENCE` → answer from the ledger, **no new SQL** ·
   `MODIFY_SCOPE` / `EXTEND_SCOPE` → reuse prior *answers* as inputs, but re-derive the *method*
   from `predikat.md` this turn · `NEW_QUESTION` → full workflow.
2. Normalize typos (`intent_mapping.md` Step 0). Never clarify an obvious typo; never inject raw
   user words into SQL.
3. Check the **domain** (`data_architecture.md` router). **Supervision (pemeriksaan / pengujian /
   inspeksi / balai) is NOT connected** — say so; never invent inspection tables.
4. Identify **ENTITY** · **OPERATION** · **DIMENSION** · **CONDITION** (year, system, product).
   **SYSTEM-SCOPE GATE:** no system named (ERBA / ERLA / gabungan) and entity is NIE / permohonan /
   produk / BTP → **clarify now, write no SQL** (`predikat.md` §3.1). Risiko / komitmen → ERBA-only
   by definition; proceed and say so.
5. Resolve implicit references ("dari situ", "tahun yang sama", "selisihnya") from the previous
   turn. Change **only** the component the user changed.
6. Multi-dimension → **DEPENDENT** (crossed: "per X dan Y") = one query, multi-column `GROUP BY`;
   **INDEPENDENT** (separate aspects) = one query each, synthesized at ANSWER. Also split when one
   dimension is ERBA-only (risiko, komitmen) and another spans both systems.
7. Emit before any SQL:

   ```
   Entity · Operation · Dimensions (DEPENDENT|INDEPENDENT)
   Time Scope: [stated year | stated range | ALL-TIME]
   System Scope: [ERBA | ERLA | UNION]
   Output Shape: [scalar | 1D-time | 1D-dim | 2D | multi-query synthesis]
   ```

   Time scope is **binary**: stated → that year; not stated → ALL-TIME. There is no
   "most recent" or "most complete" year.

---

## RESOLVE — the blocking gate

**You MUST read `context/predikat.md` before any aggregation SQL.** It is the one unconditional
read, and it carries every rule that decides whether the number is right. Do not recall these from
memory, and do not copy them from another file — the others only point here.

**Codes are resolved, never remembered.** Status, risiko, kemasan, daerah, skala, jenis permohonan,
status komitmen → `data_dictionary` at runtime (`code_resolution.md` for the pattern,
`code_translation_protocol.md` for the two-way `sumber`-aware procedure). The **only** code literals
you may write from context are the NIE `status` and `jenis_permohonan` lists in `predikat.md` §5–§6,
and the verified maps below.

**For ANY coded business concept (not just product segments), check the verified maps FIRST:**
`context/verified_bindings.md` (concept → proven column+code) and
`context/filter_code_reference.md` (pipeline stage → status codes, risk taxonomies, counting
entity, known decoy columns). A hit there is the binding — skip free probing. Several concepts
have a lexically tempting wrong column (`klaim` vs `klasifikasi_id='305'`;
`klasifikasi_id='309'` vs `pemrosesan='301'`) that free probing reliably falls into.

**Product segments** (AMDK, garam, roti, …) live in `jenis_pangan` / `kategori_pangan` — the only
codes **not** in the dictionary. If not in the maps above, use `business_glossary.md` §Product
Segment Codes, or its `nama_kategori` probe for a segment not listed. **If more than one plausible
code family (or column) comes back, ask the user.** Never pick silently: "roti" also matches
*Lemak Reroti* and *Ragi Roti*, and a silent pick swings the answer ~20% and differs between
sessions.

**Business definitions** (UMKM scope, "pangan olahan", "dibatalkan") come from
`business_glossary.md` or the dictionary — never from world knowledge. Ask: *did I read this this
turn, or am I assuming?* If assuming → read it.

**Exception — forecast / anomaly follow-ups on the same series.** The engine is deterministic;
rebuilding slightly different (but equally "valid") SQL each turn is what makes a forecast appear to
change. If the follow-up does not change series, grain, or filter, **reuse the prior turn's exact
SQL** (`forecast_guide.md`).

Write the resolved constructs down. **No SQL until they are written.**

---

## EXECUTE

- Follow the SQL shape in `query_recipes.md`; apply every filter from `predikat.md`.
- Tables are `warehouse.public.<table>` — `warehouse` is the DuckDB alias for the attached
  PostgreSQL source.
- One query per resolved question. Prefer a single round-trip with `GROUP BY` over many per-year
  queries.
- If a query errors, fix the SQL — never silently change the question to fit the error.

---

## AUDIT — mandatory before answering

Run `evidence-auditor`. It blocks on:

1. **Scope match** — does the executed scope equal the committed scope (entity, system, time)?
2. **Counting method** — `COUNT(DISTINCT …)`, never `COUNT(*)`. The tables are versioned.
3. **Filters match the population** (`predikat.md` §4–§5) — test accounts · issued-NIE status
   filter only when counting issued NIE (never stacked onto a population defined by another
   workflow state) · correct date column.
4. **Codes resolved** — no raw code shown to the user.
5. **Coverage** — if the result is dominated by NULL / `'NULL'` / "Tanpa Kategori", stop: switch to
   a better-covered column, or state the limitation honestly.

If a check fails, fix and re-run. Do not answer past a failed check.

---

## ANSWER

- Output contract per `SEEKNAL_ASK.md` §6 (`RINGKAS` / `ANALITIS` / `AUDIT_GRADE`).
- State the scope you used (system, time, entity) — especially when you applied a default.
- Every number traces to executed evidence. Never to memory, never to a context file.
- If a limitation remains, say it. Never dress an unresolved ambiguity as a confident answer.
- Answer in the user's language.

### CSV export (one-time, agent-decided)

When the final answer presents data (a table, breakdown, ranking, trend), export **the SQL behind
the final answer** — once per turn, after the answer is resolved:

```
upload_to_s3(sql=<the final answer's SQL>, filename=<descriptive>.csv)
```

- **At most once per turn**, and only for the query the answer is actually built on — not for
  discovery, probe, or intermediate queries.
- Decide **after** the answer is settled, not before.
- Skip for a bare scalar with no rows worth exporting, for `EXPLAIN_EVIDENCE` turns, and when the
  user declines.
- Mention the link in the answer.

> Honesty rules (never answer from memory · never switch entity or system silently · never show a
> raw code · never state a number you did not execute) are global — `SEEKNAL_ASK.md` §7.
