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
| `t_produk_3_rilis_erla` | 2012 → now | TIMESTAMP/BIGINT | risk `jenis_dokumen` (different codes) · no commitment |
| `t_btp_3_erba` / `t_btp_3_erla` | 2023→now / 2018→2024 | TEXT / native | BTP (food additives) |
| `m_trader_rba` / `m_trader_rla` | master | mixed | scale col: `skala_industri_id` vs `skala_industri` (names differ) |
| `data_dictionary` | — | — | code→label, 21 exact categories (`filter_code_reference.md` §4b) |

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
- Risk: ERBA `kategori_dokumen` (4 tiers), ERLA `jenis_dokumen` (3 tiers, different codes) —
  never reuse one system's code on the other; default risk scope = ERBA-only.
- Commitment: ERBA-only.
- ERBA-only columns: `jenis_penolakan_komitmen`, `kode_kbli`, `ecolabel`, `sub_kemasan_id`.

## Classification columns (a product concept can live in several)

`jenis_pangan` · `kategori_pangan` · `klasifikasi_id` · `pemrosesan` · `peruntukan` are all
filled in both systems; `nama_kategori` is ERBA-only ~40% filled (search only, never group).
The same concept can live in a DIFFERENT column per system. Check
`filter_code_reference.md` §4–§5 first; if two candidate columns both match with materially
different populations → clarify. (`klasifikasi_id` is a valid, fully-populated column.)

## Tools

This file = planning map. `describe_table` = verify exact column names before complex SQL.
