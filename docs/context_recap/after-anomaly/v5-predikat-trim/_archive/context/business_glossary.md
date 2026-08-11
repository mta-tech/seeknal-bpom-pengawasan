# BPOM Business Glossary

## Registration systems: ERBA and ERLA

BPOM operates two product registration systems. Both cover all product types
(domestic and imported). The distinction is generational, not geographic.

| Aspect | ERBA | ERLA |
|---|---|---|
| Full name | E-Registrasi Baru | E-Registrasi Lama |
| Meaning | New system (primary 2023+) | Legacy system (historical 2012–2022) |
| Product rows | 245,248 | 412,608 |
| Date range | Sep 2022 → now | 2012 → now |
| Column types (`tanggal`, `trader_id`) | **ALL TEXT — cast required** | TIMESTAMP / BIGINT |
| Product tables | `t_produk_3_erba`, `t_btp_3_erba` | `t_produk_3_rilis_erla`, `t_btp_3_erla` |
| Trader reference | `m_trader_rba` | `m_trader_rla` |
| Valid NIE status | `'0999'`, `'0906'`, `'9999'` | `'0099'`, `'0999'`, `'0906'`, `'9999'` |
| NIE jenis_permohonan | `'301'`, `'305'` | `'301'`, `'304'`, `'305'` |
| Risk column | `kategori_dokumen` ✓ | `jenis_dokumen` ✓ (**different codes — see warning below**) |
| Commitment (`status_komitmen`) | ✓ tracked | ✗ not available |
| Test accounts (exclude) | `trader_id::bigint NOT IN (5,17,50,85)` | `trader_id != 3384` |

For full coverage, UNION ERBA and ERLA. Use ERBA-only for commitment queries.
`nomor` values do NOT overlap between systems — UNION ALL + COUNT DISTINCT is accurate.

**Do not use "dalam negeri" or "impor" to describe ERBA vs ERLA.** Both systems
contain domestic and imported products. ERBA/ERLA is a system-generation distinction, not geographic.

---

## Core metrics

### NIE (Nomor Izin Edar) — Izin Edar
A product license number issued by BPOM. Each unique `nomor` value is one NIE.
- Count with: `COUNT(DISTINCT nomor)`
- Date of issue: `tanggal` column
- User terms: "izin edar", "NIE", "izin terbit", "jumlah izin edar"
- Covers: `t_produk_3_erba`, `t_produk_3_rilis_erla`, `t_btp_3_erba`, `t_btp_3_erla`

### Permohonan — Application
A registration application submitted by a company. Each unique `produk_id` is one application.
- Count with: `COUNT(DISTINCT produk_id)`
- Date of payment: `tanggal_bayar` — this is the ONLY correct date for permohonan counts
- User terms: "permohonan", "permohonan izin edar", "jumlah permohonan", "registrasi", "pengajuan"
- Do NOT use `tanggal_aju` (submission date) — use `tanggal_bayar` (payment date)
- Covers: same 4 tables as NIE

---

## Product types

### BTP (Bahan Tambahan Pangan)
Food additives. Stored in `t_btp_3_erba` and `t_btp_3_erla`.
Separate from regular product tables.

### AMDK (Air Minum Dalam Kemasan)
Bottled drinking water. Identified by `jenis_pangan`:
- ERBA: `jenis_pangan = '1401'`
- ERLA: `jenis_pangan IN ('651', '652', '655')`

### Garam Beryodium
Iodized salt. Production SQL uses `kategori_pangan` (not `jenis_pangan`):
- ERBA: `kategori_pangan = '120101000001'` (production SQL verified 2026-07-15)
- ERLA: `kategori_pangan = '12010103'`

---

## Risk categories (Kategori Dokumen / Jenis Dokumen)

Both ERBA and ERLA track risk, but via **different columns with different code mappings**.
Do NOT use the same code on both tables for risk queries.

**Presentation convention:** a risk level is always presented with its full qualified name —
"Risiko Tinggi", "Risiko Menengah Tinggi", "Risiko Menengah Rendah" — not the bare adjective
("Tinggi", "Menengah Tinggi"). The canonical labels below already carry the "Risiko " prefix;
use them verbatim in the answer rather than the raw `data_dictionary.deskripsi`, which may
store only the bare level.

> ⚠️ **Risk codes do NOT mean the same thing across systems, and ERLA has fewer levels.**
> Resolve risk **per system, from the dictionary** — never reuse one system's code on the other.
> Do not read risk codes from a static table here; look them up via
> `context/code_translation_protocol.md` (ERBA risk = `kategori_dokumen` → kategori
> `KATEGORI_DOKUMEN`; ERLA risk = `jenis_dokumen` → kategori `JENIS_DOKUMEN`).

**Structural facts to reason with (not a code cache):**
- **ERBA has 4 risk levels**, ERLA has **3** (Low / High / **Medium**). The cross-map is therefore
  **lossy**: ERLA's Medium-Risk spans both *Menengah Tinggi* and *Menengah Rendah*. **ERLA cannot
  isolate Menengah Tinggi alone.** For an MT-specific count, ERBA is the authoritative source; if a
  combined figure is requested, state that ERLA contributes combined medium risk.
- Always write a **separate WHERE per UNION side** (resolve ERBA codes and ERLA codes independently).
- If asked to equate an ERLA level to an ERBA level, **test the equivalence against data** (compare
  magnitudes) before relying on it — see `code_translation_protocol.md` §3. Default risk scope =
  **ERBA-only** unless the user explicitly asks for combined.

---

## Industry scale (Skala Industri)

- ERBA: `m_trader_rba.skala_industri_id` — stored as VARCHAR, values `'1'`–`'4'` or single space `' '`
- ERLA: `m_trader_rla.skala_industri` — stored as VARCHAR, values `'1'`–`'4'`, empty string `''`, or SQL NULL
- Codes: 1=Mikro, 2=Kecil, 3=Menengah, 4=Besar
- UMKM = Mikro + Kecil + Menengah (codes 1, 2, 3)

**Null/empty handling differs between systems:**
- ERBA: space `' '` means Importir (no SQL NULL in this column)
- ERLA: both empty string `''` AND SQL NULL mean Importir

Correct COALESCE pattern for both systems:
```sql
COALESCE(NULLIF(TRIM(ref.skala_industri_id::text), ''), 'Importir')  -- ERBA
COALESCE(NULLIF(TRIM(ref.skala_industri::text),    ''), 'Importir')  -- ERLA
```

**Do not confuse skala industri with status usaha.** `status_usaha` is a separate
column (31=Produsen, 33=Importir). They are not interchangeable.

---

## Commitment status (Status Komitmen)

Only applies to `t_produk_3_erba` where `kategori_dokumen = '303'` (MR). **Resolve the codes from
the dictionary** (kategori `STATUS_KOMITMEN`, sumber `ERBA`) via `code_translation_protocol.md` —
do not rely on a static code list here (the dictionary is authoritative and more complete; e.g. it
includes "Draft Pemenuhan Komitmen", which a hand-kept table missed).

**Concept the agent must apply (not a code cache):**
- **Final vs transient matters for counting.** A settled outcome ("dibatalkan" / "disetujui")
  counts only the **final-state** code(s); a still-in-progress validation (e.g. "Validasi
  Pembatalan") is **transient** and is NOT folded into the settled count. When the user asks for a
  settled outcome, resolve which code is the *final* one from the dictionary and count that.
- Always normalize: `ROUND(status_komitmen::numeric)::int::text = '<code>'` (NOT plain `= '5'` —
  see `data_quality_rules.md` §status_komitmen normalization).
- "Why cancelled / alasan pembatalan" → query `jenis_penolakan_komitmen`, not the status itself.

**Two different counting questions — do NOT conflate (this is the RC-4 fix):**
1. **"NIE that also has commitment status X"** (e.g. "berapa NIE MR yang komitmennya disetujui?")
   → keep all NIE filters (status, jenis_permohonan) **and** add the commitment filter.
2. **"Applications whose commitment was cancelled"** (e.g. "berapa MR yang dibatalkan?")
   → this is an application-lifecycle count; **drop the NIE status filter** — most cancellations
   occur *before* a NIE is issued, so requiring valid-NIE status massively undercounts.
   See `data_quality_rules.md` §Commitment queries.

---

## Application types (Jenis Permohonan)

| Code | Label | Notes |
|---|---|---|
| `301` | Permohonan Baru | New application |
| `302` | Perubahan Mayor | Composition change (bahan baku/formula) |
| `303` | Perubahan Minor | Administrative/document update only (not composition) |
| `304` | Daftar Ulang | Re-registration (ERLA only for NIE filter) |
| `305` | Baru Notifikasi | New notification-based application |

NIE re-registration is performed 5 years after the original NIE issue date.

**Perubahan Mayor vs Minor:** "Perubahan mayor" = changes to product composition or
formula. "Perubahan minor" = document, label, or administrative changes only.

---

## Makloon products

Products with `status_produk = '304'` are contract-manufactured (makloon).
For these, use producer columns: `produsen_id`, `nama_produsen`, `alamat_produsen`,
`daerah_produsen`, `negara_produsen` — not the trader columns.

---

## Product Segment Codes (ERBA and ERLA use different codes)

These segment identifiers cannot be discovered from `data_dictionary`. Use the
table below first; for unknown segments use the discovery query at the bottom.

| Segment | ERBA filter | ERLA filter |
|---|---|---|
| AMDK (Air Minum Dalam Kemasan) | `jenis_pangan = '1401'` | `jenis_pangan IN ('651','652','655')` |
| Garam Beryodium | `kategori_pangan = '120101000001'` (production) | `kategori_pangan = '12010103'` |
| BTP / food additives | table `t_btp_3_erba` | table `t_btp_3_erla` |
| Makloon (contract manufacturing) | `status_produk = '304'`, use `produsen_*` columns | ERBA only |

> Segment codes are **not** in `data_dictionary`. Prefer the **parent category** for completeness
> and confirm by coverage (a sub-code under-counts). For segments not listed, **discover** via the
> `nama_kategori` probe below — never hardcode a sub-code as the segment's definition.

> AMDK handover: pre-2023 AMDK data is in ERLA (651/652/655); 2023+ is in ERBA (1401).
> For ALL-TIME AMDK: always include ERBA (1401) + ERLA (651/652/655) in UNION.

**For segments NOT in the table above — use `nama_kategori` discovery:**

```sql
-- Step 1: find jenis_pangan codes by category name
SELECT DISTINCT jenis_pangan, nama_kategori, COUNT(*) AS cnt
FROM warehouse.public.t_produk_3_rilis_erla   -- or t_produk_3_erba
WHERE nama_kategori ILIKE '%<keyword>%'
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10

-- Step 2: confirm with a name sample
SELECT DISTINCT nama FROM warehouse.public.[table]
WHERE jenis_pangan = '<code>' LIMIT 5
```

Use `nama_kategori` (standardized category label) for discovery.
Do NOT use `nama ILIKE '%keyword%'` as primary filter — product names are inconsistent.

---

## Deprecated / unused columns

These columns exist in the database schema but are **no longer used** by BPOM:
- `klasifikasi_id` in `t_produk_3_erba` — do not filter or group by this column
- `takaran_saji` in `t_produk_3_erba` — do not use for serving size queries

---

## Additional product attributes

### PMR (Program Manajemen Risiko)
Column `pmr` in `t_produk_3_erba`.
- `1` = company participates in PMR
- `0` = does not participate

### Ecolabel
Column `ecolabel` in `t_produk_3_erba`.
- `1` = product uses eco-friendly packaging
- `0` = does not

### Klaim (Claims)
Column `klaim` in product tables.
- `1` = product has a special claim (health, nutrition, etc.)
- `0` or NULL = no special claim

### Brand queries
When a user asks about a specific brand (`merk`), match exactly. If other products
have similar names, exclude them. Answer only based on the exact brand requested.

### Domestik / Impor (origin)
There is **no dedicated domestic/import flag column**. Origin is derived from the factory country
`negara_pabrik` (or `negara_produsen`):
- **Domestik** = `negara_pabrik = 'ID'` (Indonesia)
- **Impor** = `negara_pabrik <> 'ID'` (e.g. `CN`, `MY`, `KR`, …) — resolve the country code to a
  name via `data_dictionary` (`NEGARA_PABRIK dan NEGARA_PRODUSEN`).

ERBA/ERLA are registration **systems**, NOT an origin indicator — never infer domestic/import from
the system. When answering an origin question, **state the basis** ("berdasarkan negara pabrik").

---

## Column distinctions to avoid confusion

### kategori_dokumen vs jenis_dokumen
These are two different columns that both exist in ERBA and ERLA tables:

| Column | Purpose | Use for |
|---|---|---|
| `kategori_dokumen` | Risk level classification | Risk queries (MR/MT/T). ERBA values are authoritative; use ERBA-only for risk analysis |
| `jenis_dokumen` | Document type classification | Document routing queries, NOT for risk level |

Do not use `jenis_dokumen` when the user asks about risk level (MR/MT/T).
Do not use `kategori_dokumen` when the user asks about document type.

### skala_industri vs status_usaha
- `skala_industri_id` / `skala_industri` = size classification (Mikro/Kecil/Menengah/Besar/Importir)
- `status_usaha` = legal type (31=Produsen, 33=Importir)
These are not interchangeable. "Skala industri" and "skala usaha" both refer to the
size columns, NOT to `status_usaha`.

---

## Column Purpose Guide — What Question Does Each Column Answer

Columns are often confused because their names overlap semantically. This section
defines the *question each column answers* and what it does NOT answer.

### Columns That Answer "What Stage Is This Record In?" (Workflow State)

These columns track where a record is in the registration process. They are
**process trackers**, not explanations or business classifications.

| Column | Table | Answers | Does NOT answer |
|---|---|---|---|
| `status` | ERBA + ERLA | "What is the current processing stage of this record?" | Why it was cancelled; what kind of document it is |
| `status_komitmen` | ERBA only (MR) | "What is the current commitment stage for this MR product?" | Why the commitment was rejected |
| `status_produk` | ERBA | "What production type is this?" (31=producer, 33=importer, 304=makloon) | Risk level; document quality |

**Important for "alasan/mengapa" questions:** `status` is a workflow tracker.
Status code values such as `0999`, `9999`, `0906`, `0009`, `0912` are process stage codes.
They are NOT reasons for cancellation, rejection, or any business decision.
Never report `status` code values as "uncategorized cancellation reasons" — they have
nothing to do with the reason; they record where the process currently stands.

### Columns That Answer "Why?" (Reason / Description)

These columns store the explanation for a business decision or rejection.

| Column | Table | Answers | Data dictionary category |
|---|---|---|---|
| `jenis_penolakan_komitmen` | ERBA only (MR) | "Why was this commitment rejected or cancelled?" | `JENIS_PENOLAKAN_KOMITMEN` (9 reason codes) |

When the user asks "apa alasan pembatalan", "mengapa izin dibatalkan", or
"alasan penolakan terbanyak":
- USE: `jenis_penolakan_komitmen` → JOIN `data_dictionary WHERE kategori = 'JENIS_PENOLAKAN_KOMITMEN'`
- DO NOT USE: `status` column values
- DO NOT USE: `status_komitmen` codes as reason labels

The 9 reason codes in `JENIS_PENOLAKAN_KOMITMEN` (from `data_dictionary`):
1 = Jenis kemasan/data pabrik tidak sesuai · 2 = Proses pengolahan tidak sesuai ·
3 = Kategori pangan tidak sesuai · 4 = Penggunaan bahan baku/BTP tidak sesuai ·
5 = Pencantuman peruntukan/klaim/organik · 6 = Dokumen tidak sesuai ·
7 = Dokumen tidak diunggah · 8 = Pangan segar · 10 = Rekomendasi pengawasan

### Columns That Answer "What Is the Risk Level?" (Classification)

| Column | Table | Answers | Critical warning |
|---|---|---|---|
| `kategori_dokumen` | ERBA | "What is the risk classification of this product?" (4 levels) | codes resolve only against `KATEGORI_DOKUMEN` (sumber ERBA) |
| `jenis_dokumen` | ERLA | "What is the risk classification?" (3 levels, different codes) | codes resolve only against `JENIS_DOKUMEN` (sumber ERLA) |

⚠️ **The same numeric code means different things in ERBA vs ERLA.** Resolve risk codes
**per system, from the dictionary** (`code_translation_protocol.md`) — never reuse one system's
risk code on the other. Always write a **separate WHERE per UNION side**.

`jenis_dokumen` in ERBA describes the document type submitted (not risk level).
`jenis_dokumen` in ERLA carries risk information (different codes than ERBA).
When answering risk level questions for ERBA → always use `kategori_dokumen`, not `jenis_dokumen`.
