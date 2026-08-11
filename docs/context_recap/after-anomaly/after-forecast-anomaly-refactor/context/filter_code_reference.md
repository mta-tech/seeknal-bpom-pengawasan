#VERIFIED CODE ANCHORS (NOT THE FULL CATALOG) - STATUS, RISK, SEGMENT, PRODUCT; ABSENT CODE => READ FULL CATEGORY#

Codes listed here are VERIFIED anchors — use them directly, no re-probing. Codes NOT listed here
still exist: `data_dictionary` is the broadest catalog available, this file is only the shortcut.
On conflict, this file wins ONLY where a row explicitly says so; everywhere else the dictionary
wins. **But the dictionary is NOT complete and its `sumber` column is not authoritative** — live
data provably holds codes absent from it (§4d). Report such codes, never hide them, and never
treat "absent from the dictionary" as "absent from the data".

This file stores structure only — columns, codes, scope rules. Every number in an answer comes
from SQL executed this turn. Query only these tables: `t_produk_3_erba`,
`t_produk_3_rilis_erla`, `t_btp_3_erba`, `t_btp_3_erla`, `m_trader_rba`, `m_trader_rla`,
`data_dictionary` (no `mv_*` views exist in this warehouse).

## 0. Choosing the resolution path

| Case | Path |
|---|---|
| Concept exactly matches an anchor below | use the anchor directly |
| Same FAMILY as an anchor, code not listed ("BTP pengawet", "kemasan kertas ERLA") | read ALL rows of that exact category: `SELECT kode, deskripsi FROM data_dictionary WHERE kategori = '<exact>'` — categories are small |
| User term is a LABEL, not a code ("dari China", "risiko rendah") | scoped ILIKE is CORRECT here: lock the category first, then `deskripsi ILIKE '%label%'` INSIDE it. Only unscoped/cross-category ILIKE is forbidden |
| Free product segment (roti, susu, kopi, …) | `nama_kategori` discovery (§5) — fuzzy territory by design |
| More than one plausible column/code family | ask the user — never pick silently |

**Code values collide across categories** (`301`–`305` mean unrelated things in
KATEGORI_DOKUMEN, KLASIFIKASI_ID, JENIS_PERMOHONAN, STATUS_PRODUK): the COLUMN determines the
meaning — never pick a column because its code value happens to match.

**Status set follows the question's verb:** "aktif / masih berlaku / distribusi saat ini" →
`status = '0999'` (per system). "terdaftar / total / pernah terbit" → ERBA
`IN ('0999','0906','9999')`, ERLA `IN ('0099','0999','0906','9999')` (`predikat.md` §3).

---

## 1. Counting entity

| Question subject | Count |
|---|---|
| NIE / izin edar / "produk terdaftar" | `COUNT(DISTINCT nomor)`, exclude empty `nomor` |
| permohonan / pengajuan / **persetujuan produk** (approved applications) | `COUNT(DISTINCT produk_id)` |
| perusahaan | `COUNT(DISTINCT trader_id)` — within ONE system only |

- Never `COUNT(*)` on the product/BTP tables (`predikat.md` §1).
- One `nomor` spans multiple `produk_id` rows — swapping the entity changes the answer up to
  several-fold with identical filters.
- Combined-system company counts: `trader_id` is NOT comparable between ERBA and ERLA — dedupe
  by company NAME; on a name collision keep the ERBA record.
- Name-dedupe exists ONLY for that cross-system merged headline. Within one system the company
  entity is ALWAYS `trader_id` — never dedupe by name inside a system (names collide across
  branches) — and a combined answer still shows the per-system `trader_id` counts as labelled
  rows next to the merged figure.
- Company population default = the trader MASTER (`m_trader_rba`/`m_trader_rla`): "berapa
  perusahaan skala X / produsen / importir" counts registered traders WITHOUT joining product
  tables. Join to products ONLY when the question says "yang punya produk/NIE" — and when both
  readings are live, show both as labelled numbers (§12: "terdaftar: X · punya produk: Y").
  The MASTER count MUST appear in the answer whenever the question is about companies by
  attribute — even when a join reading leads.

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
- **"Sedang diproses (petugas)" — canonical headline** for "sedang diproses / antrian"
  questions: the active officer queue = Evaluator + Verifikator 1/2 + Direktur/Deputi/Kepala
  Badan + Data Tambahan. **"Belum selesai (total)"** = everything not in a terminal state
  (`NOT IN` Terbit/Perubahan/Sudah Diubah + Dibatalkan/Dicabut/Tidak Berlaku) — this wider
  reading includes registrant-side Draft/Bayar states. Lead with the canonical headline and
  ALWAYS attach the other reading as **ONE labelled companion number produced by its own
  `NOT IN` query** — print the single total explicitly (a part breakdown may follow, but
  never replaces the single number). The two readings differ by tens of thousands.
- "Nyangkut / bottleneck / paling banyak menumpuk" = rank the STAGES of this table with ONE
  `GROUP BY` over the stage buckets and name the largest — never a single hand-picked code.

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
- **Presentation** (`predikat.md` §12): a question touching the risk FAMILY reports each class
  as its own labelled number — "Menengah Tinggi (`302`): X · Menengah Rendah (`303`): Y" — a
  merged figure only as a labelled sum, never as the sole unlabelled answer. Never widen one
  asked class to its neighbours silently ("produk MR" = `303` only).
- **Naming**: MR/MT are official BPOM abbreviations for Menengah Rendah/Menengah Tinggi, not
  free English glosses ("Medium Risk" alone is imprecise) — general rule + more examples in
  `predikat.md` §12-B.

---

## 4. Exact codes per domain

| Concept | Column | Codes |
|---|---|---|
| Status produk (ERBA) | `status_produk` | `301` produsen sendiri · `302` impor · `304` makloon · `306` Single MD Induk · `307` Single MD Anak |
| Jenis permohonan | `jenis_permohonan` | `301` baru · `302` mayor · `303` minor · `304` daftar ulang · `305` baru notifikasi |
| Status komitmen | `status_komitmen` (MR scope `kategori_dokumen='303'`) | codes, ROUND normalization, Case A/B → `predikat.md`. **Canonical "disetujui" = `4`+`7` combined**, but the answer ALWAYS shows the labelled split (`predikat.md` §12): `4` Komitmen Disetujui (murni) · `7` Komitmen Disetujui Dengan Catatan · gabungan = labelled sum. Code `8` (Validasi Pembatalan) is transient toward `5` — date-stamp answers that use it |
| BTP | `jenis_btp` · `bentuk_sediaan` (`101` cair/pasta ·`102` serbuk ·`103` bahan penolong ·`104` gas ·`105` padat) · `jenis_produk_btp` (`301` tunggal ·`302` campuran ·`303` perisa ·`304` bahan penolong) | resolve labels via dictionary |
| Kemasan | `kemasan_id` | ERBA: `1` kaca ·`2` plastik ·`3` kertas ·`4` komposit ·`5` logam ·`6` lainnya ·`7` ganda. ERLA: `31` kaca ·`32` plastik ·`33` kertas/karton ·`34` karton laminat ·`35` kaleng ·`36` aluminium foil ·`37` komposit ·`38` ganda ·`39` lainnya. Never reuse one system's code on the other. Finer detail: `SUB_KEMASAN_ID` |
| Peruntukan | `peruntukan` | `0201` peruntukan khusus · `0000` umum |
| Pemrosesan | `pemrosesan` | `301` organik · `302` GMO · `304` iradiasi |
| Klasifikasi pangan | `klasifikasi_id` | `301` makanan · `302` minuman · `305` berklaim · `310` diet · `311` bayi & anak · `312` ibu hamil/menyusui |

**Jenis permohonan:** add a JP filter ONLY when the question explicitly says **"baru"** /
"baru notifikasi" (ERBA `IN ('301','303','305')` — exclude 302 mayor; ERLA `IN ('301','303','304','305')`). "Terbit" is NOT a
trigger — "NIE yang terbit di 2025" counts ALL jenis_permohonan. Any other count — including
"jumlah izin edar …" — takes NO jenis_permohonan filter (`predikat.md` RC-2 is the rule).

**Fixed column bindings — never substitute:**
- berklaim → `klasifikasi_id='305'`, never the `klaim` column
- organik → `pemrosesan='301'`, never `klasifikasi_id='309'`

**Compound/OR questions on ANY code family in this section** (kemasan, BTP, klasifikasi,
pemrosesan, status produk — not just one column): the two systems don't always split a concept
the same way — one system may have a single code where the other has several (e.g. kemasan:
ERBA `5` Logam ↔ ERLA `35` Kaleng + `36` Aluminium Foil). When the question names a concept
broader than one code, or is phrased as "X atau Y", resolve it by reading the FULL category —
`SELECT kode, deskripsi FROM data_dictionary WHERE kategori='<family>'` — and include every code
whose description is a member of the asked concept. Never stop at the first ILIKE hit on a
single keyword: matching only `deskripsi ILIKE '%kaleng%'` for "logam atau kaleng" finds one
code and silently drops its sibling, undercounting materially (verified >2x on the kemasan
family). The same risk applies to any other family in the table above with more than one code
per side.

## 4b. Dictionary category router — exact `kategori` strings

Query `data_dictionary WHERE kategori = '<exact string>'` (mind `sumber`). Never ILIKE on
`deskripsi` when the category is known. The 21 categories:

| Concept family | `kategori` (exact string) | Filter column |
|---|---|---|
| Workflow status | `STATUS` | `status` (§2) |
| Risiko / dokumen | `KATEGORI_DOKUMEN` / `JENIS_DOKUMEN` | `kategori_dokumen` / `jenis_dokumen` (§3) |
| Negara asal | `NEGARA_PABRIK dan NEGARA_PRODUSEN` | `negara_pabrik`, `negara_produsen` |
| Daerah / wilayah | `DAERAH_TRADER, DAERAH_PABRIK, DAERAH_PRODUSEN, PROVINSI_ID, KOTAKAB_ID` | `daerah_trader`, `daerah_pabrik`, `daerah_produsen`, `provinsi_id`, `kotakab_id` — probe one sample row for the code format before filtering |
| Skala industri | `SKALA_INDUSTRI dan SKALA_INDUSTRI_ID` | `m_trader_rba.skala_industri_id` / `m_trader_rla.skala_industri` (names differ): `1` mikro ·`2` kecil ·`3` menengah ·`4` besar; UMKM = 1+2+3. Empty means Importir — ERBA stores `' '`, ERLA `''`/NULL: always `COALESCE(NULLIF(TRIM(col::text),''),'Importir')`, never GROUP BY the raw column |
| Status usaha | `STATUS_USAHA` | `status_usaha` on product tables (`31` produsen · `33` importir) counts PRODUCTS; booleans `is_status_industri_produsen`/`_importir` on `m_trader_rba` count COMPANIES (a trader can be both) — pick by the asked entity and say which |
| Penolakan komitmen | `JENIS_PENOLAKAN_KOMITMEN` | `jenis_penolakan_komitmen` (ERBA-only, codes 1–10). Values can be pipe-combined (`'1|3'`): match with `string_to_array(col,'|') @> ARRAY['<kode>']`, never plain equality |
| Bidang usaha | `KODE_KBLI` | KBLI columns on trader tables |
| Kemasan / sub-kemasan | `KEMASAN_ID` / `SUB_KEMASAN_ID` | `kemasan_id` / sub-kemasan (§4) |
| BTP | `JENIS_BTP` / `BENTUK_SEDIAAN` / `JENIS_PRODUK_BTP` | matching `t_btp_*` columns (§4) |
| Istilah/akronim | `AKRONIM` | label lookup only |
| Others | `JENIS_PERMOHONAN` · `STATUS_KOMITMEN` · `STATUS_PRODUK` · `KLASIFIKASI_ID` · `PERUNTUKAN` · `PEMROSESAN` | §4 |

`JENIS_PANGAN` / `KATEGORI_PANGAN` are not dictionary categories → §5.

- **"Berapa produsen / importir (perusahaan)" — canonical**: `m_trader_rba` flags
  `is_status_industri_produsen='1'` / `is_status_industri_importir='1'` (TEXT `'1'`/`'0'`,
  not boolean), entity `trader_id`, population = the whole master. `status_usaha` `31`/`33`
  counts PRODUCTS — use it only when the question is about products, never as the company
  headline. A company can be both — say so when both flags are reported.

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

## 4d. Dictionary gaps & cross-system code divergence (verified 2026-07-23)

Two failure modes here produce **silently wrong answers**, not errors. Both are general — they
apply to any coded column, not just the ones listed as examples.

**(1) A `sumber` of "ERLA dan ERBA" does NOT guarantee the two systems share a code range.**
The clearest verified case: `JENIS_BTP` is catalogued as "ERLA dan ERBA" with codes 13–52, yet
ERLA's `t_btp_3_erla.jenis_btp` actually uses an entirely separate range **777–805 that appears
in NO dictionary category at all**. Filtering ERLA with an ERBA code (e.g. `jenis_btp='47'`)
therefore returns **0 rows** — which reads as "ERLA has none of these" but really means "wrong
code system for this table." Conversely `kategori_dokumen` is catalogued ERBA-only, yet ERLA data
populates it (301–304). **Rule: before reporting 0 / "tidak ada" for one system, list that
system's own values — `SELECT DISTINCT <col>, COUNT(*) FROM <that table> GROUP BY 1` — and only
then conclude.** A zero from a cross-system code is evidence of a mapping gap, not of absence.

**(2) Codes present in data but missing from the dictionary.** Verified examples (re-check, the
set grows): `jenis_dokumen` **304** (both systems; ~1.4k ERBA / ~2.5k ERLA rows) · `peruntukan`
**0103/0104/0105/0106** (ERBA) and **010101/0103/0105/0106** (ERLA) · `pemrosesan` **303, 403**
(ERBA) and **303** (ERLA) · `jenis_btp` **21/22/24/25** (ERBA — code 21 alone is ~1.5k NIE) ·
`bentuk_sediaan` **214** (ERBA) · `status` **000X/0201/0500/0504/0900/0909/0916** (ERBA, already
flagged in §2). The dictionary also holds internal collisions — `PEMROSESAN` kode `304` carries
two different descriptions ("Pangan Very Low Risk" and "Iradiasi"). When a filter would silently
drop such rows (especially `NOT IN` buckets and "lainnya" categories), say so in the answer
rather than presenting a total as complete.

**(3) Families with no dictionary category at all:** `JENIS_PANGAN` and `KATEGORI_PANGAN` — resolve
via `nama_kategori` discovery (§5) and state in the answer that the mapping is empirical, not
dictionary-backed.

---

## 5. Product segments (`jenis_pangan` / `kategori_pangan`)

| Segment | ERBA | ERLA |
|---|---|---|
| AMDK | `jenis_pangan IN ('1401','1402')` | `jenis_pangan IN ('651','652','655')` |
| Garam beryodium | `kategori_pangan = '120101000001'` (never `jenis_pangan='1204'`) | `kategori_pangan = '12010103'` |
| Formula bayi (strict) | `jenis_pangan IN ('1301','1302')` | `jenis_pangan IN ('604','622','624')` |

- "Formula bayi" ≠ "produk bayi & anak" (broad) — the broad concept spans many more codes; ask
  which the user means.
- Segments not listed here: probe `nama_kategori` with ILIKE; if multiple
  plausible code families return, ask the user.
- For sensitive answers on a segment (pencabutan, pembatalan): spot-check `nama`/`merk` of the
  matched rows and report any rows that do not belong to the segment.
- Breakdown by kategori pangan: group on the 2-digit prefix `LEFT(kategori_pangan, 2)`
  (e.g. `07` bakeri, `08` daging, `13` PKGK).
