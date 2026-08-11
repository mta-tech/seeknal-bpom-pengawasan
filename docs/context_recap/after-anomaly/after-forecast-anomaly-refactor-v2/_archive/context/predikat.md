# Predikat — Single Source of Truth for Counting, Scope, and Filters

**This file is authoritative.** Every counting method, mandatory filter, default scope, and
event rule lives here — stated **once**. No other context file restates them; they only point here.

**Before writing any aggregation SQL, read this file.** Never recall a filter, a status list,
or a counting method from memory or from another file.

Tables are qualified `warehouse.public.<table>` — `warehouse` is the DuckDB alias for the
attached PostgreSQL source (`seeknal_agent.yml` → `sources.warehouse.namespace`).

---

## 1. Counting method — the single largest source of wrong numbers

The product tables are **versioned**: the same `nomor` (NIE) appears on several rows as it is
revised. Status `9999` = *"Sudah Diubah"* — a superseded row, an old version of a record that
has since changed.

**`COUNT(*)` therefore double-counts.** Measured on production:

| Table | `COUNT(*)` | `COUNT(DISTINCT nomor)` | Inflation |
|---|---:|---:|---:|
| `t_produk_3_erba` | 187,364 | 139,993 | **+25%** |
| `t_produk_3_rilis_erla` | 407,711 | 175,057 | **+57%** |

| Entity | Count with | Never |
|---|---|---|
| NIE / izin edar | `COUNT(DISTINCT nomor)` | `COUNT(*)` |
| Permohonan / pengajuan | `COUNT(DISTINCT produk_id)` | `COUNT(*)` |
| Perusahaan | `COUNT(DISTINCT t.trader_id)` — from the **product** table | `COUNT(DISTINCT m.trader_id)` — LEFT JOIN yields NULLs |

Applies to all four product/BTP tables. A BTP table is structurally a product table.

The count column follows **what is being counted, not the user's noun** — the same everyday word
can refer to issued licences in one question and applications in another. Decide from the
question's subject; if genuinely ambiguous and the numbers differ materially → clarify (§2 gate
in `SEEKNAL_ASK.md`).

**Default for "berapa produk X terdaftar / punya izin edar":** the subject is the registered
licence → `COUNT(DISTINCT nomor)` (exclude empty `nomor`). Reaching for `produk_id` because the
user said "produk" is the most common entity mistake — verified to inflate answers up to ~2x on
real concepts even when every filter is correct. Use `produk_id` only when the question is about
applications/submissions themselves.

**Per-year totals:** a `nomor` recurring across years double-counts when the yearly rows are
summed. The grand total must be a **separate global `COUNT(DISTINCT …)`** over the whole set
(standalone aggregate, subquery, or `GROUP BY ROLLUP`) — **never** the sum of the per-year rows.

---

## 2. Date column — decided by the entity, not the table

| Counting | Correct column | Wrong |
|---|---|---|
| NIE (izin edar) | `tanggal` — issue date | `tanggal_aju`, `tanggal_bayar` |
| Permohonan | `tanggal_bayar` — payment date | `tanggal_aju` |

`tanggal_berkas`, `tanggal_diambil` are process dates — never count on them.
`tanggal_exp` is not a counting date either, **but it IS the correct filter column when the
question's condition concerns the licence's validity period ending** → filter `tanggal_exp` on
the asked period (cast on the ERBA side — §9).
The table being BTP does not change the choice.

**Use ranges, never `EXTRACT`.** Ranges are pushed down to PostgreSQL; `EXTRACT()` is evaluated
in DuckDB *after* a full table transfer and times out on large tables.

```sql
-- single year {Y}
WHERE tanggal >= '{Y}-01-01' AND tanggal < '{Y+1}-01-01'

-- all-time (a wide bounded range also drops the 1900/1970 artifacts — no extra filter needed)
WHERE tanggal >= '2000-01-01' AND tanggal < '2030-01-01'
-- per-year breakdown: GROUP BY date_trunc('year', tanggal)   -- GROUP, do not filter
```

**NULL `tanggal` in ERBA:** many rows carry `tanggal = NULL` or `''` — products still in
evaluation, no NIE issued yet. Range filters drop them automatically. For `GROUP BY` without a
range filter, guard explicitly: `WHERE tanggal IS NOT NULL AND tanggal != ''`.

---

## 3. Default scope — when the user does not say

| Missing | Default | Never |
|---|---|---|
| **Year** | ALL-TIME (`>= '2000-01-01' AND < '2030-01-01'`) + per-year breakdown | a single year (e.g. 2023), or "the most complete year" |
| **System** | **NO DEFAULT — you MUST clarify (§3.1)** | silently UNION, or silently pick ERBA |
| **System — risiko / komitmen** | **ERBA only** (ERLA has no `status_komitmen`; ERLA risk codes differ) | UNION — and do **not** clarify; this one is settled |
| **"pangan olahan"** | main product tables only (`t_produk_*`) | add BTP unless the user says BTP / total / all / combined |
| **"semua sistem registrasi"** | ERBA + ERLA, product tables only | add BTP — a *system* is ERBA/ERLA; BTP is a product *type* |
| **Result limit** | top 10, and state the full total | truncate silently |

Time scope is **binary**: stated → that year; not stated → ALL-TIME. There is no third option.
A year or range stated by the user always overrides.

### 3.1 System scope — no default, clarify

Question does not name a system (ERBA / ERLA / gabungan) **and** entity is NIE / permohonan /
produk / BTP → call `request_clarification` (or `ask_user`) **before any SQL**. Never guess.

Options, **Gabungan** marked `recommended`: Gabungan ERBA+ERLA · ERBA saja · ERLA saja.

**Exception:** risiko and komitmen are ERBA-only by definition → proceed, state it, do not ask.

---

## 4. Mandatory exclusions

| Exclusion | ERBA | ERLA |
|---|---|---|
| Test accounts | `trader_id::bigint NOT IN (5,17,50,85)` | `trader_id != 3384` |
| Bad data years (1900/1970) | covered by the wide date range (§2) | same |
| Regional placeholders | `daerah_* IS NOT NULL AND daerah_* != 'NULL' AND daerah_* != '9999'` | same |

---

## 5. Valid NIE status — **NIE queries only**

**Applies only when the population being counted is issued NIE.** A population defined by any
other workflow state (resolved from `data_dictionary`) already has its own status condition;
stacking this filter on top **erases the population being asked about** (§7 Case B is the worked
example: stacking turns 5,198 into 254).

| Table | Valid status |
|---|---|
| ERBA (`t_produk_3_erba`, `t_btp_3_erba`) | `'0999'`, `'0906'`, `'9999'` |
| ERLA (`t_produk_3_rilis_erla`, `t_btp_3_erla`) | `'0099'`, `'0999'`, `'0906'`, `'9999'` |

**Do NOT apply a status filter to permohonan counts.** Permohonan = every application submitted,
regardless of outcome.

`9999` = "Sudah Diubah" is included because a superseded row still represents a real issued NIE —
which is precisely why §1 requires `COUNT(DISTINCT nomor)` so it is not counted twice.

---

## 6. `jenis_permohonan` — conditional, by intent (RC-2)

**Not universal.** Choose by what is being counted:

| Intent | Signal | Filter |
|---|---|---|
| Newly issued NIE | "NIE baru", "terbit di {periode}", "baru" | ERBA `IN ('301','305')` · ERLA `IN ('301','304','305')` |
| All active NIE / total registered | "total produk terdaftar", "berapa NIE {segmen}" | **no `jenis_permohonan` filter** — valid `status` alone |
| Permohonan (applications) | "permohonan", "registrasi", "pengajuan" | all types `IN ('301','302','303','304','305')`, **no status filter** |

A product whose current valid NIE arrived via Perubahan (`302`/`303`) still holds an active NIE.
Filtering "all active NIE" by `('301','305')` drops them and undercounts (Produk MD 2025:
30,760 with the filter vs 36,706 without).

**Ambiguous and the word "baru" is absent → treat as "all active NIE"** (status filter only), and
state the basis in the answer.

---

## 7. Commitment — two distinct cases (RC-4)

`status_komitmen` exists **only** in `t_produk_3_erba`, and only for MR (`kategori_dokumen='303'`).
Choosing the wrong case is the cause of the MR-dibatalkan error (**254 vs ~5,199**).

**Case A — "NIE that ALSO has commitment status X"**
("berapa NIE MR yang komitmennya disetujui?") — the subject is the **issued NIE**.
→ Keep all NIE filters; commitment is an *additional* filter on top.

```sql
WHERE kategori_dokumen = '303'
  AND status IN ('0999','0906','9999')                        -- valid NIE — REQUIRED here
  AND jenis_permohonan IN ('301','305')                       -- REQUIRED here
  AND ROUND(status_komitmen::numeric)::int::text = '<code>'
  AND trader_id::bigint NOT IN (5,17,50,85)
```

**Case B — "applications whose commitment was [outcome]"**
("berapa MR yang dibatalkan?") — the subject is the **application lifecycle**, not the NIE.
→ **Drop the valid-NIE `status` filter.** Most cancellations happen *before* a NIE is issued;
requiring active-NIE status undercounts by ~95%.

```sql
WHERE kategori_dokumen = '303'
  AND ROUND(status_komitmen::numeric)::int::text = '<code>'
  AND trader_id::bigint NOT IN (5,17,50,85)
  -- NO status filter, NO jenis_permohonan filter
```

**How to tell them apart:** if the thing being counted is named "NIE" / "izin edar" → Case A.
If it asks how many were "dibatalkan / ditolak / disetujui" as a lifecycle outcome → Case B.

**Final vs transient:** a settled outcome counts only the **final-state** code. "Validasi
Pembatalan" is transient and is NOT folded into the settled count. Resolve which code is final
from `data_dictionary` (kategori `STATUS_KOMITMEN`, sumber `ERBA`).

**"Why was it cancelled"** → `jenis_penolakan_komitmen`, never the status codes.

---

## 8. `status_komitmen` — mixed number format (silent data loss)

ERBA stores `status_komitmen` as TEXT with **two formats for the same value**: some rows `'5'`,
others `'5.0'`. Production: `'5'` → 5,061 rows · `'5.0'` → 209 rows.

```sql
-- WRONG — silently drops the '5.0' rows (~4% of commitment data)
WHERE status_komitmen = '5'

-- CORRECT — captures both
WHERE ROUND(status_komitmen::numeric)::int::text = '5'
```

Apply to **every** `status_komitmen` filter. Affected codes: `0`, `1`, `4`, `5`, `7`, `8`, `9`.

---

## 9. ERBA is all TEXT — casts are mandatory

ERBA stores every column as TEXT; ERLA uses TIMESTAMP / BIGINT. **Cast on the ERBA side.**

| ERBA column | Cast |
|---|---|
| `tanggal`, `tanggal_bayar` | `::timestamp` |
| `trader_id` | `::bigint` |
| `status_komitmen` | see §8 |

⚠️ **PostgreSQL has no `TRY_CAST` / `SAFE_CAST` / `TRY_CONVERT`** — those are DuckDB/BigQuery
dialects and are a **syntax error** here. Use `::type` and guard bad values with
`WHERE col IS NOT NULL AND col != ''`.

**Canonical UNION template** (cast on the ERBA side only):

```sql
SELECT nomor, tanggal::timestamp AS tanggal, trader_id::bigint AS trader_id
FROM warehouse.public.t_produk_3_erba
WHERE tanggal IS NOT NULL AND tanggal != ''
  AND status IN ('0999','0906','9999')
  AND trader_id::bigint NOT IN (5,17,50,85)
  AND tanggal::timestamp >= '{Y}-01-01' AND tanggal::timestamp < '{Y+1}-01-01'

UNION ALL

SELECT nomor, tanggal, trader_id
FROM warehouse.public.t_produk_3_rilis_erla
WHERE status IN ('0099','0999','0906','9999')
  AND trader_id != 3384
  AND tanggal >= '{Y}-01-01' AND tanggal < '{Y+1}-01-01'
```

Aggregate the union with `COUNT(DISTINCT nomor)` (§1). `nomor` does not overlap between the two
systems, so `UNION ALL` + `COUNT DISTINCT` is accurate.
For ALL-TIME, widen both ranges to `'2000-01-01'`…`'2030-01-01'`.

Risk and commitment need a **separate WHERE per UNION side** — the codes are not equivalent
across systems.

---

## 10. Skala industri — NULL/empty means Importir

| System | Column | Empty representation |
|---|---|---|
| ERBA | `m_trader_rba.skala_industri_id` | single space `' '` |
| ERLA | `m_trader_rla.skala_industri` | empty string `''` **or** SQL NULL |

```sql
COALESCE(NULLIF(TRIM(ref.skala_industri_id::text), ''), 'Importir')  -- ERBA
COALESCE(NULLIF(TRIM(ref.skala_industri::text),    ''), 'Importir')  -- ERLA
```

Codes: 1=Mikro · 2=Kecil · 3=Menengah · 4=Besar. **UMKM = 1 + 2 + 3** (Mikro + Kecil + **Menengah**).

`status_usaha` (31=Produsen, 33=Importir) is a **different** column — not interchangeable.

---

## 11. Join discipline

- **Always `LEFT JOIN`** to `m_trader_*` — orphan `trader_id` values exist; `INNER JOIN` drops data.
- Count companies from the product table's `t.trader_id`, never the master's (LEFT JOIN → NULLs).
- There is **no unified view** — ERBA + ERLA coverage must be UNIONed manually.

---

## 12. `execute_sql`

- **One statement per call.** No `;` — multi-statement SQL is rejected by the runtime and the call
  is wasted. Need two results → two calls, or fold into one query (`UNION ALL` / `GROUP BY` / CTE).
- **Never `EXTRACT(YEAR …)` to filter** — it forces a full table transfer. Use a bounded range
  (§2). `EXTRACT` is fine only for labelling an already-grouped result.
