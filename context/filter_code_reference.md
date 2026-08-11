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
| Same FAMILY as an anchor, code not listed ("kemasan kertas ERLA", "BTP perisa") | read ALL rows of that exact category: `SELECT kode, deskripsi FROM data_dictionary WHERE kategori = '<exact>'` — categories are small |
| User term is a LABEL, not a code ("dari China", "risiko rendah") | scoped ILIKE is CORRECT here: lock the category first, then `deskripsi ILIKE '%label%'` INSIDE it. Only unscoped/cross-category ILIKE is forbidden |
| Free product segment (roti, susu, kopi, …) | `nama_kategori` discovery (§5) — fuzzy territory by design |
| More than one plausible column/code family | ask the user — never pick silently |

**Code values collide across categories** (`301`–`305` mean unrelated things in
KATEGORI_DOKUMEN, KLASIFIKASI_ID, JENIS_PERMOHONAN, STATUS_PRODUK): the COLUMN determines the
meaning — never pick a column because its code value happens to match.

**Close the code set — finding ONE code is not the end of resolution.**

Resolution feels finished the moment a code matches the user's word. It is not. A business
concept is a *set* of codes far more often than it is a single one, and the set is not visible
from the code you happened to land on. Resolution ends only when this question has an answer:
*is there another code in this category that also belongs to the concept being asked about?*

The failure this prevents is the quietest one in the whole system. A filter with one code out of
three still runs, still returns a plausible number, still charts and exports cleanly. Nothing
signals that two thirds of the population never entered the query. The only defence is to close
the set deliberately, before the SQL is written.

Three triggers, all readable from the data itself:

1. **The chosen code's `deskripsi` is not unique in its category.** The dictionary gives several
   distinct codes the same wording — `Pendaftar - Draft` sits on both `0910` and `0912`;
   `Pendaftar - Perlu Data Tambahan` sits on five codes at once. A label lookup returns rows that
   look like duplicates of one another and are not: each carries its own population. When the
   description repeats, take **every** code that shares it.
2. **The asked concept is wider than any single description.** "Disetujui", "perubahan",
   "logam atau kaleng", "dicabut atau dihapus" — none of these is the wording of one dictionary
   row. They name a business idea the catalogue splits across members. Read the full category
   and take every member of that idea.
3. **The question spans both systems.** ERBA and ERLA do not always cut a concept at the same
   place: one may hold a single code where the other holds two. Translation between them can be
   **1:many**, never assume 1:1 (§4 closure table).

**Closure is bounded by the asked concept, never by string similarity.** Widening is as wrong as
narrowing, and it is the mistake this rule can cause if applied mechanically. "Ditolak Sistem"
(`0908`, `0911`, `0918`) and "Ditolak petugas" (`0902`, `0905`, `0913`) share the word *ditolak*
and are different populations; merging them because the strings look alike produces a number
nobody asked for. The bucket lists in §2 and the closure table in §4 draw those boundaries — use
them as the edge of the set, not the keyword.

**Source priority — which wins when two paths disagree.**

Where this file already hands over a complete code set — the §2 pipeline buckets and the §4
closure table — that set **beats** anything a dictionary listing returns. This is not a matter of
convenience; the dictionary is structurally unable to give coverage:

- its descriptions repeat across codes, so a listing cannot tell you where a concept ends;
- its ERLA codes are stored **unpadded** while the data stores four characters, so a listing can
  return codes that match nothing at all (§4b);
- its `sumber` column does not reliably say which system actually uses a code (§4d).

The dictionary is the authority on what a code **means**. This file is the authority on which
codes a concept **covers**. Verifying a set against the dictionary is good practice; letting that
verification *shrink* a set that was already correct is the failure to avoid.

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
| Verifikator 1 | `0402, 0403, 0405, 0406, 0407, 0417` |
| Verifikator 2 | `0500, 0502, 0504` (use exactly these; dictionary rows `0501, 0503` hold no ERBA rows) |
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
  states only. BTP pipeline: query BOTH `t_btp_3_erba` AND `t_btp_3_erla` — unlike the ERLA
  product table, the ERLA BTP table does carry live pipeline states.
- **The BTP tables use a smaller status set than the product table** — do not copy a stage's
  code list across without checking. `t_btp_3_erba` has no `0009`; `t_btp_3_erla` has no `0099`
  and carries `0299` (an ERLA-namespace code, §4b); of the Verifikator 2 trio only `0502`
  appears on either BTP table.
- "Permohonan"/"produk" in a pipeline question is ambiguous about BTP: present both figures
  (produk-only and produk+BTP, each labeled with its source tables), or state which scope is used
  and why. The gap is stage-dependent: small on the large registrant-side stages, wider elsewhere.
- **Keep every code of a stage, even the empty ones.** Several listed codes currently hold no
  ERBA rows — `0402`, `0406` (Verifikator 1), `0601`, `0666` (Direktur), `0700` (Deputi),
  `0905` (Ditolak lainnya). Leaving them in the filter costs nothing and survives them filling
  up later, but the ANSWER must not present an empty code as a contributing stage: say which
  codes actually carried the rows.
- A `NOT IN` bucket silently absorbs rows no stage claims: rare codes `000X, 0417, 0900, 0909,
  0916`, and — the largest of them — rows whose `status` is **four spaces** (`TRIM(status)=''`,
  which `status <> ''` does not catch). Mention this absorption when presenting a `NOT IN` total.
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
| Status produk | `status_produk` | `301` produsen sendiri · `302` impor · `304` makloon · `306` Single MD Induk · `307` Single MD Anak. Catalogued ERBA-only but **ERLA populates it too**, and ERLA additionally carries `303` and `305`, which no dictionary row describes |
| Jenis permohonan | `jenis_permohonan` | `301` baru · `302` mayor · `303` minor · `304` daftar ulang · `305` baru notifikasi |
| Status komitmen | `status_komitmen` (MR scope `kategori_dokumen='303'`) | codes, ROUND normalization, Case A/B → `predikat.md`. **Canonical "disetujui" = `4`+`7` combined**, but the answer ALWAYS shows the labelled split (`predikat.md` §12): `4` Komitmen Disetujui (murni) · `7` Komitmen Disetujui Dengan Catatan · gabungan = labelled sum. Code `8` (Validasi Pembatalan) is transient toward `5` — date-stamp answers that use it |
| BTP | `jenis_btp` · `bentuk_sediaan` (`101` cair/pasta ·`102` serbuk ·`103` bahan penolong ·`104` gas ·`105` padat) · `jenis_produk_btp` (`301` tunggal ·`302` campuran ·`303` perisa ·`304` bahan penolong) | resolve labels via dictionary |
| Kemasan | `kemasan_id` | ERBA: `1` kaca ·`2` plastik ·`3` kertas ·`4` komposit ·`5` logam ·`6` lainnya ·`7` ganda. ERLA: `31` kaca ·`32` plastik ·`33` kertas/karton ·`34` karton laminat ·`35` kaleng ·`36` aluminium foil ·`37` komposit ·`38` ganda ·`39` lainnya. Never reuse one system's code on the other. Finer detail: `SUB_KEMASAN_ID` |
| Peruntukan | `peruntukan` | `0201` peruntukan khusus · `0000` umum. Both systems also hold undocumented non-umum codes (`0103`/`0104`/`0105`/`0106`, ERLA also `010101`) — see the tie-break below |
| Pemrosesan | `pemrosesan` | `300` tanpa proses tertentu · `301` organik · `302` GMO · `304` iradiasi. `300` covers ~99,6% of all rows, so a `pemrosesan` breakdown is one dominant bucket plus slivers — say so rather than presenting it as an informative split |
| Klasifikasi pangan | `klasifikasi_id` | **13 codes, not 6**: `3` Deputi 3 (Pangan) · `301` makanan · `302` minuman · `303` BTP · `304` minuman beralkohol · `305` berklaim · `306` herbal · `307` iradiasi · `308` rekayasa genetika · `309` organik *(decoy — see bindings)* · `310` diet · `311` bayi & anak · `312` ibu hamil/menyusui |

**Residual buckets are not classes — and they are large.**

Some codes in a family do not name a business class at all. They name the organisational unit that
owns the record, or the absence of any particular treatment: `klasifikasi_id='3'` is
"Deputi 3 (Pangan)", the directorate; `pemrosesan='300'` is "Tanpa Proses Tertentu", the default.
Both carry a large share of their table, and `klasifikasi_id='3'` is still growing — it is not a
legacy remnant that can be waved away.

This creates a two-sided trap, and both sides have to be avoided at once:

- **Never answer a class question with the residual code.** "Berapa produk makanan" is
  `klasifikasi_id='301'` and nothing else. Folding the directorate bucket into Makanan inflates
  the answer with records that were never classified as food at all.
- **Never present the classes as exhausting the population either.** Makanan + Minuman is not the
  whole of registered ERBA, because a large block sits unclassified in `3`. An answer that offers
  two numbers and implies they add up to everything is misleading even when both numbers are right.

The resolution is to **count the residual share in the same query that produces the breakdown**,
then state it as a labelled row. That keeps the answer honest about coverage while keeping every
figure something you actually ran this turn.

The general form: when a code holds a large share of its family and its description names an
organisational unit or a default rather than a business class, treat it as the residual bucket.
Not an answer, not invisible — a labelled remainder.

**Peruntukan khusus — two defensible readings, one headline.**

The catalogue defines only two `peruntukan` values, `0000` (umum) and `0201` (khusus). The data
holds more: several undocumented non-umum codes that are neither. So "produk dengan peruntukan
khusus" has two honest readings — the catalogued code, or everything that is not umum.

Lead with **`peruntukan='0201'`**: it is the code the business defines, and it is what the
canonical answer expects. When the question asks for *all* special-purpose products rather than
for that code specifically, attach "everything except `0000`" as a labelled companion figure and
name the undocumented codes it brings in. What is never acceptable is silently choosing the wider
reading — the number moves and nothing in the answer explains why.

**Jenis permohonan:** add a JP filter ONLY when the question explicitly says **"baru"** /
"baru notifikasi" (ERBA `IN ('301','303','305')` — exclude 302 mayor; ERLA `IN ('301','303','304','305')`). "Terbit" is NOT a
trigger — "NIE yang terbit di 2025" counts ALL jenis_permohonan. Any other count — including
"jumlah izin edar …" — takes NO jenis_permohonan filter (`predikat.md` §4 is the rule).

**Fixed column bindings — never substitute** (the wrong side returns a plausible-but-wrong number, not an error):
- berklaim → `klasifikasi_id='305'`, never the `klaim` column (free text).
- organik → `pemrosesan='301'`, never `klasifikasi_id='309'`.
- peruntukan khusus → `peruntukan='0201'`, never `'0000'` (umum — a far larger population).
- impor → `status_produk='302'`; `302` in another column is unrelated (`jenis_permohonan`=mayor, `kategori_dokumen`=Menengah Tinggi) — pick the column by meaning (§0). (`status_usaha='33'` returns the same population here, so it is a naming preference, not a trap.)
- makloon / kontrak → `status_produk='304'`, never the workflow `status` column.
- perusahaan / ranking name → `m_trader_*.nama` via `trader_id`, never a `nama_perusahaan` column on the product table.

### Closure table — concepts that need MORE THAN ONE code

A business concept is often wider than any single `deskripsi`. Use this table directly; do not
re-derive the set from the dictionary (§0 "which source wins").

| Concept | ERBA | ERLA | If one code is dropped |
|---|---|---|---|
| logam / kaleng (rigid) | `5` | `35` | — |
| logam incl. aluminium foil | `5` | `35`,`36` | most of the ERLA side is lost |
| komposit atau laminat | `4` | `34`,`37` | most of the ERLA side is lost |
| komitmen "disetujui" | `4`,`7` | — | most of the population is lost |
| perubahan / revisi | `302`,`303` | `302`,`303` | roughly half is lost |
| permohonan "baru" (JP) | `301`,`303`,`305` | `301`,`303`,`304`,`305` | a visible share is lost |
| risiko Tinggi | `301`,`304` | — | small, but still state the split |
| dicabut atau dihapus | `0009`,`0000` | `0009`,`0000` | small, but still state the split |

**Why a concept needs several codes — two structural reasons, both verified on live data.**

*Asymmetric granularity.* The two systems did not cut the world at the same joints. ERBA `5` is
"Logam", one code for every metal packaging; ERLA splits the same idea into `35` "Kaleng" and
`36` "Aluminium Foil". ERBA `4` is "Komposit/laminat", one code; ERLA splits it into `34`
"Karton Laminat" and `37` "Komposit". Translating a concept across systems is therefore a
**1:many** mapping in both directions, and treating it as 1:1 drops whichever sibling the wording
did not happen to name.

*Duplicate descriptions.* Inside one system, the same `deskripsi` sits on several codes. A keyword
match against descriptions finds the first and has no way to know siblings exist — they read as
duplicates of a row already taken.

**The worked example.** "Kemasan logam atau kaleng", resolved by matching
`deskripsi ILIKE '%kaleng%'` inside `KEMASAN_ID`: the pattern hits ERLA `35` "Kaleng" and returns
a clean, plausible answer. It never sees `36` "Aluminium Foil", because that description contains
neither *logam* nor *kaleng* — yet foil is metal packaging and belongs to the asked concept. The
query runs, the number is wrong, nothing complains.

**For a concept not in the table above:** read the FULL category —
`SELECT kode, deskripsi FROM data_dictionary WHERE kategori='<family>'` — and include every code
whose description is a member of what was asked. Categories are small, so this costs one lookup,
not a search. Never stop at the first single-keyword ILIKE hit. This applies to `status` exactly
as much as it applies to kemasan, BTP, klasifikasi, pemrosesan and status produk.

⚠️ **The severity words in the table are calibration for you, never figures for the answer.**

They exist so you can rank omissions when the budget is tight: dropping a sibling in the kemasan
family costs far more than dropping one in the risk family, and that ordering should shape where
you spend a verification query. They are **not** measurements of today's data — the database moves
and these words do not move with it.

So they must never be restated to the user as a quantity. Every number in an answer comes from SQL
run this turn (`predikat.md` §12-B, Gate 5). If a share genuinely belongs in the answer — the
residual bucket's weight, the gap between two readings — compute it in the same query that
produced the headline, and quote that.

## 4b. Dictionary category router — exact `kategori` strings

Query `data_dictionary WHERE kategori = '<exact string>'` (mind `sumber`). Never ILIKE on
`deskripsi` when the category is known. The 21 categories:

| Concept family | `kategori` (exact string) | Filter column |
|---|---|---|
| Workflow status | `STATUS` | `status` (§2). **`sumber='ERLA'` rows are stored unpadded** (`999`, `99`, `9`, `0`) while the data holds 4 characters (`0999`, `0099`, `0009`, `0000`) — pad with `LPAD(kode,4,'0')` before filtering, or the query returns nothing |
| Risiko / dokumen | `KATEGORI_DOKUMEN` / `JENIS_DOKUMEN` | `kategori_dokumen` / `jenis_dokumen` (§3) |
| Negara asal | `NEGARA_PABRIK dan NEGARA_PRODUSEN` | `negara_pabrik`, `negara_produsen` |
| Daerah / wilayah | `DAERAH_TRADER, DAERAH_PABRIK, DAERAH_PRODUSEN, PROVINSI_ID, KOTAKAB_ID` | `daerah_trader`, `daerah_pabrik`, `daerah_produsen`, `kotakab_id` — dictionary stores the **dotted** kabupaten/kota form (`31.75`), the columns store it **undotted** (`3175`): join on `REPLACE(kode,'.','')`. The category holds kabupaten/kota only, so **`provinsi_id` has no rows of its own** and part of `kotakab_id` falls outside it — report unmapped regions rather than dropping them |
| Skala industri | `SKALA_INDUSTRI dan SKALA_INDUSTRI_ID` | `m_trader_rba.skala_industri_id` / `m_trader_rla.skala_industri` (names differ): `1` mikro ·`2` kecil ·`3` menengah ·`4` besar; UMKM = 1+2+3. Empty means Importir — ERBA stores `' '`, ERLA `''`/NULL: always `COALESCE(NULLIF(TRIM(col::text),''),'Importir')`, never GROUP BY the raw column |
| Status usaha | `STATUS_USAHA` | `status_usaha` on product tables (`31` produsen · `33` importir) counts PRODUCTS; booleans `is_status_industri_produsen`/`_importir` on `m_trader_rba` count COMPANIES (a trader can be both) — pick by the asked entity and say which |
| Penolakan komitmen | `JENIS_PENOLAKAN_KOMITMEN` | `jenis_penolakan_komitmen` (ERBA-only, codes 1–10). Values can be pipe-combined (`'1\|3'`): match with `string_to_array(col,'\|') @> ARRAY['<kode>']`, never plain equality |
| Bidang usaha | `KODE_KBLI` | `kode_kbli` on **`t_produk_3_erba` / `t_btp_3_erba`** — the trader tables have no such column and a query against them errors. It therefore counts PRODUCTS by business field; to count companies, aggregate to `trader_id` and say so |
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
  **This is ERBA-only for a structural reason:** `m_trader_rla` has no such columns, so there is
  no ERLA figure and no combined one. State that limit instead of implying national coverage.

## 4c. Identifier & attribute patterns

- `nomor` prefix: `MD ` dalam negeri · `ML ` impor — **one space after the prefix**, so
  `LIKE 'MD %'` is the pattern; `ER…` is the internal application id of a submission with no
  licence yet. A handful of rows deviate (no space, or an embedded carriage return); say so if
  the count is presented as exhaustive. `BPOM RI MD` is the printed-label form and appears
  nowhere in the database.
- Missing-data questions: `kategori_dokumen` is **NULL, never an empty string** — test with
  `IS NULL`. In ERBA that is a small data-quality artifact; in ERLA it covers a large part of the
  table and is a migration artifact, not a business state. Either way the business concept
  "belum dikategorikan" is `jenis_dokumen='000'` (§3).
- "Masih berlaku" = valid status AND (`tanggal_exp` > today OR `tanggal_exp` empty).
  "Dicabut" ≠ "kadaluarsa": status and expiry are independent dimensions — a revoked NIE can
  still be inside its validity window.
- Expiry slices: `tanggal_exp` (both product tables), range filter with ERBA cast rules
  (`predikat.md` §9). Date-column choice (aju vs bayar vs terbit): `predikat.md` §2.
- Product name / brand: `nama ILIKE` / `merk ILIKE` — free text, no code; state the exact
  pattern used in the answer.

## 4d. Dictionary gaps & cross-system code divergence (verified 2026-08-04)

All five produce **silently wrong answers**, not errors, and all are general — the examples are
illustrations, not the whole set. The common shape: the dictionary describes an idealised catalogue
and the tables hold something adjacent to it, so a query built from the catalogue alone can miss,
misname, or wrongly zero out real data.

**(1) A shared `sumber` does not guarantee a shared code range.**

`JENIS_BTP` is catalogued as "ERLA dan ERBA" with codes 13–52. Yet `t_btp_3_erla.jenis_btp` does
not use that range at all — it uses 777–805, a set of values no dictionary category describes.
Running `jenis_btp='47'` (Pewarna) against the ERLA table therefore returns **0 rows**. Read
naively that says "ERLA has no colouring agents", which is false; what it actually says is
"this is the wrong code system for this table". The mirror case also exists: `kategori_dokumen`
is catalogued ERBA-only, yet ERLA data populates it with 301–304.

→ **Before reporting 0 or "tidak ada" for one system, list that system's own values**:
`SELECT DISTINCT <col>, COUNT(*) FROM <that table> GROUP BY 1`. A zero produced by a cross-system
code is evidence of a mapping gap, never of absence.

→ Where a range carries **no labels anywhere** — 777–805 is the clear case — the concept simply
cannot be filtered on that side. Answer for the system that can be mapped, and name the limit
explicitly. Reporting the unmappable side as zero turns a gap in the catalogue into a claim about
the business.

**(2) A code absent from its own `sumber` block may still be catalogued under the other one.**

Before declaring a code undocumented, look it up in the ERLA block **with padding**:
`LPAD(kode,4,'0')` (§4b). Several `status` values that ERBA data carries — `0500`, `0504`, `0417`,
`0900`, `0909`, `0916`, and `0299` in `t_btp_3_erla` — resolve there and do have official
descriptions. They only look orphaned because the ERBA block does not list them and the ERLA block
stores them without leading zeros.

The consequence is worth stating plainly: **the `status` column mixes both namespaces.** "Not in
the ERBA block" means "check the ERLA block", not "unknown code". Labelling such a row as an
anomaly when the catalogue can name it is a loss of information the answer did not need to take.

**(3) Codes genuinely absent from the dictionary** (re-check; the set moves): `jenis_dokumen` 304 ·
`peruntukan` 0103/0104/0105/0106 (ERBA), 010101/0103/0105/0106 (ERLA) · `pemrosesan` 303, 403
(ERBA), 303 (ERLA) · `jenis_btp` 21/22/24/25 (ERBA) · `bentuk_sediaan` 214 (ERBA) ·
`status_produk` 303, 305 (ERLA) · `status` `000X` and the four-space value (ERBA, §2).
The dictionary also collides internally — `PEMROSESAN` 304 carries two descriptions.
→ When a filter would drop such rows (`NOT IN` buckets, "lainnya"), say so rather than presenting
the total as complete.

**(4) Listed codes that hold no rows.** `status_komitmen` 2 · `status` ERBA
0402/0406/0601/0666/0700/0905 · a third of `JENIS_BTP`. Keep them in the filter so it survives
them filling up, but never present an empty code as a contributing member of a breakdown.

**(5) Families with no dictionary category at all:** `JENIS_PANGAN`, `KATEGORI_PANGAN` — resolve
via §5 and say the mapping is empirical, not dictionary-backed.

---

## 5. Product segments (`jenis_pangan` / `kategori_pangan`)

| Segment | ERBA | ERLA |
|---|---|---|
| AMDK | `jenis_pangan IN ('1401','1402')` | `jenis_pangan IN ('651','652','655')` |
| Garam beryodium | `jenis_pangan = '1204'` — the PARENT code, covers every garam variant | `kategori_pangan = '12010103'`; ERLA has no `1204` namespace, so `nama_kategori ILIKE '%garam%'` is the fallback (wider — it also catches bumbu) |
| Formula bayi (strict) | `jenis_pangan IN ('1301','1302')` | `jenis_pangan IN ('604','622','624')` |

Two structural rules govern this whole family, and both are easy to violate without noticing.

**No shared namespace between systems.** `jenis_pangan` has **zero overlap** between ERBA and
ERLA — not "mostly different", not "different in places": no value appears on both sides. The
ranges differ, the lengths differ, and the anchors in the table above are three examples of a
property that holds for every segment, including the two hundred-plus that are not listed here.

The practical consequence: a code carried from one system to the other **always** returns zero,
and that zero means "wrong namespace", never "this segment does not exist here". Resolve each side
independently, every time, even when the segment feels obvious. `kategori_pangan` is comparable
across systems only on its 2-digit prefix; below that the two systems use different lengths and the
values are not the same thing.

**Parent code before child code.** `kategori_pangan` refines `jenis_pangan` — it is the child level
of the same hierarchy, not a parallel column. `jenis_pangan='1204'` covers the whole garam family;
`kategori_pangan='120101000001'` is one variant inside it and silently excludes the siblings that
share the parent.

Start at the parent. Descend to a child only when the question names that specific variant. This is
the segment-level form of the closure rule in §0: picking a child when the question asked about the
family is the same failure as picking one code out of a set.

- "Formula bayi" ≠ "produk bayi & anak" (broad) — the broad concept spans many more codes; ask
  which the user means.
- **Segments not listed here (kopi, sirup, teh, …) — the resolution order.** Try the coded columns
  first, `jenis_pangan` / `kategori_pangan`: a code filter is cheap, exact, and reusable. Only when
  the concept is genuinely free-text, probe **`nama_kategori`** (or `nama` / `merk` — never
  `nama_produk`, which does not exist) with ILIKE. Probe it on **both systems**: the column is
  filled in both, and ERLA holds the richer catalogue, so treating it as an ERBA-only column
  discards the better half of the evidence.
- **Never answer with a yearly trend because the segment would not resolve.** This is the specific
  failure worth naming: the question asks about a product segment, the segment does not fall out of
  the first probe, and the turn drifts into "here is the registration trend 2020–2026" — a real
  answer to a question nobody asked. A trend is only ever the answer when the question asked for a
  trend. If the segment will not resolve, resolve it another way or ask; do not substitute a
  different metric (`predikat.md` §7).
- ILIKE is for discovery, not repeated counting: run it once (scoped, one combined query, with a
  `LIMIT`) to find the code/category, then count on that code. If it returns nothing, answer
  honestly — don't keep permuting keywords.
- **Close the free-text set too — §0 applies here as much as to codes.** One ILIKE usually matches
  several `nama_kategori` values, and they are not interchangeable. "Kopi" spans a dozen of them —
  Kopi Bubuk, Kopi Instan, Minuman Kopi, Biji Kopi, Minuman Serbuk Kopi, and more — while "kopi
  instan" is one. Answering "berapa produk kopi" with the Kopi Instan rows alone is the free-text
  version of taking one code out of a set. Judge the width from the question, **list the matched
  values in the answer** so the reader can see the scope you used, and ask when the width is
  genuinely ambiguous rather than guessing.
- **Free text carries two hazards a code filter does not, and both belong in the answer.**
  First, spelling varies inside the same column — `Garam Konsumsi Beriodium` and
  `Garam Konsumsi Ber**y**odium` are separate values of the same idea, so a pattern anchored on one
  spelling silently loses the other. Second, a broad pattern leaks: `%garam%` also catches
  "Bumbu Penguat Rasa dan Garam", which is a seasoning, not salt. Name the exact pattern used, and
  spot-check the matched rows before presenting the figure as definitive — a coded column, where
  one exists, is always the tighter instrument.
- A question that names a segment AND another attribute ("kopi dari Indonesia", "sirup impor")
  resolves each part on its own column and ANDs them in one WHERE — segment via the probe above,
  origin via `negara_pabrik` (`ID` = Indonesia/domestik, other = impor). Never drop one part.
- For sensitive answers on a segment (pencabutan, pembatalan): spot-check `nama`/`merk` of the
  matched rows and report any rows that do not belong to the segment.
- Breakdown by kategori pangan: group on the 2-digit prefix `LEFT(kategori_pangan, 2)`
  (e.g. `07` bakeri, `08` daging, `13` PKGK). Deeper than two digits the codes are not comparable
  across systems — ERBA and ERLA use different lengths.
