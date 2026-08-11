# Filter Code Reference — concept → column + code

**This file is the authoritative code map.** For any coded business concept: check
`verified_bindings.md`, then this file, BEFORE any schema or dictionary probing. A hit here IS
the binding. Codes not listed here resolve via `data_dictionary` (`code_resolution.md`); if
probing surfaces more than one plausible column or code family, ask the user — never pick
silently.

This file stores structure only — columns, codes, scope rules. Every number in an answer comes
from SQL executed this turn. Query only these tables: `t_produk_3_erba`,
`t_produk_3_rilis_erla`, `t_btp_3_erba`, `t_btp_3_erla`, `m_trader_rba`, `m_trader_rla`,
`data_dictionary` (no `mv_*` views exist in this warehouse).

---

## 1. Counting entity

| Question subject | Count |
|---|---|
| NIE / izin edar / "produk terdaftar" | `COUNT(DISTINCT nomor)`, exclude empty `nomor` |
| permohonan / pengajuan (application rows) | `COUNT(DISTINCT produk_id)` |
| perusahaan | `COUNT(DISTINCT trader_id)` — within ONE system only |

- Never `COUNT(*)` on the product/BTP tables (`predikat.md` §1).
- One `nomor` spans multiple `produk_id` rows — swapping the entity changes the answer up to
  several-fold with identical filters.
- Combined-system company counts: `trader_id` is NOT comparable between ERBA and ERLA — dedupe
  by company NAME; on a name collision keep the ERBA record.

---

## 2. Pipeline stages → status codes

| Stage | ERBA codes |
|---|---|
| Evaluator | `0301, 0308` |
| Verifikator 1 | `0402, 0403, 0405, 0406, 0407` |
| Verifikator 2 | `0500, 0502, 0504` (use exactly these; ignore dictionary rows `0501, 0503`) |
| Direktur | `0600, 0601, 0666` |
| Deputi / Kepala Badan | `0700` / `0800` |
| Draft | `0910, 0912` |
| Bayar (menunggu pembayaran SPB/HPR) | `0903, 0907` |
| Data Tambahan | `0308, 0402, 0407` (petugas) **+** `0901, 0914, 0915, 0917, 0951` (pendaftar) — always both groups |
| Ditolak Sistem | `0908, 0911, 0918` |
| Ditolak lainnya (penerimaan/verifikasi) | `0902, 0905, 0913` |
| Terbit / Perubahan / Sudah Diubah | `0999` / `0906` / `9999` |
| Dibatalkan / Dicabut / Tidak Berlaku | `0000, 0009, 0099` |

Rules:
- Product pipeline: query `t_produk_3_erba` only — `t_produk_3_rilis_erla` contains final
  states only. BTP pipeline: query BOTH `t_btp_3_erba` AND `t_btp_3_erla`.
- "Permohonan"/"produk" in a pipeline question is ambiguous about BTP, and the choice shifts
  some stages by more than 10%: present both figures (produk-only and produk+BTP, each labeled
  with its source tables), or state which scope is used and why.
- A `NOT IN` bucket silently absorbs rare unlisted codes (`000X, 0201, 0900, 0909, 0916` —
  real rows): mention this when using `NOT IN`.
- "Currently in stage X" is a point-in-time snapshot; it moves both directions over time.

---

## 3. Risk category

| Concept | Filter |
|---|---|
| Risiko Tinggi | `kategori_dokumen IN ('301','304')` — Tinggi includes Tinggi Notifikasi |
| Risiko Tinggi Notifikasi (explicitly asked) | `kategori_dokumen = '304'` |
| Risiko Menengah Tinggi | `kategori_dokumen = '302'` |
| Risiko Menengah Rendah | `kategori_dokumen = '303'` |

- Risk is ERBA-only by definition; `kategori_dokumen` is the risk column.
- `jenis_dokumen` (`301` Low · `302` High · `303` Medium · `000` belum dikategorikan) is a
  separate cross-system typing — use it only when the user explicitly asks for that view, and
  never mix the two columns in one query.
- "Belum dikategorikan / belum punya kategori risiko" = `jenis_dokumen = '000'`.

---

## 4. Exact codes per domain

| Concept | Column | Codes |
|---|---|---|
| Status produk (ERBA) | `status_produk` | `301` produsen sendiri · `302` impor · `304` makloon · `306` Single MD Induk · `307` Single MD Anak |
| Jenis permohonan | `jenis_permohonan` | `301` baru · `302` mayor · `303` minor · `304` daftar ulang · `305` baru notifikasi |
| Status komitmen | `status_komitmen` (MR scope `kategori_dokumen='303'`) | codes, ROUND normalization, Case A/B → `predikat.md`. Disetujui = `IN ('4','7')` (with catatan combined). Code `8` (Validasi Pembatalan) is transient toward `5` — date-stamp answers that use it |
| BTP | `jenis_btp` · `bentuk_sediaan` (`101` cair/pasta ·`102` serbuk ·`103` bahan penolong ·`104` gas ·`105` padat) · `jenis_produk_btp` (`301` tunggal ·`302` campuran ·`303` perisa ·`304` bahan penolong) | resolve labels via dictionary |
| Kemasan | `kemasan_id` | ERBA: `1` kaca ·`2` plastik ·`3` kertas ·`4` komposit ·`5` logam ·`6` lainnya ·`7` ganda. ERLA: `31` kaca ·`32` plastik ·`33` kertas/karton ·`34` karton laminat ·`35` kaleng ·`36` aluminium foil ·`37` komposit ·`38` ganda ·`39` lainnya. Never reuse one system's code on the other. Finer detail: `SUB_KEMASAN_ID` |
| Peruntukan | `peruntukan` | `0201` peruntukan khusus · `0000` umum |
| Pemrosesan | `pemrosesan` | `301` organik · `302` GMO · `304` iradiasi |
| Klasifikasi pangan | `klasifikasi_id` | `301` makanan · `302` minuman · `305` berklaim · `310` diet · `311` bayi & anak · `312` ibu hamil/menyusui |

**Jenis permohonan on NIE counts:** standard "Jumlah Izin Edar …" metrics add
`jenis_permohonan IN ('301','305')` on ERBA and `IN ('301','304','305')` on ERLA. A free-form
"berapa NIE terbit …" without that framing counts ALL jenis_permohonan. The two readings differ
materially — state which one the answer uses, or clarify (`predikat.md` RC-2).

**Fixed column bindings — never substitute:**
- berklaim → `klasifikasi_id='305'`, never the `klaim` column
- organik → `pemrosesan='301'`, never `klasifikasi_id='309'`

## 4b. Dictionary category router — exact `kategori` strings

Query `data_dictionary WHERE kategori = '<exact string>'` (mind `sumber`). Never ILIKE on
`deskripsi` when the category is known. The 21 categories:

| Concept family | `kategori` (exact string) | Filter column |
|---|---|---|
| Workflow status | `STATUS` | `status` (§2) |
| Risiko / dokumen | `KATEGORI_DOKUMEN` / `JENIS_DOKUMEN` | `kategori_dokumen` / `jenis_dokumen` (§3) |
| Negara asal | `NEGARA_PABRIK dan NEGARA_PRODUSEN` | `negara_pabrik`, `negara_produsen` |
| Daerah / wilayah | `DAERAH_TRADER, DAERAH_PABRIK, DAERAH_PRODUSEN, PROVINSI_ID, KOTAKAB_ID` | `daerah_trader`, `daerah_pabrik`, `daerah_produsen`, `provinsi_id`, `kotakab_id` — probe one sample row for the code format before filtering |
| Skala industri | `SKALA_INDUSTRI dan SKALA_INDUSTRI_ID` | `m_trader_rba.skala_industri_id`: `1` mikro ·`2` kecil ·`3` menengah ·`4` besar |
| Status usaha | `STATUS_USAHA` | `status_usaha` on product tables (`31` produsen · `33` importir) counts PRODUCTS; booleans `is_status_industri_produsen`/`_importir` on `m_trader_rba` count COMPANIES (a trader can be both) — pick by the asked entity and say which |
| Penolakan komitmen | `JENIS_PENOLAKAN_KOMITMEN` | `jenis_penolakan_komitmen` (ERBA-only, codes 1–10). Values can be pipe-combined (`'1|3'`): match with `string_to_array(col,'|') @> ARRAY['<kode>']`, never plain equality |
| Bidang usaha | `KODE_KBLI` | KBLI columns on trader tables |
| Kemasan / sub-kemasan | `KEMASAN_ID` / `SUB_KEMASAN_ID` | `kemasan_id` / sub-kemasan (§4) |
| BTP | `JENIS_BTP` / `BENTUK_SEDIAAN` / `JENIS_PRODUK_BTP` | matching `t_btp_*` columns (§4) |
| Istilah/akronim | `AKRONIM` | label lookup only |
| Others | `JENIS_PERMOHONAN` · `STATUS_KOMITMEN` · `STATUS_PRODUK` · `KLASIFIKASI_ID` · `PERUNTUKAN` · `PEMROSESAN` | §4 |

`JENIS_PANGAN` / `KATEGORI_PANGAN` are not dictionary categories → §5.

## 4c. Identifier & attribute patterns

- `nomor` prefix: `MD %` dalam negeri · `ML %` impor · `ER…` internal application id (no
  MD/ML issued yet). Probe one sample row for the exact spacing before filtering.
- Missing-data questions: `kategori_dokumen` NULL/empty is a small data-quality artifact —
  use it only when the question is explicitly about missing data; the business concept
  "belum dikategorikan" is `jenis_dokumen='000'` (§3).
- "Masih berlaku" = valid status AND (`tanggal_exp` > today OR `tanggal_exp` empty).
  "Dicabut" ≠ "kadaluarsa": status and expiry are independent dimensions — a revoked NIE can
  still be inside its validity window.
- Expiry slices: `tanggal_exp` (both product tables), range filter with ERBA cast rules
  (`predikat.md` §9). Date-column choice (aju vs bayar vs terbit): `predikat.md` §2.
- Product name / brand: `nama ILIKE` / `merk ILIKE` — free text, no code; state the exact
  pattern used in the answer.

---

## 5. Product segments (`jenis_pangan` / `kategori_pangan`)

| Segment | ERBA | ERLA |
|---|---|---|
| AMDK | `jenis_pangan IN ('1401','1402')` | `jenis_pangan IN ('651','652','655')` |
| Garam beryodium | `kategori_pangan = '120101000001'` (never `jenis_pangan='1204'`) | `kategori_pangan = '12010103'` |
| Formula bayi (strict) | `jenis_pangan IN ('1301','1302')` | `jenis_pangan IN ('604','622','624')` |

- "Formula bayi" ≠ "produk bayi & anak" (broad) — the broad concept spans many more codes; ask
  which the user means.
- Segments not listed here: probe `nama_kategori` (`business_glossary.md`); if multiple
  plausible code families return, ask the user.
- For sensitive answers on a segment (pencabutan, pembatalan): spot-check `nama`/`merk` of the
  matched rows and report any rows that do not belong to the segment.
- Breakdown by kategori pangan: group on the 2-digit prefix `LEFT(kategori_pangan, 2)`
  (e.g. `07` bakeri, `08` daging, `13` PKGK).
