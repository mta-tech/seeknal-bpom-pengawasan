# Code Resolution Guide

The `data_dictionary` table resolves all numeric/coded column
values to human-readable labels. **Never present raw codes to users.**

> **Code MEANING is resolved by `context/code_translation_protocol.md`** — the two-way,
> `sumber`-aware lookup. This file covers only the **transformation procedures** that the
> lookup needs (the column→kategori pointer, region `ROUND(/100,2)`, AKRONIM, legacy codes).
> Do NOT read or write code→meaning answers here; look them up at runtime via the protocol.
> Every lookup/JOIN MUST filter `data_dictionary.sumber` (`ERBA` / `ERLA` / `ERBA dan ERLA`
> / `ERLA dan ERBA`) — omitting it fan-outs multi-source categories (`STATUS`, `KEMASAN_ID`)
> and shared codes (e.g. `9999`).

## Table structure

```
sumber    — source scope (e.g. 'ERBA dan ERLA')
kategori  — category name (the lookup key)
kode      — the code value (e.g. '1', '301', '72.71')
deskripsi — human-readable label (e.g. 'Mikro', 'Permohonan Baru')
```

## Resolution workflow

After every query that returns coded columns:
1. Identify which columns contain codes
2. Look up the correct `kategori` from the table below
3. JOIN or query `data_dictionary` to get `deskripsi`
4. Replace codes with labels in the final answer

**Single lookup query (always filter `sumber`, with fallback):**
```sql
-- Step 1: try system-specific sumber first
SELECT sumber, kode, deskripsi
FROM data_dictionary
WHERE kategori = '<kategori>'
  AND sumber IN ('<SYSTEM>', 'ERBA dan ERLA', 'ERLA dan ERBA')   -- <SYSTEM> = ERBA | ERLA
ORDER BY kode;

-- Step 2: if 0 rows, fall back to any sumber (some codes are stored under a different
-- system label than the table they appear in — e.g. certain ERLA STATUS codes are only
-- registered with sumber='ERBA' or 'ERLA dan ERBA')
SELECT sumber, kode, deskripsi
FROM data_dictionary
WHERE kategori = '<kategori>'
  AND kode = '<value>';
```

**JOIN pattern (always filter `sumber` to prevent fan-out):**
```sql
LEFT JOIN data_dictionary dd
  ON dd.kategori = '<kategori>'
  AND dd.sumber IN ('<SYSTEM>', 'ERBA dan ERLA', 'ERLA dan ERBA')
  AND dd.kode = <column>::text
-- If the JOIN drops rows you expected, retry without the sumber filter to diagnose
```

## Kode tidak ditemukan (code exists in the table, no dictionary match)

Different case from "unknown column" (bottom of this file). Try, in order:

1. **Cross-`sumber`** — already step 2 of the workflow above (some codes are registered under a
   different system label than the table they appear in).
2. **Normalize the number format** — the two systems store the same code differently (leading
   zeros: table `'0999'` vs dictionary `'999'`). When string match fails, compare numerically:
   `dd.kode::int = <column>::int` (guard non-numeric with a `~ '^[0-9]+$'` check), then confirm
   with a sample. Verified on ERLA `status`: fixes resolution from 49.8% → 100%.
3. **Still no match** → legacy/artifact code. Show the **raw code with an honest note** (same
   pattern as the legacy Kemendagri region codes below). **Never invent a label.**

**Label resolution never changes the count.** Do not drop rows because their code failed to
resolve — resolution is presentation-only; the COUNT logic stands on its own.

## Column → kategori mapping

| Column | Kategori | Notes |
|---|---|---|
| `skala_industri_id`, `skala_industri` | `SKALA_INDUSTRI dan SKALA_INDUSTRI_ID` | NULL/empty → "Importir" |
| `jenis_permohonan` | `JENIS_PERMOHONAN` | |
| `kategori_dokumen` | `KATEGORI_DOKUMEN` | risk level → prefix "Risiko " (see below) |
| `status_komitmen` | `STATUS_KOMITMEN` | |
| `status` | `STATUS` | |
| `status_produk` | `STATUS_PRODUK` | |
| `status_usaha` | `STATUS_USAHA` | |
| `bentuk_sediaan` | `BENTUK_SEDIAAN` | |
| `jenis_btp` | `JENIS_BTP` | |
| `jenis_dokumen` | `JENIS_DOKUMEN` | |
| `jenis_produk_btp` | `JENIS_PRODUK_BTP` | |
| `kemasan_id` | `KEMASAN_ID` | |
| `sub_kemasan_id` | `SUB_KEMASAN_ID` | |
| `klasifikasi_id` | `KLASIFIKASI_ID` | |
| `kode_kbli` | `KODE_KBLI` | |
| `negara_pabrik`, `negara_produsen` | `NEGARA_PABRIK dan NEGARA_PRODUSEN` | |
| `peruntukan` | `PERUNTUKAN` | |
| `daerah_pabrik`, `daerah_trader`, `daerah_produsen` | `DAERAH_TRADER, DAERAH_PABRIK, DAERAH_PRODUSEN, PROVINSI_ID, KOTAKAB_ID` | Requires conversion (see below) |
| `kategori_pangan` | `AKRONIM` | Requires prefix (see below) |
| **`jenis_pangan`** | **`JENIS_PANGAN`** | Product segment codes (AMDK, Garam, roti, kopi, etc.). Source-aware — ERBA and ERLA use different codes for the same concept (e.g. AMDK ERBA=1401, ERLA=651/652/655). |

## Risk level label — ERBA and ERLA are DIFFERENT (resolve each from the dictionary)

ERBA risk (`kategori_dokumen`, kategori `KATEGORI_DOKUMEN`, sumber `ERBA`) and ERLA risk
(`jenis_dokumen`, kategori `JENIS_DOKUMEN`, sumber `ERLA dan ERBA`) **do NOT share labels** —
do not assume one mirrors the other. Resolve each per system via the protocol; the dictionary
returns ERBA as `Tinggi` / `Menengah Tinggi` / `Menengah Rendah` / `Tinggi Notifikasi` and ERLA
as `Pangan Low Risk` / `Pangan High Risk` / `Pangan Medium Risk` (3 levels — ERLA has no separate
Menengah Tinggi). See `code_translation_protocol.md` §0.

**Presentation:** for the ERBA risk levels, present the user-facing label **prefixed with
"Risiko "** (`Tinggi` → "Risiko Tinggi", etc.) — never the bare adjective. Apply this at the
resolution step, the moment the code becomes a label, so the prefix appears everywhere the level
shows (tables, prose, breakdowns).

## Regional code conversion (daerah_pabrik etc.)

Product tables store regional codes as 4-digit strings (e.g. `'7271'`) but
`data_dictionary.kode` uses decimal format (e.g. `'72.71'`).

**Correct conversion:**
```sql
ROUND(daerah_pabrik::numeric / 100, 2)::text
```

Do NOT use `(daerah_pabrik::numeric / 100)::text` — this produces trailing zeros
that will not match (e.g. `'12.0900000000000000'` vs `'12.09'`).

**Full JOIN pattern for daerah:**
```sql
LEFT JOIN data_dictionary dd
  ON dd.kategori = 'DAERAH_TRADER, DAERAH_PABRIK, DAERAH_PRODUSEN, PROVINSI_ID, KOTAKAB_ID'
  AND dd.kode = ROUND(daerah_pabrik::numeric / 100, 2)::text
```

**Unresolved region codes (no `data_dictionary` match):** a `daerah` code that does not match even after the conversion above is an **old Kemendagri code carried over from the legacy ERLA system** (RPO update is pending, per Pusdatin). Codes already aligned to the current Kemendagri scheme resolve normally. When a code does not resolve, present it with this explanation — e.g. *"region code 3701 is a legacy Kemendagri code from the ERLA system, not yet updated"* — instead of a bare "label not found", and still show the raw code.

## Food category codes (kategori_pangan)

`kategori_pangan` stores long codes; the first 2 characters map to a broad category.

```sql
LEFT JOIN data_dictionary dd
  ON dd.kategori = 'AKRONIM'
  AND dd.kode = 'KP ' || LEFT(kategori_pangan, 2)
```

Examples: KP 14=Minuman, KP 07=Produk Bakeri, KP 06=Sereal.

## Fallback: unknown coded column

If a result column contains codes not listed above:
1. Run `SELECT DISTINCT kategori FROM data_dictionary ORDER BY kategori`
   to see all available categories
2. Match the column name semantically to the closest kategori
3. Run `SELECT kode, deskripsi FROM data_dictionary WHERE kategori = '...'`
4. Replace codes with labels before presenting the answer

## Discover all categories

```sql
SELECT DISTINCT kategori FROM data_dictionary ORDER BY kategori
```
