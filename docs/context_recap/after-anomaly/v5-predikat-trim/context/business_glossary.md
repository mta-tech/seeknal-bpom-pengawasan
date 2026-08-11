# BPOM Business Glossary

> **Stable business definitions only.** Code lists and segment mappings are not here — they live
> in `data_dictionary` (lookup at runtime). Predicates (counting, scope, filters) live in
> `context/predikat.md`. This file holds concepts that are *definitional* and do not change.

---

## Registration systems: ERBA and ERLA

BPOM operates two product registration systems. Both cover all product types
(domestic and imported). The distinction is **generational, not geographic**.

| Aspect | ERBA | ERLA |
|---|---|---|
| Full name | E-Registrasi Baru | E-Registrasi Lama |
| Meaning | New system (primary 2023+) | Legacy system (historical 2012–2022) |
| Column types (`tanggal`, `trader_id`) | **ALL TEXT — cast required** | TIMESTAMP / BIGINT |
| Product tables | `t_produk_3_erba`, `t_btp_3_erba` | `t_produk_3_rilis_erla`, `t_btp_3_erla` |
| Trader reference | `m_trader_rba` | `m_trader_rla` |
| Risk column | `kategori_dokumen` | `jenis_dokumen` (**different codes — see warning below**) |
| Commitment (`status_komitmen`) | ✓ tracked (MR only) | ✗ not available |
| Scale column (master) | `skala_industri_id` | `skala_industri` (**different name**) |

**Do not use "dalam negeri" or "impor" to describe ERBA vs ERLA.** Both systems
contain domestic and imported products. Origin is derived from `negara_pabrik`:
- Domestik = `negara_pabrik = 'ID'`


---

## Risk categories — structural facts

⚠️ **Risk codes do NOT mean the same thing across systems, and ERLA has fewer levels.**

- **ERBA has 4 risk levels** (`kategori_dokumen` → kategori `KATEGORI_DOKUMEN`)
- **ERLA has 3 levels** (`jenis_dokumen` → kategori `JENIS_DOKUMEN`): Low / High / Medium
- Cross-map is **lossy**: ERLA's Medium spans both *Menengah Tinggi* and *Menengah Rendah*.
  ERLA **cannot isolate Menengah Tinggi alone**. For an MT-specific count, ERBA is authoritative.
- Resolve risk codes **per system, from `data_dictionary`** — never reuse one system's code on the other.
- Always write a **separate WHERE per UNION side**.
- Default risk scope = **ERBA-only** unless the user explicitly asks for combined.
- Presentation: always use full qualified name — "Risiko Tinggi", "Risiko Menengah Tinggi",
  "Risiko Menengah Rendah" — not the bare adjective.

---

## Column distinctions (avoid confusion)

### `kategori_dokumen` vs `jenis_dokumen`
| Column | Purpose | Use for |
|---|---|---|
| `kategori_dokumen` | Risk level classification | Risk queries (MR/MT/T). ERBA authoritative. |
| `jenis_dokumen` | Document type classification | Document routing queries, NOT risk level |

Do not use `jenis_dokumen` when the user asks about risk level.
Do not use `kategori_dokumen` when the user asks about document type.

### `skala_industri` vs `status_usaha`
- `skala_industri_id` / `skala_industri` = **size classification** (Mikro/Kecil/Menengah/Besar/Importir)
- `status_usaha` = **legal type** (31=Produsen, 33=Importir)

These are not interchangeable. "Skala industri" and "skala usaha" both refer to the
size columns, NOT to `status_usaha`. UMKM = Mikro + Kecil + Menengah (codes 1, 2, 3).

For NULL/empty handling on skala industri, see `predikat.md` §7 (default scope) — empty/space
values mean Importir.

---

## Deprecated / unused columns (DO NOT use)

These exist in the schema but are no longer used by BPOM:
- `klasifikasi_id` in `t_produk_3_erba` — do not filter or group by this column
- `takaran_saji` in `t_produk_3_erba` — do not use for serving size queries

---

## Where to find what (routing)

| Need | Look in |
|---|---|
| Code → label (status, kemasan, daerah, jenis_permohonan, risk, skala) | `data_dictionary` (DB) — 22 categories, lookup via `code_resolution.md` procedure |
| How to count (DISTINCT vs *, which date column) | `context/predikat.md` §1–2 |
| NIE sah filter, RC-2, RC-4 Case A/B | `context/predikat.md` §3–5 |
| Default scope (year, system) | `context/predikat.md` §7 |
| Mandatory exclusions (test accounts, bad years) | `context/predikat.md` §8 |
| ERBA cast rules, UNION template | `context/predikat.md` §9–10 |
| status_komitmen format bug ('5' vs '5.0') | `context/predikat.md` §6 |
| Coverage-aware column choice, regional edge cases | `context/data_quality_rules.md` |
| Table topology, JOIN rules | `context/data_architecture.md` |
| Question → entity/operation/dimension | `context/intent_mapping.md` |
| SQL shapes (canonical templates) | `context/query_recipes.md` |
