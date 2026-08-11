#DATABASE STRUCTURE MAP - TABLE INVENTORY, JOIN RULES, UNION TOPOLOGY, AND ERBA VS ERLA DIFFERENCES#

Domain: **Registrasi Pangan** only. Supervision (pemeriksaan/pengujian/sampling/balai) is NOT
connected — say so honestly, never invent tables. Forecast questions → `forecast_guide.md`
(computed on-demand via `run_forecast` from `t_produk_3_erba`/`t_btp_3_erba` — do NOT query the
pre-computed `forecast_permohonan` table; it is stale and bypasses the live engine, giving numbers
that differ from the answer).

## Tables

| Table | Coverage | Types | Notes |
|---|---|---|---|
| `t_produk_3_erba` | Sep 2022 → now | **ALL TEXT — cast required** | risk `kategori_dokumen` · commitment `status_komitmen` |
| `t_produk_3_rilis_erla` | 2012 → now | TIMESTAMP/BIGINT | risk `jenis_dokumen` (different codes) · no commitment · **final states only** |
| `t_btp_3_erba` | Jun 2022 → now | **MIXED — not all TEXT** | dates and `trader_id` are already native (see below) |
| `t_btp_3_erla` | Dec 2017 → now | native | still receiving rows; it did **not** stop in 2024 |
| `m_trader_rba` / `m_trader_rla` | master | mixed | scale col: `skala_industri_id` vs `skala_industri` (names differ) |
| `data_dictionary` | — | — | code→label, 21 exact categories (`filter_code_reference.md` §4b) |

**Types are per TABLE, not per system.** "ERBA is all TEXT" is a fact about `t_produk_3_erba` and
about nothing else. `t_btp_3_erba` shares the system but not the typing: its four date columns are
`timestamp` and `trader_id` is `bigint`, while `produk_id` and `status` stay TEXT.

Carrying the product-table cast across is a hard error rather than a harmless extra —
`NULLIF(tanggal,'')::timestamp` on a `timestamp` column raises `invalid input syntax`, and the
failure surfaces only at execution, consuming the turn's one corrected retry. Before querying a
table this turn has not touched, read its row above or confirm with `describe_table`
(`predikat.md` §9).

Identities: `nomor` = NIE · `produk_id` = permohonan · `trader_id` = company.
No unified `mv_*` views exist — combined coverage is always a manual UNION.

## Joins (no foreign keys — these must be known, not guessed)

- product/BTP `.trader_id` → **LEFT JOIN** `m_trader_*` (orphans exist; INNER JOIN drops data).
- Count companies from `t.trader_id`, never `m.trader_id` (LEFT JOIN NULLs).
- Codes → `data_dictionary` by exact `kategori` + `kode` (+ `sumber`).

## UNION topology

| Intent | Tables |
|---|---|
| NIE / produk pangan olahan (combined) | `t_produk_3_erba` ∪ `t_produk_3_rilis_erla` |
| BTP (combined) | `t_btp_3_erba` ∪ `t_btp_3_erla` |
| Total incl BTP (only if user explicitly asks) | all 4 |

> **Forecast exception:** this UNION topology is for general analyst queries ONLY.
> **Forecast is ERBA-only** — never UNION ERLA into a `run_forecast` series
> (`forecast_guide.md §1/§3`; ERLA's CV is always too high). In a forecast context,
> ERLA = a separate historical-trend block, never a mixed series.

"Pangan olahan" = product tables only. Write a separate WHERE per UNION side — status sets,
jenis_permohonan sets, casts, and test-account filters all differ (`predikat.md` §10 template).
`nomor` does not overlap across systems → `UNION ALL` is safe.

**Multi-dimension shapes:** crossed dimensions ("per tahun DAN daerah") = ONE query,
`GROUP BY date_trunc('year', tanggal), daerah_pabrik`. Independent aspects = one query each,
synthesized in the answer. Never emulate a 2D grouping with repeated single-dimension queries.

## ERBA vs ERLA differences that cause wrong answers

- ERBA columns are ALL TEXT → cast before compare/UNION (`predikat.md` §9). ERLA is native.
- **Which columns actually differ (verified against `information_schema`, 2026-08-05).** The two
  tables share these column names but not their types, so the cast belongs on the ERBA side and
  nowhere else:

  | Columns | `t_produk_3_erba` | `t_produk_3_rilis_erla` |
  |---|---|---|
  | `tanggal` `tanggal_aju` `tanggal_bayar` `tanggal_berkas` `tanggal_diambil` `tanggal_exp` `tanggal_hprspb` `tanggal_exp_hprspb` `tanggal_lbl` `last_proses` | TEXT | `timestamp` |
  | `trader_id` `pabrik_id` `produsen_id` `user_id` `td_label` `td_pengajuan` `td_penolakan` `ttd` `perbaiki_label` `single_md` | TEXT | `bigint` |
  | `biaya` `jumlah_bayar` `nilaif0` `pmr` `takaran_saji` | TEXT | `double precision` |
  | `english` `hardcopy` `makanan` `pending` `webreg` `webreg_pgsql` | TEXT | `boolean` |

  Applying the ERBA cast to the ERLA side is not a harmless extra — it raises on a column that is
  already typed, and the failure surfaces only at execution, consuming the turn's one corrected
  retry.

- **A UNION across the two systems must agree on type for every column above.** `UNION types text
  and timestamp cannot be matched` is a hard failure that returns nothing, and it is the single
  most common way a combined ERBA+ERLA query dies. Resolve it by casting the ERBA side up
  (`NULLIF(tanggal,'')::timestamp`, `trader_id::bigint`) so both branches meet at the native type;
  never cast the ERLA side down to text to make the shapes line up, because that silently changes
  how the values sort and compare.

- **ERBA's text dates and ids are clean, which makes the cast safe.** Every row in `tanggal`,
  `tanggal_aju`, `tanggal_bayar`, `tanggal_berkas` and `tanggal_exp` is ISO `YYYY-MM-DD HH:MM:SS`
  with zero blanks and zero malformed values, and `trader_id` is numeric on every row. Ranges:
  `tanggal` 1970-01-01 → today, `tanggal_exp` 1970-01-01 → 2031-08-04. A cast that returns NULL
  here means the filter is wrong, not that the data is dirty.

- Risk: ERBA `kategori_dokumen` (4 tiers), ERLA `jenis_dokumen` (3 tiers, different codes) —
  never reuse one system's code on the other; default risk scope = ERBA-only.
- Commitment: ERBA-only.
- ERBA-only columns: `jenis_penolakan_komitmen`, `kode_kbli`, `ecolabel`, `sub_kemasan_id`.

## Classification columns (a product concept can live in several)

`jenis_pangan` · `kategori_pangan` · `klasifikasi_id` · `pemrosesan` · `peruntukan` are all
filled in both systems. `nama_kategori` is filled in BOTH: **ERBA ~40%, ERLA ~96%** — ERLA is
the richer catalogue and is the primary place to look up a free product segment (search only,
never group). The same concept can live in a DIFFERENT column per system. Check
`filter_code_reference.md` §4–§5 first; if two candidate columns both match with materially
different populations → clarify. (`klasifikasi_id` is a valid, fully-populated column.)

**"Belum dikategorikan" flips answer by column, so answer on the column the user named.** Fill
rates are not comparable across these columns — in `t_produk_3_erba` (259.681 rows)
`jenis_pangan` and `kategori_pangan` have **0 empty**, `kategori_dokumen` 1.130, and
`nama_kategori` **154.798**. The same question therefore answers "none" or "154 thousand"
depending only on which column was read; naming the column used is what makes the answer checkable.

**Coded segment columns do not share a namespace across systems.** `jenis_pangan` has zero overlap
between ERBA and ERLA — not "mostly different", literally no shared value: the ranges differ and
the lengths differ. `kategori_pangan` is comparable only on its 2-digit prefix; below that the two
systems use different depths and identical-looking prefixes are not the same category.

The consequence for planning a query: a segment code carried from one system to the other always
returns zero, and that zero is a namespace mismatch, never evidence that the segment is absent.
Resolve each side on its own, every time (`filter_code_reference.md` §5).

## Finding a dimension this file does not list

This file names tables and traps, not every column. A dimension missing here is not missing from
the data — locate it before falling back to one you already know.

1. **Does the column exist, and where?** Column sets are not symmetric across the two tables
   (`describe_table`). Present in one system only = the question is single-system *structurally*;
   say which system rather than implying both contributed.
2. **Coded or free text?** A code means nothing alone — resolve it in `data_dictionary` by
   `kategori` AND `sumber` (the same code sits under several categories). Locate the category via
   `WHERE deskripsi ILIKE '%<term>%'`. No matching category → the codes are undocumented: report
   the distribution, say the meaning is unrecorded, never borrow a label from another category.
3. **Free text: probe, then filter exactly.** `ILIKE` discovers, it never filters.
   `SELECT nama_kategori, COUNT(*) ... WHERE nama_kategori ILIKE '%<term>%' GROUP BY 1 ORDER BY 2 DESC`,
   then `WHERE nama_kategori = '<exact value>'`. Shipping the wildcard answered 17.645 where the
   exact category held 309 — neighbours are often LARGER, so widening hands the answer to a segment
   nobody asked about.

**Sentinels are not categories.** `'0'`, `'9999'`, `''` = not filled, and they can top a ranking.
Exclude them from rankings; report them separately as a data-quality note.

**Parent codes bundle what child codes split.** A question naming a specific material must descend
to the child column; answered at the parent level it can be off by orders of magnitude.

**Pick the column the question means.** Registrant, manufacturer and factory are different parties
and rank differently; submission/payment/issue/expiry dates answer different questions. Name the
column you used.

## Tools

This file = planning map. `describe_table` = verify exact column names before complex SQL.
