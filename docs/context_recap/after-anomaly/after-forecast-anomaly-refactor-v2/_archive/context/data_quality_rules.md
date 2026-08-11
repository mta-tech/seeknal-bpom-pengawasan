# Data Quality — Residual Quirks

> **Counting method, mandatory filters, valid status, scope defaults, casts, commitment cases,
> and `status_komitmen` normalization now live in `context/predikat.md` — the single source of
> truth. Read that file before writing aggregation SQL.**
>
> This file holds only what is left: coverage traps and column edge cases that shape *which
> column* you pick, not *how* you filter.

---

## Coverage-aware column choice (general principle)

When more than one column can represent the same concept, **choose by data coverage, not by name
match**. A semantically-plausible column is useless as a grouping or ranking key if most of its
rows are empty.

- Before `GROUP BY` / ranking on a dimension, prefer the column (or resolvable code) with the best
  coverage for that concept.
- If the result is **dominated by NULL / `'NULL'` / "Tanpa Kategori" / "tidak teridentifikasi"** —
  stop. Switch to a more complete column for the same concept, or to a resolvable code, before
  answering.
- If coverage is still low, **report the limitation honestly** (state the share that is
  unidentified). Never present "Tanpa Kategori" / "NULL" as if it were the answer, and never
  silently switch to a different subject or dimension that happens to have data.

**Known coverage facts** (verify by query — data drifts):

- **Category.** `nama_kategori` is **mostly empty** — unusable as a grouping key. For a category
  breakdown or ranking, use the resolvable code `kategori_pangan` → AKRONIM `'KP ' || LEFT(…,2)`
  (near-full coverage; see `code_resolution.md`).
  `nama_kategori ILIKE` is for **searching** a named segment (see `business_glossary.md` §Product
  Segment Codes), **never** for grouping.
- **Region.** `daerah_pabrik` (factory) resolves for only a minority of rows; the trader master
  `m_trader_rba.kotakab_id` / `provinsi_id` (company location) is essentially complete. For an
  unqualified "daerah", prefer the trader-master kab/kota — see `intent_mapping.md` §Daerah.

---

## Regional code edge cases

When querying `daerah_pabrik`, `daerah_trader`, or `daerah_produsen`:

- String `'NULL'` = missing data → exclude.
- `'9999'` = test/placeholder → exclude.
  *(Note: `9999` in the `STATUS` column means "Sudah Diubah" — a different meaning entirely.
  Codes are only meaningful within their `kategori`.)*
- Conversion to the dictionary format is required — see `code_resolution.md` §Regional code
  conversion (`ROUND(col::numeric / 100, 2)::text`).
- **Unmatched codes** (no dictionary match after conversion) are **legacy Kemendagri codes carried
  over from ERLA** (RPO update pending, per Pusdatin). Present the raw code with that explanation —
  never a bare "label not found", and never a guessed label.

---

## NULL `tanggal` in ERBA

A significant share of ERBA rows carry `tanggal = NULL` or `''` — products still in evaluation,
no NIE issued yet.

- Date-range filters exclude them automatically (`NULL::timestamp` fails the comparison).
- For `GROUP BY` without a date-range filter, guard explicitly:
  `WHERE tanggal IS NOT NULL AND tanggal != ''`
- They are correctly excluded from every NIE count — a NIE requires a valid `tanggal`.

---

## Deprecated / unused columns

These exist in the schema but are **no longer used** by BPOM. Do not filter or group by them:

- `klasifikasi_id` in `t_produk_3_erba`
- `takaran_saji` in `t_produk_3_erba`
