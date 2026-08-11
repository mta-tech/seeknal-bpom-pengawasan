---
name: evidence-auditor
description: "Audit gathered SQL evidence BEFORE answering a BPOM data question. Verifies the chosen result matches the captured intent, that all mandatory filters are present, that the number is internally consistent, and that nothing was fabricated. Returns PASS or FIX with a reason. Use as the REFLECT step of bpom-analyst, or whenever multiple queries produced conflicting numbers."
tags: [bpom, audit, verification, reflection, quality-gate]
version: "1.0.0"
---

# Evidence Auditor — Verification Gate Before Answering

Purpose: **assess** a set of query results against intent + business rules, then
decide whether it is safe to answer. This is not about writing the answer — it is about **auditing the evidence**.

Run BEFORE generating, especially when: multiple different numbers exist, a query
failed/timed out, the conversation is long, or a number feels too large.

---

## Input being checked
- **INTENT** from the CAPTURE phase: {entity, operation, dimension, condition (year, system, BTP?)}.
- **EVIDENCE**: list of candidate numbers + the originating query for each.

## Audit checklist (answer every point)

### A. Scope match (most common source of errors)
- [ ] Entity correct? (NIE→`COUNT(DISTINCT nomor)`, permohonan→`produk_id`, perusahaan→`trader_id`)
- [ ] Time column correct? (NIE→`tanggal`; permohonan→`tanggal_bayar`)
- [ ] Year scope correct: if a year/range was stated → it matches & uses a **date range** (not EXTRACT); if **no year was stated → result must be ALL-TIME** (wide range), NOT a single year?
- [ ] System correct? (requested ERBA → ERBA only; risk/commitment → ERBA-only; combined → UNION ERBA+ERLA)
- [ ] BTP scope correct? ("pangan olahan" = main product; BTP only if explicitly requested)

### B. Mandatory filters (source: **`context/predikat.md`** — the single source of truth)
- [ ] **`COUNT(DISTINCT …)` used — `COUNT(*)` is a BLOCK.** The product tables are versioned
      (status `9999` = "Sudah Diubah" = a superseded row). `COUNT(*)` inflates by **+25% (ERBA)**
      and **+57% (ERLA)**. This is the single largest source of wrong numbers.
- [ ] **Per-year totals are not summed.** A grand total must be a separate global
      `COUNT(DISTINCT …)`, never the sum of the yearly rows — a `nomor` recurring across years
      double-counts.
- [ ] Coded filter values are **dictionary-resolved & sumber-aware** (not recalled); no `sumber`-blind lookup/JOIN (fan-out on `STATUS`/`KEMASAN_ID`/code `9999`)
- [ ] **ERLA `status` label resolved with leading zeros stripped** — the ERLA table stores `'0999'`
      but the dictionary stores `'999'`. A plain join leaves ~50% of ERLA rows unlabelled
      (`code_resolution.md`).
- [ ] **`status_komitmen` normalized** with `ROUND(status_komitmen::numeric)::int::text` — a plain
      `= '5'` silently drops the `'5.0'` rows (~4% of commitment data).
- [ ] Status filter **matches the population** (per `predikat.md` §5): counting issued NIE →
      filter present (ERBA `0999/0906/9999`, ERLA +`0099`); population defined by another
      workflow state → NIE filter **ABSENT** — its presence is equally a BLOCK, it erases the
      asked population
- [ ] `jenis_permohonan` correct **for the intent** — "NIE baru" → ERBA `301/305`, ERLA `301/304/305`; "all active NIE" → **no `jenis_permohonan` filter**; permohonan = all types, NO status filter
- [ ] Test accounts excluded (ERBA `5,17,50,85`; ERLA `3384`); years 1900/1970 excluded
- [ ] Commitment uses the right case: **Case A** ("NIE with commitment X") keeps NIE filters; **Case B** (lifecycle "dibatalkan/ditolak") **drops the valid-NIE `status` filter** — counting Case B with the NIE filter undercounts ~95% (the 254-vs-~5,199 error)

### C. Consistency & plausibility
- [ ] `COUNT DISTINCT ≤ COUNT`; subset (e.g. MR) ≤ total
- [ ] Consistent with numbers from previous turns (e.g. NIE ERBA 2023 must be the same in every turn)
- [ ] **No inflation symptoms (single year)**: for a stated single year, a count far above the per-year expectation (one ERBA year ≈ 30k NIE pangan olahan) usually means a missing status/jenis_permohonan filter
- [ ] **Scope-aware, both directions**: an all-time count is the SUM across years (several × a single year) — NOT inflation. Conversely, if the question stated NO year/range but the result covers only one year, suspect UNDER-scope (too small) and re-run all-time
- [ ] Result ≠ 0 without a clear reason

### D. Honesty
- [ ] Every number comes from a query that was actually executed & passed checks A–C
- [ ] No number was "filled in from expectation" after a failed/timed-out query
- [ ] If a query failed → that failure is reported, not covered with a substitute number

---

### E. Data availability check (run before concluding "data is not available")

When a query returns 0 rows or an unexpectedly small count, verify these before
declaring data unavailable:

- [ ] Is the queried table non-empty? Run `SELECT COUNT(*) FROM warehouse.public.[table]`
      to confirm — do not rely on a remembered count. Table sizes change as data grows.
- [ ] ERBA query: are TEXT columns cast correctly?
      `tanggal::timestamp` · `tanggal_bayar::timestamp` · `trader_id::bigint`
- [ ] `status_komitmen` filter: uses `ROUND(status_komitmen::numeric)::int::text`, NOT plain `= '5'`?
      (ERBA mixes `'5'` and `'5.0'` for the same value — plain equality misses half the rows)
- [ ] Risk filter: correct column per system, **resolved from the dictionary with `sumber`**?
      ERBA → `kategori_dokumen` (KATEGORI_DOKUMEN, sumber ERBA) | ERLA → `jenis_dokumen` (JENIS_DOKUMEN) —
      codes are **not** interchangeable; ERLA has 3 levels (no separate Menengah Tinggi)
- [ ] Segment uses the **parent** category (e.g. Garam `jenis_pangan='1204'`), not a narrow sub-code?
- [ ] Mandatory NIE filters present even when adding extra dimensions?
      `status IN (...)` AND `jenis_permohonan IN (...)` AND test account exclusion
- [ ] ALL-TIME UNION query: does it include both ERBA and ERLA?
- [ ] AMDK query: correct code per system?
      ERBA `jenis_pangan = '1401'` | ERLA `jenis_pangan IN ('651','652','655')`
- [ ] ERBA `tanggal` NULL present in GROUP BY without date range? (add `WHERE tanggal IS NOT NULL AND tanggal != ''`)

If all checks pass and result is still 0 → conclude data is absent for this scope.
If any check fails → fix and re-run. Do NOT declare unavailability before exhausting all checks.

---

## Verdict
- **PASS** → one authoritative number selected; safe to GENERATE.
- **FIX: <reason + action>** → return to PLAN/EXECUTE (e.g. "add status filter", "switch to ERBA-only", "use tanggal_bayar"). Maximum 3 rounds.
- **HONEST-FAIL** → data cannot be retrieved/verified after exhausting retries. State the limitation honestly; **do not fabricate numbers**.

## Example verdicts
- Evidence: permohonan ERBA 2023 = 60,826, NIE ERBA 2023 = 55,142 (year **2023 stated**).
  → **FIX**: for the single year 2023, NIE ERBA should be ~30,276; 55,142 indicates a missing status/jenis_permohonan filter (inflation). Re-run with complete filters.
- Evidence: question "berapa NIE MR?" (**no year stated**) → result 9,695 (one year only).
  → **FIX (under-scope)**: no year was given, so scope should be all-time, not a single year. 9,695 is the 2023-only figure. Re-run without a single-year filter (wide range / all years) and report total + per-year.
- Evidence: AMDK ERBA 2023 could not be retrieved (timeout), but user asked about AMDK.
  → **HONEST-FAIL**: report retrieval failure; do not emit an AMDK number that did not come from a query.
