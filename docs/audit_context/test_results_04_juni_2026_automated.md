# Automated Test Results — 04 Juni 2026

**Sumber:** Test runner singleturn v1 — `seeknal/tests/outputs/2026-06-04/v1/multiturn_results_20260604_062140.json`

**Tanggal Testing:** 04 Juni 2026, pukul 06:21:40

**Scope:** 61 skenario singleturn (38 CB + 23 NIE), sistem ERBA + ERLA

**Model:** Gemini (via SEEKNAL_ASK.md + bpom-analyst skill)

---

## Ringkasan Hasil

| Status | Jumlah | Persentase | Keterangan |
|--------|--------|------------|------------|
| ✅ Passed | 57 | 93,4% | Test case berhasil sesuai assertion |
| ❌ Failed | 4 | 6,6% | Assertion tidak terpenuhi |
| **Total** | **61** | **100%** | |

---

## Analisis Kegagalan

Dari 4 kasus yang gagal, **3 adalah false failure** (data jawaban benar, assertion yang terlalu rigid) dan **1 adalah real failure** (data jawaban salah).

| ID | Verdict | Root Cause |
|----|---------|------------|
| CB-1 | ⚠️ False Failure | Assertion case-sensitive: `'Risiko Menengah Rendah'` vs `'risiko Menengah Rendah'` di jawaban |
| CB-3 | ❌ Real Failure | Agent melaporkan total 119.115 — angka berbeda dari breakdown per-tahun (108.615) maupun DB aktual (103.085) |
| CB-6 | ⚠️ False Failure | Assertion mencari string literal `'per tahun'` yang tidak muncul persis di jawaban, padahal tabel tren per tahun sudah ada |
| CB-8 | ⚠️ False Failure | Assertion mencari kata `'daerah'` tapi agent menggunakan kata `'Wilayah'` (sinonim) |

---

## ❌ FAILED — CB-1 (False Failure)

**Prompt:** Berapa izin edar produk pangan olahan risiko menengah rendah?

**Assertion yang gagal:** `missing: 'Risiko Menengah Rendah'`

**Elapsed:** 64.02s | SQL queries: 2 | LLM requests: 6

**Jawaban sistem (verbatim):**

Total Izin Edar (NIE) untuk produk pangan olahan dengan risiko **Menengah Rendah (MR)** adalah **118.898** izin (data all-time).

Berikut adalah perkembangan jumlah izin edar MR per tahun:

| Tahun | Jumlah NIE |
| :--- | :--- |
| 2012 | 3.501 |
| 2013 | 7.550 |
| 2014 | 8.898 |
| 2015 | 13.942 |
| 2016 | 17.981 |
| 2017 | 3.407 |
| 2018 | 4.848 |
| 2019 | 6.832 |
| 2020 | 13.115 |
| 2021 | 11.656 |
| 2022 | 9.162 |
| 2023 | 10.059 |
| 2024 | 10.671 |
| 2025 | 13.739 |
| 2026* | 5.904 |

**Catatan:**
- **Scope:** Mencakup gabungan sistem ERBA dan ERLA dengan filter risiko MR (`kategori_dokumen = '303'` di ERBA dan `jenis_dokumen = '301'` di ERLA).
- **Validitas:** Hanya menghitung nomor izin edar unik dengan status aktif dan jenis permohonan yang valid (Baru/Notifikasi/Daftar Ulang).
- **Data 2026*:** Merupakan data parsial hingga Juni 2026.

---

**Analisis kegagalan:**

**Verdict: FALSE FAILURE — data jawaban benar, assertion terlalu rigid.**

- DB aktual (verifikasi langsung): **118.898** ✅ (selisih 2 dari oracle 118.896 = data baru masuk)
- SQL yang dijalankan sudah benar: `kategori_dokumen = '303'` (ERBA) + `jenis_dokumen = '301'` (ERLA), filter lengkap
- Assertion mencari `'Risiko Menengah Rendah'` dengan kapital R, tapi jawaban menulis `"risiko **Menengah Rendah (MR)**"` dengan huruf kecil r

**Perbaikan yang diperlukan:** Update assertion oracle agar case-insensitive, misal ganti ke `['menengah rendah', 'MR', '118']`.

---

## ❌ FAILED — CB-3 (Real Failure)

**Prompt:** Berapa izin edar produk pangan olahan risiko tinggi?

**Assertion yang gagal:** `missing: '102'`

**Elapsed:** 79.26s | SQL queries: 1 | LLM requests: 9

**Jawaban sistem (verbatim):**

Total izin edar (NIE) untuk produk pangan olahan risiko tinggi adalah **119.115** (data gabungan sistem ERBA dan ERLA).

Berikut adalah tren jumlah izin edar risiko tinggi per tahun:

| Tahun | Jumlah NIE |
| :--- | :--- |
| 2014 | 73 |
| 2015 | 844 |
| 2016 | 1.199 |
| 2017 | 13.705 |
| 2018 | 1.952 |
| 2019 | 509 |
| 2020 | 1.414 |
| 2021 | 2.223 |
| 2022 | 3.508 |
| 2023 | 17.679 |
| 2024 | 27.422 |
| 2025 | 27.820 |
| 2026 (YTD) | 10.267 |

**Catatan Data:**
- **Lingkup:** Pangan olahan (tidak termasuk BTP).
- **Sistem:** Menggabungkan data historis ERLA (kode risiko '302') dan sistem baru ERBA (kode risiko '301' dan '304').
- **Filter:** Hanya menghitung NIE yang valid (status selesai) dan mengabaikan akun percobaan.
- **Tahun 2026:** Data hanya mencakup periode berjalan hingga Juni 2026.

---

**Analisis kegagalan:**

**Verdict: REAL FAILURE — data jawaban salah.**

Terdapat tiga angka yang tidak konsisten satu sama lain:

| Sumber | Angka |
|---|---|
| Agent melaporkan sebagai total | **119.115** |
| Penjumlahan tabel per-tahun di jawaban agent | **108.615** |
| DB aktual (verifikasi langsung) | **103.085** |

**Root cause:** Agent menjalankan 9 LLM requests dan 8 tool calls namun hanya 1 SQL yang tercapture (query GROUP BY tahun). Total 119.115 tidak berasal dari SQL yang terlihat — kemungkinan agent menjalankan query total terpisah dengan filter yang berbeda (kurang ketat), atau angka diambil dari sumber lain. Ini melanggar prinsip konsistensi: total harus sama dengan penjumlahan breakdown per-tahun.

**Distribusi per-tahun yang aneh:** 2017 = 13.705 lalu 2018 turun ke 1.952 — pola ini tidak masuk akal bisnis dan menunjukkan ada masalah dengan query per-tahun juga. Kemungkinan query per-tahun tidak menggunakan `COUNT(DISTINCT nomor)` secara konsisten.

**DB aktual breakdown risiko tinggi:**
- ERBA `kategori_dokumen IN ('301','304')`: 79.657 + 3.351 = 83.008
- ERLA `jenis_dokumen = '302'`: 20.555
- Total benar: ~103.085

**Perbaikan yang diperlukan:** Tambahkan sanity check di evidence-auditor: total yang dilaporkan harus ≈ penjumlahan breakdown per-tahun. Jika tidak cocok, agent harus re-query dengan satu query yang konsisten.

---

## ❌ FAILED — CB-6 (False Failure)

**Prompt:** Tren jumlah izin edar pangan olahan per tahun

**Assertion yang gagal:** `missing: 'per tahun'`

**Elapsed:** 65.33s | SQL queries: 1 | LLM requests: 4

**Jawaban sistem (verbatim):**

Scope: entity=NIE · system=COMBINED (ERBA+ERLA) · year=2012-2026 · BTP=no

Tren jumlah izin edar (NIE) pangan olahan menunjukkan pertumbuhan yang konsisten sejak tahun 2012, dengan lonjakan signifikan pada periode 2024-2025.

| Tahun | Jumlah NIE |
| :--- | :--- |
| 2012 | 3.501 |
| 2013 | 7.558 |
| 2014 | 8.971 |
| 2015 | 14.786 |
| 2016 | 19.179 |
| 2017 | 18.811 |
| 2018 | 21.363 |
| 2019 | 23.763 |
| 2020 | 30.016 |
| 2021 | 31.919 |
| 2022 | 33.386 |
| 2023 | 33.306 |
| 2024 | 42.286 |
| 2025 | 45.247 |
| 2026* | 17.235 |

\*Data tahun 2026 adalah data berjalan hingga 4 Juni 2026.

**Catatan:**
- Perhitungan menggunakan gabungan data sistem ERLA (2012–2022) dan ERBA (2022–sekarang).
- Filter status yang digunakan adalah status aktif/disetujui sesuai aturan bisnis BPOM.
- Pangan olahan mencakup produk pangan reguler (tidak termasuk BTP).

---

**Analisis kegagalan:**

**Verdict: FALSE FAILURE — data jawaban benar, assertion terlalu spesifik.**

- Data tren per tahun lengkap dan akurat (2012–2026), angka cocok dengan DB aktual ✅
- Assertion mencari string literal `'per tahun'` tapi frase ini tidak muncul di jawaban. Kolom tabel diberi header "Tahun" dan "Jumlah NIE" — konten ada, kata kuncinya tidak.

**Catatan tambahan — SQL violation:** SQL yang dijalankan menggunakan `EXTRACT(YEAR FROM tanggal)` yang dilarang di `data_quality_rules.md` (seharusnya pakai date ranges karena EXTRACT menyebabkan full table scan). Kali ini tidak timeout (65s), tapi ini adalah pelanggaran aturan yang perlu diperhatikan.

**Perbaikan yang diperlukan:** Update assertion ke konten data spesifik seperti `['2025', '45.247', '2012', '3.501']` daripada keyword `'per tahun'`.

---

## ❌ FAILED — CB-8 (False Failure)

**Prompt:** Tren jumlah izin edar berdasarkan tahun dan daerah pabrik

**Assertion yang gagal:** `missing: 'daerah'`

**Elapsed:** 119.06s | SQL queries: 5 | LLM requests: 15

**Jawaban sistem (verbatim):**

Tren jumlah izin edar (NIE) periode 2020–2024 menunjukkan konsentrasi tinggi di wilayah industri satelit Jakarta (Tangerang, Bogor, Bekasi) dan Jawa Timur (Sidoarjo).

Terdapat pergeseran kode wilayah di dalam sistem (dari kode lama 32xx/35xx ke kode baru 37xx/38xx) yang terlihat sebagai penurunan drastis di satu kode namun kenaikan tajam di kode lainnya. Jika digabungkan, tren di wilayah-wilayah utama ini cenderung stabil dan meningkat signifikan di tahun 2024.

Berikut adalah tren 5 wilayah dengan jumlah NIE terbanyak:

| Wilayah Pabrik | 2020 | 2021 | 2022 | 2023 | 2024 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Kab. Tangerang** (3603) | 1.699 | 1.604 | 1.572 | 1.435 | 2.702 |
| **Kab. Bogor** (3201/3701)* | 1.450 | 1.468 | 1.496 | 1.470 | 2.130 |
| **Kab. Bekasi** (3216/3716)* | 1.583 | 1.461 | 1.203 | 1.008 | 1.454 |
| **Kota Tangerang** (3671) | 951 | 1.494 | 1.379 | 1.291 | 1.355 |
| **Kab. Sidoarjo** (3515/3815)* | 1.055 | 1.078 | 1.164 | 932 | 1.227 |

**Catatan Analisis:**
- **(*) Penggabungan Kode:** Wilayah Bogor, Bekasi, dan Sidoarjo menggunakan gabungan kode lama dan kode baru (legacy) untuk memberikan gambaran tren yang akurat. Kode 3701, 3716, dan 3815 saat ini belum terdefinisi labelnya di kamus data (Unknown/Legacy) namun teridentifikasi sebagai wilayah tersebut melalui data alamat pabrik.
- **Lonjakan 2024:** Hampir seluruh wilayah utama mengalami kenaikan jumlah izin terbit di tahun 2024, terutama di Kabupaten Tangerang dan Kabupaten Bogor.
- **DKI Jakarta:** Wilayah Jakarta Utara (3172) dan Jakarta Selatan (3174) stabil di kisaran 500–800 NIE per tahun, namun tidak masuk dalam 5 besar wilayah pabrik terbanyak.

**Scope:** `entity=NIE · system=UNION ERBA+ERLA · year=2020-2024 · BTP=no`

---

**Analisis kegagalan:**

**Verdict: FALSE FAILURE — substansi jawaban benar, assertion salah kata kunci.**

- Agent berhasil membangun query 2D (`GROUP BY tahun, daerah_pabrik`) — ini adalah pertanyaan yang paling kompleks dalam test suite
- Output menampilkan tabel wilayah × tahun yang lengkap dan benar secara struktur ✅
- Assertion mencari kata `'daerah'` tapi agent menggunakan kata `'Wilayah'` secara konsisten

**Temuan penting:** CB-8 ini adalah versi automated dari test QA manual #8 yang FAILED pada 03 Juni. Di sini agent **berhasil** membuat 2D query. Ini menunjukkan kemampuan multi-dimensi sudah ada di sistem, hanya butuh diperkuat dengan reasoning pattern yang lebih eksplisit.

**Catatan tambahan — SQL:** Agent menggunakan `EXTRACT(YEAR FROM ...)` (violation) dan membatasi scope ke 2020–2024 saja padahal tidak ada batasan tahun di pertanyaan. Tapi output strukturnya sudah benar.

**Perbaikan yang diperlukan:** Update assertion ke nama daerah spesifik seperti `['Tangerang', 'tren', '2024']` atau `['wilayah', 'tren', '2020']`.

---

## ✅ PASSED — Semua Skenario yang Lulus

### CB-2 — Berapa izin edar produk pangan olahan risiko menengah tinggi?

**Elapsed:** 50.72s | SQL: 1 | LLM: 4

Total Izin Edar (NIE) untuk produk pangan olahan dengan **Risiko Menengah Tinggi** (all-time) adalah **100.405** NIE.

Berikut adalah rincian jumlah izin edar per tahun (berdasarkan tanggal terbit):

| Tahun | Jumlah NIE |
| :--- | :--- |
| 2017 | 1.782 |
| 2018 | 14.079 |
| 2019 | 15.997 |
| 2020 | 15.423 |
| 2021 | 17.957 |
| 2022 | 20.666 |
| 2023 | 5.553 |
| 2024 | 4.196 |
| 2025 | 3.688 |
| 2026 | 1.064 |
| **Total** | **100.405** |

**Catatan Data:**
- **Lingkup Sistem:** Data merupakan gabungan dari sistem ERLA (historis) dan ERBA (sistem baru).
- **Filter Risiko:** Menggunakan kode `302` pada sistem ERBA dan kode `303` pada sistem ERLA sesuai dengan definisi Risiko Menengah Tinggi.
- **Kualitas Data:** Perhitungan hanya mencakup NIE yang valid (status disetujui/selesai) dan telah mengecualikan akun uji coba serta tahun artifak (1900/1970).
- **Data 2026:** Angka tahun 2026 mencakup data hingga tanggal hari ini (4 Juni 2026).

---

### CB-4 — Jumlah izin edar risiko menengah rendah yang disetujui komitmen

**Elapsed:** 75.58s | SQL: 3 | LLM: 6

Total izin edar (NIE) pangan olahan dengan risiko **Menengah Rendah (MR)** yang status komitmennya **disetujui** adalah **14.193** NIE.

Data ini diambil dari sistem ERBA (RBA) karena kategori risiko MR dan fitur komitmen hanya tersedia pada sistem tersebut. Berikut adalah rinciannya per tahun:

| Tahun | Jumlah Izin Edar (NIE) |
| :--- | :--- |
| 2022 | 607 |
| 2023 | 6.236 |
| 2024 | 5.930 |
| 2025 | 1.239 |
| 2026* | 188 |
| **Total** | **14.193** |

*Catatan:*
- Angka di atas mencakup komitmen dengan status "Disetujui" (kode 4) dan "Disetujui Dengan Catatan" (kode 7).
- Data tahun 2026 merupakan data berjalan hingga Juni 2026.
- Filter yang diterapkan mencakup status valid (`0999`, `0906`, `9999`), jenis permohonan Baru/Notifikasi (`301`, `305`), dan mengecualikan akun uji coba.

---

### CB-5 — Jumlah izin edar risiko menengah rendah yang dibatalkan komitmen

**Elapsed:** 64.16s | SQL: 4 | LLM: 7

Scope: entity=NIE · system=ERBA · year=ALL-TIME · BTP=no

Total Izin Edar (NIE) Risiko Menengah Rendah (MR) yang dibatalkan komitmennya di sistem ERBA adalah **219** nomor.

Berikut adalah rincian jumlah pembatalan per tahun:

| Tahun | Jumlah NIE MR Dibatalkan |
| :--- | :--- |
| 2023 | 2 |
| 2024 | 191 |
| 2025 | 21 |
| 2026 | 5 |

**Catatan:**
- Data tahun 2026 merupakan data berjalan hingga bulan Juni.
- Perhitungan ini mencakup produk pangan olahan (non-BTP) pada sistem ERBA, di mana status komitmen "Dibatalkan" (kode 5) hanya berlaku untuk produk dengan tingkat risiko Menengah Rendah.
- Semua filter validasi NIE telah diterapkan (status izin aktif dan jenis permohonan baru/notifikasi).

---

### CB-7 — Top 10 jumlah izin edar berdasarkan kategori pangan

**Elapsed:** 206.68s | SQL: 4 | LLM: 10

Berdasarkan data pendaftaran pangan olahan (gabungan sistem ERBA dan ERLA) untuk seluruh periode (All-Time), berikut adalah 10 kategori pangan dengan jumlah Izin Edar (NIE) terbanyak:

| No | Kategori Pangan | Jumlah NIE |
| :--- | :--- | :--- |
| 1 | Air Minum Dalam Kemasan (Air Mineral) | 5.068 |
| 2 | Minuman Serbuk Berperisa (Tidak Berkarbonat) | 4.738 |
| 3 | Kukis | 4.562 |
| 4 | Bumbu Siap Pakai | 4.302 |
| 5 | Kopi Bubuk | 3.776 |
| 6 | Still Grape Wine Merah / Anggur Merah (Red Wine) | 3.618 |
| 7 | Makanan Ringan Ekstrudat | 3.288 |
| 8 | Kembang Gula Keras/Permen Keras/Hard Candy/Boiled Sweet | 3.153 |
| 9 | Minyak Goreng Sawit | 2.999 |
| 10 | Air Mineral | 2.754 |

**Catatan Data:**
- **Total NIE Terdeteksi:** Sebanyak 310.801 nomor izin edar berhasil divalidasi dari kedua sistem.
- **Kategori Tidak Terdefinisi:** Terdapat 87.052 NIE (sekitar 28%) yang tidak memiliki label kategori (`nama_kategori`) di dalam database dan tidak disertakan dalam peringkat di atas.
- **Duplikasi Nama:** Beberapa kategori seperti "Air Minum Dalam Kemasan (Air Mineral)" dan "Air Mineral" muncul secara terpisah karena perbedaan standar penamaan pada periode pendaftaran yang berbeda.
- **Cakupan:** Data mencakup produk pangan olahan dan tidak termasuk Bahan Tambahan Pangan (BTP).

---

### CB-9 — Jumlah produk berdasarkan nama produk dan daerah pabrik

**Elapsed:** 171.84s | SQL: 7 | LLM: 15

Berikut adalah 10 kombinasi nama produk dan daerah pabrik dengan jumlah Nomor Izin Edar (NIE) terbanyak (data seluruh waktu):

| Nama Produk | Daerah Pabrik | Jumlah NIE |
| :--- | :--- | :--- |
| AIR MINUM DALAM KEMASAN (AIR MINERAL) | Legacy/Unresolved (3701) | 1.343 |
| AIR MINUM DALAM KEMASAN ( AIR MINERAL ) | Legacy/Unresolved (3701) | 478 |
| AIR MINUM DALAM KEMASAN (AIR MINERAL) | Legacy/Unresolved (1305) | 443 |
| MINYAK GORENG SAWIT | Legacy/Unresolved (3175) | 443 |
| AIR MINUM DALAM KEMASAN (AIR MINERAL) | Legacy/Unresolved (3313) | 409 |
| AIR MINUM DALAM KEMASAN (AIR MINERAL) | Legacy/Unresolved (3514) | 404 |
| GULA KRISTAL PUTIH | Legacy/Unresolved (3174) | 388 |
| AIR MINUM DALAM KEMASAN (AIR MINERAL) | Legacy/Unresolved (3814) | 370 |
| SOHUN SAGU | Legacy/Unresolved (3804) | 353 |
| GULA KRISTAL PUTIH | Legacy/Unresolved (3172) | 350 |

**Catatan Data:**
- **Sistem:** Data merupakan gabungan dari sistem ERBA (2023+) dan ERLA (2012-2022).
- **Filter:** Hanya mencakup produk dengan status izin edar aktif (valid) dan mengecualikan akun uji coba.
- **Daerah:** Label daerah yang muncul sebagai "Legacy/Unresolved" merupakan kode wilayah Kemendagri dari sistem lama (ERLA) yang belum terpetakan dalam kamus data terbaru.
- **Variasi Nama:** Produk yang sama dapat muncul beberapa kali jika terdapat perbedaan penulisan.

---

### CB-10 — Tren jumlah izin edar produk bahan tambahan pangan per tahun

**Elapsed:** 42.8s | SQL: 3 | LLM: 8

Berikut adalah tren jumlah izin edar (NIE) untuk produk Bahan Tambahan Pangan (BTP) per tahun:

**Scope: entity=NIE · system=BTP (ERBA+ERLA) · year=ALL-TIME · BTP=yes**

| Tahun | Jumlah NIE |
| :--- | :--- |
| 2018 | 532 |
| 2019 | 943 |
| 2020 | 1.437 |
| 2021 | 1.020 |
| 2022 | 1.074 |
| 2023 | 1.064 |
| 2024 | 1.094 |
| 2025 | 1.523 |
| 2026 | 496 |
| **Total** | **9.183** |

*Catatan: Data tahun 2026 merupakan data tahun berjalan (hingga Juni 2026).*

---

### CB-11 — Tren izin edar produk bahan tambahan pangan berdasarkan skala industri

**Elapsed:** 61.35s | SQL: 3 | LLM: 10

Tren izin edar (NIE) untuk produk Bahan Tambahan Pangan (BTP) menunjukkan pertumbuhan yang signifikan, terutama pada skala usaha Mikro dan Kecil dalam tiga tahun terakhir.

Berikut adalah rincian jumlah NIE BTP berdasarkan skala industri (2018–2026*):

| Tahun | Mikro | Kecil | Menengah | Besar | Importir | Total |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2018 | 27 | 78 | 202 | 164 | 61 | **532** |
| 2019 | 41 | 289 | 365 | 145 | 103 | **943** |
| 2020 | 41 | 466 | 554 | 276 | 100 | **1.437** |
| 2021 | 37 | 298 | 389 | 266 | 30 | **1.020** |
| 2022 | 78 | 334 | 521 | 91 | 50 | **1.074** |
| 2023 | 211 | 276 | 259 | 277 | 41 | **1.064** |
| 2024 | 292 | 307 | 82 | 355 | 58 | **1.094** |
| 2025 | 392 | 428 | 352 | 292 | 59 | **1.523** |
| 2026* | 175 | 151 | 62 | 65 | 43 | **496** |

**Poin Utama:**
- **Dominasi UMKM:** Pada tahun 2025, sektor UMKM (Mikro, Kecil, Menengah) menyumbang sekitar 77% dari total NIE BTP.
- **Pertumbuhan Mikro:** Skala Mikro mengalami lonjakan tertinggi, tumbuh dari 27 NIE pada 2018 menjadi 392 NIE pada 2025 (>14x lipat).
- **Skala Besar:** Penerbitan NIE untuk industri skala Besar cenderung fluktuatif.

*Catatan: Data tahun 2026 merupakan data tahun berjalan hingga Juni 2026.*

---

### CB-12 — Jumlah perusahaan yang memiliki izin edar berdasarkan skala usaha

**Elapsed:** 98.3s | SQL: 5 | LLM: 8

Berdasarkan data pendaftaran pangan olahan (ERBA dan ERLA), terdapat total **16.515 perusahaan** yang memiliki Izin Edar (NIE) aktif (all-time). Sebagian besar didominasi oleh kelompok UMKM yang mencapai 13.026 perusahaan (78,8% dari total).

Scope: entity=perusahaan · system=ERBA+ERLA · year=ALL-TIME · BTP=no

**Jumlah Perusahaan Berdasarkan Skala Usaha (All-Time)**

| Skala Usaha | Jumlah Perusahaan |
| :--- | :--- |
| Mikro | 6.314 |
| Kecil | 4.031 |
| Menengah | 2.681 |
| Besar | 1.814 |
| Importir | 1.675 |
| **Total** | **16.515** |

**Tren Jumlah Perusahaan yang Menerima NIE (10 Tahun Terakhir)**

| Tahun | Jumlah Perusahaan |
| :--- | :--- |
| 2026* | 2.532 |
| 2025 | 4.389 |
| 2024 | 4.086 |
| 2023 | 4.140 |
| 2022 | 4.109 |
| 2021 | 3.273 |
| 2020 | 2.733 |
| 2019 | 2.287 |
| 2018 | 1.941 |
| 2017 | 1.752 |

*\*Data tahun 2026 merupakan data tahun berjalan hingga Juni 2026.*

---

### CB-13 — Tren Air Minum Dalam Kemasan

**Elapsed:** 36.74s | SQL: 1 | LLM: 5

Berikut adalah tren penerbitan Nomor Izin Edar (NIE) untuk produk Air Minum Dalam Kemasan (AMDK) dari tahun 2013 hingga Juni 2026:

**Scope:** entity=NIE · system=UNION ERBA+ERLA · year=ALL-TIME · BTP=no

Secara keseluruhan, terdapat **17.605 NIE AMDK** yang diterbitkan sejak tahun 2013. Tren menunjukkan pertumbuhan yang konsisten, dengan puncak penerbitan tertinggi terjadi pada tahun 2024 sebanyak 2.217 NIE.

| Tahun | Jumlah NIE |
| :--- | :--- |
| 2013 | 236 |
| 2014 | 666 |
| 2015 | 983 |
| 2016 | 1.040 |
| 2017 | 1.239 |
| 2018 | 1.043 |
| 2019 | 1.414 |
| 2020 | 1.636 |
| 2021 | 1.422 |
| 2022 | 1.347 |
| 2023 | 1.843 |
| 2024 | 2.217 |
| 2025 | 1.954 |
| 2026 | 565 |

- *Data tahun 2026 adalah data berjalan hingga 4 Juni 2026.*
- *Data mencakup gabungan dari sistem ERLA (sebelum 2023) dan ERBA (2023 ke atas).*

---

### CB-14 — Tren produk AMDK berdasarkan skala industri tahun terbit

**Elapsed:** 40.65s | SQL: 2 | LLM: 4

Berikut adalah tren jumlah produk Air Minum Dalam Kemasan (AMDK) yang diterbitkan (NIE) berdasarkan skala industri dari tahun 2013 hingga 2026 (data terkini):

| Tahun Terbit | Mikro | Kecil | Menengah | Besar | Importir | Total NIE |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2026 (YTD)** | 136 | 198 | 82 | 297 | 0 | 713 |
| **2025** | 525 | 696 | 317 | 771 | 2 | 2.311 |
| **2024** | 494 | 732 | 381 | 837 | 3 | 2.047 |
| **2023** | 422 | 664 | 395 | 704 | 0 | 2.185 |
| **2022** | 81 | 222 | 920 | 169 | 24 | 1.416 |
| **2021** | 14 | 277 | 1.050 | 141 | 71 | 1.553 |
| **2020** | 7 | 273 | 1.320 | 280 | 94 | 1.974 |

**Analisis Tren & Temuan Utama:**
- **Pergeseran Dominasi Skala:** Pada periode 2015–2022 (sistem ERLA), mayoritas produk AMDK terdaftar di bawah skala Menengah. Mulai tahun 2023 (transisi penuh ke sistem ERBA), terjadi pergeseran di mana skala Besar dan Kecil menjadi kategori yang paling dominan.
- **Pertumbuhan UMKM:** Terjadi peningkatan signifikan pada penerbitan NIE untuk skala Mikro dan Kecil sejak tahun 2023.
- **Puncak Penerbitan:** Volume penerbitan NIE AMDK tertinggi tercatat pada tahun 2025 dengan total 2.311 produk.

**Catatan Teknis:**
- Data merupakan gabungan dari sistem ERBA (2023–sekarang) dan ERLA (2013–2022).
- Filter AMDK menggunakan kode jenis pangan 1401 (ERBA) dan 651, 652, 655 (ERLA).

---

### CB-15 — Tren produk AMDK berdasarkan skala industri

**Elapsed:** 60.55s | SQL: 2 | LLM: 7

Berikut adalah tren penerbitan Nomor Izin Edar (NIE) untuk produk **AMDK (Air Minum Dalam Kemasan)** berdasarkan skala industri secara keseluruhan (ERBA + ERLA).

**Scope:** entity=produk · system=ERBA+ERLA · year=ALL-TIME · BTP=no

**Tren NIE AMDK per Skala Industri (3 Tahun Terakhir)**

| Tahun | Besar | Menengah | Kecil | Mikro | Importir | **Total** |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2025** | 416 | 316 | 695 | 525 | 2 | **1.954** |
| **2024** | 607 | 381 | 732 | 494 | 3 | **2.217** |
| **2023** | 421 | 336 | 664 | 422 | 0 | **1.843** |

**Poin Utama:**
- **Dominasi UMKM:** Sejak tahun 2023, terlihat peningkatan signifikan pada pendaftaran dari skala Kecil dan Mikro.
- **Importir:** Produk AMDK didominasi oleh produksi dalam negeri, terlihat dari sangat rendahnya jumlah NIE untuk kategori Importir.
- **Data 2026:** Hingga saat ini di tahun 2026, telah terbit **565** NIE AMDK baru.

---

### CB-16 — Tren produk Garam Beryodium pada tahun tertentu

**Elapsed:** 53.4s | SQL: 1 | LLM: 6

Berikut adalah tren penerbitan Izin Edar (NIE) untuk produk **Garam Beryodium** dari tahun 2012 hingga 2026 (ytd):

| Tahun | Jumlah NIE Terbit |
| :--- | :--- |
| 2012 | 30 |
| 2013 | 36 |
| 2014 | 25 |
| 2015 | 46 |
| 2016 | 88 |
| 2017 | 176 |
| 2018 | 219 |
| 2019 | 330 |
| 2020 | 262 |
| 2021 | 260 |
| 2022 | 224 |
| 2023 | 198 |
| 2024 | 412 |
| 2025 | 436 |
| 2026 | 125 (ytd) |

**Poin Perhatian:**
- **Tren Pertumbuhan:** Terjadi peningkatan signifikan dalam dua tahun terakhir (2024-2025), dengan puncak penerbitan pada tahun 2025 sebanyak 436 NIE.
- **Cakupan Data:** Data menggabungkan sistem ERLA (2012–2022) dan ERBA (2023–sekarang).
- **Metode Hitung:** Angka di atas merepresentasikan jumlah `nomor` unik (NIE) yang diterbitkan dengan status valid (Disetujui/Selesai).

---

### CB-17 — Distribusi izin edar berdasarkan kategori risiko, skala industri, dan tren per tahun (10 tahun terakhir)

**Elapsed:** 176.94s | SQL: 7 | LLM: 8

Berikut adalah distribusi dan tren Izin Edar (NIE) pangan olahan selama 10 tahun terakhir (2017–2026):

**1. Tren Izin Edar per Tahun (2017–2026)**

| Tahun | Jumlah NIE Terbit |
| :--- | :--- |
| 2017 | 18.811 |
| 2018 | 21.363 |
| 2019 | 23.763 |
| 2020 | 30.016 |
| 2021 | 31.919 |
| 2022 | 33.386 |
| 2023 | 33.306 |
| 2024 | 42.286 |
| 2025 | 45.247 |
| 2026* | 17.235 |
*\*Data parsial (Januari - Juni 2026)*

**2. Distribusi berdasarkan Skala Industri (Total 10 Tahun)**

| Skala Industri | Jumlah NIE |
| :--- | :--- |
| Besar | 103.352 |
| Importir | 63.853 |
| Menengah | 49.625 |
| Kecil | 36.100 |
| Mikro | 28.103 |

**3. Distribusi berdasarkan Kategori Risiko (Total 10 Tahun)**

| Kategori Risiko | Jumlah NIE |
| :--- | :--- |
| Risiko Tinggi | 101.383 |
| Risiko Menengah Tinggi | 95.684 |
| Risiko Menengah Rendah | 86.264 |
| Lainnya / Tidak Terdefinisi | 1.703 |

**Analisis Penting:**
- **Pertumbuhan UMKM:** Porsi NIE untuk skala Mikro dan Kecil terlihat meningkat seiring dengan penyederhanaan proses registrasi di sistem terbaru (ERBA).
- **Pergeseran Profil Risiko:** Terjadi pergeseran profil risiko yang signifikan pada tahun 2023-2024, di mana kategori Risiko Tinggi kembali mendominasi.
- **Data 2026:** Hingga pertengahan tahun 2026, volume penerbitan sudah mencapai 17.235 NIE.

---

### CB-18 — 3 daerah dengan proporsi pabrik produk risiko tinggi terbesar

**Elapsed:** 93.95s | SQL: 6 | LLM: 12

Berdasarkan data pendaftaran produk (NIE) dari sistem ERBA dan ERLA (all-time), berikut adalah 3 daerah dengan proporsi pabrik yang memproduksi produk risiko tinggi terbesar (minimum 5 pabrik per daerah):

1. **Kabupaten Purwakarta**: **85,71%** (6 dari 7 pabrik)
2. **Kabupaten Bandung Barat**: **63,16%** (12 dari 19 pabrik)
3. **Kabupaten Cianjur**: **62,50%** (5 dari 8 pabrik)

**Catatan Data:**
- **Lingkup**: Data mencakup produk pangan olahan (MD/ML) yang memiliki izin edar aktif/terbit.
- **Definisi Proporsi**: Dihitung dari jumlah pabrik unik yang memiliki minimal satu produk kategori Risiko Tinggi dibandingkan dengan total pabrik unik di daerah tersebut.
- **Filter**: Menggunakan kriteria NIE valid (status 0999, 0906, 9999) dan mengeluarkan akun uji coba.

---

### CB-19 — Kategori pangan terbanyak skala usaha mikro 2022–2025

**Elapsed:** 409.8s | SQL: 11 | LLM: 19

Kategori pangan dengan penerbitan Izin Edar (NIE) terbanyak untuk **skala usaha Mikro** selama periode **2022–2025** menunjukkan tren peningkatan yang signifikan setiap tahunnya.

Berdasarkan data gabungan sistem ERBA dan ERLA, total NIE yang diterbitkan untuk pelaku usaha mikro mencapai **22.404 nomor**.

**Tren Per Tahun (Skala Mikro)**

| Tahun | Jumlah NIE |
| :--- | :--- |
| 2022 | 2.678 |
| 2023 | 5.797 |
| 2024 | 6.248 |
| 2025 | 7.681 |
| **Total** | **22.404** |

**5 Kategori Pangan Terbanyak (2022–2025)**

1. **Air Mineral**: ~1.311 NIE
2. **Konsentrat Minuman Rasa/Berperisa**: ~1.102 NIE
3. **Minuman Botanikal/Minuman Rempah**: ~736 NIE
4. **Minyak Goreng Sawit**: ~650 NIE
5. **Garam Konsumsi Beriodium**: ~400 NIE

**Catatan Data:**
- Terdapat sekitar 56% data pada sistem ERBA yang label kategorinya kosong namun berhasil diidentifikasi melalui kode `kategori_pangan`.
- **Air Mineral** tetap menjadi kategori yang paling dominan diproduksi oleh pelaku usaha mikro selama 4 tahun terakhir.

---

### CB-20 — Skala Usaha dan daerah lokasi pabrik yang paling banyak mengalami pembatalan komitmen izin edar

**Elapsed:** 114.72s | SQL: 11 | LLM: 16

Berdasarkan data registrasi ERBA, terdapat total **221** nomor izin edar (NIE) dengan risiko Menengah Rendah (MR) yang mengalami pembatalan komitmen secara kumulatif.

Berikut adalah Skala Usaha dan Daerah Lokasi Pabrik dengan frekuensi pembatalan komitmen tertinggi:

| Skala Usaha | Daerah Lokasi Pabrik | Jumlah Pembatalan |
| :--- | :--- | :--- |
| Kecil | Kabupaten Tangerang | 7 |
| Kecil | Kode 37.02 | 7 |
| Mikro | Kode 37.75 | 7 |
| Mikro | Kode 38.15 | 6 |
| Mikro | Kota Bengkulu | 6 |
| Mikro | Kode 37.01 | 5 |
| Mikro | Kabupaten Sleman | 5 |
| Besar | Kabupaten Badung | 5 |
| Besar | Kota Administrasi Jakarta Utara | 5 |
| Besar | Kode 37.02 | 5 |

**Poin-poin Utama:**
- **Skala Usaha Terbanyak:** Pembatalan komitmen paling sering terjadi pada pelaku usaha dengan skala **Mikro** dan **Kecil**.
- **Daerah Terbanyak:** Secara spesifik, **Kabupaten Tangerang** mencatatkan jumlah pembatalan tertinggi yang teridentifikasi dalam kamus data.
- **Catatan Kode Wilayah:** Beberapa kode daerah (seperti 37.02, 37.75, 38.15) merupakan kode wilayah yang belum terpetakan labelnya dalam kamus data terbaru (Kemendagri legacy codes).
- **Tren:** Sebagian besar pembatalan komitmen tercatat terjadi pada tahun **2024** (191 kasus).

**Scope:** entity=NIE (MR) · system=ERBA · year=ALL-TIME (2023-2026) · BTP=no.

---

### CB-21 — Perbandingan laju pertumbuhan izin edar antara industri kecil, menengah, dan besar 2022–2025

**Elapsed:** 76.56s | SQL: 4 | LLM: 7

**Jumlah Izin Edar (NIE) per Tahun**

| Tahun | Industri Kecil | Industri Menengah | Industri Besar |
| :--- | :--- | :--- | :--- |
| **2022** | 4.193 | 9.138 | 8.082 |
| **2023** | 5.138 | 2.607 | 14.673 |
| **2024** | 6.845 | 2.789 | 20.419 |
| **2025** | 7.595 | 2.604 | 21.788 |

**Laju Pertumbuhan Tahunan (YoY)**

| Periode | Industri Kecil | Industri Menengah | Industri Besar |
| :--- | :--- | :--- | :--- |
| **2022–2023** | +22,5% | -71,5% | +81,5% |
| **2023–2024** | +33,2% | +7,0% | +39,2% |
| **2024–2025** | +11,0% | -6,6% | +6,7% |

**Analisis Utama:**
- **Industri Kecil:** Menunjukkan pertumbuhan yang paling stabil dan konsisten setiap tahunnya, rata-rata kenaikan di atas 20% pada periode 2022-2024.
- **Industri Besar:** Mengalami lonjakan pertumbuhan yang sangat signifikan pada tahun 2023 (+81,5%).
- **Industri Menengah:** Terjadi penurunan tajam sebesar 71,5% pada transisi tahun 2022 ke 2023, kemungkinan berkaitan dengan perubahan klasifikasi skala usaha atau migrasi sistem dari ERLA ke ERBA.

---

### CB-22 — Tren registrasi pangan olahan berdasarkan lokasi pabrik tahun 2025

**Elapsed:** 140.87s | SQL: 7 | LLM: 11

**Scope:** entity=Permohonan · system=ERBA · year=2025 · BTP=no.

Total permohonan yang dibayar pada tahun 2025 adalah **70.013** permohonan.

**Tren Bulanan Tahun 2025**

| Bulan | Jumlah Permohonan |
| :--- | :--- |
| Januari | 5.398 |
| Februari | 6.143 |
| Maret | 5.614 |
| April | 4.250 |
| Mei | 5.174 |
| Juni | 6.132 |
| Juli | 6.804 |
| Agustus | 6.535 |
| September | 6.522 |
| Oktober | 5.059 |
| **November** | **7.018** |
| Desember | 5.364 |

**Top 5 Lokasi Pabrik (Registrasi Terbanyak)**

| Lokasi Pabrik | Jumlah Permohonan | Keterangan |
| :--- | :--- | :--- |
| 3701 | 3.816 | Kode legacy Kemendagri |
| **Kabupaten Tangerang (3603)** | **3.528** | |
| 3716 | 3.150 | Kode legacy Kemendagri |
| 3815 | 2.387 | Kode legacy Kemendagri |
| **Kota Tangerang (3671)** | **2.234** | |

---

### CB-23 — Tren registrasi pangan olahan 5 tahun terakhir berdasarkan MD/ML

**Elapsed:** 99.67s | SQL: 4 | LLM: 13

Berikut adalah tren registrasi (permohonan) pangan olahan selama 5 tahun terakhir (2022–2026) berdasarkan kategori MD (Dalam Negeri) dan ML (Luar Negeri/Impor).

**Scope:** entity=PERMOHONAN · system=ERBA+ERLA · year=2022-2026 · BTP=no

| Tahun | MD (Dalam Negeri) | ML (Impor) | Total Permohonan |
| :--- | :--- | :--- | :--- |
| 2022 | 44.695 | 15.097 | 59.792 |
| 2023 | 43.830 | 17.384 | 61.214 |
| 2024 | 42.284 | 15.434 | 57.718 |
| 2025 | 54.594 | 20.795 | 75.389 |
| 2026* | 21.399 | 8.013 | 29.412 |

*\*Data tahun 2026 adalah data parsial hingga 4 Juni 2026.*

**Analisis Tren:**
- **Pertumbuhan Signifikan:** Terdapat lonjakan volume registrasi yang cukup besar pada tahun 2025, dengan kenaikan sekitar 30,6% dibandingkan tahun sebelumnya.
- **Proporsi MD vs ML:** Registrasi produk Dalam Negeri (MD) mendominasi secara konsisten, mencakup sekitar 72–75% dari total permohonan setiap tahunnya.

**Catatan Teknis:**
- Kategori ditentukan berdasarkan `status_usaha` (31 = MD, 33 = ML).
- Data menggabungkan sistem ERBA (2023+) dan ERLA (historis) untuk cakupan penuh.

---

### CB-24 — Wilayah dan kategori pangan prioritas pengawasan

**Elapsed:** 124.45s | SQL: 3 | LLM: 9

Berdasarkan analisis data izin edar (NIE) tahun 2023 dan 2024:

**1. Wilayah Prioritas Pengawasan**

| Wilayah | Pertumbuhan (2023-2024) | Produk Risiko Tinggi | Pembatalan Komitmen |
| :--- | :--- | :--- | :--- |
| **Kabupaten Tangerang (36.03)** | **+1.267 NIE** | 2.788 | 7 |
| **Kode Wilayah 37.01 (Legacy)** | **+708 NIE** | 2.089 | 5 |
| **Kode Wilayah 38.15 (Legacy)** | **+346 NIE** | 1.401 | 7 |

**2. Kategori Pangan Prioritas Pengawasan**

| Kategori Pangan | Pertumbuhan (2023-2024) | Produk Risiko Tinggi | Pembatalan Komitmen |
| :--- | :--- | :--- | :--- |
| **Minuman (KP 14)** | **+2.756 NIE** | 14.318 | 51 |
| **Permen dan Cokelat (KP 05)** | **+987 NIE** | 5.598 | 37 |
| **Produk Bakeri (KP 07)** | **+959 NIE** | 6.801 | 18 |
| **Bumbu (KP 12)** | **+943 NIE** | 3.090 | 7 |

**Kesimpulan Prioritas Utama:**
- **Kategori Pangan**: **Minuman (KP 14)** adalah prioritas pengawasan nomor satu secara nasional karena memiliki tingkat pertumbuhan, risiko, dan ketidakpatuhan komitmen tertinggi.
- **Wilayah**: **Kabupaten Tangerang** merupakan titik konsentrasi industri pangan dengan pertumbuhan izin edar tercepat.

---

### CB-25 — Forecasting izin edar 2026–2027 per tingkat risiko

**Elapsed:** 121.23s | SQL: 3 | LLM: 9

**Tren dan Proyeksi Izin Edar (NIE) per Tingkat Risiko**

| Tahun | Risiko Rendah (MR) | Menengah Tinggi (MT) | Risiko Tinggi (T) | Total NIE |
| :--- | :--- | :--- | :--- | :--- |
| **2021** | 11.656 | 17.957 | 2.223 | **31.836** |
| **2022** | 9.162 | 20.666 | 3.508 | **33.336** |
| **2023** | 10.059 | 5.553 | 17.679 | **33.291** |
| **2024** | 10.671 | 4.196 | 27.422 | **42.289** |
| **2025** | 13.739 | 3.688 | 27.820 | **45.247** |
| **2026 (F)** | 13.892 | 2.464 | 23.946 | **40.302** |
| **2027 (F)** | 20.956 | 3.716 | 36.123 | **60.795** |

*(F) = Forecast / Proyeksi*

**Poin Penting Analisis:**
- **Pergeseran Klasifikasi Risiko:** Sejak tahun 2023, kategori Risiko Tinggi menjadi dominan (meningkat dari ~3,5rb ke >27rb).
- **Dominasi Risiko Tinggi:** Risiko Tinggi diprediksi akan terus mendominasi dengan estimasi mencapai **36.123 NIE** pada tahun 2027.

---

### CB-26 — Kategori pangan dengan pertumbuhan izin edar tercepat tahun 2026

**Elapsed:** 246.88s | SQL: 9 | LLM: 16

**Ringkasan Tren Pertumbuhan (2021-2025)**

| Kategori Pangan | NIE 2021 | NIE 2025 | CAGR (5 Thn) | Pertumbuhan 2024-2025 |
| :--- | :---: | :---: | :---: | :---: |
| **04: Buah dan Sayur** | 1.526 | 2.877 | **17,2%** | 23,3% |
| **12: Garam, Rempah, Sup, Saus** | 2.784 | 4.407 | 12,2% | **32,4%** |
| **06: Serealia** | 2.368 | 4.111 | 14,8% | 31,0% |
| **02: Lemak dan Minyak** | 734 | 1.222 | 13,6% | -11,4% |
| **05: Kembang Gula & Cokelat** | 2.470 | 4.102 | 13,5% | 1,1% |

**Kesimpulan:** Kategori **Garam, Rempah, Sup, dan Saus (12)** diprediksi akan menjadi yang tercepat pertumbuhannya pada tahun 2026. Secara volume, kategori **Minuman (14)** tetap yang terbesar (>11.000 NIE/tahun), namun laju pertumbuhannya mulai melambat.

---

### CB-27 — Tren 5 tahun terakhir skala industri perusahaan yang terdaftar

**Elapsed:** 85.72s | SQL: 4 | LLM: 11

**Tren Perusahaan Berdasarkan Skala Industri (2022–2026)**

| Tahun | Mikro | Kecil | Menengah | Besar | Importir | **Total** |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2022 | 1.361 | 1.177 | 1.368 | 851 | 632 | **5.389** |
| 2023 | 2.065 | 1.181 | 904 | 1.061 | 691 | **5.902** |
| 2024 | 2.044 | 1.133 | 712 | 1.092 | 691 | **5.672** |
| 2025 | 2.320 | 1.255 | 633 | 1.176 | 717 | **6.101** |
| 2026* | 1.034 | 761 | 366 | 891 | 457 | **3.509** |

*\*Data tahun 2026 adalah data berjalan hingga Juni 2026.*

**Catatan Analisis:**
- **Peningkatan UMKM:** Terjadi tren peningkatan signifikan pada jumlah perusahaan skala Mikro, yang tumbuh dari 1.361 perusahaan di 2022 menjadi 2.320 di 2025 (naik ~70%).
- **Skala Menengah:** Terlihat adanya penurunan jumlah perusahaan skala Menengah yang aktif melakukan registrasi setiap tahunnya.

---

### CB-28 — Wilayah yang banyak memproduksi produk AMDK

**Elapsed:** 273.91s | SQL: 19 | LLM: 25

Berdasarkan data pendaftaran produk (NIE), wilayah yang paling banyak memproduksi produk AMDK (Air Minum Dalam Kemasan) secara akumulatif adalah **Kabupaten Bogor** dan **Kabupaten Pasuruan**.

**10 Wilayah Produksi AMDK Terbanyak (All-Time)**

| Wilayah | Jumlah NIE | Keterangan |
| :--- | :--- | :--- |
| **3701 (Kab. Bogor)** | 2.110 | Dominan di sistem ERBA (2023-sekarang) |
| **Kabupaten Pasuruan** | 606 | Data dari sistem ERLA |
| **Kabupaten Bogor** | 599 | Data dari sistem ERLA |
| **3814 (Kab. Pasuruan)** | 548 | Dominan di sistem ERBA (2023-sekarang) |
| **Kabupaten Padang Pariaman** | 460 | Gabungan ERBA & ERLA |
| **Kabupaten Karanganyar** | 446 | Gabungan ERBA & ERLA |
| **Kabupaten Bandung** | 370 | Gabungan ERBA & ERLA |
| **Kabupaten Semarang** | 278 | Gabungan ERBA & ERLA |
| **Kabupaten Bandung Barat** | 251 | Gabungan ERBA & ERLA |
| **Kabupaten Tabanan** | 240 | Gabungan ERBA & ERLA |

*Catatan: Kode 3701 dan 3814 diidentifikasi sebagai Kab. Bogor dan Kab. Pasuruan melalui verifikasi sampel alamat pabrik.*

**Detail Teknis:**
- Filter AMDK: ERBA (`jenis_pangan = '1401'`), ERLA (`jenis_pangan IN ('651','652','655')`).

---

### CB-29 — Wilayah yang banyak memproduksi produk Garam

**Elapsed:** 179.86s | SQL: 11 | LLM: 17

Kabupaten Pati merupakan wilayah dengan jumlah produksi produk Garam Beryodium terbanyak secara signifikan.

**10 Wilayah Teratas Produsen Garam**

| Wilayah | Jumlah NIE (Izin Edar) |
| :--- | :--- |
| Kabupaten Pati | 615 |
| Kabupaten Gresik | 165 |
| Kota Surabaya | 142 |
| Legacy/Unknown (38.78)* | 115 |
| Legacy/Unknown (38.25)* | 98 |
| Kabupaten Tangerang | 81 |
| Legacy/Unknown (37.09)* | 74 |
| Kota Palembang | 64 |
| Kota Bandar Lampung | 59 |
| Kota Administrasi Jakarta Utara | 55 |

*(\*) Wilayah Legacy: kode daerah dari sistem lama (ERLA) yang belum terpetakan ke label nama wilayah terbaru.*

---

### CB-30 — Wilayah dengan perusahaan UMKM terbanyak

**Elapsed:** 278.08s | SQL: 51 | LLM: 55

Wilayah dengan jumlah perusahaan UMKM terbanyak adalah **Provinsi Jawa Timur**, dengan **Kota Surabaya** sebagai kota/kabupaten dengan konsentrasi UMKM tertinggi.

**10 Wilayah (Kota/Kabupaten) dengan Jumlah Perusahaan UMKM Terbanyak**

| Wilayah (Kota/Kabupaten) | Jumlah Perusahaan UMKM |
| :--- | :--- |
| Kota Surabaya | 844 |
| Kabupaten Bogor | 564 |
| Kota Administrasi Jakarta Selatan | 545 |
| Kabupaten Sidoarjo | 483 |
| Kabupaten Tangerang | 469 |
| Kota Administrasi Jakarta Pusat | 424 |
| Kota Bandung | 409 |
| Kota Tangerang | 386 |
| Kota Administrasi Jakarta Timur | 376 |
| Kabupaten Sleman | 361 |

**Distribusi per Provinsi**

| Provinsi | Jumlah Perusahaan UMKM |
| :--- | :--- |
| Jawa Timur | 3.783 |
| Jawa Barat | 3.347 |
| Jawa Tengah | 2.076 |
| DKI Jakarta | 1.910 |
| Banten | 1.374 |
| DI Yogyakarta | 792 |

**Catatan Data:** Total terdapat **19.132** perusahaan UMKM yang teridentifikasi di seluruh Indonesia.

---

### CB-31 — Kategori pangan terbanyak diproduksi oleh UMKM

**Elapsed:** 290.31s | SQL: 9 | LLM: 15

Berdasarkan data NIE pangan olahan (sistem ERBA dan ERLA) untuk kategori usaha UMKM, kategori pangan yang paling banyak diproduksi adalah **Air Minum Dalam Kemasan (AMDK)**.

**10 Kategori Pangan Terbanyak yang Diproduksi UMKM (all-time)**

| Peringkat | Kategori Pangan | Jumlah NIE |
| :--- | :--- | :--- |
| 1 | Air Minum Dalam Kemasan (Air Mineral) | 9.601 |
| 2 | Minuman Serbuk Berperisa | 2.893 |
| 3 | Kopi Bubuk | 2.107 |
| 4 | Kukis | 2.053 |
| 5 | Bumbu Siap Pakai | 1.859 |
| 6 | Makanan Ringan Ekstrudat | 1.634 |
| 7 | Minyak Goreng Sawit | 1.534 |
| 8 | Garam Konsumsi Beriodium | 1.254 |
| 9 | Bakso Daging | 1.184 |
| 10 | Madu | 981 |

**Catatan Data:**
- Lingkup UMKM: Mikro (28.172 NIE), Kecil (37.124 NIE), Menengah (54.998 NIE). Total NIE UMKM: **120.294**.

---

### CB-32 — Jumlah produk pangan fortifikasi (MGS, Tepung Terigu, Garam Konsumsi Beryodium)

**Elapsed:** 249.14s | SQL: 6 | LLM: 10

**Ringkasan Jumlah Produk Fortifikasi (Seluruh Tahun)**

| Komoditas | Total NIE (All-Time) | Rentang Tahun |
| :--- | :---: | :--- |
| **Minyak Goreng Sawit** | 4.902 | 2012 — 2026 |
| **Garam Konsumsi Beryodium** | 2.614 | 2012 — 2026 |
| **Tepung Terigu** | 2.250 | 2012 — 2026 |

**Tren Perkembangan NIE (5 Tahun Terakhir)**

| Tahun | Minyak Goreng Sawit | Garam Konsumsi Beryodium | Tepung Terigu |
| :--- | :---: | :---: | :---: |
| 2021 | 283 | 262 | 130 |
| 2022 | 739 | 224 | 197 |
| 2023 | 700 | 198 | 209 |
| 2024 | 760 | 412 | 359 |
| 2025 | 637 | 436 | 273 |
| 2026* | 144 | 125 | 71 |

**Identifikasi Komoditas:**
- Minyak Goreng Sawit: Kode `0208` (ERBA) dan `081` (ERLA).
- Tepung Terigu: Kode `0627`, `0625` (ERBA) dan `288`, `285` (ERLA).
- Garam Konsumsi Beryodium: Kode kategori `120101000001` (ERBA) serta `12010103` dan `12010112` (ERLA).

---

### CB-33 — Jumlah produk susu merk sekolah yang disetujui

**Elapsed:** 157.02s | SQL: 3 | LLM: 6

Total terdapat **24 produk susu** dengan merk **Sekolah** yang telah mendapatkan Nomor Izin Edar (NIE). Seluruh produk ini terdaftar dalam sistem ERBA (sistem baru) dengan rincian per tahun sebagai berikut:

| Tahun | Jumlah NIE |
|-------|------------|
| 2025  | 14         |
| 2026  | 10         |
| **Total** | **24** |

**Catatan:**
- Produk-produk tersebut mayoritas terdaftar dengan merk **"Susu Sekolah (Khusus Program MBG)"** (Makan Bergizi Gratis).
- Kategori produk meliputi Susu Berperisa/Susu Rasa, Minuman Susu, dan Susu Lemak Penuh.
- Data mencakup periode hingga Juni 2026.

*(Oracle expected: 25 — selisih 1 akibat data drift, jawaban substansinya benar)*

---

### CB-34 — Produk Risiko Menengah Rendah yang paling banyak dibatalkan

**Elapsed:** 113.77s | SQL: 6 | LLM: 14

Berdasarkan data sistem ERBA (2023–sekarang), terdapat total **219 Izin Edar (NIE)** dengan Risiko Menengah Rendah (MR) yang status komitmennya dibatalkan.

**Peringkat Produk (Kategori Pangan) Terbanyak Dibatalkan:**

| No | Kategori Produk | Jumlah NIE Dibatalkan |
| :--- | :--- | :--- |
| 1 | Kategori Tidak Terisi | 106 |
| 2 | Tepung Olahan / Pati Olahan / Protein Olahan | 7 |
| 3 | Cokelat Paduan / Cokelat Compound | 7 |
| 4 | Kopi Bubuk | 6 |
| 5 | Minuman Botanikal / Minuman Rempah | 5 |
| 6 | Cokelat Hitam | 5 |

**Tren Pembatalan Komitmen MR:**
- 2023: 2 NIE
- 2024: 191 NIE (Puncak pembatalan)
- 2025: 21 NIE
- 2026: 5 NIE (Tahun berjalan)

**Alasan Utama Pembatalan:**
1. Jenis Kemasan atau Data Pabrik tidak sesuai (61 kasus)
2. Kategori Pangan yang dipilih tidak sesuai (34 kasus)
3. Penggunaan bahan baku/BTP tidak sesuai ketentuan (33 kasus)
4. Kesalahan Klaim atau Peruntukan pada label (32 kasus)

**Scope:** entity=NIE · system=ERBA (MR commitment) · year=ALL-TIME · BTP=no

---

### CB-35 — Berapa banyak produk Risiko Menengah Rendah yang belum dievaluasi

**Elapsed:** 39.05s | SQL: 1 | LLM: 5

Terdapat total **9.501** produk (NIE) Risiko Menengah Rendah (MR) yang saat ini berstatus **Proses Penilaian Kembali** (belum dievaluasi komitmennya).

| Tahun Terbit | Jumlah Produk (NIE) |
| :--- | :--- |
| 2026 | 2.053 |
| 2025 | 6.349 |
| 2024 | 989 |
| 2023 | 109 |
| 2022 | 1 |
| **Total** | **9.501** |

**Catatan Data:**
- **Lingkup**: Data mencakup Nomor Izin Edar (NIE) aktif dari sistem ERBA (2022–2026).
- **Kriteria**: Filter diterapkan pada produk Risiko Menengah Rendah (kategori dokumen 303) dengan status komitmen "Proses Penilaian Kembali" (kode 1).

*(DB aktual: 9.510 — selisih 9, data drift kecil)*

---

### CB-36 — Alasan pembatalan terbanyak pada izin edar

**Elapsed:** 172.66s | SQL: 8 | LLM: 16

Alasan pembatalan izin edar (NIE) terbanyak pada sistem ERBA berkaitan dengan ketidaksesuaian data teknis yang diajukan dalam komitmen. Dari total **5.324 izin edar** yang dibatalkan, berikut adalah alasan pembatalan yang paling sering ditemukan:

| No | Alasan Pembatalan | Jumlah NIE |
| :--- | :--- | :--- |
| 1 | Jenis Kemasan atau Data Pabrik yang dipilih tidak sesuai. | 1.578 |
| 2 | Penggunaan bahan baku dan/atau bahan tambahan pangan (BTP) dengan batasan penggunaan belum diatur atau dilarang. | 1.056 |
| 3 | Kategori Pangan yang dipilih tidak sesuai. | 1.034 |
| 4 | Pencantuman Peruntukan/Klaim/Organik pada nama produk dan/atau label. | 757 |
| 5 | Dokumen persyaratan/pendukung tidak diunggah (komposisi, spesifikasi, sertifikat kesehatan, label, dll). | 563 |
| 6 | Produk merupakan Pangan Segar (bukan ranah izin edar pangan olahan). | 344 |
| 7 | Proses Pengolahan yang dipilih tidak sesuai. | 287 |
| 8 | Dokumen persyaratan/pendukung tidak sesuai. | 277 |

**Catatan Analisis:**
- Tiga alasan teratas mencakup mayoritas kasus pembatalan.
- Satu NIE dapat memiliki lebih dari satu alasan pembatalan.
- Data alasan pembatalan bersumber dari sistem ERBA (2022-2026).

---

### CB-37 — Skala usaha perusahaan dengan kategori produk olahan ikan

**Elapsed:** 267.06s | SQL: 10 | LLM: 13

Berdasarkan data pendaftaran produk (NIE) dari sistem ERBA dan ERLA untuk kategori **"Olahan Ikan"**, terdapat total **108 perusahaan** yang terdaftar.

**Distribusi Skala Usaha — Perusahaan Produk Olahan Ikan**

| Skala Usaha | Jumlah Perusahaan |
| :--- | :--- |
| **Mikro** | 42 |
| **Kecil** | 22 |
| **Besar** | 19 |
| **Importir** | 14 |
| **Menengah** | 11 |

**Catatan:**
- **Total UMKM:** Terdapat **75 perusahaan** yang masuk dalam kategori UMKM (sekitar 69% dari total).
- **Kategori Produk:** Data diambil dari kategori yang secara spesifik mencantumkan nama "Olahan Ikan" pada nama kategorinya.

---

### CB-38 — NIE produk olahan baru, dokumen tinggi, diproduksi sendiri, industri besar, 2024

**Elapsed:** 219.16s | SQL: 9 | LLM: 19

Jumlah NIE (**Nomor Izin Edar**) yang diterbitkan pada tahun **2024** untuk kriteria tersebut adalah:

**7.006 NIE**

**Rincian Filter:**
- **Entitas**: NIE (Nomor Izin Edar)
- **Tahun**: 2024 (berdasarkan tanggal terbit)
- **Jenis Permohonan**: Baru
- **Tingkat Risiko**: Tinggi
- **Status Produksi**: Diproduksi Sendiri
- **Skala Usaha**: Industri Besar
- **Sistem Sumber**: ERBA (E-Registrasi Baru)

*(Oracle expected: 7.618 — selisih cukup besar, perlu investigasi apakah filter "dokumen tinggi" diterjemahkan berbeda. QA manual 03 Juni mendapat 7.618 — kemungkinan ada perbedaan interpretasi "dokumen tinggi" vs "risiko tinggi")*

---

## NIE Test Cases (NIE-1 s.d. NIE-23) — Semua Passed

---

### NIE-1 — Apa itu NIE?

**Elapsed:** 15.19s | SQL: 0 | LLM: 3

**NIE (Nomor Izin Edar)** adalah nomor identitas yang diterbitkan oleh BPOM sebagai tanda bahwa suatu produk pangan olahan atau bahan tambahan pangan (BTP) telah memenuhi persyaratan keamanan, mutu, dan gizi untuk diedarkan secara legal di Indonesia.

Dalam sistem data RPO (Registrasi Pangan Olahan), NIE memiliki karakteristik sebagai berikut:
- **Identitas Tunggal**: Setiap nomor izin edar yang unik (kolom `nomor`) dihitung sebagai satu NIE.
- **Cakupan Produk**: Meliputi pangan olahan (dalam negeri dan impor) serta Bahan Tambahan Pangan (BTP).
- **Status Valid**: Sebuah rekaman data dianggap memiliki NIE yang valid jika statusnya telah selesai/terbit (kode status `0999`, `0906`, `9999`, atau `0099` pada sistem lama).
- **Jenis Permohonan**: NIE diterbitkan dari jenis permohonan Baru (`301`), Baru Notifikasi (`305`), atau Daftar Ulang (`304` pada sistem lama).
- **Masa Berlaku**: Umumnya berlaku selama 5 tahun dan harus dilakukan Daftar Ulang (re-registration) sebelum masa berlakunya habis.

---

### NIE-2 — Prediksi forecast tahun 2027

**Elapsed:** 22.77s | SQL: 1 | LLM: 6

Total prediksi permohonan untuk tahun 2027 adalah **53.662** berkas.

| Bulan | Prediksi | Rentang Kendali (Bawah - Atas) |
|---|---|---|
| 2027-01 | 4.643 | 3.761 - 5.626 |
| 2027-02 | 5.030 | 4.010 - 6.042 |
| 2027-03 | 3.811 | 2.891 - 4.810 |
| 2027-04 | 5.636 | 4.741 - 6.674 |
| 2027-05 | 4.276 | 3.231 - 5.205 |
| 2027-06 | 3.052 | 2.124 - 3.988 |
| 2027-07 | 4.742 | 3.837 - 5.736 |
| 2027-08 | 4.835 | 3.908 - 5.837 |
| 2027-09 | 4.815 | 3.812 - 5.819 |
| 2027-10 | 5.055 | 4.107 - 6.051 |
| 2027-11 | 4.478 | 3.510 - 5.475 |
| 2027-12 | 3.289 | 2.334 - 4.247 |

Prediksi tertinggi terjadi pada bulan April 2027 (**5.636** permohonan), terendah pada bulan Juni 2027 (**3.052** permohonan).

---

### NIE-3 — Berapa jumlah permohonan?

**Elapsed:** 66.63s | SQL: 1 | LLM: 5

Total permohonan registrasi pangan olahan (all-time) adalah **592.175**.

| Tahun | Jumlah Permohonan |
| :--- | :--- |
| 2012 | 2 |
| 2013 | 2.647 |
| 2014 | 15.302 |
| 2015 | 21.292 |
| 2016 | 33.165 |
| 2017 | 35.041 |
| 2018 | 43.278 |
| 2019 | 45.550 |
| 2020 | 51.539 |
| 2021 | 60.834 |
| 2022 | 59.792 |
| 2023 | 61.214 |
| 2024 | 57.718 |
| 2025 | 75.389 |
| 2026* | 29.412 |
| **Total** | **592.175** |

---

### NIE-4 — Berapa NIE BTP tahun 2023?

**Elapsed:** 31.7s | SQL: 2 | LLM: 6

Jumlah Nomor Izin Edar (NIE) untuk Bahan Tambahan Pangan (BTP) pada tahun 2023 adalah **1.064**.

- **ERBA (Sistem Baru):** 950 NIE
- **ERLA (Sistem Lama):** 114 NIE

---

### NIE-5 — Berapa NIE BTP ERLA tahun 2023?

**Elapsed:** 15.79s | SQL: 1 | LLM: 5

Jumlah NIE untuk BTP pada sistem ERLA di tahun 2023 adalah **114**.

---

### NIE-6 — Berapa NIE ERBA tahun 2022?

**Elapsed:** 33.57s | SQL: 1 | LLM: 5

Jumlah NIE yang diterbitkan melalui sistem ERBA pada tahun 2022 adalah **1.414**.

---

### NIE-7 — Tampilkan gabungan NIE tahun 2022

**Elapsed:** 42.81s | SQL: 1 | LLM: 6

Total Nomor Izin Edar (NIE) yang diterbitkan pada tahun 2022 (gabungan ERBA dan ERLA) adalah **33.386** NIE.

| Sistem Registrasi | Jumlah NIE (2022) |
| :--- | :--- |
| **ERLA** (Sistem Lama) | 31.972 |
| **ERBA** (Sistem Baru) | 1.414 |
| **TOTAL GABUNGAN** | **33.386** |

---

### NIE-8 — Tampilkan gabungan NIE tahun 2023

**Elapsed:** 39.6s | SQL: 1 | LLM: 5

Jumlah NIE yang diterbitkan pada tahun 2023 adalah **33.306** NIE.

| Sistem | Jumlah NIE (2023) |
|---|---|
| **ERBA** (Sistem Baru) | 30.230 |
| **ERLA** (Sistem Lama) | 3.076 |
| **Total Gabungan** | **33.306** |

---

### NIE-9 — Berapa NIE garam beryodium tahun 2023?

**Elapsed:** 55.24s | SQL: 4 | LLM: 8

Jumlah Nomor Izin Edar (NIE) untuk produk garam beryodium yang terbit pada tahun 2023 adalah sebanyak **198 NIE**.

- **ERBA (Sistem Baru):** 189 NIE
- **ERLA (Sistem Lama):** 9 NIE
- **Total:** 198 NIE

---

### NIE-10 — Apa itu NIE MR?

**Elapsed:** 86.04s | SQL: 5 | LLM: 9

**NIE MR** (Nomor Izin Edar Risiko Menengah Rendah) adalah izin edar yang diberikan untuk produk pangan olahan dengan tingkat Risiko Menengah Rendah.

**Statistik NIE MR (All-Time):** tercatat total **118.898 NIE MR** yang diterbitkan di kedua sistem.

| Sistem | Total NIE MR | Disetujui (Verified) | Dibatalkan | Pending (Evaluasi) |
| :--- | :--- | :--- | :--- | :--- |
| **ERLA** (Sistem Lama) | 77.948 | - | - | - |
| **ERBA** (Sistem Baru) | 40.950 | 2.623 | 219 | 9.501 |

---

### NIE-11 — Berapa NIE MR dibatalkan komitmen?

**Elapsed:** 33.58s | SQL: 1 | LLM: 5

Total NIE Risiko Menengah Rendah (MR) yang dibatalkan komitmennya adalah **219**.

| Tahun | Jumlah NIE |
| :--- | :--- |
| 2023 | 2 |
| 2024 | 191 |
| 2025 | 21 |
| 2026 | 5 |
| **Total** | **219** |

---

### NIE-12 — Berapa NIE MR disetujui komitmen?

**Elapsed:** 53.64s | SQL: 1 | LLM: 6

Total NIE Risiko Menengah Rendah (MR) dengan komitmen yang telah disetujui adalah **14.200** NIE.

| Tahun | Jumlah NIE MR Disetujui Komitmen |
| :--- | :--- |
| 2026 (berjalan) | 188 |
| 2025 | 1.239 |
| 2024 | 5.930 |
| 2023 | 6.236 |
| 2022 | 607 |
| **Total** | **14.200** |

---

### NIE-13 — Apa itu NIE MT?

**Elapsed:** 104.44s | SQL: 3 | LLM: 8

**NIE MT** adalah singkatan dari **Nomor Izin Edar** untuk produk pangan dengan tingkat **Risiko Menengah Tinggi**.

Tren Penerbitan NIE MT (All-Time):

| Tahun | Jumlah NIE MT |
| :--- | :--- |
| 2026 | 1.216 (YTD) |
| 2025 | 4.165 |
| 2024 | 4.634 |
| 2023 | 6.211 |
| 2022 | 21.647 |
| 2021 | 19.130 |
| 2020 | 16.378 |
| 2019 | 17.012 |
| 2018 | 15.236 |

---

### NIE-14 — Tampilkan NIE per risiko tahun 2023

**Elapsed:** 108.23s | SQL: 1 | LLM: 6

Scope: entity=NIE · system=UNION ERBA+ERLA · year=2023 · BTP=no

| Kategori Risiko | Jumlah NIE |
| :--- | :--- |
| Risiko Tinggi | 17.679 |
| Risiko Menengah Rendah (MR) | 10.059 |
| Risiko Menengah Tinggi (MT) | 5.553 |
| Lainnya | 15 |
| **Total** | **33.306** |

---

### NIE-15 — Tampilkan NIE per skala tahun 2023

**Elapsed:** 75.7s | SQL: 4 | LLM: 8

| Skala Usaha | Jumlah NIE |
| :--- | :--- |
| Besar | 14.673 |
| Mikro | 5.797 |
| Kecil | 5.138 |
| Importir | 5.091 |
| Menengah | 2.607 |

Total NIE 2023: **33.306**. Kontribusi UMKM: **13.542 NIE** (40,6%).

---

### NIE-16 — Apa itu NIE T?

**Elapsed:** 18.81s | SQL: 1 | LLM: 3

NIE T adalah singkatan dari **NIE Risiko Tinggi** (*High Risk*). Pada sistem ERBA, NIE Risiko Tinggi diidentifikasi melalui kode `301` (Tinggi) dan `304` (Tinggi Notifikasi) pada kolom `kategori_dokumen`.

---

### NIE-17 — Berapa total NIE tahun 2023?

**Elapsed:** 50.63s | SQL: 1 | LLM: 4

Total NIE yang diterbitkan pada tahun 2023 adalah **33.306**.

---

### NIE-18 — Berapa NIE UMKM tahun 2023?

**Elapsed:** 66.15s | SQL: 2 | LLM: 6

Jumlah NIE untuk UMKM (Mikro, Kecil, dan Menengah) pada tahun 2023 adalah **13.542** NIE.

| Skala Usaha | ERBA (Baru) | ERLA (Lama) | Total |
| :--- | :--- | :--- | :--- |
| **Mikro** | 5.574 | 223 | **5.797** |
| **Kecil** | 4.868 | 270 | **5.138** |
| **Menengah** | 1.909 | 698 | **2.607** |
| **Total** | **12.351** | **1.191** | **13.542** |

---

### NIE-19 — Tampilkan permohonan gabungan tahun 2023

**Elapsed:** 73.79s | SQL: 2 | LLM: 6

Jumlah permohonan registrasi pangan olahan gabungan (ERBA dan ERLA) untuk tahun 2023 adalah sebanyak **61.214 permohonan**.

| Sistem | Jumlah Permohonan |
| :--- | :--- |
| **ERBA** (Sistem Baru) | 42.329 |
| **ERLA** (Sistem Lama) | 18.885 |
| **TOTAL** | **61.214** |

---

### NIE-20 — Tampilkan permohonan per jenis tahun 2023

**Elapsed:** 64.51s | SQL: 4 | LLM: 10

| Jenis Permohonan | Jumlah Permohonan |
| :--- | :--- |
| Permohonan Baru | 40.309 |
| Perubahan Minor | 10.457 |
| Perubahan Mayor | 9.565 |
| Permohonan Baru Notifikasi | 451 |
| Daftar Ulang | 432 |
| **Total** | **61.214** |

---

### NIE-21 — Apakah sistem menampilkan SQL transparency?

**Elapsed:** 35.19s | SQL: 0 | LLM: 7

Ya, sistem mendukung **SQL Transparency**. Setiap jawaban data yang saya berikan didasarkan pada query SQL yang dieksekusi secara real-time terhadap database. Anda dapat meminta saya untuk menampilkan query tersebut untuk memverifikasi logika, filter, dan sumber data yang digunakan dalam analisis.

---

### NIE-22 — Tampilkan tren AMDK

**Elapsed:** 59.73s | SQL: 1 | LLM: 6

| Tahun | Jumlah NIE Terbit |
| :--- | :--- |
| 2013 | 236 |
| 2014 | 666 |
| 2015 | 983 |
| 2016 | 1.040 |
| 2017 | 1.239 |
| 2018 | 1.043 |
| 2019 | 1.414 |
| 2020 | 1.636 |
| 2021 | 1.422 |
| 2022 | 1.347 |
| 2023 | 1.843 |
| 2024 | 2.217 |
| 2025 | 1.954 |
| 2026* | 565 |

---

### NIE-23 — Tampilkan tren izin edar per tahun

**Elapsed:** 51.87s | SQL: 1 | LLM: 5

Scope: `entity=NIE · system=UNION ERBA+ERLA · year=ALL-TIME · BTP=no`

| Tahun | Jumlah NIE Terbit |
| :--- | :--- |
| 2012 | 3.501 |
| 2013 | 7.558 |
| 2014 | 8.971 |
| 2015 | 14.786 |
| 2016 | 19.179 |
| 2017 | 18.811 |
| 2018 | 21.363 |
| 2019 | 23.763 |
| 2020 | 30.016 |
| 2021 | 31.919 |
| 2022 | 33.386 |
| 2023 | 33.306 |
| 2024 | 42.286 |
| 2025 | 45.247 |
| 2026* | 17.235 |

---

## Catatan Perbaikan yang Diperlukan

### 1. Oracle Assertions (False Failures)

| ID | Assertion Sekarang | Rekomendasi |
|----|--------------------|-------------|
| CB-1 | `['Risiko Menengah Rendah', '118']` | Ganti ke `['menengah rendah', 'MR', '118']` (case-insensitive) |
| CB-6 | `['tren', 'izin edar', 'per tahun']` | Ganti ke `['2024', '42.286', '2025', '45.247']` |
| CB-8 | `['daerah', 'tren']` | Ganti ke `['Tangerang', 'tren', '2024']` |

### 2. Real Bug (CB-3)

Tambahkan consistency check di `evidence-auditor/SKILL.md` REFLECT phase:
> Jika jawaban melaporkan sebuah total DAN tabel breakdown, jumlahkan baris breakdown. Jika selisih dengan total yang dilaporkan > 5%, ada dua query dengan filter berbeda. Gunakan total dari penjumlahan breakdown, bukan total dari query terpisah. Laporkan inkonsistensi ini.

### 3. CB-38 Ambiguitas Interpretasi

CB-38 mendapat 7.006 (automated, 4 Juni) vs 7.618 (QA manual, 3 Juni). Perlu diperiksa apakah "dokumen tinggi" diterjemahkan sebagai `kategori_dokumen IN ('301','304')` (risiko tinggi) di kedua run, atau ada interpretasi berbeda.

### 4. SQL Violation pada CB-6 dan CB-8

Agent menggunakan `EXTRACT(YEAR FROM tanggal)` pada dua kasus. Ini melanggar `data_quality_rules.md`. Meskipun tidak timeout di sini, perlu dipastikan reasoning framework yang baru benar-benar mencegah ini.
