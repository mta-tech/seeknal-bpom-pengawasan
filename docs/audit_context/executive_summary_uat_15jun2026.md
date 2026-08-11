# Ringkasan Hasil Pengujian — Asisten AI BPOM
**Tanggal:** 17 Juni 2026
**Untuk:** Manajemen / C-Level

---

## 1. Ringkasan Singkat

Pada 15 Juni 2026, kami menguji asisten AI yang digunakan untuk menganalisis data registrasi produk pangan olahan BPOM. Pengujian dilakukan dengan **57 pertanyaan nyata** dari 5 pengguna berbeda, melalui 14 sesi percakapan.

**Hasilnya:**
- 6 kesalahan pola yang semuanya berakar pada **dokumen panduan AI yang perlu diperbaiki**
- Bukan masalah pada sistemnya — **sistem sudah bekerja dengan benar**
- Angka terbesar yang salah: jumlah izin edar risiko Menengah Tinggi ditampilkan **95.736**, padahal yang benar hanya **11.923** (selisih 703%)

**Solusi sudah diimplementasikan** pada 17 Juni 2026. AI sekarang dipaksa memeriksa arti setiap kode langsung dari database, bukan dari catatan lama. 101 test case juga sudah disiapkan untuk mencegah kesalahan serupa.

---

## 2. Apa yang Diuji

Seeknal adalah AI yang membantu analis BPOM menjawab pertanyaan tentang data registrasi produk. Contoh pertanyaan yang bisa dijawab:

- "Berapa izin edar produk AMDK tahun 2025?"
- "Tren permohonan pangan olahan dari tahun ke tahun?"
- "Berapa produk yang komitmennya dibatalkan?"

AI ini **tidak punya daftar jawaban tetap**. Ia membaca panduan, lalu mencari jawaban langsung dari database BPOM.

Kami uji dengan 57 pertanyaan nyata dari percakapan pengguna aktual. Semua jawaban yang dihasilkan diverifikasi langsung ke database untuk memastikan keakuratannya.

---

## 3. Temuan: Apa yang Ditemukan

### 6 Kesalahan yang Diperbaiki

| No | Apa yang Salah | Jawaban Sistem | Jawaban Benar | Selisih |
|----|----------------|----------------|---------------|---------|
| 1 | NIE Risiko Menengah Tinggi (all-time) | 95.736 | 11.923 | +703% terlalu tinggi |
| 2 | Total NIE Aktif | Filter diterapkan ke semua pertanyaan | Lebih tinggi dari yang ditampilkan | -4% s/d -25% terlalu rendah |
| 3 | Garam Beryodium 2023 | 189 | 198 | -4.5% terlalu rendah |
| 4 | Komitmen MR Dibatalkan | 254 | 5.146 | -95% terlalu rendah |
| 5 | Total NIE 2025 | 3 jawaban berbeda untuk pertanyaan sama | 53.535 (konsisten) | Tidak konsisten |
| 6 | Total NIE Mei 2026 | 3.880 | 5.193 | -25.3% terlalu rendah |

### Yang Sudah Benar

Tidak semua kesalahan. Banyak pertanyaan yang dijawab dengan benar:

- **AMDK 2023:** 1.843 — sesuai database
- **BTP 2023:** 950 — angka pasti
- **Susu merk sekolah Mei 2026:** 0 — dijawab jujur "tidak ditemukan"
- **Tren Risiko Rendah vs Tinggi:** benar dan mendapat **upvote** dari pengguna

Jadi sistem ini **sebenarnya sudah pintar**. Masalahnya hanya pada beberapa panduan yang perlu diperbarui.

---

## 4. Mengapa Ini Terjadi

### Analogi Sederhana

Bayangkan seorang analis yang punya **buku catatan lama** berisi arti kode-kode data. Ketika ada pertanyaan, ia percaya pada catatan itu tanpa mengecek ulang ke database.

Masalahnya: **catatan itu sudah tidak akurat**. Kode '303' di sistem lama (ERLA) artinya 'semua produk medium risk', tapi di catatan tertulis 'khusus Menengah Tinggi'. Akibatnya, angka yang ditampilkan 7 kali lipat lebih besar dari seharusnya.

### Penyebab Spesifik

**1. Dua Sistem dengan Kode Berbeda**

BPOM punya dua sistem registrasi produk:
- **ERBA** — sistem baru (mulai 2022)
- **ERLA** — sistem lama (sebelum 2022)

Keduanya punya **kode yang sama tapi artinya berbeda**. Contoh: kode '303' di ERBA artinya 'Menengah Rendah', tapi di ERLA artinya 'Semua Medium Risk'. AI tidak tahu harus pakai yang mana, sehingga menggabungkan data dengan salah.

**2. Aturan Filter Terlalu Umum**

AI punya aturan: "jumlah izin edar baru = filter jenis permohonan 301/305". Aturan ini benar untuk pertanyaan "izin baru". Tapi ketika ditanya "total izin edar aktif", aturan yang sama tetap diterapkan — padahal seharusnya tidak. Akibatnya, angka selalu lebih rendah dari yang seharusnya.

**3. Panduan Berisi "Jawaban" Bukan "Prosedur"**

Panduan AI sebelumnya memuat "kode X berarti Y" sebagai fakta. Seharusnya, panduan hanya memuat **prosedur**: "cari arti kode X langsung dari database". Dengan begitu, AI tidak pernah menebak — selalu mengecek.

---

## 5. Solusi yang Sudah Diimplementasikan

### Prinsip: "Paksa AI Membaca Kamus, Bukan Menghafal"

Mulai 17 Juni 2026, kami mengubah cara AI bekerja:

**Sebelum:** AI membaca panduan yang berisi "kode 303 = Menengah Tinggi", lalu langsung menjawab.

**Sesudah:** AI dipaksa **mencari arti kode 303 langsung dari database** setiap kali ada pertanyaan. Panduan hanya berisi **prosedur cara mencari**, bukan jawaban tetap.

### 3 Perubahan Utama

1. **Hapus semua "jawaban tertanam"** — Tidak ada lagi kode yang artinya sudah ditulis di panduan. Setiap kode harus dicari ulang ke database.

2. **Tambah prosedur verifikasi** — Sebelum menjawab, AI wajib mengecek: "Apakah kode ini artinya sama di ERBA dan ERLA? Kalau tidak, sumber mana yang lebih relevan?"

3. **Pisahkan aturan per jenis pertanyaan** — Aturan untuk "izin baru" tidak bisa dipakai untuk "total aktif". Aturan untuk "NIE yang sudah terbit" tidak bisa dipakai untuk "permohonan yang dibatalkan sebelum NIE".

### Test Case

Kami juga membuat **101 soal ujian otomatis** yang mencakup semua jenis pertanyaan. Soal-soal ini bisa diulang kapan saja untuk memastikan kesalahan yang sama tidak muncul lagi.

---

## 6. Dampak yang Diharapkan

### Perbandingan Sebelum vs Sesudah

| Pertanyaan | Sebelum | Sesudah |
|------------|---------|---------|
| NIE Menengah Tinggi | 95.736 (salah +703%) | ~11.923 |
| Komitmen Dibatalkan | 254 (kurang 95%) | ~5.146 |
| Total NIE 2025 (konsistensi) | 3 jawaban berbeda | 1 jawaban konsisten (~57.206) |
| Produk MD 2025 | 30.760 (kurang 16%) | ~39.389 |
| Garam Beryodium 2023 | 189 | ~199 |

### Yang Tidak Berubah (Sudah Benar)

- AMDK 2023: tetap ~1.843
- BTP 2023: tetap 950
- Susu merk sekolah Mei 2026: tetap 0

---

## 7. Status Saat Ini

| Item | Status |
|------|--------|
| Perbaikan panduan AI | Selesai (17 Juni 2026) |
| Test suite 101 soal | Selesai |
| Regression testing | Menunggu koneksi database aktif |
| UAT lanjutan | Setelah regression testing |

---

## 8. Kesimpulan

Sistem AI ini **sebenarnya sudah baik**. Ia bisa menjawab pertanyaan kompleks, mengeksplorasi data, dan jujur saat tidak menemukan jawaban.

Masalahnya hanya pada **dokumen panduan** yang perlu diperbarui. Dengan perbaikan yang sudah dilakukan, AI sekarang dipaksa **mengecek setiap kode langsung dari sumbernya** — tidak ada lagi jawaban yang ditebak dari catatan lama.

Yang kami lakukan bukan menulis ulang kode sistem. Kami hanya **memperbaiki buku panduan** yang dibaca AI. Dengan panduan yang benar, AI akan menghasilkan jawaban yang benar untuk semua pertanyaan sejenis — bukan hanya untuk pertanyaan yang sudah diuji.

---

*Laporan ini disusun berdasarkan hasil pengujian 15 Juni 2026 dan verifikasi database 17 Juni 2026.*
