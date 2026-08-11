# Data Architecture — Semantic Map & Relations (BPOM RPO)

> **Status:** Updated June 2026. ERBA is now the primary system for 2023+ data (245,049 rows).
> ERBA stores ALL columns as TEXT — see `data_quality_rules.md` for mandatory cast rules.
>
> **Purpose of this file:** give the agent a *relations & meaning map* (joins, UNION, which column
> belongs to which system, prohibitions) that **cannot** be discovered from `list_tables`/`describe_table`.
> Use this for query planning; use `describe_table` only to **verify exact column names** when uncertain.

---

## 0. Domain router — which domain does this question belong to?

| If the user asks about… | Domain | See |
|---|---|---|
| izin edar / NIE / permohonan / product / BTP / company / risk / scale / commitment | **Registrasi Pangan** | this file (sections 1–6) |
| predictions / forecast permohonan | Forecast | `context/forecast_guide.md` (table `forecast_permohonan`) |

Determine the domain FIRST. Wrong domain = completely wrong answer.

> **Supervision domain is NOT connected.** Questions about pemeriksaan / pengujian / sampling / inspection / balai (post-market supervision) cannot be answered — that database is not attached to this project. Say so honestly; do NOT route to or invent `star.*` / inspection tables.

---

## 1. Table inventory — Registrasi Pangan (`warehouse.public.*`)

| Table | Rows | Date range | Column types | Risk / Commitment |
|---|---|---|---|---|
| `t_produk_3_erba` | 245,049 | Sep 2022 → now | **ALL TEXT** ⚠️ | `kategori_dokumen` / `status_komitmen` |
| `t_produk_3_rilis_erla` | 412,607 | 2012 → now | TIMESTAMP / BIGINT | `jenis_dokumen` / ✗ not available |
| `t_btp_3_erba` | 6,696 | 2023 → now | **ALL TEXT** ⚠️ | — |
| `t_btp_3_erla` | 9,782 | 2018 → 2024 | TIMESTAMP / BIGINT | — |
| `m_trader_rba` | 14,642 | — | mixed | Scale: `skala_industri_id` |
| `m_trader_rla` | 10,284 | — | mixed | Scale: `skala_industri` (different name!) |
| `data_dictionary` | 1,141 | — | — | 21 categories — see `code_resolution.md` |
| `forecast_permohonan` | 111 | Feb 2022 → Apr 2031 | — | 51 actual + 60 predicted months |

> Key identities: `nomor` = NIE (izin edar), `produk_id` = permohonan, `trader_id` = company.
>
> **ERBA/ERLA handover:** 2022–2023 — both systems were active in that period.
> ERBA is the primary system for **2023+ data**. ERLA covers **2012–2022** historical data.
> For ALL-TIME queries: UNION ERBA + ERLA. `nomor` values do NOT overlap — UNION ALL is safe.
>
> ⚠️ **ERBA TEXT columns:** `tanggal`, `tanggal_bayar`, `trader_id` must be cast before UNION.
> See `data_quality_rules.md` §ERBA Schema for the canonical UNION template.

---

## 2. ERD / relations & join rules (NO formal FOREIGN KEY)

All columns are nullable; no FK to introspect → **joins must be known, not guessed.**

```
t_produk_3_erba.trader_id        ──(LEFT JOIN)──►  m_trader_rba.trader_id
t_produk_3_rilis_erla.trader_id  ──(LEFT JOIN)──►  m_trader_rla.trader_id
t_btp_3_erba / t_btp_3_erla      ──(LEFT JOIN)──►  m_trader_* (via trader_id)
all product/btp tables            ── code resolution ──► data_dictionary (by category+code)
```

Mandatory join rules:
- **Always `LEFT JOIN`** to `m_trader_*` — there are **orphan `trader_id`** values (products with no master record). `INNER JOIN` will drop data.
- **Count companies from `t.trader_id`**, NOT `m.trader_id` — `COUNT(DISTINCT m.trader_id)` is wrong because LEFT JOIN can produce NULL.
- **No unified view** (`mv_produk_gabungan` etc.) — ERBA+ERLA coverage **must be UNION manually**.

---

## 3. UNION topology (full coverage)

| Intent | Tables to UNION |
|---|---|
| NIE/Food product **combined** | `t_produk_3_erba` ∪ `t_produk_3_rilis_erla` |
| BTP combined | `t_btp_3_erba` ∪ `t_btp_3_erla` |
| **Permohonan pangan olahan** combined | `t_produk_3_erba` ∪ `t_produk_3_rilis_erla` — **product tables only** (same "pangan olahan = product" rule as NIE). e.g. ERBA 42.329 + ERLA 18.884 = 61.213 for 2023. |
| **Permohonan total incl BTP** (only if user explicitly says total / BTP / all) | 4 tables: product + BTP, ERBA + ERLA (distinct `UNION`, since `produk_id` can overlap across tables) |

> "pangan olahan" = **product** tables only; BTP is counted separately unless user requests total/both.
> ERBA vs ERLA **filters differ** → write WHERE for each side of the UNION separately (see `query_recipes.md`).

---

## 4. Structural differences ERBA vs ERLA (primary source of errors)

| Aspect | ERBA | ERLA |
|---|---|---|
| Data year range | Sep 2022 → now | 2012 → now |
| Rows (product) | 245,049 | 412,607 |
| Column types (`tanggal`, `trader_id`) | **TEXT — requires cast** | TIMESTAMP / BIGINT |
| Risk column | `kategori_dokumen` ✓ | **NOT PRESENT** (`jenis_dokumen` has risk via different codes — see §4a) |
| Commitment column | `status_komitmen` ✓ | **NOT PRESENT** |
| Scale column (master) | `skala_industri_id` | `skala_industri` (**different name**) |
| Province (master) | `provinsi_id` (bigint) | `provinsi` (text) |
| Valid status (NIE) | `0999, 0906, 9999` | + `0099` |
| jenis_permohonan (NIE) | `301, 305` | + `304` (Daftar Ulang) |
| Test accounts (exclude) | `trader_id::bigint NOT IN (5,17,50,85)` | `trader_id != 3384` |
| ERBA-only columns | `jenis_penolakan_komitmen`, `kode_kbli`, `ecolabel`, `sni_sukarela`, `sub_kemasan_id`, `status_komitmen` | — |

**Routine implication:** questions about **commitment** → **ERBA-only** (column does not exist in ERLA).
For **risk** queries: ERBA uses `kategori_dokumen`, ERLA uses `jenis_dokumen` with **different codes** — see §4a.

### §4a — Risk Column and Code Differences (CRITICAL)

ERBA and ERLA track risk through different columns; **resolve each system's codes from the
dictionary, sumber-aware** (`code_translation_protocol.md`) — do not read a code→level table here.
ERBA risk = `kategori_dokumen` (kategori `KATEGORI_DOKUMEN`, **4 levels**); ERLA risk =
`jenis_dokumen` (kategori `JENIS_DOKUMEN`, **3 levels**: Low / High / Medium).

⚠️ The same numeric code means different things in the two systems, and **ERLA has no separate
Menengah Tinggi** — its Medium-Risk code spans MT + MR (so ERLA cannot isolate MT; for an MT count
ERBA is authoritative). Never apply the same code to both tables; write a **separate WHERE per UNION
side**. If equating an ERLA level to an ERBA level, test by magnitude first (protocol §3). Default
risk scope = ERBA-only; see `business_glossary.md` §Risk categories.

---

## 5. Main column groups (orientation, not a complete list)

`t_produk_3_erba` (~100 columns). Verify exact names with `describe_table`. Column groups:
- **Identity:** `produk_id`, `nomor` (NIE), `nama`, `merk`
- **Company/factory/producer:** `trader_id`, `pabrik_id`, `produsen_id` + columns with `*_pabrik`/`*_produsen` suffix
- **Classification:** `jenis_pangan`, `kategori_pangan`, `nama_kategori`
- **Regulatory:** `kategori_dokumen` (risk), `status_komitmen`, `jenis_penolakan_komitmen`
- **Status:** `status`, `status_produk`, `status_usaha`
- **Permohonan:** `jenis_permohonan`, `jenis_dokumen`
- **Time:** `tanggal_aju`, `tanggal` (ISSUE date — for NIE), `tanggal_bayar` (PAYMENT date — for permohonan), `tanggal_exp`
- **Attributes:** `pmr`, `ecolabel`, `klaim`, `kemasan_id`

⚠️ **Deprecated columns — do NOT use for filters/grouping:** `klasifikasi_id`, `takaran_saji` (no longer used by BPOM).

---

## 6. Special cases
- **Makloon** (contract manufacturing): `status_produk = '304'` (ERBA only). Use `produsen_*` columns, not pabrik/trader columns.
- **Disambiguating similar columns:** `kategori_dokumen` (risk) ≠ `jenis_dokumen` (document type); `skala_industri(_id)` (business scale) ≠ `status_usaha` (31=Producer/33=Importer). See `business_glossary.md`.

---

## 7. How to use alongside introspection tools
- **This file** = relations map & join intent (planning).
- **`describe_table`** = verify exact column names/types before complex queries.
- **`seeknal source sync`** (if run) populates `.seeknal/context/sources/` with auto-generated overview/columns/relationships/profiling — a complement, not a replacement for this semantic map (sync cannot infer joins because there are no FKs).
