# 15 — Ekspektasi Informasi User vs Ketersediaan Data & Boundary Sistem

> Sumber: 340 pertanyaan real user KAI (filter db `pengawasan`) + analisis schema `public` database `pengawasan`.
> Snapshot: `sync = 2026-08-12 23:23`.
> Tujuan: memberi agent peta **apa yang user harapkan** vs **apa yang benar-benar tersedia**, sehingga jawaban jujur untuk data yang tidak ada.

## Matriks Ekspektasi vs Ketersediaan

| # | Ekspektasi user (dari KAI) | Status | Sumber data / SQL | Catatan |
|---|---|---|---|---|
| 1 | Jumlah pengawasan (total, per UPT, per tahun) | ✅ ADA | `mv_pengawasan` COUNT | Entity: baris vs event (lihat `16`) |
| 2 | Hasil MK/TMK per komoditi per periode | ✅ ADA | `kesimpulan_penilaian_*` × `tgl_start` | Filter `<> 'Null'` |
| 3 | Trend pengawasan per komoditi per tahun | ✅ ADA | `tgl_start` × `komoditi` GROUP BY | 2026 partial |
| 4 | Verdict per UPT (balai) | ✅ ADA | `nama_balai` × verdict | 45% pertanyaan |
| 5 | Reversal pusat vs balai | ✅ ADA | `kesimpulan_penilaian_pusat` vs `_balai` | Template #3 |
| 6 | Ketidaksesuaian / klausul pelanggaran | ✅ ADA (pangan only) | `mv_pengawasan_ketidaksesuaian` | 100% PRODUK PANGAN |
| 7 | Media iklan per komoditi | ✅ ADA | `media_iklan` | Nilai kode: CETAK, MEDIA_LUARRUANG, ELEKTRONIK, dll |
| 8 | Nama produk & NIE per event | ✅ ADA | `nama_produk`, `nie` | Multi-produk per event |
| 9 | Timeline sampling → kabalai → direktur | ⚠️ PARTIAL | `mv_pengawasan_timeline` | Milestone ada; **rule deadline eksternal** |
| 10 | Pemenuhan timeline (SLA compliance %) | ⚠️ PARTIAL | timeline + business rule | Rule "9 bulan" **belum di DB** |
| 11 | Target vs realisasi per UPT | ⚠️ PARTIAL | `coverage_balai` (target) vs main | Target hanya 2024; join via UPPER() |
| 12 | UPT yang tidak melaporkan | ⚠️ PARTIAL | anti-join coverage → main | Perlu definisi "tidak melaporkan" (periode) |
| 13 | Sarana produksi / produsen | ❌ TIDAK ADA | — | `pendaftar` = registrant, BUKAN produsen |
| 14 | Jenis pangan / kategori pangan | ❌ TIDAK ADA (domain lain) | — | Ada di database registrasi `neo` |
| 15 | Provinsi | ❌ TIDAK ADA | — | Hanya `kabupaten_kota` |
| 16 | Cek BPOM / CEKB POM | ❌ EKSTERNAL | — | Sistem web eksternal |
| 17 | SIAPik | ❌ EKSTERNAL | — | Sistem lain BPOM |
| 18 | BKO (bahan kimia obat) | ❌ TIDAK ADA | — | Tak ada kolom |
| 19 | Detail sampling (laboratorium, parameter) | ⚠️ PARTIAL | "sampling" = workflow stage, bukan kolom | Beda DB (pengujian) |
| 20 | Data perorangan petugas | ⚠️ PARTIAL | kolom pejabat | Bukan user focus |

## Boundary Sistem / Database

### Database `pengawasan` — MILIK KITA (7 tabel, schema public)

- `mv_pengawasan` (183.968 baris / 172.180 event)
- `mv_pengawasan_ketidaksesuaian`
- `mv_pengawasan_timeline`
- `mv_pengawasan_log`
- `mv_pengawasan_agg`
- `mv_pengawasan_coverage` alias `coverage_balai`
- `mv_pengawasan_target`

### Database LAIN (bukan pengawasan) — JANGAN di-join, honest

| Database | Isi | Relevan jika user tanya |
|---|---|---|
| `neo` | Registrasi produk (`t_produk_3_*`) | jenis pangan, kategori pangan, produsen |
| `pemeriksaan` | Pemeriksaan sarana | sarana produksi (parsial) |
| `pengujian` | Pengujian sampling | parameter lab, hasil uji |
| `penandaan` | Penandaan | label detail |
| DB lain (external web) | Cek BPOM, SIAPik | NIE lookup, siapik ID |

**Aturan**: agent boleh **menyebutkan** bahwa data ada di database lain, TAPI tidak boleh mengarang nilai. Jika user insist, arahkan ke sistem terkait.

## Template Honest Response (frasa → jawaban jujur)

Dipakai ketika user bertanya data yang ❌ tidak tersedia.

### 1. Sarana produksi / produsen
> "Informasi **sarana produksi / produsen** tidak tersedia di database pengawasan. Kolom `pendaftar` berisi **pemohon registrasi** (registrant), bukan pabrik/produsen. Data produsen dapat dicari melalui registrasi produk di database `neo` atau sistem Cek BPOM."

### 2. Jenis / kategori pangan
> "Kolom **jenis pangan / kategori pangan** tidak ada di database pengawasan. Data pengawasan hanya memuat `komoditi = 'PRODUK PANGAN'` sebagai label kelompok. Detail jenis/kategori pangan berada di database registrasi `neo` (`t_produk_3_*`)."

### 3. Provinsi
> "Database pengawasan tidak memiliki kolom **provinsi**. Informasi wilayah yang tersedia hanya `kabupaten_kota` pada tabel `coverage_balai`."

### 4. Cek BPOM
> "**Cek BPOM** adalah sistem eksternal yang tidak terkoneksi ke database pengawasan. Saya tidak bisa mengambil NIE/sarana produksi/nama produk dari sistem tersebut. Data produk yang tersedia di pengawasan: `nama_produk`, `nie`."

### 5. SIAPik
> "**SIAPik** adalah sistem eksternal (Sistem Informasi Pengawasan Internal BPOM) yang tidak terhubung ke database ini."

### 6. BKO
> "Kolom **BKO (bahan kimia obat)** tidak tersedia di database pengawasan."

### 7. Klausul pelanggaran untuk non-pangan
> "Data **klausul pelanggaran / ketidaksesuaian** hanya tersedia untuk `komoditi = 'PRODUK PANGAN'`. Komoditi lain (OBAT, KOSMETIKA, dll.) tidak memiliki baris ketidaksesuaian di database pengawasan."

### 8. Perbandingan "9 bulan" — rule tidak ada
> "Rule **'batas 9 bulan berikutnya'** adalah business rule organisasi yang **belum terdokumentasi sebagai metadata di database pengawasan**. Database hanya menyimpan tanggal milestone. Untuk menjawab ketepatan waktu, saya butuh konfirmasi: deadline dihitung dari tanggal apa (tgl_start / tgl_end / tgl_sampling)?"

## Status Verdict — Apa yang Bisa Dijawab Pasti

| Pertanyaan | Bisa dijawab? | Notes |
|---|---|---|
| Berapa MK/TMK per komoditi | ✅ | Filter `<> 'Null'` |
| Perbedaan pusat vs balai | ✅ | Hitung via 3 kolom verdict |
| Severity TMK (kritikal/mayor/minor) | ✅ | Nilai verdict memuat severity |
| Kenapa ada 'Null' verdict | ⚠️ | Belum dinilai / dihentikan. Arahkan ke workflow log |
| Verdict untuk komoditi Cluster B/C | ⚠️ | Aturan akhir per komoditi (`09`), 4 komoditi butuh `verdict_*` kolom bukan `akhir` |

## Prioritas Jawaban (bila data tersedia parsial)

1. **Jawab dengan data yang ADA** + sebutkan populasi yang dipakai (mis. "dari 183.968 baris, ...")
2. **Sebutkan yang TIDAK tersedia** + sistem alternatif
3. **Tanya klarifikasi** jika butuh business rule eksternal (9 bulan, definisi "tidak melaporkan")
4. **JANGAN fabrikasi** nilai dari database lain

## Ringkasan Korelasi dengan File Dokumentasi Lain

| File | Korelasi dengan ekspektasi user |
|---|---|
| `04` timeline | Milestone untuk ekspektasi #9, #10, #20 |
| `05` agg | Basis agregasi utk ekspektasi #3, #4 |
| `06` ketidaksesuaian | Ekspektasi #6, #7 template |
| `08` komoditi | Ekspektasi #2, #3, #4 |
| `09` verdict/reversal | Ekspektasi #5, ekspektasi #2 |
| `12` honest gaps | Sumber utama boundary |
| `14` vocabulary | Frasa user → kolom (dasar honest response) |
| `16` SQL pairs | SQL untuk tiap ekspektasi yang tersedia |