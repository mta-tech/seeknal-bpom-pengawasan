Peta database — daftar tabel, kunci join, topologi UNION, dan perbedaan ERBA vs ERLA

Domain: **Registrasi Pangan** saja. Pengawasan (pemeriksaan/pengujian/sampling/balai) **tidak
tersambung** — katakan jujur, jangan pernah mengarang tabel.

## Tabel

| Tabel | Cakupan | Tipe | Catatan |
|---|---|---|---|
| `t_produk_3_erba` | Sep 2022 → kini | **SEMUA TEXT — wajib cast** | risiko `kategori_dokumen` · komitmen `status_komitmen` |
| `t_produk_3_rilis_erla` | 2012 → kini | TIMESTAMP/BIGINT | risiko `jenis_dokumen` (kode berbeda) · tanpa komitmen · **hanya keadaan final** |
| `t_btp_3_erba` | Jun 2022 → kini | **CAMPURAN — bukan semua TEXT** | tanggal & `trader_id` sudah native |
| `t_btp_3_erla` | Des 2017 → kini | native | masih menerima baris; tidak berhenti di 2024 |
| `m_trader_rba` / `m_trader_rla` | master perusahaan | campuran | kolom skala: `skala_industri_id` vs `skala_industri` (namanya berbeda) |
| `data_dictionary` | — | — | kode→label, 21 kategori persis (`kategori` + `sumber`) |

**Tipe itu per TABEL, bukan per sistem.** "ERBA semua TEXT" berlaku untuk `t_produk_3_erba` dan
tidak untuk yang lain — `t_btp_3_erba` berbagi sistem tapi tidak berbagi tipe. Cast yang dibawa
menyeberang **menggagalkan query** dan menghabiskan satu-satunya retry (`00-menghitung.md` §4).

## Struktur kolom & asimetri sistem

**`t_produk_3_rilis_erla` adalah subset murni `t_produk_3_erba`**: 94 kolom beririsan, **0** kolom
hanya-ERLA, dan hanya **6** kolom hanya-ERBA —
`ecolabel` · `jenis_penolakan_komitmen` · `kode_kbli` · `sni_sukarela` · `status_komitmen` ·
`sub_kemasan_id`.

Konsekuensinya: setiap pertanyaan yang bertumpu pada salah satu dari enam kolom itu **single-system
secara struktural**, bukan pilihan lingkup. Sebut sistemnya; jangan menyajikannya sebagai angka
nasional.

## Join — tidak ada foreign key, jadi harus diketahui, bukan ditebak

Database ini **tanpa foreign key dan tanpa indeks** pada dua tabel besar — setiap query adalah
pemindaian penuh, sehingga **jumlah query** adalah biaya utamanya, bukan kerumitannya.

- produk/BTP `.trader_id` → **LEFT JOIN** `m_trader_*` (ada yatim; INNER JOIN membuang data).
- Hitung perusahaan dari `t.trader_id`, **tidak pernah** `m.trader_id` (LEFT JOIN menghasilkan NULL).
- Kode → `data_dictionary` lewat `kategori` + `kode` persis (+ `sumber`).
- Identitas: `nomor` = NIE · `produk_id` = permohonan · `trader_id` = perusahaan.
- Tidak ada view `mv_*` gabungan — cakupan gabungan selalu UNION manual.

## Topologi UNION

| Maksud | Tabel |
|---|---|
| NIE / produk pangan olahan (gabungan) | `t_produk_3_erba` ∪ `t_produk_3_rilis_erla` |
| BTP (gabungan) | `t_btp_3_erba` ∪ `t_btp_3_erla` |
| Total termasuk BTP (**hanya bila pengguna eksplisit meminta**) | keempatnya |

"Pangan olahan" = tabel produk saja. WHERE ditulis terpisah per sisi — set status, set
jenis_permohonan, cast, dan filter akun uji semuanya berbeda (`00-menghitung.md` §5).

> **Pengecualian forecast:** topologi ini untuk query analis umum saja. **Forecast ERBA-only** —
> jangan pernah meng-UNION ERLA ke deret `run_forecast` (`forecast_guide.md`). Jangan pula query
> tabel `forecast_permohonan` yang sudah basi; hitung lewat `run_forecast`.

**Bentuk multi-dimensi:** dimensi bersilang ("per tahun DAN daerah") = SATU query,
`GROUP BY date_trunc('year', tanggal), daerah_pabrik`. Aspek yang saling bebas = satu query
masing-masing, disintesis di jawaban. Jangan meniru pengelompokan 2D dengan query 1D berulang.

## Rute

- Kolom yang ada di satu sistem saja, atau kolom yang tidak diatur halaman mana pun →
  `95-dimensi-lain.md` (prosedur penemuan dimensi).
- Menyentuh tabel yang belum di-query turn ini → `describe_table` sebelum menulis cast.
