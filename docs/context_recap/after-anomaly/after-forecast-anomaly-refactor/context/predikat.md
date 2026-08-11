#PREDIKAT - RULES FOR ACCURATE COUNTING, STATUS FILTERS, APPLICATION TYPES, AND COMMITMENT CASES ON VERSIONED TABLES#

> **Single source of truth.** Reference this file. DO NOT recall literals from memory.
> Each rule appears **exactly once** — here.

---

## 1. Counting Method (CRITICAL — tables are versioned)

The product tables are **versioned**: status `9999` means "Sudah Diubah" (revised). A single
NIE/permohonan can span multiple rows. `COUNT(*)` over-counts because it counts revisions, not
entities. Magnitude of over-count: **+25% ERBA, +57% ERLA**.

| Entity     | Method                      | Why                                              |
|------------|-----------------------------|--------------------------------------------------|
| NIE        | `COUNT(DISTINCT nomor)`     | One NIE = one `nomor`; revisions share `nomor`   |
| Permohonan | `COUNT(DISTINCT produk_id)` | One application = one `produk_id`                |
| Perusahaan | `COUNT(DISTINCT t.trader_id)` | Count from the product table, NOT `m_trader_*` — `LEFT JOIN` produces NULL for orphans, so `COUNT(DISTINCT m.trader_id)` silently drops them |

`COUNT(*)` on these tables is a **BLOCK** — the answer is wrong by 25–57%, not approximately right.

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
| **Permohonan (applications)**         | "permohonan/registrasi/pengajuan"             | all types `IN ('301','302','303','304','305')`, **no status filter** |

**"Terbit" is NOT a JP trigger.** Every NIE "terbit" — "NIE yang terbit di 2025" counts ALL
jenis_permohonan in that period. Only the explicit word "baru" narrows to exclude 302 (mayor):
ERBA `IN ('301','303','305')`.
A product whose current valid NIE came via Perubahan (`302`/`303`) still holds an active NIE;
filtering by `('301','305')` without "baru" undercounts materially (verified ~13%).
**Default when "baru" is absent → no JP filter (status filter only).**

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

---

## 9. ERBA Cast Rules (all columns are TEXT)

ERBA stores **all** columns as TEXT, including dates and IDs. ERLA uses native TIMESTAMP/BIGINT.
**Always cast on the ERBA side** before UNION or comparison.

| ERBA Column       | Cast                                                    |
|-------------------|---------------------------------------------------------|
| `tanggal`         | `::timestamp` (or `NULLIF(tanggal,'')::timestamp` for empty-string safety) |
| `tanggal_bayar`   | `::timestamp`                                           |
| `trader_id`       | `::bigint`                                              |
| `status_komitmen` | `::numeric)::int::text` (see §6 — mixed format)        |

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
- **any abbreviation or shorthand used in the answer spells out its full term at least once**
  — this is GENERAL, not limited to any one domain (risk, pipeline, segment, entity, ...): MR
  → "Menengah Rendah" (never "Medium Risk" alone — that drops the Rendah/Tinggi distinction
  that IS the classification), MT → "Menengah Tinggi", JP → "Jenis Permohonan", BTP → "Bahan
  Tambahan Pangan", NIE → "Nomor Izin Edar", AMDK → "Air Minum Dalam Kemasan", UMKM → "Usaha
  Mikro, Kecil, dan Menengah" — and the same for any other shorthand this document or
  `filter_code_reference.md` uses. The abbreviation may follow or repeat after that, never
  replace the full term as the answer's only identifier.

**C. Time breakdown is part of the default answer shape.** An aggregate answer shows:
total → per-code split → a period × category table (rows = year; month when the range is
≤ 2 years or the user asks; columns = the code split). Build this table with ONE final
`GROUP BY` query shaped like the answer — never assemble it by hand from scattered results.
**Headline vs breakdown — never derive one from the other.** The headline total comes from its
OWN global `COUNT(DISTINCT …)` query with NO `GROUP BY`. It is NEVER obtained by adding up the
rows of a partitioned result — any partition: period, status code, system, or code family. These
tables are versioned, so one `nomor` legitimately appears in several partitions (revisions across
years, status transitions); summing a breakdown therefore inflates the total — measured at
1.2x–1.9x on real populations here, an error large enough to change the business conclusion. The
longer a population's history, the worse it gets: a legacy code family summed per year came to
12.962 against an actual 6.965. If the only query
that succeeded was partitioned, spend one more call on the global query rather than adding the
rows; if the budget is gone, report the breakdown and say the total is not yet established —
never invent it by summation. Always state briefly that the parts need not sum to the total.

**D. Proportionality.** A narrow single-code, single-system question gets a direct answer +
provenance + time breakdown — not a full decomposition report. Decompose when the question
spans a family or the canonical definition combines codes.

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
