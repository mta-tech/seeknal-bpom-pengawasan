# Query Recipes — Adaptive SQL Frameworks (BPOM RPO)

> **Status:** NEW file (enhancement). These are **NOT SQL pairs to be applied rigidly.**
> A recipe = **a reference framework you adapt** to the question. Replace
> `{...}` placeholders, add/remove filters per intent. Never force a recipe when its scope
> doesn't fit — adapt it, or write from scratch using `intent_mapping.md` + `data_quality_rules.md`.

**Conventions:**
- Year uses **date ranges**, not EXTRACT: `{Y}` = year, range `>= '{Y}-01-01' AND < '{Y+1}-01-01'`.
- **No year in the prompt → drop the `{Y}` single-year filter** and use the all-time wide range `>= '2000-01-01' AND < '2030-01-01'` for ANY recipe (not just R3/R11). Prefer **ONE query with `GROUP BY date_trunc('year', ...)`** (single round-trip — lighter on the connection than many per-year queries); present the per-year rows, then the total at the end. A stated year/range always overrides. **The end total is a separate global `COUNT(DISTINCT nomor)`/`produk_id` over the whole set — NOT the sum of the per-year rows** (a `nomor` recurring across years double-counts; use a standalone aggregate, a subquery, or `GROUP BY ROLLUP`).
- **Sub-year / month granularity** — a third time form alongside single-year and all-time:
  - "per bulan" / "tren bulanan" → `GROUP BY date_trunc('month', <col>)`.
  - a named month (e.g. "bulan Mei") → add `EXTRACT(MONTH FROM <col>::timestamp) = {M}`. If a year is
    also given, keep the year range; **if no year is given, group by year** (`date_trunc('year', <col>)`)
    so the month is shown for each year that has data, then the total — do NOT collapse to one year.
  - "N tahun/bulan terakhir", "terbaru" → resolve against the **latest period present in the data**
    (e.g. `MAX`), never a hardcoded year.
- **Never substitute `forecast_permohonan` for an actual count.** That table is for forecast intent only (see `forecast_guide.md`); for real permohonan/NIE counts always query the transactional product tables. If the real query fails, report the failure honestly — do NOT fall back to an aggregate/forecast table.
- Always fully-qualified: `warehouse.public.<table>`.
- Always exclude test accounts + years 1900/1970.
- Resolve codes to labels via `warehouse.public.data_dictionary` (see `code_resolution.md`).

---

## R1 — NIE pangan olahan, ERBA, single year
```sql
SELECT COUNT(DISTINCT nomor) AS jumlah_nie
FROM warehouse.public.t_produk_3_erba
WHERE tanggal >= '{Y}-01-01' AND tanggal < '{Y+1}-01-01'
  AND status IN ('0999','0906','9999')
  AND jenis_permohonan IN ('301','305')
  AND trader_id NOT IN (5,17,50,85)
```

## R2 — NIE pangan olahan, COMBINED (ERBA + ERLA), single year
> "pangan olahan" = product tables only (without BTP). BTP is counted separately if requested.
```sql
SELECT COUNT(DISTINCT nomor) AS jumlah_nie FROM (
  SELECT nomor FROM warehouse.public.t_produk_3_erba
  WHERE tanggal >= '{Y}-01-01' AND tanggal < '{Y+1}-01-01'
    AND status IN ('0999','0906','9999')
    AND jenis_permohonan IN ('301','305')
    AND trader_id NOT IN (5,17,50,85)
  UNION ALL
  SELECT nomor FROM warehouse.public.t_produk_3_rilis_erla
  WHERE tanggal >= '{Y}-01-01' AND tanggal < '{Y+1}-01-01'
    AND status IN ('0099','0999','0906','9999')
    AND jenis_permohonan IN ('301','304','305')
    AND trader_id != 3384
) g
```

## R3 — NIE per risk category, ERBA (default ERBA-only)
> Do NOT hardcode the risk labels. Resolve them via the dictionary JOIN (sumber-aware) so labels
> come from the source. For a specific level ("risiko menengah tinggi"), first resolve the code
> inbound (`code_translation_protocol.md` §2.1) and add `AND p.kategori_dokumen = '{resolved}'`.
```sql
SELECT 'Risiko ' || COALESCE(dd.deskripsi, p.kategori_dokumen) AS kategori_risiko,
       COUNT(DISTINCT p.nomor) AS jumlah_nie
FROM warehouse.public.t_produk_3_erba p
LEFT JOIN warehouse.public.data_dictionary dd
  ON dd.kategori = 'KATEGORI_DOKUMEN' AND dd.sumber = 'ERBA'
  AND dd.kode = p.kategori_dokumen
WHERE p.tanggal >= '{Y}-01-01' AND p.tanggal < '{Y+1}-01-01'
  AND p.status IN ('0999','0906','9999')
  AND p.jenis_permohonan IN ('301','305')   -- "NIE baru"; omit for "all active NIE" (see data_quality_rules §jenis_permohonan)
  AND p.trader_id NOT IN ('5','17','50','85')
  AND p.kategori_dokumen IN ('301','302','303','304')
GROUP BY 1 ORDER BY 2 DESC
```

## R4 — NIE per skala industri, ERBA (+ label, + Importir)
```sql
SELECT COALESCE(NULLIF(TRIM(CAST(m.skala_industri_id AS VARCHAR)), ''), 'Importir') AS skala_kode,
       COUNT(DISTINCT p.nomor) AS jumlah_nie
FROM warehouse.public.t_produk_3_erba p
LEFT JOIN warehouse.public.m_trader_rba m ON p.trader_id = m.trader_id
WHERE p.tanggal >= '{Y}-01-01' AND p.tanggal < '{Y+1}-01-01'
  AND p.status IN ('0999','0906','9999')
  AND p.jenis_permohonan IN ('301','305')
  AND p.trader_id NOT IN (5,17,50,85)
GROUP BY 1 ORDER BY 2 DESC
-- then resolve codes 1/2/3/4 → Mikro/Kecil/Menengah/Besar via data_dictionary (category 'SKALA_INDUSTRI and SKALA_INDUSTRI_ID')
```

## R5 — UMKM (Mikro+Kecil+Menengah), ERBA
> UMKM = skala_industri_id IN ('1','2','3'). Do not include Importir/Besar.
```sql
SELECT COUNT(DISTINCT p.nomor) AS jumlah_umkm
FROM warehouse.public.t_produk_3_erba p
LEFT JOIN warehouse.public.m_trader_rba m ON p.trader_id = m.trader_id
WHERE p.tanggal >= '{Y}-01-01' AND p.tanggal < '{Y+1}-01-01'
  AND p.status IN ('0999','0906','9999')
  AND p.jenis_permohonan IN ('301','305')
  AND p.trader_id NOT IN (5,17,50,85)
  AND TRIM(CAST(m.skala_industri_id AS VARCHAR)) IN ('1','2','3')
```

## R6 — MR commitment, ERBA (TWO cases — pick by intent, see data_quality_rules §Commitment)
> Resolve the `status_komitmen` code(s) from the dictionary (kategori `STATUS_KOMITMEN`, sumber
> `ERBA`) via `code_translation_protocol.md`; count **final-state** codes only (a transient
> validation state is not a settled outcome). Always normalize with `ROUND(...)::int` — the column
> mixes `'5'` and `'5.0'`, so a plain `= '5'` silently misses the `'.0'` rows.

**Case A — NIE that ALSO has commitment status X** (subject = issued NIE → keep ALL NIE filters):
```sql
SELECT COUNT(DISTINCT nomor) AS jumlah
FROM warehouse.public.t_produk_3_erba
WHERE kategori_dokumen = '303'                              -- MR
  AND tanggal >= '{Y}-01-01' AND tanggal < '{Y+1}-01-01'
  AND status IN ('0999','0906','9999')                      -- valid NIE — REQUIRED in Case A
  AND jenis_permohonan IN ('301','305')                     -- REQUIRED in Case A
  AND trader_id NOT IN ('5','17','50','85')
  AND ROUND(status_komitmen::numeric)::int::text = '{resolved final code}'
```

**Case B — applications whose commitment was [outcome]** (subject = lifecycle → DROP NIE status):
```sql
SELECT COUNT(DISTINCT nomor) AS jumlah     -- or COUNT(DISTINCT produk_id) for application count
FROM warehouse.public.t_produk_3_erba
WHERE kategori_dokumen = '303'                              -- MR
  AND ROUND(status_komitmen::numeric)::int::text = '{resolved final code}'
  AND trader_id NOT IN ('5','17','50','85')
  -- NO status IN (...) and NO jenis_permohonan filter — cancellations mostly precede NIE issuance
  -- add a date range only if the user states one
```

## R7 — Permohonan, ERBA, single year (produk_id + tanggal_bayar, NO status filter)
```sql
SELECT COUNT(DISTINCT produk_id) AS jumlah_permohonan
FROM warehouse.public.t_produk_3_erba
WHERE tanggal_bayar >= '{Y}-01-01' AND tanggal_bayar < '{Y+1}-01-01'
  AND jenis_permohonan IN ('301','302','303','304','305')
  AND trader_id NOT IN (5,17,50,85)
```

## R8 — Permohonan pangan olahan COMBINED (ERBA + ERLA, product tables only)
> "pangan olahan" = **product tables only**. Add BTP (4-table UNION) **only if** the user explicitly asks for total / BTP / all. e.g. 2023 → 61.213 (ERBA 42.329 + ERLA 18.884).
```sql
SELECT COUNT(DISTINCT produk_id) AS jumlah_permohonan FROM (
  SELECT produk_id FROM warehouse.public.t_produk_3_erba       WHERE tanggal_bayar >= '{Y}-01-01' AND tanggal_bayar < '{Y+1}-01-01' AND trader_id NOT IN (5,17,50,85)
  UNION
  SELECT produk_id FROM warehouse.public.t_produk_3_rilis_erla WHERE tanggal_bayar >= '{Y}-01-01' AND tanggal_bayar < '{Y+1}-01-01' AND trader_id != 3384
) g
-- Total incl BTP (ONLY if explicitly requested): add `UNION SELECT produk_id FROM warehouse.public.t_btp_3_erba ...`
-- and `UNION SELECT produk_id FROM warehouse.public.t_btp_3_erla ...` with the same date/test-account filters.
```

## R9 — NIE BTP, ERBA / ERLA
```sql
-- ERBA:
SELECT COUNT(DISTINCT nomor) FROM warehouse.public.t_btp_3_erba
WHERE tanggal >= '{Y}-01-01' AND tanggal < '{Y+1}-01-01'
  AND status IN ('0999','0906','9999') AND jenis_permohonan IN ('301','305')
  AND trader_id NOT IN (5,17,50,85)
-- ERLA: replace table → t_btp_3_erla, status +'0099', jenis_permohonan +'304', trader_id != 3384
```

## R10 — Product segment (AMDK / Garam) — classification CODES, prefer PARENT category
> Segment codes are NOT in `data_dictionary`. Prefer the **parent category** for full coverage; a
> sub-code under-counts. For segments not listed, **discover** via `nama_kategori` (see §Product
> Segment discovery in `business_glossary.md` / `intent_mapping.md`) — never hardcode a sub-code.
```sql
-- AMDK ERBA:  ... AND jenis_pangan = '1401'
-- AMDK ERLA:  ... AND jenis_pangan IN ('651','652','655')
-- Garam ERBA: ... AND kategori_pangan = '120101000001'   -- production SQL uses this specific sub-code
-- Garam ERLA: ... AND kategori_pangan = '12010103'
-- Insert into the NIE framework (R1/R2). If user asks "in ERBA {year}" → ERBA only for that year, don't mix ERLA/total.
```

> **Risk grouping (production)**: "Risiko Tinggi" = `kategori_dokumen IN ('301','304')` combined.
> Never split 301 and 304 when user asks "tinggi" — production treats them as one bucket.
> MT = `'302'`, MR = `'303'` separately.

## R11 — NIE per risk, ALL YEARS (use when NO year is stated)
> Alternative to R3 when the question omits a year. No single-year filter — wide range only.
```sql
SELECT 'Risiko ' || COALESCE(dd.deskripsi, p.kategori_dokumen) AS kategori_risiko,
       COUNT(DISTINCT p.nomor) AS jumlah_nie
FROM warehouse.public.t_produk_3_erba p
LEFT JOIN warehouse.public.data_dictionary dd
  ON dd.kategori = 'KATEGORI_DOKUMEN' AND dd.sumber = 'ERBA'
  AND dd.kode = p.kategori_dokumen
WHERE p.tanggal >= '2000-01-01' AND p.tanggal < '2030-01-01'  -- all-time range (no EXTRACT; drops 1900/1970)
  AND p.status IN ('0999','0906','9999')
  AND p.jenis_permohonan IN ('301','305')   -- "NIE baru"; omit for "all active NIE" (see data_quality_rules §jenis_permohonan)
  AND p.trader_id NOT IN ('5','17','50','85')
  AND p.kategori_dokumen IN ('301','302','303','304')
GROUP BY 1 ORDER BY 2 DESC
-- Per-year trend: add date_trunc('year', p.tanggal) to SELECT and GROUP BY.
-- NOTE: no year filter — this is the correct shape when the user states no year.
```

## R12 — Application age / SLA (how long an in-process application has been waiting)

> Use when the user asks: "sudah berapa lama", "lama tertahan", "SLA", "belum selesai", "durasi",
> "menunggak", "> N hari". Entity = PERMOHONAN; age = days since payment date.
> Only meaningful for in-process applications — exclude rows with a final outcome.
> "Final vs in-process" must be resolved from the status column via the dictionary (do not hardcode
> stage codes). As a practical starting point, in-process statuses are those NOT matching any of the
> valid NIE statuses (`'0999','0906','9999'` ERBA; `'0099','0999','0906','9999'` ERLA) and not in
> explicit rejection statuses — verify from data_dictionary kategori `STATUS` before filtering.

```sql
-- ERBA: applications still in-process, ranked by age (oldest first)
SELECT produk_id,
       nomor,
       tanggal_bayar::date                                    AS tgl_bayar,
       CURRENT_DATE - tanggal_bayar::date                     AS umur_hari,
       COALESCE(dd.deskripsi, p.status)                       AS status_label
FROM warehouse.public.t_produk_3_erba p
LEFT JOIN warehouse.public.data_dictionary dd
  ON dd.kategori = 'STATUS' AND dd.sumber = 'ERBA'
  AND dd.kode = p.status
WHERE p.tanggal_bayar IS NOT NULL AND p.tanggal_bayar != ''
  AND p.status NOT IN ('0999','0906','9999')      -- exclude completed NIE
  AND p.trader_id NOT IN (5,17,50,85)
  -- optional: AND CURRENT_DATE - p.tanggal_bayar::date > {N}  for "> N hari" questions
ORDER BY umur_hari DESC
LIMIT 20;

-- Aggregation: how many applications per age bucket?
SELECT
  CASE
    WHEN CURRENT_DATE - tanggal_bayar::date <= 30  THEN '0–30 hari'
    WHEN CURRENT_DATE - tanggal_bayar::date <= 90  THEN '31–90 hari'
    WHEN CURRENT_DATE - tanggal_bayar::date <= 180 THEN '91–180 hari'
    ELSE '> 180 hari'
  END AS umur_bucket,
  COUNT(DISTINCT produk_id) AS jumlah_permohonan
FROM warehouse.public.t_produk_3_erba
WHERE tanggal_bayar IS NOT NULL AND tanggal_bayar != ''
  AND status NOT IN ('0999','0906','9999')
  AND trader_id NOT IN (5,17,50,85)
GROUP BY 1 ORDER BY MIN(CURRENT_DATE - tanggal_bayar::date);
```

> For ERLA: replace table `t_produk_3_erba` → `t_produk_3_rilis_erla`, remove `::date` cast on
> `tanggal_bayar` (ERLA stores as TIMESTAMP), change `trader_id` exclusion to `!= 3384`.

## R13 — Root cause decomposition (inflection point analysis)

> Use when the user asks "kenapa", "mengapa", "penyebab", "apa yang menyebabkan naik/turun".
> Step 1: confirm the inflection from the trend (use R11 or R7 per-year variant first).
> Step 2: decompose at the inflection year by the most informative dimensions (jenis_permohonan,
> kategori_dokumen, top traders, segment). Pick dimensions most likely to explain the shift.
> Never fabricate a policy reason — only name what the data shows.

```sql
-- Step 1: confirm the trend (adapt from R11 / R7 for the relevant entity)
-- [run the trend query first; identify year Y_inflection where the change is sharpest]

-- Step 2a: decompose by jenis_permohonan at the inflection year (example: permohonan ERBA)
SELECT jenis_permohonan,
       COALESCE(dd.deskripsi, p.jenis_permohonan)  AS jenis_label,
       COUNT(DISTINCT produk_id)                    AS jumlah
FROM warehouse.public.t_produk_3_erba p
LEFT JOIN warehouse.public.data_dictionary dd
  ON dd.kategori = 'JENIS_PERMOHONAN'
  AND dd.sumber IN ('ERBA','ERBA dan ERLA','ERLA dan ERBA')
  AND dd.kode = p.jenis_permohonan
WHERE tanggal_bayar >= '{Y_inflection}-01-01' AND tanggal_bayar < '{Y_inflection+1}-01-01'
  AND trader_id NOT IN (5,17,50,85)
GROUP BY 1,2 ORDER BY 3 DESC;

-- Step 2b: decompose by top 5 traders (who drove the surge/drop?)
SELECT trader_id, COUNT(DISTINCT produk_id) AS jumlah
FROM warehouse.public.t_produk_3_erba
WHERE tanggal_bayar >= '{Y_inflection}-01-01' AND tanggal_bayar < '{Y_inflection+1}-01-01'
  AND trader_id NOT IN (5,17,50,85)
GROUP BY trader_id ORDER BY jumlah DESC LIMIT 5;
-- then JOIN to m_trader_rba for company name

-- Step 2c: compare the inflection year against the prior year for the dominant dimension
-- run the same query with Y_inflection-1 and compare counts side by side
```

> Synthesize using Pattern F (SKILL.md §GENERATE): name the top contributor and state it as a
> data-supported hypothesis. Never present it as a confirmed cause.

---

## Adaptation notes
- If the question requires a different scope (e.g. + BTP, or different year) → modify the recipe, don't force it.
- After execution, **always go through the REFLECT/AUDIT phase** (see skill `bpom-analyst` / `evidence-auditor`) before answering.
- If results look suspicious (e.g. count much larger than domain expectation) → check whether status/jenis_permohonan/year filters are missing (common cause of count inflation). For an **all-time** query (no year stated), a count several times a single year is expected — that is not inflation.
