# Testing WhatsApp Bot 03 Juni 2026

**Sumber:** [Confluence PD - Testing WhatsApp Bot 03 Juni 2026](https://mtatech.atlassian.net/wiki/spaces/PD/pages/1081868354/Testing+WhatsApp+Bot+03+Juni+2026)

**Tanggal Testing:** 03 Juni 2026

**Scope:** SC-2 (Sistem ERBA + ERLA)

---

## Ringkasan Status Hasil QA

| No | Status | Jumlah | Persentase | Keterangan |
|----|--------|--------|------------|------------|
| 1 | ✅ Passed Green | 26 | 68,42% | Test case berhasil sesuai expected result |
| 2 | ⚠️ Passed with Notes | 11 | 28,95% | Test case sesuai secara data, tetapi masih membutuhkan penyederhanaan atau catatan perbaikan |
| 3 | ❌ Failed | 1 | 2,63% | Test case belum sesuai expected result atau data tidak berhasil ditampilkan |
| 4 | **Total** | **38** | **100%** | Total seluruh test case pada tabel QA |

---

## ❌ FAILED (1 Test Case)

### 8. Bagaimana tren izin edar berdasarkan lokasi pabrik dan tahun penerbitannya?

**Level:** L2

**Expected Result:** Tren per daerah & tahun

**Status:** ❌ failedRed

**Screenshot:** `image-20260603-063703.png`

**Jawaban Bot:**

Secara keseluruhan, tren penerbitan Nomor Izin Edar (NIE) untuk produk pangan olahan terus menunjukkan peningkatan yang signifikan sejak tahun 2012, dengan puncaknya tercatat pada tahun 2025.

> Scope: entity=NIE · system=UNION (ERBA+ERLA) · year=ALL-TIME · BTP=no

**1. Tren Penerbitan NIE per Tahun**

Berikut adalah pertumbuhan jumlah izin edar (NIE) yang diterbitkan setiap tahunnya:

| Tahun | Jumlah NIE Terbit |
|-------|-------------------|
| 2020 | 30.016 |
| 2021 | 31.919 |
| 2022 | 33.386 |
| 2023 | 33.306 |
| 2024 | 42.286 |
| 2025 | 45.247 |
| 2026 | 17.021 |

> Tahun 2026 berjalan (data hingga Juni 2026).

**2. Lokasi Pabrik Teratas (All-Time)**

Wilayah Tangerang dan sekitarnya mendominasi lokasi pabrik dengan jumlah NIE terbanyak secara historis:

| Nama Daerah | Jumlah NIE |
|-------------|------------|
| Kabupaten Tangerang | 16.270 |
| Kota Tangerang | 10.071 |
| Region Code 3701 (Legacy) | 9.859 |
| Region Code 3716 (Legacy) | 7.825 |
| Kota Administrasi Jakarta Utara | 5.825 |
| Kabupaten Sidoarjo | 5.064 |
| Region Code 3815 (Legacy) | 4.803 |
| Kabupaten Bekasi | 4.742 |
| Kota Administrasi Jakarta Selatan | 4.634 |
| Kabupaten Bogor | 4.366 |

> **Catatan Kode Wilayah:** Kode wilayah seperti 3701, 3716, dan 3815 merupakan kode lama Kemendagri yang terbawa dari sistem migrasi ERLA dan saat ini sedang dalam proses pemutakhiran data (RPO update pending).

**3. Tren 5 Lokasi Pabrik Teratas (2021-2025)**

Tren pertumbuhan NIE di lima lokasi dengan volume tertinggi dalam 5 tahun terakhir:

| Tahun | Lokasi Pabrik | Jumlah NIE |
|-------|---------------|------------|
| 2024 | Kabupaten Tangerang | 2.702 |
| 2024 | Legacy Code 3701 | 2.102 |
| 2025 | Kabupaten Tangerang | 2.552 |
| 2025 | Legacy Code 3701 | 2.277 |
| 2025 | Legacy Code 3815 | 1.623 |

Kabupaten Tangerang secara konsisten menjadi lokasi pabrik dengan volume penerbitan izin edar tertinggi setiap tahunnya. Pertumbuhan tajam terlihat pada tahun 2024 dan 2025 di hampir seluruh wilayah industri utama.

**Catatan Perbaikan:**

Data sebaiknya ditampilkan per daerah dan per tahun, bukan hanya jumlah totalnya saja. Angka yang ditampilkan cukup jumlah izin edar yang valid untuk tiap lokasi. Formatnya juga perlu dibuat singkat dan berurutan supaya mudah dibaca di WhatsApp.

**Contoh format yang diharapkan:**

**Tren Izin Edar Produk Pangan Olahan per Tahun dan Lokasi Pabrik**

- **Kabupaten Tangerang**
  - 2020: 1.200 izin edar
  - 2021: 1.350 izin edar
  - 2022: 1.527 izin edar
  - 2023: 1.600 izin edar
  - 2024: 1.800 izin edar
  - 2025: 1.950 izin edar
  - (dst…)

---

## ⚠️ PASSED WITH NOTES (11 Test Cases)

---

### 13. Bagaimana tren registrasi produk Air Minum Dalam Kemasan (AMDK) setiap tahun?

**Level:** L2

**Expected Result:** Tren AMDK per tahun

**Status:** ⚠️ passed with notesYellow

**Screenshot:** `image-20260603-064329.png`

**Jawaban Bot:**

Berikut adalah tren registrasi produk Air Minum Dalam Kemasan (AMDK) berdasarkan jumlah Nomor Izin Edar (NIE) yang diterbitkan setiap tahunnya (gabungan sistem ERBA dan ERLA):

> Scope: entity=NIE · system=UNION (ERBA+ERLA) · year=ALL-TIME · BTP=no · product=AMDK

| Tahun | Jumlah NIE Terbit |
|-------|-------------------|
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
| 2026 (s.d. Juni) | 553 |

**Poin Perhatian:**

- Tren registrasi AMDK menunjukkan kenaikan yang signifikan sejak 2013 dan mencapai puncaknya pada tahun 2024 dengan 2.217 NIE.
- Terdapat penurunan volume pada periode 2021-2022, namun melonjak kembali secara drastis mulai tahun 2023.
- Data tahun 2026 berjumlah 553 NIE merupakan data berjalan hingga 3 Juni 2026.

**Catatan Perbaikan:**

Jawaban benar secara data (angka tahunan sesuai), tetapi **perlu disederhanakan dan diringkas** agar lebih ramah untuk WhatsApp: cukup tampilkan tren singkat dan puncak/titik penting, tanpa perlu menyebut sistem internal atau kode teknis.

**Versi ideal ringkas untuk WhatsApp:**

**Tren Registrasi AMDK per Tahun (NIE)**

- 2013: 236
- 2014: 666
- 2015: 983
- 2016: 1.040
- 2017: 1.239
- 2018: 1.043
- 2019: 1.414
- 2020: 1.636
- 2021: 1.422 (sedikit turun)
- 2022: 1.347 (turun)
- 2023: 1.843 (naik drastis)
- 2024: 2.217 (puncak)
- 2025: 1.954
- 2026 (s.d. Juni): 553

**Ringkasan tren:**

- Peningkatan signifikan dari 2013 hingga puncak 2024.
- Penurunan sementara di 2021–2022.
- Data 2026 masih parsial (hingga Juni).

---

### 17. Tampilkan distribusi izin edar berdasarkan risiko produk, skala industri, dan tren 10 tahun terakhir.

**Level:** L2

**Expected Result:** Data 3 dimensi akurat

**Status:** ⚠️ passed with notesYellow

**Screenshot:** `image-20260603-065318.png`

**Jawaban Bot:**

Berikut adalah distribusi Izin Edar (NIE) pangan olahan berdasarkan risiko produk, skala industri, serta tren perkembangannya dalam 10 tahun terakhir (2016 – Juni 2026).

> Scope: entity=NIE · system=Gabungan ERBA & ERLA (Risiko: ERBA saja) · year=2016-2026 · BTP=no

**1. Distribusi Berdasarkan Risiko Produk (ERBA)**

Data risiko produk tersedia pada sistem ERBA (sistem terbaru). Sebagian besar produk yang terdaftar masuk dalam kategori Risiko Tinggi.

| Risiko | Jumlah NIE |
|--------|------------|
| Tinggi | 79.554 |
| Menengah Rendah | 40.916 |
| Menengah Tinggi | 11.809 |
| Tinggi Notifikasi | 3.292 |

**2. Distribusi Berdasarkan Skala Industri (Gabungan)**

Ditinjau dari skala usaha, pelaku usaha skala Besar dan Importir mendominasi jumlah izin edar yang terbit. Total kontribusi UMKM (Mikro, Kecil, Menengah) adalah sebanyak 116.201 NIE.

| Skala Industri | Jumlah NIE |
|----------------|------------|
| Besar | 104.479 |
| Importir | 69.240 |
| Menengah | 51.749 |
| Kecil | 36.578 |
| Mikro | 27.874 |

**3. Tren Izin Edar 10 Tahun Terakhir**

Terlihat tren pertumbuhan yang konsisten setiap tahunnya, dengan lonjakan signifikan mulai tahun 2024. Data tahun 2026 masih bersifat parsial (hingga Juni 2026).

| Tahun | Jumlah NIE |
|-------|------------|
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
| 2026 | 17.021 |

**Catatan Penting:**

- Data risiko hanya mencakup sistem ERBA karena kolom kategori risiko tidak tersedia pada sistem lama (ERLA).
- Skala industri "Importir" mencakup pelaku usaha yang tidak terdefinisi skala industrinya pada profil trader.
- Peningkatan tajam pada tahun 2024-2025 menunjukkan efektivitas percepatan layanan registrasi atau peningkatan kepatuhan pelaku usaha.

**Catatan Perbaikan:**

Jawaban sudah benar secara data, tetapi **perlu diringkas** agar lebih ramah untuk WhatsApp. Misal:

**Ringkasan Distribusi Izin Edar (2016–2026)**

**Risiko Produk (ERBA):**

- Tinggi: 79.554 NIE
- Menengah Rendah: 40.916 NIE
- Menengah Tinggi: 11.809 NIE
- Tinggi Notifikasi: 3.292 NIE

**Skala Industri:**

- Besar: 104.479 NIE
- Menengah: 51.749 NIE
- Kecil: 36.578 NIE
- Mikro: 27.874 NIE
- Importir: 69.240 NIE

**Tren 10 Tahun Terakhir (2016–2025):**

- Konsisten naik setiap tahun, lonjakan signifikan mulai 2024–2025.
- Tahun 2026 masih parsial (hingga Juni).

**Catatan:** Data risiko hanya mencakup sistem ERBA, sementara sistem lama ERLA tidak memiliki kategori risiko lengkap.

---

### 20. Daerah dan skala usaha mana yang paling sering mengalami pembatalan komitmen izin edar?

**Level:** L2

**Expected Result:** Skala + daerah + jumlah

**Status:** ⚠️ passed with notesYellow

**Screenshot:** `image-20260603-082819.png`

**Jawaban Bot:**

Berdasarkan data pendaftaran produk (ERBA) untuk seluruh periode (2022–2026), berikut adalah rincian pembatalan komitmen izin edar:

- **Skala Usaha Terbanyak:** Mikro (1.499 pembatalan).
- **Daerah Terbanyak:** Kota Administrasi Jakarta Timur (553 pembatalan).
- **Kombinasi Terbanyak:** Pelaku usaha Mikro di Kabupaten Bantul (224 pembatalan).

**1. Top 5 Daerah dengan Pembatalan Terbanyak**

| Daerah | Jumlah Pembatalan |
|--------|-------------------|
| Kota Administrasi Jakarta Timur | 553 |
| Kota Administrasi Jakarta Barat | 445 |
| Kota Administrasi Jakarta Selatan | 353 |
| Kota Administrasi Jakarta Pusat | 350 |
| Kabupaten Bantul | 253 |

**2. Pembatalan Berdasarkan Skala Usaha**

| Skala Usaha | Jumlah Pembatalan |
|-------------|-------------------|
| Mikro | 1.499 |
| Kecil | 312 |
| Menengah | 267 |

**3. Tren Pembatalan Komitmen Per Tahun**

Pembatalan komitmen mencapai puncaknya pada tahun 2023.

| Tahun | Jumlah Pembatalan |
|-------|-------------------|
| 2022 | 183 |
| 2023 | 2.499 |
| 2024 | 2.002 |
| 2025 | 250 |
| 2026 | 10 |

**Catatan:**

- Data ini hanya mencakup sistem ERBA, karena fitur komitmen hanya tersedia pada sistem tersebut (terutama untuk risiko Menengah Rendah/MR).
- Jumlah pembatalan di Kabupaten Bantul sangat didominasi oleh pelaku usaha skala Mikro (88% dari total pembatalan di daerah tersebut).
- Pembatalan di wilayah DKI Jakarta tersebar di berbagai skala usaha, terutama Importir dan Besar.

**Catatan Perbaikan:**

Jawaban sudah benar secara data, tetapi **perlu diringkas** agar lebih ramah untuk WhatsApp. Misal:

**Pembatalan Komitmen Izin Edar (2022–2026)**

- **Skala Usaha Terbanyak:** Mikro – 1.499 pembatalan
- **Daerah Terbanyak:** Jakarta Timur – 553 pembatalan
- **Kombinasi Terbanyak:** Mikro di Kabupaten Bantul – 224 pembatalan

**Top 5 Daerah dengan Pembatalan:**

1. Jakarta Timur – 553
2. Jakarta Barat – 445
3. Jakarta Selatan – 353
4. Jakarta Pusat – 350
5. Kabupaten Bantul – 253

**Tren Pembatalan per Tahun:**

- 2022: 183
- 2023: 2.499 (puncak)
- 2024: 2.002
- 2025: 250
- 2026: 10 (data parsial)

**Catatan:** Data hanya mencakup sistem ERBA, fitur komitmen tidak tersedia di sistem lama (ERLA). Pembatalan di Kabupaten Bantul didominasi pelaku usaha skala Mikro (88%).

---

### 24. Wilayah dan kategori pangan apa yang perlu diprioritaskan untuk pengawasan berdasarkan risiko, pertumbuhan izin edar, dan pembatalan komitmen?

**Level:** L3

**Expected Result:** Rekomendasi multi-aspek komprehensif

**Status:** ⚠️ passed with notesYellow

**Screenshot:** `image-20260603-070627.png`, `image-20260603-070651.png`

**Jawaban Bot:**

Berdasarkan analisis data izin edar (NIE) dari sistem ERBA dan ERLA untuk periode 2022–2023, berikut adalah wilayah dan kategori pangan yang perlu diprioritaskan untuk pengawasan:

**1. Prioritas Berdasarkan Kategori Pangan**

| Kategori Pangan | Risiko Tinggi (NIE) | Pembatalan Komitmen | Pertumbuhan (YoY) | Catatan Pengawasan |
|-----------------|---------------------|---------------------|-------------------|-------------------|
| Konsentrat Minuman Rasa | 266 | 47 | Sangat Tinggi | Risiko ganda: pertumbuhan pesat dan tingkat pembatalan komitmen tinggi |
| Minuman Berperisa | 64 | 46 | Tinggi | Fokus pada pemenuhan komitmen label/klaim (MR) |
| Still Grape Wine / Anggur | 806 | 0 | Sangat Tinggi | Volume risiko tinggi (T) sangat besar; pengawasan ketat terhadap asal produk |
| Biskuit / Kukis | 180 | 29 | Stabil | Kategori padat industri dengan pembatalan komitmen yang signifikan |
| Makanan Ringan (Ekstrudat/Simulasi) | 149 | 18 | Stabil | Prioritas untuk pengawasan rutin di jalur distribusi |

**2. Prioritas Berdasarkan Wilayah (Daerah Pabrik)**

| Wilayah | Risiko Tinggi (NIE) | Pembatalan Komitmen | Pertumbuhan (YoY) |
|---------|---------------------|---------------------|-------------------|
| Kabupaten Tangerang | 1.002 | 86 | -8,7% |
| Kota Tangerang | 799 | 88 | -6,4% |
| Kabupaten Bantul | 273 | 122 | +50,0% |
| Region 3701 | 773 | 130 | +59,3% |
| Region 3815 | 539 | 66 | - |

**Catatan Perbaikan:**

Jawaban benar secara data, tetapi perlu **diringkas dan disederhanakan** untuk WhatsApp. Contoh ringkasan yang lebih ramah:

**Prioritas Pengawasan (2022–2023)**

**Kategori Pangan dengan Risiko Tinggi & Pertumbuhan Pesat:**

1. Konsentrat Minuman Rasa – NIE: 266, Pembatalan: 47, Pertumbuhan: Sangat Tinggi
2. Minuman Berperisa – NIE: 64, Pembatalan: 46, Pertumbuhan: Tinggi
3. Still Grape Wine / Anggur – NIE: 806, Pembatalan: 0, Pertumbuhan: Sangat Tinggi
4. Biskuit / Kukis – NIE: 180, Pembatalan: 29, Pertumbuhan: Stabil
5. Makanan Ringan (Ekstrudat/Simulasi) – NIE: 149, Pembatalan: 18, Pertumbuhan: Stabil

**Wilayah Prioritas (Risiko Tinggi):**

- Kabupaten Tangerang – NIE: 1.002, Pembatalan: 86, Pertumbuhan: -8,7%
- Kota Tangerang – NIE: 799, Pembatalan: 88, Pertumbuhan: -6,4%
- Kabupaten Bantul – NIE: 273, Pembatalan: 122, Pertumbuhan: +50%
- Region 3701 – NIE: 773, Pembatalan: 130, Pertumbuhan: +59,3%
- Region 3815 – NIE: 539, Pembatalan: 66

**Catatan:** Data legacy ERLA masih dalam pemutakhiran. Fokus pengawasan pada Konsentrat Minuman dan Minuman Berperisa, terutama wilayah Tangerang Raya dan Kabupaten Bantul.

---

### 29. Daerah mana yang paling banyak memproduksi produk garam?

**Level:** L2

**Expected Result:** Ranking wilayah Garam

**Status:** ⚠️ passed with notesYellow

**Screenshot:** `image-20260603-070951.png`

**Jawaban Bot:**

Daerah yang paling banyak memproduksi produk garam (berdasarkan jumlah Izin Edar/NIE yang diterbitkan) adalah Kabupaten Pati, dengan total 615 produk.

Berikut adalah daftar 5 daerah dengan jumlah produksi produk garam terbanyak (All-Time):

| Daerah | NIE ERBA | NIE ERLA | Total NIE |
|--------|----------|----------|-----------|
| Kabupaten Pati | 256 | 359 | 615 |
| Kabupaten Gresik | 0 | 174 | 174 |
| Kota Surabaya | 0 | 143 | 143 |
| Legacy/Other (3878) | 110 | 5 | 115 |
| Legacy/Other (3825) | 91 | 6 | 97 |

**Catatan Analisis:**

- **Lingkup Data:** Data mencakup produk dengan kategori "Garam dan Penggantinya" (kategori pangan 12.01.01) dari sistem ERBA (baru) dan ERLA (lama).
- Kabupaten Pati mendominasi produksi garam nasional dengan kontribusi signifikan baik di sistem lama maupun sistem baru.
- **Legacy/Other:** Kode wilayah seperti 3878 dan 3825 adalah kode wilayah lama dari sistem ERLA yang belum terpetakan ke label nama daerah terbaru dalam kamus data pusat (Pusdatin).
- **Status NIE:** Angka di atas hanya menghitung produk dengan status NIE aktif/disetujui.

**Catatan Perbaikan:**

Jawaban benar secara data, tetapi perlu **diringkas dan disederhanakan** untuk WhatsApp. Contoh:

**Top 5 Daerah Produsen Garam (All-Time)**

1. **Kabupaten Pati** – Total: 615 produk (ERBA: 256, ERLA: 359)
2. **Kabupaten Gresik** – Total: 174 produk (ERLA: 174)
3. **Kota Surabaya** – Total: 143 produk (ERBA: 0, ERLA: 143)
4. **Legacy/Other (3878)** – Total: 115 produk (ERBA: 110, ERLA: 5)
5. **Legacy/Other (3825)** – Total: 97 produk (ERBA: 91, ERLA: 6)

**Catatan:** Angka menghitung produk dengan status NIE aktif/disetujui. Kode legacy 3878/3825 masih belum terpetakan ke nama daerah terbaru. Kabupaten Pati mendominasi produksi garam nasional.

---

### 32. Berapa jumlah produk fortifikasi untuk MGS, Tepung Terigu, dan Garam Beryodium?

**Level:** L1

**Expected Result:** 3 produk terpisah + jumlah

**Status:** ⚠️ passed with notesYellow

**Screenshot:** `image-20260603-083357.png`

**Jawaban Bot:**

Berdasarkan data registrasi pangan olahan (NIE), berikut adalah jumlah produk fortifikasi untuk kategori Minyak Goreng Sawit (MGS), Tepung Terigu, dan Garam Beryodium secara akumulatif (seluruh tahun):

> Scope: entity=NIE · system=UNION (ERBA+ERLA) · year=ALL-TIME · BTP=no

| Jenis Produk | Total NIE | ERBA | ERLA |
|--------------|-----------|------|------|
| Minyak Goreng Sawit | 4.523 | 2.269 | 2.254 |
| Garam Beryodium | 2.615 | 1.166 | 1.449 |
| Tepung Terigu | 1.854 | 537 | 1.317 |

**Catatan Data:**

- Angka di atas mencakup seluruh produk yang terdaftar dalam kategori pangan terkait, di mana fortifikasi (seperti Vitamin A untuk MGS, Zat Besi/Seng untuk Tepung Terigu, dan Iodium untuk Garam) merupakan kewajiban sesuai standar SNI.
- Data merupakan gabungan dari sistem ERBA (New E-Registration) dan ERLA (Legacy System) dengan filter akun pengujian dan tahun data artefak telah dikeluarkan.
- Untuk Tepung Terigu, data mencakup varian Tepung Terigu Standar, Self-Raising, dan Wholemeal.
- Untuk Garam Beryodium, data mencakup Garam Konsumsi Beriodium (padat dan cair).

**Catatan Perbaikan:**

Data benar, tapi terlalu panjang dan teknis; perlu diringkas untuk WhatsApp agar angka utama mudah dibaca.

**Jumlah Produk Fortifikasi (All-Time)**

- **Minyak Goreng Sawit (MGS):** 4.523 NIE (ERBA 2.269, ERLA 2.254)
- **Garam Beryodium:** 2.615 NIE (ERBA 2.166, ERLA 1.449)
- **Tepung Terigu:** 1.854 NIE (ERBA 537, ERLA 1.317)

**Catatan:** Data mencakup seluruh varian produk dan status NIE aktif/disetujui.

---

### 34. Produk risiko menengah rendah apa yang paling sering mengalami pembatalan?

**Level:** L1

**Expected Result:** Daftar terurut pembatalan

**Status:** ⚠️ passed with notesYellow

**Screenshot:** `image-20260603-083830.png`

**Jawaban Bot:**

Berdasarkan data pendaftaran pangan olahan risiko Menengah Rendah (MR) di sistem ERBA, berikut adalah ringkasan mengenai pembatalan produk:

**Status Pembatalan Terbanyak:** Produk risiko menengah rendah paling sering mengalami pembatalan dengan status Dicabut/Dibatalkan (kode 0009).

**Jumlah Produk:** Tercatat sebanyak 2.515 produk dalam kategori risiko menengah rendah yang memiliki status Dicabut/Dibatalkan (0009). Sebagai perbandingan, hanya terdapat 1 produk dengan status Dihapus/Dibatalkan (kode 0000).

**Catatan/Caveat:**

- Bukti data yang tersedia saat ini menunjukkan statistik berdasarkan kode status pembatalan, namun tidak merinci nama produk atau kategori pangan spesifik (seperti jenis makanan/minuman tertentu) yang paling banyak dibatalkan.
- Terdapat status dengan jumlah besar seperti kode 0999 (138.630 data) dan 0906 (33.066 data), namun deskripsi label untuk kode-kode tersebut tidak ditemukan dalam referensi kamus data yang tersedia, sehingga tidak dapat dikategorikan sebagai pembatalan.

**Catatan Perbaikan:**

Data benar, tapi **tidak ada nama produk spesifik dan terlalu panjang**; perlu diringkas untuk WhatsApp.

**Produk Risiko Menengah Rendah – Pembatalan Terbanyak**

- Total produk dengan status Dicabut/Dibatalkan: **2.515 produk**
- Status dihapus/dibatalkan: **1 produk**
- Catatan: Tidak dapat mengidentifikasi nama produk spesifik karena keterbatasan data.

---

### 36. Apa alasan pembatalan izin edar yang paling sering terjadi?

**Level:** L1

**Expected Result:** Alasan + jumlah terbanyak

**Status:** ⚠️ passed with notesYellow

**Screenshot:** `image-20260603-084321.png`

**Jawaban Bot:**

Berdasarkan data deskriptif yang tersedia, alasan pembatalan izin edar yang paling sering terjadi adalah ketidaksesuaian data kemasan atau data pabrik. Berikut adalah 5 alasan pembatalan teratas berdasarkan frekuensi kejadiannya:

| Alasan Pembatalan | Jumlah Kejadian |
|-------------------|-----------------|
| Jenis Kemasan atau Data Pabrik yang dipilih tidak sesuai | 1.505 |
| Penggunaan bahan baku/BTP tidak sesuai ketentuan | 1.012 |
| Kategori Pangan yang dipilih tidak sesuai | 972 |
| Pencantuman Peruntukan/Klaim/Organik pada nama/label | 707 |
| Dokumen persyaratan/pendukung tidak diunggah | 556 |

**Catatan:**

- Terdapat sejumlah besar data pembatalan yang tercatat dengan kode status umum seperti 9999 (205.497 baris) dan 0999 (183.830 baris) yang tidak memiliki pemetaan label alasan spesifik dalam bukti yang ditemukan.
- Analisis di atas didasarkan pada data yang memiliki deskripsi alasan tertulis secara eksplisit.

**Catatan Perbaikan:**

Data benar, tapi terlalu panjang dan teknis; perlu diringkas untuk WhatsApp agar alasan dan jumlah mudah dibaca.

**Alasan Pembatalan Izin Edar Terbanyak**

1. **Jenis kemasan/data pabrik tidak sesuai:** 1.505 kejadian
2. **Penggunaan bahan baku/BTP tidak sesuai ketentuan:** 1.012 kejadian
3. **Kategori pangan dipilih tidak sesuai:** 972 kejadian
4. **Pencantuman permutamatuka/label organik:** 707 kejadian
5. **Dokumen persyaratan/prosedur tidak diikuti:** 556 kejadian

**Catatan:** Data juga mencakup status 9999 & 0999, untuk kejadian yang tidak memiliki label spesifik.

---

### 38. Berapa jumlah NIE produk olahan baru tahun 2024 dengan kriteria dokumen tinggi, diproduksi sendiri, dan berasal dari industri besar?

**Level:** L3

**Expected Result:** Jumlah sesuai filter multi-kriteria

**Status:** ⚠️ passed with notesYellow

**Screenshot:** `image-20260603-085020.png`

**Jawaban Bot:**

Jumlah NIE produk olahan baru pada tahun 2024 dengan kriteria dokumen tinggi, status diproduksi sendiri, dan berasal dari industri besar adalah 7.618.

**Detail Cakupan Data:**

- **Entitas:** Nomor Izin Edar (NIE) Terbit (Pangan Olahan).
- **Sistem:** ERBA (sistem yang mencatat kriteria dokumen/risiko).
- **Periode:** 1 Januari 2024 – 31 Desember 2024.
- **Kriteria:**
  - Jenis Permohonan: Baru dan Baru Notifikasi.
  - Kriteria Dokumen: Tinggi dan Tinggi Notifikasi.
  - Status Produksi: Diproduksi Sendiri.
  - Skala Usaha: Industri Besar.

**Catatan:**

Data ini hanya mencakup pendaftaran melalui sistem ERBA karena kriteria dokumen (risiko) hanya tersedia pada sistem tersebut.

**Catatan Perbaikan:**

Data benar, tetapi perlu **diringkas agar lebih ramah WhatsApp**.

**Jumlah NIE Produk Olahan Baru 2024 (Dokumen Tinggi, Diproduksi Sendiri, Industri Besar)**

- Total: **7.618 NIE**

**Catatan:** Data hanya mencakup sistem ERBA; mencakup semua produk dengan kriteria dokumen tinggi dan status produksi sendiri.
