# Code Resolution Guide

This file is a helper for column-shape handling.
It is not the authority for business-code meaning.

Use it to identify likely lookup categories and conversion patterns.
Final binding still happens at runtime through:

- `context/code_translation_protocol.md`
- `context/source_discovery_protocol.md`

## 1. Principle

If a coded column appears in results:

1. identify the likely lookup category,
2. resolve through `data_dictionary` with correct `sumber`,
3. translate to labels before answering.

## 2. Candidate column -> kategori orientation

Treat the mapping below as candidate orientation only.

| Column | Likely kategori |
|---|---|
| `skala_industri_id`, `skala_industri` | `SKALA_INDUSTRI dan SKALA_INDUSTRI_ID` |
| `jenis_permohonan` | `JENIS_PERMOHONAN` |
| `kategori_dokumen` | `KATEGORI_DOKUMEN` |
| `status_komitmen` | `STATUS_KOMITMEN` |
| `status` | `STATUS` |
| `status_produk` | `STATUS_PRODUK` |
| `status_usaha` | `STATUS_USAHA` |
| `bentuk_sediaan` | `BENTUK_SEDIAAN` |
| `jenis_btp` | `JENIS_BTP` |
| `jenis_dokumen` | `JENIS_DOKUMEN` |
| `jenis_produk_btp` | `JENIS_PRODUK_BTP` |
| `kemasan_id` | `KEMASAN_ID` |
| `sub_kemasan_id` | `SUB_KEMASAN_ID` |
| `klasifikasi_id` | `KLASIFIKASI_ID` |
| `kode_kbli` | `KODE_KBLI` |
| `negara_pabrik`, `negara_produsen` | `NEGARA_PABRIK dan NEGARA_PRODUSEN` |
| `peruntukan` | `PERUNTUKAN` |
| `daerah_pabrik`, `daerah_trader`, `daerah_produsen` | regional dictionary category |
| `kategori_pangan` | `AKRONIM` for broad prefix only |

## 3. Cross-system caution

The same code or similarly named column may not mean the same thing in ERBA and ERLA.
Never use this file to assume equivalence.

## 4. Region conversion

Some regional codes need conversion before matching dictionary entries.

Pattern:

```sql
ROUND(daerah_pabrik::numeric / 100, 2)::text
```

## 5. Broad food-category prefix

`kategori_pangan` can resolve to a broad family through:

```sql
'KP ' || LEFT(kategori_pangan, 2)
```

This is broad only.
If the user asks for a narrower segment, escalate to source discovery.
