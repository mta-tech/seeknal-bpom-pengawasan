# Intent Mapping — User Question to Data Mapping (BPOM RPO)

> **Status:** NEW file (enhancement). Distilled from `docs/01_entity_registry.md`,
> `docs/02_dimension_registry.md`, `docs/03_operation_registry.md`.
> **Two important corrections made during distillation** (to stay consistent with `context/`):
> 1. Year filtering uses **date ranges**, NOT `EXTRACT(YEAR ...)` — see
>    `data_quality_rules.md` (EXTRACT times out on SSH tunnel).
> 2. ERBA/ERLA is a **system generation distinction, NOT domestic/imported** — see
>    `business_glossary.md`. Do not use the terms "dalam negeri/impor".

This file's purpose = **schema-linking** layer. Used in the **CAPTURE** step:
map user words → **ENTITY + OPERATION + DIMENSION + CONDITION** before writing SQL.

---

## Question Decomposition — Read the Structure Before the Words

Before normalizing typos or mapping entities, identify the four structural components
of the question. This determines **what the query must produce** and at what granularity.

| Component | Identifies | Determines |
|---|---|---|
| **Subject** | The entity the user is asking about | Granularity of GROUP BY and output rows |
| **Predicate** | What the user wants to know about the subject | Metric column and aggregation function |
| **Modifier** | Conditions that restrict the scope | WHERE clause and filters |
| **Scope dimensions** | Additional axes the result must cover | Extra GROUP BY columns |

### Decomposition Examples

| Question | Subject | Predicate | Modifier | Scope dims | Query shape |
|---|---|---|---|---|---|
| "Berapa NIE risiko tinggi?" | NIE | count | risiko tinggi | none | scalar |
| "Tren NIE per daerah dan tahun" | NIE trend | change over time | none | daerah + tahun (dependent) | GROUP BY tahun, daerah |
| "Produk apa yang paling banyak dibatalkan?" | produk → kategori | dibatalkan count | paling banyak (TOP) | none | GROUP BY nama_kategori ORDER BY COUNT DESC |
| "Daerah mana UMKM terbanyak?" | daerah | UMKM NIE count | terbanyak | none | GROUP BY daerah_pabrik ORDER BY COUNT DESC |
| "Distribusi NIE per risiko, skala, tren 10 tahun" | NIE distribution | count by 3 aspects | 10 tahun | risiko + skala + tren (independent) | 3 separate queries + synthesis |

### Subject Determines Granularity — The Key Principle

The subject noun controls what one row of output represents. This generalizes to
any question — including ones not listed in this file:

| Subject form | What one output row represents | GROUP BY column |
|---|---|---|
| "berapa" / scalar count | a single number | none |
| "tren" / per tahun | one year | `date_trunc('year', tanggal)` |
| "daerah mana" / "wilayah apa" | one region | `daerah_pabrik` (resolved to label) |
| "produk apa" / "kategori apa" | one product category | `nama_kategori` |
| "perusahaan mana" | one company | `trader_id` or `nama_trader` |
| "skala apa" / "skala usaha" | one industry scale | `skala_industri_id` / `skala_industri` |
| "risiko apa" | one risk level | `kategori_dokumen` (ERBA) |

**Critical disambiguation — "produk apa yang paling X" is a RANKING, not a LIST:**
- LIST / SEARCH = "cari produk", "tampilkan produk" → individual product rows, use `nama`
- RANKING = "produk apa yang paling banyak X" → category aggregation, use `GROUP BY nama_kategori`
- These are different operations. "Produk apa" in a ranking context = which CATEGORY ranks highest.

### Dependent vs Independent Dimensions

When a question mentions multiple dimensions, determine the relationship:

**DEPENDENT** — the user wants dimensions crossed together in one result:
- Signals: "tren PER X", "X dan Y" within one phrase, "berdasarkan X per tahun"
- Strategy: one query with `GROUP BY dim1, dim2`
- Example: "tren per daerah dan tahun" → one query, `GROUP BY date_trunc('year', tanggal), daerah_pabrik`

**INDEPENDENT** — the user wants each dimension as a separate analysis:
- Signals: "berdasarkan risiko, skala, dan tren" (listed as separate aspects)
- Strategy: N queries, one per dimension, synthesize in GENERATE
- Example: "distribusi per risiko, per skala, dan tren 10 tahun" → 3 queries

---

## Step 0 — Normalize informal language & typos (MANDATORY first)

> After Step 0, proceed to **Step 0.5** before entity resolution.

**Step 0a — Structural normalization (before anything else):**
Normalize the question's format before parsing its meaning. Surface structure must not
alter interpretation.
- Content inside `(...)` or `[...]` carries the same semantic weight as content outside.
  Strip the brackets; keep the content.
  Example: `"tren per tahun (10 tahun terakhir)"` = `"tren per tahun 10 tahun terakhir"`
- Commas, "dan", "serta", "maupun" are equivalent dimension separators.
  Example: `"risiko, skala, dan tren"` = three separate dimensions, same as `"risiko dan skala dan tren"`
- Word order within a dimension list does not change the set of dimensions.

Only after structural normalization: map typos/synonyms to their canonical form. **Do not**
inject raw user words into SQL (e.g. `ILIKE '%jumlh%'`). **Do not** ask for clarification
on obvious typos.

| What user typed | Canonical meaning |
|---|---|
| jumlh, jmlh, brp, berapa, total, banyak | OPERATION = COUNT |
| thn, tahun, periode | DIMENSION = time |
| izin edr, izin edar, NIE, nie, izin terbit, nomor izin | ENTITY = NIE |
| permohnan, pemohonan, pengajuan, registrasi, daftar | ENTITY = PERMOHONAN |
| skala usaha, skala industri, umkm, mikro, kecil, menengah, besar | DIMENSION = scale |
| risiko, resiko, MR, MT, tinggi, menengah | DIMENSION = risk |
| garam beryodium, amdk, btp | DIMENSION = product segment |
| dari situ, yang tadi, itu, tahun yang sama, selisihnya | IMPLICIT REFERENCE (see below) |

---

---

## Step 0.5 — Product Segment Resolution (before entity resolution)

If the user mentions a specific product type (AMDK, susu, garam, BTP, etc.):

1. Check `context/business_glossary.md` §Product Segment Codes first
2. If listed: use the `jenis_pangan` or `kategori_pangan` filter for each system separately
   (ERBA and ERLA codes differ — they are NOT interchangeable)
3. If NOT listed: run discovery via `nama_kategori`:
   ```sql
   SELECT DISTINCT jenis_pangan, nama_kategori, COUNT(*) AS cnt
   FROM warehouse.public.[table]
   WHERE nama_kategori ILIKE '%<keyword>%'
   GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10
   ```
4. Confirm result: `SELECT DISTINCT nama FROM [table] WHERE jenis_pangan = '<code>' LIMIT 5`
5. NEVER use `nama ILIKE '%keyword%'` as the primary segment filter —
   `nama` is inconsistent; `nama_kategori` is standardized

---

## ENTITY registry (identify ONE primary entity)

### NIE (Izin Edar)
- Trigger: izin edar, NIE, terbit, izin terbit, nomor izin
- Metric: `COUNT(DISTINCT nomor)` · Time column: `tanggal` (ISSUE date)
- Tables: `t_produk_3_erba` + `t_produk_3_rilis_erla` (UNION; "pangan olahan" = product tables, NOT BTP)
- Mandatory ERBA filter: status `IN ('0999','0906','9999')`, jenis_permohonan `IN ('301','305')`
- Mandatory ERLA filter: status `IN ('0099','0999','0906','9999')`, jenis_permohonan `IN ('301','304','305')`
- Risk (`kategori_dokumen`) & commitment (`status_komitmen`) **exist in ERBA only**.

### PERMOHONAN (Application)
- Trigger: permohonan, pengajuan, registrasi, daftar, aplikasi
- Metric: `COUNT(DISTINCT produk_id)` · Time column: `tanggal_bayar` (PAYMENT date)
- Tables: **pangan olahan = product tables only** (`t_produk_3_erba` + `t_produk_3_rilis_erla`); add BTP (`t_btp_3_erba` + `t_btp_3_erla` → 4-table UNION) **only if** the user explicitly asks for total / BTP / all. Same "pangan olahan = product" rule as NIE.
- **NO status filter** (permohonan = all applications, regardless of outcome).
- jenis_permohonan: all `('301','302','303','304','305')`.

### BTP (Bahan Tambahan Pangan)
- Trigger: BTP, bahan tambahan, aditif, pengawet, pemanis, perisa
- Metric & filters = same as NIE, but using `t_btp_3_erba` + `t_btp_3_erla` tables.
- BTP **does not have** `kategori_dokumen` (risk).

### PERUSAHAAN (Trader / Business Entity)
- Trigger: perusahaan, trader, pelaku usaha, pemilik
- Metric: `COUNT(DISTINCT t.trader_id)` (from product table, **not** master) · LEFT JOIN to `m_trader_*`.

### PRODUK / MAKLOON
- PRODUK → LIST/SEARCH operation (row detail), not aggregation.
- MAKLOON → ERBA subset, filter `status_produk = '304'`, use `produsen_*` columns.

**Universal filter (all entities):** exclude test accounts (ERBA `trader_id NOT IN (5,17,50,85)`,
ERLA `trader_id != 3384`) and exclude years 1900/1970.

---

## DIMENSION registry (how to slice data)

### Time — use DATE RANGES (not EXTRACT)
- Single year Y: `tanggal >= 'Y-01-01' AND tanggal < '(Y+1)-01-01'` (NIE) / `tanggal_bayar` (permohonan).
- Multi-year trend: `GROUP BY date_trunc('year', <column>)` or range per year.
- Range Y1..Y2: `tanggal >= 'Y1-01-01' AND tanggal < '(Y2+1)-01-01'`; if "tren/per tahun" → also `GROUP BY date_trunc('year', <column>)`.
- Relative ("N tahun terakhir", "terbaru"): resolve against MAX(year) in the data, NOT 2023.
- **No year mentioned → do NOT assume a single year.** Default = ALL years: use a wide bounded range `tanggal >= '2000-01-01' AND tanggal < '2030-01-01'` (pushed to PostgreSQL, also drops 1900/1970 artifacts — no EXTRACT), report total + per-year breakdown, and state the scope. Never silently fall back to 2023.

**Deterministic time dimension rules (no exceptions):**

| Keyword present | SQL shape — always |
|---|---|
| tren, per tahun, setiap tahun, perkembangan | `GROUP BY date_trunc('year', col)` |
| tren per [dimension] (e.g. tren per daerah) | `GROUP BY year, dimension` — **ONE query**, not two separate queries |
| distribusi [A] dan [B] | `GROUP BY col_A, col_B` — ONE query |
| **per bulan / tren bulanan** | `GROUP BY date_trunc('month', col)` |
| **a named month (e.g. "bulan Mei")** | filter `EXTRACT(MONTH FROM col)=M` (or a month range) |
| no year stated | range 2000–2030 + `GROUP BY date_trunc('year', col)` |

> Adding "setiap tahun", "tren", or "per bulan" to a question does **NOT** change the entity
> (NIE vs permohonan). Entity is resolved in Step 0 and stays fixed. Time keywords affect only
> the SQL shape, not the entity or metric.

**Granularity = the smallest time unit the user names.** A month beats a year when both appear.

**Month named WITHOUT a year → break that month down PER YEAR** (one row for the month in each year
that has data), then the grand total. Do NOT ask for a year, do NOT assume a single year.
(e.g. "permohonan bulan Mei" → that month's count for each year in the data + total.)

**Count breakdown — never lead with a bare total.** A COUNT question ("berapa NIE risiko tinggi",
"berapa permohonan UMKM", …) is answered as the **time breakdown first, grand total on the last
line** — not a lone scalar:
- no year stated → one row per year that has data + grand total;
- month named, no year → one row per year for that month + grand total;
- a single explicit year → that year's figure (no month split unless the user names a month).
- **The grand total is a GLOBAL `COUNT(DISTINCT nomor)` (or `produk_id`) over the whole set — NOT
  the arithmetic sum of the per-year rows.** A `nomor` can appear in several years (renewal/variation),
  so summing per-year distinct counts double-counts it (e.g. MR all-time: row-sum 141.682 vs true
  distinct 119.314). Compute the total with a separate global aggregate, a subquery, or
  `GROUP BY ROLLUP` — never by adding the rows.

**Derive the year range from the DATA — never hardcode a start/end year.** First determine the
**latest available year** from the data/schema, then derive the window:
- "N tahun terakhir" = the last N years up to the latest available year;
- "1 tahun terakhir" / "terbaru" = the latest available year;
- all-time = every year present, earliest-with-data through latest-with-data.
Teach the process (find latest year → derive window); never assume "2023" or "the current year".

### Risk — resolve per system from the dictionary ⚠️ (never reuse a code across systems)
ERBA risk = `kategori_dokumen` (kategori `KATEGORI_DOKUMEN`); ERLA risk = `jenis_dokumen` (kategori
`JENIS_DOKUMEN`). **The same numeric code means a different level in each system.** Do NOT read codes
from a table here — resolve each system's codes at runtime via `code_translation_protocol.md`
(inbound word→code, sumber-aware). Reasoning facts to apply:
- **ERBA has 4 levels** (Tinggi / Menengah Tinggi / Menengah Rendah / Tinggi Notifikasi);
  **ERLA has 3** (Low / High / **Medium** Risk).
- The cross-map is **lossy**: ERLA's Medium-Risk spans both MT and MR — **ERLA cannot isolate
  Menengah Tinggi**. For an MT count, ERBA is authoritative; if combined, state the ERLA limitation.
- For any combined risk count, **resolve and apply ERBA codes and ERLA codes separately** (separate
  WHERE per UNION side); if equating an ERLA level to an ERBA level, **test by magnitude first**
  (`code_translation_protocol.md` §3).
- **Default risk scope = ERBA-only**; mix ERLA only when the user explicitly asks for combined.

### Skala Industri / UMKM
- Column: ERBA `m_trader_rba.skala_industri_id` · ERLA `m_trader_rla.skala_industri` (DIFFERENT NAME!)
- Codes: `1`=Mikro, `2`=Kecil, `3`=Menengah, `4`=Besar · **UMKM = 1,2,3** (Mikro+Kecil+Menengah — all three; dropping Menengah is a common error)
- NULL / '' / ' ' = **Importir**. Use **LEFT JOIN** + `COALESCE(NULLIF(TRIM(...),''),'Importir')`.
- ⚠️ Do not assume "Besar" is the largest group — in real data Importir can be #1; determine from query results.
- **Scale lives ONLY in the trader master**, never in product/BTP tables. It is therefore available
  for **every** entity — NIE, permohonan, **and BTP** — via the `m_trader` join on `trader_id`.
  "tren BTP per skala" is fully answerable: join `t_btp_*` → `m_trader_*`, then `GROUP BY year, skala`.

### Daerah / Wilayah (region) — choose the column by SEMANTICS + COVERAGE
Region appears in several columns that mean different things and have very different completeness.
Pick deliberately; do not default to the first name that matches.

| User phrase | Column | Meaning | Coverage |
|---|---|---|---|
| "daerah" / "kab/kota" / "provinsi" (unqualified) | JOIN `m_trader_rba.kotakab_id` / `provinsi_id` | company / business location | **high (≈100%)** — default |
| "daerah/lokasi **pabrik**", "tempat produksi" | `daerah_pabrik` (product table) | factory location | **low (many `'NULL'`/unresolved)** |
| "daerah **produsen**" | `daerah_produsen` (product table) | producer/makloon location | sparse |

- **Default for an unqualified "daerah" = company kab/kota** (`m_trader` join) — it is the most
  complete and what users usually mean.
- Use `daerah_pabrik` **only** when the user explicitly says pabrik/produksi — and then **state that
  it is factory location (≠ company location; they differ for a sizeable share of records) and report
  the coverage gap** (a large fraction will not resolve).
- Region codes need conversion + may be legacy Kemendagri codes — see `code_resolution.md`. Keep the
  raw code when unresolved; never silently switch to a different dimension that happens to have data.

### Kategori pangan as a BREAKDOWN / RANKING dimension
For "kategori terbanyak", "Top N kategori", "per kategori" → group by the **resolvable code**, not the
free-text name. `nama_kategori` is **mostly empty** (~3 of 5 rows) → grouping by it makes "Tanpa
Kategori" dominate and is wrong. Use `kategori_pangan` resolved to a broad category via AKRONIM
(`'KP ' || LEFT(kategori_pangan,2)`, ~full coverage; see `code_resolution.md`). State the granularity
(broad category) when finer detail is not reliably available. (`nama_kategori` ILIKE remains fine for
*searching* a specific named segment in Step 0.5 — just not as a grouping key.)

### Durasi / SLA / Aging (process age)
- Trigger words: "sudah berapa lama", "lama tertahan", "belum selesai", "SLA", "durasi proses",
  "menunggak", "lebih dari N hari", "terlambat", "pending terlama".
- Entity = PERMOHONAN (not NIE — aging measures the application lifecycle, not the issued license).
- Age column = `CURRENT_DATE - tanggal_bayar::date` (ERBA: cast required; ERLA: native date).
- **Only meaningful for in-process applications** — exclude rows that already have a final outcome
  (approved/rejected). Filter by stage codes that indicate "still open" (resolve from dict or product
  status column — do not hardcode "in-process" codes; discover from the status dimension).
- See R12 in `query_recipes.md` for the canonical aging query template.
- Do NOT confuse age with `tanggal` (NIE issue date) — that is the NIE date, not the application start.

### Status Komitmen — `status_komitmen` (ERBA + **MR only** `kategori_dokumen='303'`)
Resolve the term→code from the dictionary (kategori `STATUS_KOMITMEN`, sumber `ERBA`) via
`code_translation_protocol.md` — do not read codes from a table here. Normalize with
`ROUND(status_komitmen::numeric)::int::text`. Count the **final-state** code for settled outcomes
(not transient validation states).
> **Two cases (RC-4) — do not conflate:** (1) "NIE that also has commitment status X" → keep all
> NIE filters + add commitment filter; (2) "applications whose commitment was cancelled" → drop the
> NIE status filter (cancellations mostly precede NIE issuance). See `data_quality_rules.md`.

### Specific product segments
| Segment | ERBA | ERLA |
|---|---|---|
| AMDK | `jenis_pangan = '1401'` | `jenis_pangan IN ('651','652','655')` |
| Garam Beryodium | `kategori_pangan = '120101000001'` | `kategori_pangan = '12010103'` |

### jenis_permohonan (`jenis_permohonan`)
`301`=Baru · `302`=Perubahan Mayor · `303`=Perubahan Minor · `304`=Daftar Ulang (ERLA) · `305`=Baru Notifikasi.

---

## OPERATION → SQL pattern
| Operation | Trigger words | Pattern |
|---|---|---|
| COUNT | jumlah, berapa, total | `COUNT(DISTINCT <metric>)` |
| TREND | tren, per tahun, perkembangan | `GROUP BY <time> ORDER BY <time>` |
| BREAKDOWN | per, berdasarkan, menurut | `GROUP BY <dimension>` |
| TOP | terbanyak, top, paling | `ORDER BY <metric> DESC LIMIT N` |
| COMPARE | dibanding, vs, lebih besar | `CASE WHEN` or two queries then reconcile |
| LIST | daftar, cari, tunjukkan | `SELECT detail ... LIMIT 10` |
| INVESTIGATE | kenapa, mengapa, penyebab, apa yang menyebabkan, alasan kenaikan/penurunan | trend query → inflection point → decomposition query → name top contributor → state as hypothesis. See Synthesis Pattern F in `SKILL.md` §GENERATE |
| AGE / SLA | sudah berapa lama, lama tertahan, belum selesai, durasi proses, SLA, menunggak, > N hari | compute `CURRENT_DATE - tanggal_bayar` per application; filter by in-process status. See R12 in `query_recipes.md` |
| FORECAST | prediksi, proyeksi, estimasi ke depan, berapa nanti, bulan depan, tahun depan, semester depan, Q1/Q2/Q3/Q4, tren ke depan, akan ada berapa, target realistis, bisa mencapai, kemungkinan, perkiraan; EN: forecast, predict, projection, next month, next quarter, outlook | → Route to `bpom-forecaster` skill. Default TIME_SCOPE = 3 months; SYSTEM = ERBA only. ERLA never forecast. If question combines TREND (past) + FORECAST (future): handle past with bpom-analyst, future with bpom-forecaster, present as unified timeline. |

---

## Implicit references (multi-turn) — resolve from previous turn
- "tahun yang sama" → year from the previous turn.
- "dari situ / yang tadi / itu" → dataset/scope from the previous turn result.
- "selisihnya" → compute from **the two most recent relevant numbers** (pay attention to which pair is meant, e.g. combined − ERBA, not ERBA − ERLA).
- "kalau [dimensi/tahun/produk] lain?" → change ONLY that component; preserve entity+system+scope.

---

## Default scope (disambiguate before SQL)
- "pangan olahan" = **main product** tables (`t_produk_*`); include BTP **only** if user mentions BTP / total / all / both / combined product+BTP.
- **"semua sistem registrasi" / "semua sistem" = ERBA + ERLA (the two systems) — product tables only.**
  A *system* is ERBA/ERLA; BTP is a product *type*, not a system. Do NOT add BTP tables for "semua
  sistem" unless the user also says BTP/total/all. (Adding BTP here is a known over-scoping error.)
- Risk & commitment → **ERBA only** (ERLA has no `status_komitmen`; ERLA risk codes differ — see Risk dimension).
- System not specified → UNION ERBA+ERLA (except for risk/commitment).
- **Year not specified → ALL years (all-time)** + per-year breakdown; never default to a single year. A stated year/range always takes precedence.
