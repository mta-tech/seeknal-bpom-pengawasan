# BPOM Business Glossary

Stable business meaning only. **Counting, filters, and scope rules live in `context/predikat.md`.
Code → label lookups live in `data_dictionary`.** This file does not restate either.

The one exception is **§Product Segment Codes** — `jenis_pangan` / `kategori_pangan` are the only
coded columns *not* present in `data_dictionary`, so they are documented here.

---

## Registration systems: ERBA and ERLA

Two product registration systems. Both cover all product types, domestic **and** imported.
The distinction is **generational, not geographic**.

**They are two databases holding roughly the SAME information, WRITTEN DIFFERENTLY** —
column names, column types, code values, code formats, and feature coverage all diverge.
The table below shows **examples of these differences, not a complete list**. Never assume a
same-named column behaves the same in both systems — verify per column when unsure (one
verified example beyond this table: the two sides store the same status codes in different
formats; see `code_resolution.md` §ERLA zero-padding).

| Aspect | ERBA | ERLA |
|---|---|---|
| Full name | E-Registrasi Baru | E-Registrasi Lama |
| Era | New system (primary 2023+) | Legacy (historical 2012–2022) |
| Product tables | `t_produk_3_erba`, `t_btp_3_erba` | `t_produk_3_rilis_erla`, `t_btp_3_erla` |
| Trader master | `m_trader_rba` | `m_trader_rla` |
| Column types (`tanggal`, `trader_id`) | **ALL TEXT — cast required** | TIMESTAMP / BIGINT |
| Risk column | `kategori_dokumen` | `jenis_dokumen` (**different codes**) |
| Commitment (`status_komitmen`) | ✓ tracked | ✗ not available |

`nomor` values do **not** overlap between systems → `UNION ALL` + `COUNT(DISTINCT nomor)` is accurate.

> **Never use "dalam negeri" / "impor" to describe ERBA vs ERLA.** Both hold domestic and imported
> products. ERBA/ERLA is a system generation, not an origin.

Status lists, `jenis_permohonan` lists, test-account exclusions, and cast rules → `predikat.md`.

---

## Risk levels — resolve per system

Both systems track risk, via **different columns with different code mappings**.

- **ERBA** risk = `kategori_dokumen` → dictionary kategori `KATEGORI_DOKUMEN` (**4 levels**)
- **ERLA** risk = `jenis_dokumen` → dictionary kategori `JENIS_DOKUMEN` (**3 levels**)

> ⚠️ **The same numeric code means different things in ERBA and ERLA.** Resolve each **per system,
> from the dictionary** — never reuse one system's risk code on the other. Always write a
> **separate `WHERE` per UNION side**.

**Structural facts to reason with (not a code cache):**
- The cross-map is **lossy**: ERLA's *Medium Risk* spans both *Menengah Tinggi* and *Menengah
  Rendah*. **ERLA cannot isolate Menengah Tinggi alone.** For an MT-specific count, ERBA is
  authoritative; if a combined figure is requested, say that ERLA contributes combined medium risk.
- Before equating an ERLA level to an ERBA level, **test the equivalence against data** (compare
  magnitudes) — see `code_translation_protocol.md`.
- Default risk scope = **ERBA-only** unless the user explicitly asks for combined (`predikat.md` §3).

**Presentation:** always the full qualified name — "Risiko Tinggi", "Risiko Menengah Rendah" —
never the bare adjective.

---

## Product Segment Codes — the only codes NOT in `data_dictionary`

`jenis_pangan` and `kategori_pangan` have **no dictionary entries**. Use the table below; for any
segment not listed, use the discovery probe.

| Segment | ERBA filter | ERLA filter |
|---|---|---|
| AMDK (Air Minum Dalam Kemasan) | `jenis_pangan = '1401'` | `jenis_pangan IN ('651','652','655')` |
| Garam Beryodium | `jenis_pangan = '1204'` (parent — **not** the sub-code `120101000001`) | `kategori_pangan = '12010103'` |
| BTP / food additives | table `t_btp_3_erba` | table `t_btp_3_erla` |
| Makloon (contract manufacturing) | `status_produk = '304'`, use `produsen_*` columns | ERBA only |

> **AMDK handover:** pre-2023 AMDK is in ERLA (651/652/655); 2023+ is in ERBA (1401).
> For ALL-TIME AMDK, always UNION both.
> **Prefer the parent category** — a sub-code under-counts (Garam sub-code `120101000001` misses
> products under sibling sub-codes).

**Discovery probe — for any segment not in the table above:**

```sql
-- Step 1: find candidate jenis_pangan by category name
SELECT DISTINCT jenis_pangan, nama_kategori, COUNT(*) AS cnt
FROM warehouse.public.t_produk_3_erba          -- or t_produk_3_rilis_erla
WHERE nama_kategori ILIKE '%<keyword>%'
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 15

-- Step 2: confirm with a product-name sample
SELECT DISTINCT nama FROM warehouse.public.t_produk_3_erba
WHERE jenis_pangan = '<code>' LIMIT 5
```

> ⚠️ **The probe is broad — it returns near-matches, not just the segment.** Searching `'roti'`
> also returns *Lemak Reroti* (a shortening), *Ragi Roti* (yeast), and *Tepung Roti* (breadcrumbs).
> Including or excluding them swings the answer by ~20%.
>
> **If more than one plausible code family comes back, ASK THE USER.** Never pick silently.
> A silent pick is not deterministic — the same question in another session can produce a different
> set of codes, and therefore a different number.

Use `nama_kategori` for **discovery only**. It is mostly empty, so it is **never** a grouping key
(see `data_quality_rules.md` §Coverage).
Do not use `nama ILIKE '%keyword%'` as the primary filter — product names are inconsistent.

---

## Commitment — the concept

`status_komitmen` applies **only** to `t_produk_3_erba` where `kategori_dokumen = '303'` (MR).

Codes are resolved from the dictionary (kategori `STATUS_KOMITMEN`, sumber `ERBA`) — never from a
static list here.

**The concept the agent must apply:** a settled outcome ("dibatalkan" / "disetujui") counts only
the **final-state** code. A still-in-progress validation (e.g. "Validasi Pembatalan") is
**transient** and is not folded into the settled count.

> The two counting cases (Case A vs Case B) and the number-format trap → **`predikat.md` §7–§8**.
> This is the single largest source of commitment errors (254 vs ~5,199).

**"Why was it cancelled"** → `jenis_penolakan_komitmen` (dictionary kategori
`JENIS_PENOLAKAN_KOMITMEN`), **never** the `status` or `status_komitmen` codes. Status codes are
process-stage trackers; they are not reasons.

---

## Makloon

`status_produk = '304'` = contract-manufactured. For these, use the producer columns —
`produsen_id`, `nama_produsen`, `alamat_produsen`, `daerah_produsen`, `negara_produsen` —
not the trader columns.

---

## Domestik / Impor (origin)

There is **no dedicated origin flag**. Origin is derived from the factory country:

- **Domestik** = `negara_pabrik = 'ID'`
- **Impor** = `negara_pabrik <> 'ID'` — resolve the country code via `data_dictionary`
  (kategori `NEGARA_PABRIK dan NEGARA_PRODUSEN`)

ERBA/ERLA are **systems**, not origin indicators — never infer origin from the system.
When answering an origin question, **state the basis** ("berdasarkan negara pabrik").

---

## Column distinctions that cause errors

### `kategori_dokumen` vs `jenis_dokumen`
- `kategori_dokumen` → **risk level**. In ERBA this is authoritative for risk.
- `jenis_dokumen` → **document type** in ERBA; but in **ERLA it carries risk** (different codes).

Never use `jenis_dokumen` for ERBA risk. Never use `kategori_dokumen` for document type.

### `skala_industri` vs `status_usaha`
- `skala_industri_id` / `skala_industri` = **size** (Mikro / Kecil / Menengah / Besar / Importir)
- `status_usaha` = **legal type** (31 = Produsen, 33 = Importir)

Not interchangeable. "Skala industri" and "skala usaha" both mean the **size** columns.

> UMKM definition and the NULL→Importir handling → `predikat.md` §10.

### `status` is a process tracker, not a reason
Values like `0999`, `9999`, `0906`, `0009` record **where the record is in the workflow**.
They are **not** reasons for cancellation or rejection. Never report a `status` code as an
"uncategorized cancellation reason".

---

## Other attributes

| Column | Meaning |
|---|---|
| `pmr` | 1 = company participates in Program Manajemen Risiko |
| `ecolabel` | 1 = eco-friendly packaging |
| `klaim` | 1 = product carries a special claim (health, nutrition, …) |
| `merk` | brand — match **exactly**; exclude similarly-named products |
