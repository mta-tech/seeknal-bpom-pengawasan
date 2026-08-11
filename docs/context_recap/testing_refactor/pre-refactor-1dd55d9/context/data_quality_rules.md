# Data Quality Rules

These filters MUST be applied to NIE queries. For permohonan counts, apply
only the exclusions marked as universal (bad data years, test accounts).
Do NOT apply status filters to permohonan — see the status section below.

## Mandatory exclusions

### Bad data years
Exclude artifact years from all date-based queries:
```sql
EXTRACT(YEAR FROM tanggal) NOT IN (1900, 1970)
-- or for permohonan:
EXTRACT(YEAR FROM tanggal_bayar) NOT IN (1900, 1970)
```

### Date filter pattern — use ranges, not EXTRACT, for year scoping

When filtering to a specific year, use a date range instead of `EXTRACT(YEAR FROM ...)`.
Date ranges are pushed down to PostgreSQL; `EXTRACT()` is evaluated in DuckDB after a
full table transfer. On large tables (>100MB) over SSH tunnel, `EXTRACT` filters
cause timeouts.

**Correct — single year {Y}, pushed to PostgreSQL:**
```sql
WHERE tanggal >= '{Y}-01-01' AND tanggal < '{Y+1}-01-01'
```

**No year specified — all-time, still a range (NO EXTRACT):**
```sql
-- A wide bounded range stays pushed to PostgreSQL AND drops 1900/1970 artifacts.
WHERE tanggal >= '2000-01-01' AND tanggal < '2030-01-01'
-- For a per-year breakdown, GROUP (not filter) with date_trunc:
--   ... GROUP BY date_trunc('year', tanggal)
```

**Avoid — full table transfer before filtering:**
```sql
WHERE EXTRACT(YEAR FROM tanggal) = 2023
```

This applies to: `tanggal`, `tanggal_bayar`, and any other timestamp columns.

### Test accounts
Always exclude test/internal accounts:
- ERBA: `trader_id NOT IN (5, 17, 50, 85)`
- ERLA: `trader_id != 3384`

## Valid status values

**NIE queries only** — do NOT apply to permohonan counts.

Permohonan = all applications submitted regardless of outcome. For permohonan
counts, omit the status filter entirely.

| Table | Valid statuses (NIE only) |
|---|---|
| ERBA (`t_produk_3_erba`, `t_btp_3_erba`) | `'0999'`, `'0906'`, `'9999'` |
| ERLA (`t_produk_3_rilis_erla`, `t_btp_3_erla`) | `'0099'`, `'0999'`, `'0906'`, `'9999'` |

## jenis_permohonan — conditional, by intent (RC-2)

The `jenis_permohonan` filter is **not universal**. Choose by what the user is asking:

| Intent | Signal | jenis_permohonan filter |
|---|---|---|
| **Newly issued NIE** | "NIE baru", "terbit/diterbitkan di {periode}", "baru" | ERBA `IN ('301','305')`; ERLA `IN ('301','304','305')` |
| **All active NIE / total registered** | "total produk terdaftar", "berapa NIE/produk {segmen}" (current holders) | **no `jenis_permohonan` filter** — rely on valid `status` alone |
| **Permohonan (applications)** | "permohonan/registrasi/pengajuan" | all types `IN ('301','302','303','304','305')`, **no status filter** |

A product whose current valid NIE came via Perubahan (`302`/`303`) still holds an active NIE.
Filtering "all active NIE" by `('301','305')` drops those products and undercounts (e.g. Produk MD
2025: 30,760 with the filter vs 36,706 without). **Default when ambiguous and the word "baru" is
absent → treat as "all active NIE" (status filter only), and state the basis in the answer.**
See also `SEEKNAL_ASK.md` §Canonical Definitions ("total NIE").

## Commitment queries — two distinct cases (RC-4)

`status_komitmen` questions split into two different counts. Decide which one the user means
**before** writing SQL; applying the wrong one is the cause of the MR-dibatalkan error (254 vs
~5,199).

**Case A — "NIE that ALSO has commitment status X"**
(e.g. "berapa NIE MR yang komitmennya disetujui?") — the subject is the issued NIE.
→ Keep ALL NIE filters; `status_komitmen` is an additional filter on top.
```sql
WHERE kategori_dokumen = '303'                                   -- MR scope
  AND status IN ('0999','0906','9999')                           -- valid NIE — REQUIRED here
  AND jenis_permohonan IN ('301','305')                          -- NIE app types — REQUIRED here
  AND ROUND(status_komitmen::numeric)::int::text = '<code>'      -- resolve code via dictionary
  AND tanggal >= '...' AND tanggal < '...'
  AND trader_id NOT IN ('5','17','50','85')
```

**Case B — "applications whose commitment was [outcome]"**
(e.g. "berapa MR yang dibatalkan?") — the subject is the application lifecycle, NOT the NIE.
→ **Drop the valid-NIE `status` filter** — most cancellations happen *before* a NIE is issued, so
requiring active-NIE status undercounts by ~95%.
```sql
WHERE kategori_dokumen = '303'                                   -- MR scope
  AND ROUND(status_komitmen::numeric)::int::text = '<code>'      -- final-state code, resolved
  AND trader_id NOT IN ('5','17','50','85')
  -- NO status IN (...) filter, and no jenis_permohonan filter
```

How to tell them apart: if the question names "NIE"/"izin edar" as the thing being counted → Case A;
if it asks how many were "dibatalkan/ditolak/disetujui" as a lifecycle outcome → Case B. Resolve
the `status_komitmen` code (final vs transient) from the dictionary (`code_translation_protocol.md`).

## Date column rules

| What to count | Correct column | Wrong column |
|---|---|---|
| NIE (izin edar) | `tanggal` — issue date | `tanggal_aju`, `tanggal_bayar` |
| Permohonan | `tanggal_bayar` — payment date | `tanggal_aju` (submission only) |

Other date columns (`tanggal_berkas`, `tanggal_diambil`, `tanggal_exp`) are process
dates and should not be used for counting.

The same identity holds across all four product/BTP tables. A BTP table (`t_btp_3_erba`,
`t_btp_3_erla`) is structurally a product table: count NIE with `COUNT(DISTINCT nomor)` on
`tanggal`, count permohonan with `COUNT(DISTINCT produk_id)` on `tanggal_bayar`, and identify
the registrant via `trader_id` — the same columns as `t_produk_3_*`. The entity (NIE vs
permohonan) decides the date/count column; the table being BTP does not change it, and there
is no separate `user_id`-based counting for BTP.

## Coverage-aware column choice (general principle)

When more than one column can represent the same concept, **choose by data coverage, not by name
match**. A semantically-plausible column is useless as a grouping/ranking key if most of its rows
are empty.

- Before `GROUP BY` / ranking on a dimension, prefer the column (or resolvable code) with the best
  coverage for that concept.
- If the result is **dominated by NULL / `'NULL'` / "Tanpa Kategori" / "tidak teridentifikasi"**,
  stop — switch to a more complete column for the same concept, or a resolvable code, before answering.
- If coverage is still low, **report the limitation honestly** (state the share that is unidentified).
  Never present "Tanpa Kategori"/"NULL" as if it were the answer, and never silently switch to a
  different subject/dimension that happens to have data.

Known coverage facts (verify by query — data drifts):
- **Category:** `nama_kategori` is mostly empty (~3 of 5 rows) → unusable as a grouping key. For a
  category breakdown/ranking use the resolvable code `kategori_pangan` → AKRONIM `'KP '||LEFT(,2)`
  (near-full coverage; see `code_resolution.md`). `nama_kategori` ILIKE is for *searching* a named
  segment, not for grouping.
- **Region:** `daerah_pabrik` (factory) resolves for only a minority of rows; the trader master
  `m_trader_rba.kotakab_id`/`provinsi_id` (company location) is essentially complete. For an
  unqualified "daerah", prefer the trader-master kab/kota; see `intent_mapping.md` §Daerah.

## Regional code edge cases

When querying `daerah_pabrik`, `daerah_trader`, or `daerah_produsen`:
- Filter out: `daerah_pabrik IS NOT NULL AND daerah_pabrik != 'NULL' AND daerah_pabrik != '9999'`
- String `'NULL'` = missing data, exclude
- `'9999'` = test/placeholder code, exclude
- Unmatched codes (not in `data_dictionary`): these are **legacy Kemendagri codes from the ERLA system** (RPO update pending). Display the original code and explain it that way (see `code_resolution.md`) — do not guess a label.

## Skala industri NULL handling

When grouping by skala industri:
- `NULL` or empty string or `' '` (single space) → label as **Importir**
- Use `TRIM()` before matching to handle trailing spaces
- `COALESCE(dd.deskripsi, 'Importir')` is the correct pattern

## Default time scope

When the user does NOT mention a year or range, do not assume one. Count ALL available
years (all-time) using a wide bounded range — `tanggal >= '2000-01-01' AND tanggal < '2030-01-01'`
(`tanggal_bayar` for permohonan). The wide range stays pushed to PostgreSQL and already drops
the 1900/1970 artifacts, so no separate `EXTRACT` filter is needed. Present a total plus a
per-year breakdown (`GROUP BY date_trunc('year', ...)`) and state the scope in the answer.
A year or range stated by the user always overrides this default — never silently fall back
to a single year (e.g. 2023).

## Default result limit

When the user does not specify a maximum, return the top 10 results by default.
Always mention the total count if truncating.

---

## ERBA Schema: All Columns Are TEXT — Mandatory Cast

ERBA (`t_produk_3_erba`, `t_btp_3_erba`) stores all columns as TEXT, including
date and numeric columns. ERLA uses TIMESTAMP and BIGINT. **Always cast on the
ERBA side** before UNION or comparison with ERLA.

| ERBA Column | Cast required | Example |
|---|---|---|
| `tanggal` | `::timestamp` | `tanggal::timestamp >= '2022-01-01'` |
| `tanggal_bayar` | `::timestamp` | `tanggal_bayar::timestamp` |
| `trader_id` | `::bigint` | `trader_id::bigint NOT IN (5,17,50,85)` |
| `status_komitmen` | see normalization below | — |

⚠️ **Use only native PostgreSQL casts** — `::timestamp`, `::bigint`, or `NULLIF(col,'')::timestamp`
for empty-string safety. **PostgreSQL has NO `TRY_CAST`, `TRY_CONVERT`, or `SAFE_CAST`** (those are
DuckDB/Spark/BigQuery dialects) — emitting them is a **syntax error** and the query fails. Never use
them; cast with `::type` and guard bad values with the `WHERE col IS NOT NULL AND col != ''` filter.

**UNION ERBA + ERLA — canonical template (cast on ERBA side only):**

```sql
SELECT nomor, tanggal::timestamp AS tanggal, trader_id::bigint AS trader_id
FROM warehouse.public.t_produk_3_erba
WHERE tanggal IS NOT NULL AND tanggal != ''
  AND status IN ('0999','0906','9999')
  AND jenis_permohonan IN ('301','305')
  AND trader_id::bigint NOT IN (5,17,50,85)
  AND tanggal::timestamp >= '{Y}-01-01' AND tanggal::timestamp < '{Y+1}-01-01'

UNION ALL

SELECT nomor, tanggal, trader_id
FROM warehouse.public.t_produk_3_rilis_erla
WHERE status IN ('0099','0999','0906','9999')
  AND jenis_permohonan IN ('301','304','305')
  AND trader_id != 3384
  AND tanggal >= '{Y}-01-01' AND tanggal < '{Y+1}-01-01'
```

For ALL-TIME: replace year range with `'2000-01-01'`…`'2030-01-01'` on both sides,
then `GROUP BY date_trunc('year', tanggal)`.

---

## status_komitmen: Float/Integer Normalization

ERBA stores `status_komitmen` as TEXT. The column contains **mixed formatting**:
some rows store `'5'`, others store `'5.0'` for the same logical value.

```sql
-- WRONG — silently misses '5.0' rows:
WHERE status_komitmen = '5'

-- CORRECT — captures both '5' and '5.0':
WHERE ROUND(status_komitmen::numeric)::int::text = '5'

-- ALTERNATIVE (simpler):
WHERE status_komitmen LIKE '5%'
```

Apply this normalization for ALL `status_komitmen` filters (disetujui, dibatalkan,
pending, etc.). The affected codes are: `0`, `1`, `4`, `5`, `7`, `8`, `9`.

---

## NULL tanggal in ERBA

A significant portion of ERBA rows have `tanggal = NULL` or `tanggal = ''`. These are
products still in evaluation — no NIE has been issued yet.

- Date range filters exclude them automatically (`NULL::timestamp` fails the comparison).
- For GROUP BY queries without a date range filter, add explicit guard:
  `WHERE tanggal IS NOT NULL AND tanggal != ''`
- These rows are correctly excluded from all NIE counts (NIE requires a valid `tanggal`).
