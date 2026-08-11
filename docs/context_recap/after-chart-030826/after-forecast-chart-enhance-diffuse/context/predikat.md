#PREDIKAT - RULES FOR ACCURATE COUNTING, STATUS FILTERS, APPLICATION TYPES, AND COMMITMENT CASES ON VERSIONED TABLES#

> **Single source of truth.** Reference this file. DO NOT recall literals from memory.
> Each rule appears **exactly once** — here.

---

## 1. Counting Method (CRITICAL — tables are versioned)

The product tables are **versioned**: status `9999` means "Sudah Diubah" (revised). A single
NIE can span multiple rows. `COUNT(*)` over-counts because it counts revisions, not entities.
Order of magnitude: about a quarter too high in ERBA, **more than double in ERLA** — the wrong
entity does far more damage on the legacy side.

| Entity     | Method                      | Why                                              |
|------------|-----------------------------|--------------------------------------------------|
| NIE        | `COUNT(DISTINCT nomor)`     | One NIE = one `nomor`; revisions share `nomor`   |
| Permohonan | `COUNT(DISTINCT produk_id)` | One application = one `produk_id`                |
| Perusahaan | `COUNT(DISTINCT t.trader_id)` | Count from the product table, NOT `m_trader_*` — `LEFT JOIN` produces NULL for orphans, so `COUNT(DISTINCT m.trader_id)` silently drops them |

**`COUNT(*)` on an NIE question is a BLOCK** — the answer is wrong, not approximately right, and
no amount of correct filtering rescues it. Every revision row is counted as if it were a separate
licence.

**On a permohonan question it is not a block.** `produk_id` is unique in both product tables, so
`COUNT(DISTINCT produk_id)` and `COUNT(*)` return the identical number there. Write the DISTINCT
form anyway — it states the entity, which matters for readability and for anyone reviewing the
query — but do not treat a permohonan figure as suspect merely because it came from `COUNT(*)`,
and do not "correct" it into a different number. Re-deriving a figure that was already right is
its own kind of error: it costs budget and invites drift between the text and the query.

The distinction matters because the two failure modes pull in opposite directions. Counting NIE
with `produk_id` inflates; distrusting a correct permohonan count wastes the retry that a genuinely
wrong query would have needed.

The count column follows **what is being counted, not the user's noun** — the same everyday word
can refer to issued licences in one question and applications in another. Decide from the
question's subject; if genuinely ambiguous and the numbers differ materially → clarify
(`SEEKNAL_ASK.md` §2).

**Default for "berapa produk X terdaftar / punya izin edar":** the subject is the registered
licence → `COUNT(DISTINCT nomor)` (exclude empty `nomor`). Reaching for `produk_id` because the
user said "produk" is the most common entity mistake — verified to inflate answers up to ~2x on
real concepts even when every filter is correct. Use `produk_id` when the question is about
applications/submissions (**"persetujuan produk"** / "permohonan" / "pengajuan" / approval).

**This is a general rule, not a table-specific exception.** The wrong-entity failure shows the
same shape no matter which code family `X` filters on — `kemasan_id`, `jenis_btp`,
`bentuk_sediaan`, `jenis_produk_btp`, `klasifikasi_id`, or any column added later: the wider /
more common the filtered population, the larger the `produk_id`-vs-`nomor` gap (verified drift
on live data ranges from a few percent on narrow single codes up to 50–170% on broad ones).
Don't pattern-match on one product family from a past example — the fix is always the same:
identify the subject (licence vs application vs company), then pick the entity from the table
above.

---

## 2. Date Column Choice

| Entity     | Correct column | Wrong columns                                  |
|------------|----------------|------------------------------------------------|
| NIE        | `tanggal`      | `tanggal_aju` (submission), `tanggal_bayar` (payment) |
| Permohonan | `tanggal_bayar`| `tanggal_aju` (submission only — payment date is the canonical app date) |

`tanggal_berkas`, `tanggal_diambil` are process dates — never use them for counting.
`tanggal_exp` is not a counting date either, **but it IS the correct filter column when the
question's condition concerns the licence's validity period ending** → filter `tanggal_exp` on
the asked period (cast on the ERBA side — §9).

The same identity holds across the four product/BTP tables. A BTP table (`t_btp_3_erba`, `t_btp_3_erla`)
is structurally a product table for counting purposes.

---

## 3. NIE Sah Filter (NIE-only — NOT permohonan)

**Applies only when the population being counted is issued NIE.** A population defined by any
other workflow state (resolved from `data_dictionary`) already has its own status condition;
stacking this filter on top **erases the population being asked about** (§5 Case B is the worked
example: stacking turns 5,198 into 254). For permohonan, drop the status filter entirely —
permohonan counts all applications regardless of outcome.

**Data-quality questions are the same case.** "Belum dikategorikan / belum ditetapkan / belum
diisi" asks about the raw state of the population, so the valid-NIE filter does not belong there
either — stacking it turned 30,074 into 1,951 (-94%).

| System | `status IN (...)`            |
|--------|------------------------------|
| ERBA   | `('0999', '0906', '9999')`   |
| ERLA   | `('0099', '0999', '0906', '9999')` |

**Two tiers — pick by the question's verb.** The sets above answer "terdaftar / total / pernah
terbit". "Aktif / masih berlaku" is narrower: `status = '0999'` only (per system) —
`0906`/`9999` rows are amended/superseded, not currently-active licences.
The word "saat ini" ALONE is not an aktif trigger: "terdaftar ... saat ini" stays on the
terdaftar tier (it stamps the as-of date, not the tier). When both tiers are genuinely live in
one question, lead with terdaftar and attach the aktif figure as a labelled row (§12) — never
silently swap tiers, and never add extra narrowing (e.g. expiry-date filters) unless the user
asks for "masih berlaku".

---

## 4. RC-2 — jenis_permohonan (conditional, by intent)

`jenis_permohonan` is **not universal**. Choose by what the user is asking:

| Intent                                | Signal words                                  | Filter                                                                |
|---------------------------------------|-----------------------------------------------|-----------------------------------------------------------------------|
| **NEW / amended registrations (not major change)** | the word **"baru"** / "baru notifikasi" | ERBA `IN ('301','303','305')` (exclude 302 mayor); ERLA `IN ('301','303','304','305')` |
| **All active NIE / total registered / issued in a period** | "total produk terdaftar", "berapa NIE/produk", "NIE yang terbit di {periode}" | **no `jenis_permohonan` filter** — rely on valid `status` alone      |
| **Permohonan — default**              | "permohonan/registrasi/pengajuan", incl. "disetujui / diterima / terbit / izin edar" | all types, **plus the valid `status` set** (§3) |
| **Permohonan — raw submissions**      | the question asks for volume regardless of outcome: "berapa yang masuk/mengajukan", "seluruh periode data", a plain volume trend with no licence word | all types, **no status filter** |

**"Terbit" is NOT a JP trigger.** Every NIE "terbit" — "NIE yang terbit di 2025" counts ALL
jenis_permohonan in that period. Only the explicit word "baru" narrows to exclude 302 (mayor):
ERBA `IN ('301','303','305')`.
A product whose current valid NIE came via Perubahan (`302`/`303`) still holds an active NIE;
filtering by `('301','305')` without "baru" undercounts materially (verified ~13%).
**Default when "baru" is absent → no JP filter (status filter only).**

**The two permohonan rows are not interchangeable.** The raw-submission reading is materially
larger than the approved-only one — the gap is well beyond any tolerance the tests apply, so
choosing the wrong branch fails the question outright rather than landing near it.

Pick the branch from the wording, exactly the way §3 picks the status tier from the verb. The
default is the approved reading: most questions about permohonan are asking about submissions that
went somewhere, and "disetujui", "diterima", "terbit" and "izin edar" all point there. Drop the
status filter only when the question is explicitly about submission volume regardless of outcome —
"berapa yang masuk", "berapa yang mengajukan", "seluruh periode data", or a plain volume trend that
never mentions a licence.

Two carve-outs take neither branch:

- a **pipeline stage** question — "berapa yang nyangkut di Draft", "berapa menunggu verifikasi".
  That population is defined by its own status codes, and stacking the valid-NIE set on top erases
  it (§3);
- a **Case B commitment** question — "berapa komitmen dibatalkan". Same reasoning, different
  column: the population lives in `status_komitmen` and most of it never reached a licence (§5).

---

## 5. RC-4 — Commitment Case A/B (CRITICAL — 254 vs 5.198)

`status_komitmen` questions split into two different counts. Decide which one the user means
**before** writing SQL; applying the wrong one is the cause of the MR-dibatalkan 20× error.

| Case | Trigger                                     | Filter                                                                                       |
|------|---------------------------------------------|----------------------------------------------------------------------------------------------|
| **A** | "NIE that ALSO has commitment status X" (subject = issued NIE) | Keep ALL NIE filters (status, jenis_permohonan) **AND** add `status_komitmen` filter on top |
| **B** | "applications whose commitment was [outcome]" (subject = app lifecycle) | **DROP** the valid-NIE `status` filter and `jenis_permohonan` — most cancellations happen *before* a NIE is issued, so requiring active-NIE status undercounts by ~95% |

How to tell them apart:
- The question names "NIE"/"izin edar" as the thing being counted → **Case A**
- The question asks how many were "dibatalkan/ditolak/disetujui" as a lifecycle outcome → **Case B**

Resolve the `status_komitmen` code (final-state vs transient) from `data_dictionary` kategori
`STATUS_KOMITMEN`, sumber `ERBA`. Commitment queries are **ERBA-only** (column does not exist in ERLA).

---

## 6. status_komitmen Format Bug — Mixed '5' and '5.0'

`status_komitmen` is stored as TEXT with **mixed formatting**: some rows store `'5'`, others
store `'5.0'` for the same logical value.

```sql
-- WRONG — silently misses '5.0' rows (~209 rows lost for code 5):
WHERE status_komitmen = '5'

-- CORRECT — captures both formats:
WHERE ROUND(status_komitmen::numeric)::int::text = '5'
-- OR simpler:
WHERE status_komitmen LIKE '5%'
```

Affected codes: `0`, `1`, `4`, `5`, `7`, `8`, `9`. Apply normalization to **every**
`status_komitmen` filter.

---

## 7. Default Scope (when user doesn't specify)

| Missing        | Default                                                                                                                                                                                              |
|----------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Year**       | ALL-TIME via wide bounded range: `tanggal::timestamp >= '2000-01-01' AND tanggal::timestamp < '2030-01-01'` (drops 1900/1970 artifacts automatically). Present total + per-year breakdown via `GROUP BY date_trunc('year', ...)`. Never silently default to a single year (e.g. 2023). |
| **System**     | **NO DEFAULT — you MUST clarify.** See below. |
| **Result limit** | Top 10. Always state the total when truncating.                                                                                                                                                   |

A year or range stated by the user always overrides the default — never silently fall back.
A per-year trend is only for questions that ask for a trend/over-time. It is never a stand-in when
a segment or filter could not be resolved — resolve it or ask, don't answer with a trend instead.

### 7.1 System scope — no default, clarify

Question does not name a system (ERBA / ERLA / gabungan) **and** entity is NIE / permohonan /
produk / BTP → call `request_clarification` (or `ask_user`) **before any SQL**. Never guess.

Options, **Gabungan** marked `recommended`: Gabungan ERBA+ERLA · ERBA saja · ERLA saja.

**Exception:** risiko and komitmen are ERBA-only by definition → proceed, state it, do not ask.

---

## 8. Exclusions (mandatory on every count query)

| Filter              | SQL                                                                                       |
|---------------------|-------------------------------------------------------------------------------------------|
| Test accounts ERBA  | `trader_id::bigint NOT IN (5, 17, 50, 85)`                                                |
| Test accounts ERLA  | `trader_id != 3384`                                                                       |
| Bad data years      | Date range `>= '2000-01-01'` already drops 1900/1970 artifacts (no separate filter needed) |
| NULL tanggal guard  | For GROUP BY without date range: `WHERE tanggal IS NOT NULL AND tanggal != ''`            |
| Regional edge cases | `daerah_* IS NOT NULL AND daerah_* != 'NULL' AND daerah_* != '9999'`                      |
| Blank `status` ERBA | Stored as **four spaces**, never NULL and never `''` — `TRIM(status) = ''` catches it, `status <> ''` does not |

**Where the test-account exclusion actually matters.**

The exclusion is listed here as mandatory and should stay applied everywhere — it is cheap and it
is correct. But its weight is not uniform, and knowing where it bites changes how an answer should
be qualified.

The test traders barely register in the licensed population: they hold almost no issued NIE, so on
**NIE counts** the exclusion moves the figure by an amount too small to matter. Their rows pile up
instead in **Draft** — submissions started and never carried forward — so on **pipeline counts**
the exclusion moves the figure enough to change a verdict on its own.

The practical rule: apply it either way, but when a pipeline figure is being compared against
another source — a dashboard, an earlier report, a number the user remembers — say whether the
exclusion was applied. That single fact often explains the whole gap, and offering it saves a round
of re-querying.

---

## 9. Cast Rules — `t_produk_3_erba` only

**`t_produk_3_erba` stores all columns as TEXT**, including dates and IDs. Cast on that side
before UNION or comparison.

| Column            | Cast                                                    |
|-------------------|---------------------------------------------------------|
| `tanggal`         | `NULLIF(tanggal,'')::timestamp` — a large share of rows hold `''`, so the guard is the point, not decoration |
| `tanggal_bayar`   | `NULLIF(tanggal_bayar,'')::timestamp`                   |
| `trader_id`       | `::bigint` (values are always numeric — the cast is for the comparison, not for safety) |
| `status_komitmen` | `ROUND(...::numeric)::int::text` (see §6 — mixed format) |

⚠️ **This section does NOT extend to the BTP tables — the rule is per TABLE, not per system.**

"ERBA is all TEXT" is true of `t_produk_3_erba` and of nothing else. In `t_btp_3_erba` the four
date columns (`tanggal`, `tanggal_aju`, `tanggal_bayar`, `tanggal_exp`) are already `timestamp`
and `trader_id` is already `bigint`.

Carrying the product-table cast across is not a harmless extra — it **fails the query**:

```
NULLIF(tanggal,'')::timestamp   -- on t_btp_3_erba
→ ERROR: invalid input syntax for type timestamp: ""
```

`NULLIF` forces the empty string into the column's own type, and a `timestamp` column cannot hold
`''`. Compare dates directly on the BTP tables. `t_produk_3_rilis_erla` and `t_btp_3_erla` are
native throughout and need no casts at all.

Because the error surfaces only at execution, it consumes the one corrected retry that Gate 4
allows. When a turn touches a table it has not queried this session, check the types first —
`data_architecture.md` lists them, `describe_table` confirms them.

⚠️ **PostgreSQL only.** `TRY_CAST`, `TRY_CONVERT`, `SAFE_CAST` do not exist — they are
DuckDB/Spark/BigQuery dialects and produce syntax errors. Use `::type` only.

---

## 10. UNION Template — ERBA + ERLA

```sql
SELECT nomor, tanggal::timestamp AS tanggal, trader_id::bigint AS trader_id
FROM t_produk_3_erba
WHERE tanggal IS NOT NULL AND tanggal != ''
  AND status IN ('0999','0906','9999')           -- per §3
  AND jenis_permohonan IN ('301','305')          -- per §4, conditional
  AND trader_id::bigint NOT IN (5, 17, 50, 85)   -- per §8
  AND tanggal::timestamp >= '{Y}-01-01' AND tanggal::timestamp < '{Y+1}-01-01'

UNION ALL

SELECT nomor, tanggal, trader_id
FROM t_produk_3_rilis_erla
WHERE status IN ('0099','0999','0906','9999')
  AND jenis_permohonan IN ('301','304','305')
  AND trader_id != 3384
  AND tanggal >= '{Y}-01-01' AND tanggal < '{Y+1}-01-01'
```

For ALL-TIME: replace year range with `'2000-01-01'` … `'2030-01-01'` on both sides,
then `GROUP BY date_trunc('year', tanggal)` for per-year breakdown.

`nomor` values do NOT overlap across systems — `UNION ALL` is safe.

---

## 11. execute_sql

- **One statement per call.** No `;` — multi-statement SQL is rejected by the runtime and the call
  is wasted. Need two results → two calls, or fold into one query (`UNION ALL` / `GROUP BY` / CTE).
- **Never `EXTRACT(YEAR …)` to filter** — it forces a full table transfer. Use a bounded range
  (§7). `EXTRACT` is fine only for labelling an already-grouped result.
- Prefer filters that push down: a bounded range or a code equality is cheap; a heavy function on
  a TEXT column or an unbounded `ILIKE '%…%'` scans the whole column — use it to discover a code
  once, then count on that code.

---

## 12. Answer Contract — canonical interpretation + number provenance

Every answer takes a POSITION and shows its EVIDENCE. Both duties, always together:

**A. Answer with the canonical interpretation.** A term means what this file and
`filter_code_reference.md` define — lead with ONE decisive number under that definition.
Never present a menu of interpretations as the answer. Only when a term has NO taught
definition and two readings differ materially → decompose neutrally, flag that no canonical
definition exists yet, or clarify (§7.1).

**B. Attach the number's provenance.** Every headline number is accompanied by:
- its source code(s) with the `data_dictionary` description — "kode `7` — Komitmen Disetujui
  Dengan Catatan: 12.339", never a bare number;
- the counting entity (`nomor` / `produk_id` / `trader_id`) and source system (ERBA / ERLA);
- its constituent parts when the canonical definition combines codes — each part labelled
  with its own code, the combined figure shown as a labelled sum;
- when the question touches a code FAMILY (risiko, komitmen, pipeline, ERBA/ERLA), each member
  code reported separately with its label — a merged total only as a labelled sum, never as
  the sole unlabelled answer;
- dictionary descriptions are often English literals ("Pangan Low Risk"): present the
  Indonesian business label + code + the literal — "Risiko Rendah — `301` (Pangan Low Risk)",
  never the English label alone;
- **any abbreviation or shorthand spells out its full term at least once** — general, every
  domain: MR → "Menengah Rendah" (never "Medium Risk" alone — it drops the Rendah/Tinggi
  distinction), MT → "Menengah Tinggi", NIE → "Nomor Izin Edar", and likewise for any other
  shorthand this document or `filter_code_reference.md` uses. The abbreviation may repeat after
  that, never replace the full term as the answer's only identifier.

**C. Time breakdown is part of the default answer shape.** An aggregate answer shows:
total → per-code split → a period × category table (rows = year; month when the range is
≤ 2 years or the user asks; columns = the code split). Build this table with ONE final
`GROUP BY` query shaped like the answer — never assemble it by hand from scattered results.
**Headline vs breakdown.** Take the headline from its own global `COUNT(DISTINCT …)` query with no
`GROUP BY`. Whether a breakdown adds up to that total depends on the grouped column:

- Grouping by a column where one entity spans several rows over time (period, `status`, system, or
  any code family here) → do not sum the partitions; the same `nomor` recurs across them. Keep the
  global count and note the parts need not add up.
- Grouping by a column where one entity holds a single value at a time (`status_komitmen`) → the
  parts are disjoint and do add up to the total; summing the breakdown is fine.

When a column's kind is unclear, treat it as the first case and lean on the global count.

**D. Proportionality.** A narrow single-code, single-system question gets a direct answer +
provenance + time breakdown — not a full decomposition report. Decompose when the question
spans a family or the canonical definition combines codes.

For a specific product or narrow segment (e.g. a named product, a `nama`/`merk` search), and only
when such rows exist, add a few example rows as evidence beside the count — identifier + `nama` +
`merk` + `tanggal`. Keep it short (about 5–10 rows), and keep it out of the chart — the chart
stays on the aggregate query, the example list is text only. Skip the list for broad aggregates.

**The identifier column follows the entity chosen at Gate 3**, so the evidence matches what was
counted rather than merely sitting next to it:

- an **NIE** question shows `nomor` — `MD ` for dalam negeri, `ML ` for impor, always with one
  space after the prefix, so `LIKE 'MD %'` is the pattern that matches stored data;
- a **permohonan** question shows `produk_id`, because that is the unit that was counted.

The mismatch to avoid: a submission that has not yet been granted a licence carries an `ER…`
`nomor`, not an MD/ML one. Listing those rows under an NIE count tells the reader the licences
exist when they do not — the count itself may be right while the evidence beside it contradicts it.

Two format notes worth carrying into the answer when the list is presented as complete: a small
number of rows deviate from the pattern (no space after the prefix, or an embedded carriage
return) and will not be caught by `LIKE 'MD %'`; and `BPOM RI MD …`, the form printed on packaging,
appears nowhere in the database — filtering on it returns nothing.

**D2. Wording.** Use the canonical business term; a natural synonym alongside it is fine — don't
hinge the answer on one exact spelling ("kedaluwarsa"/"kadaluarsa", "meningkat"/"naik" are the same).

**D3. Zero is an answer.** When a correct query returns no rows, say "tidak ada / tidak ditemukan"
plainly — that is the honest result, not a failure to fix; never invent a number to fill the gap.

**E. Hygiene is applied, never spotlighted.** Test-account exclusions, casts, format
normalization (§6), dedup mechanics: always applied, never called out as their own bolded
line/sentence (e.g. never "**Eksklusi:** Akun uji coba telah dikeluarkan dari perhitungan."
standing alone). If a methodology footnote is warranted (the user asked, or the answer
already carries a short *Catatan/Metodologi* bullet list for scope/method/filter), the
exclusion fact may ride along as ONE plain bullet inside that same list — never its own
heading, never its own paragraph, never the only methodology note shown. Provenance =
business meaning (codes, descriptions, entity, system, as-of date for transient states);
plumbing is not provenance and does not get promoted to headline visibility.

**F. Consistency.** The same question MUST produce the same answer — in this session, in a
new session, and in follow-ups. Canonical resolution is deterministic: same wording → same
interpretation (this file + `filter_code_reference.md`) → same SQL shape → same numbers.
Follow-ups reuse validated answers and change only what the user changed. The only
legitimate difference between two runs of the same question is data drift — stamp the as-of
date so it is visible. This contract applies to every answer type: counts, breakdowns,
trends, forecasts, anomaly reports.
