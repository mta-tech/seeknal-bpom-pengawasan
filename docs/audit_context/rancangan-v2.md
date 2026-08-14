# Rancangan context v2 — domain `pengawasan`

**Disusun:** 14 Agustus 2026 · **Status:** rancangan, belum dieksekusi.
**Dasar:** seluruh `docs/temuan_database/`, terutama `17_cakupan_context_vs_database.md` dan
bagian konsistensi di `10_data_quality_catalog.md`.
**Acuan mutlak:** kondisi database live, bukan pembacaan skema atau dokumen sebelumnya.

Seluruh isi dokumen ini khusus domain `pengawasan`. Istilah, kode, dan perilaku kolom di sini
**tidak berlaku untuk domain lain**.

**Ini domain paling sehat dari keempatnya**, dan itu perlu disebut di depan supaya v2 tidak
menambahkan aturan yang tidak dibutuhkan hanya karena domain lain membutuhkannya.

---

## A. Yang SALAH terhadap database

**Tidak ada.** Verifikasi menyeluruh atas seluruh halaman versi sekarang di domain ini:

- setiap nama tabel dan kolom yang dirujuk **ada** di database;
- setiap literal kode yang diajarkan **ada persis** di data, termasuk kapitalisasinya —
  `KOSMETIKA` dan `OBAT TRADISIONAL (OT)` diajarkan dengan ejaan yang benar untuk domain ini;
- aturan kubus agregasi (`periode_type` wajib disaring, kubus beragregasi berdasarkan tanggal
  selesai) terbukti benar terhadap warehouse;
- peringatan bahwa nilai media memakai garis bawah sehingga `ILIKE '%luar ruang%'` tidak cocok,
  terbukti benar.

Tidak ada satu pun halaman yang perlu dikoreksi isinya.

---

## B. Yang BELUM diajarkan

| Aspek | Bukti kondisinya | Ke halaman mana |
|---|---|---|
| Katalog enam klausul ketidaksesuaian | halaman menyebut tabel dan kunci join, tetapi **tidak** menyebut `id_klasifikasi` maupun `keterangan_ketidaksesuaian`, apalagi keenam kodenya | `40-ketidaksesuaian.md` |
| Kolom target mana yang dipakai domain ini | halaman menyebut nama tabel saja; ada tujuh kolom target | `85-target-capaian.md` |
| Grain `target_balai` = balai × komoditi | penjumlahan tanpa sadar grain melipatgandakan tujuh kali | `85-target-capaian.md` |
| Kolom tahap timeline — enam kolom | dipakai SQL lama; termasuk satu kolom yang **flag biner, bukan durasi** | `60-waktu-dan-durasi.md` |
| `status_code` di log — blok tahap versus blok penolakan | nol penyebutan; dictionary lengkapnya sudah ada di temuan | `45-status-dan-alur.md` |
| Filter kesamaan persis pada nama balai wajib `trim()` | `= 'BALAI POM DI DUMAI'` → 0 baris | `85-target-capaian.md` atau halaman balai |
| Nama pelaku di log terpecah oleh cara menulis gelar | peringkat orang tidak sahih — alasan kedua di samping alasan semantik yang sudah tertulis | `45-status-dan-alur.md` |

## C. Topik yang belum punya halaman sama sekali

**Tidak ada topik besar yang hilang.** Seluruh tambahan di atas masuk ke halaman yang sudah ada.

## D. Yang secara sadar TIDAK ditambahkan

Ini bagian penting, supaya v2 tidak menyeragamkan aturan lintas domain tanpa dasar:

- **Aturan pembersihan spasi dan kapitalisasi pada kolom berkode.** Diperiksa dengan normalisasi
  berlapis: kolom vonis, komoditi, media, status, dan klausul **tidak punya satu pun kembaran**.
  Kesamaan persis aman di sini. Satu-satunya pengecualian adalah nama balai.
- **Aturan pembersihan tanggal.** Kedua kolom tanggal bersih — tanpa lubang tahun, tanpa tanggal
  mustahil. Penjaga waktu tetap dipasang sebagai perilaku umum, tetapi tanpa daftar anomali,
  karena tidak ada yang perlu didaftar.

## Diagnosis: mengapa versi yang hidup sekarang gagal di titik-titik itu

Sebelum merancang v2, penting menyebut **pola kegagalannya**, karena kalau tidak, v2 hanya akan
menambal enam lubang yang kebetulan ketahuan dan meninggalkan lubang ketujuh terbuka.

Dari seluruh temuan, kegagalannya jatuh ke empat pola — dan hanya satu di antaranya soal "kurang
konten".

### Pola 1 — Aturan menempel pada KOLOM, padahal kesalahan terjadi pada OPERASI

Ini pola paling merusak, dan buktinya paling bersih.

Normalisasi nama balai **sudah** diajarkan versi sekarang — di halaman target, untuk keperluan **join**.
Tetapi jebakan sesungguhnya muncul saat **filter kesamaan persis**, pada kolom yang sama, dengan
teknik yang sama. Aturannya ada di repositori, tekniknya dikenal, tetapi tidak pernah sampai ke
operasi tempat kesalahan terjadi.

Artinya: menempelkan aturan pada nama kolom tidak cukup. Satu kolom berperilaku berbeda saat
disaring, dikelompokkan, di-join, dan diperingkat.

### Pola 2 — Halaman yang MEMILIKI topik justru memberi arahan yang salah

Lebih berbahaya daripada tidak ada halaman sama sekali. Kalau tidak ada aturan, agent memakai
kuota probe dan sering menemukan sendiri; kalau ada aturan yang salah, ia mengikutinya dengan
yakin dan hasilnya terlihat masuk akal.

### Pola 3 — Pengetahuan berhenti di `docs/temuan_database`, tidak pernah menyeberang

Sebagian besar "lubang" ternyata **sudah terdokumentasi dengan benar** di direktori temuan sejak
awal. Yang gagal penyalurannya. Tidak ada mekanisme apa pun yang memberi tahu bahwa sebuah temuan
belum punya pasangan di `context/`.

### Pola 4 — Prosa yang tidak pernah dieksekusi

Kesalahan nama kolom dan klaim perilaku yang keliru sama-sama lahir dari kalimat yang ditulis
berdasarkan ingatan struktur, bukan dari query yang dijalankan. Tidak ada satu pun mekanisme yang
menangkapnya sampai audit ini.

---

## Solusi: lima prinsip v2

v2 **bukan penulisan ulang**. Struktur `after-insight-v1` — orkestrator yang merutekan, halaman topik kecil, skill
tipis untuk penegakan — terbukti bekerja dan dipertahankan. Yang ditambahkan adalah lima hal yang
menjawab empat pola di atas.

### Prinsip 1 — Matriks operasi pada tiap kolom berkode

Menjawab Pola 1. Setiap kolom yang punya jebakan mendapat baris ringkas: apa yang harus dilakukan
saat **menyaring**, **mengelompokkan**, **men-join**, dan **memeringkat**. Bukan paragraf baru —
satu tabel kecil, karena bentuk tabel memaksa keempat operasi dipikirkan, sedangkan prosa
membiarkan tiga di antaranya terlupa.

Bentuknya:

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| *(kolom)* | *(aturan)* | *(aturan)* | *(aturan)* | *(aturan)* |

Sel yang tidak punya jebakan ditulis "biasa" — supaya terlihat bahwa ia sudah dipertimbangkan,
bukan terlewat.

### Prinsip 2 — Kebersihan teks naik ke Gerbang, bukan tinggal di halaman

Menjawab Pola 1 juga. Cacat spasi dan kapitalisasi membelah hasil **tanpa pesan kesalahan**, dan
itu terjadi di operasi apa pun. Karena itu ia jadi butir pemeriksaan di Gate 5, bukan catatan di
satu halaman yang mungkin tidak dibuka.

### Prinsip 3 — Daftar karantina yang eksplisit

Kolom dan tabel yang **tidak boleh dikutip**, beserta alasannya dalam satu kalimat, dan apa yang
harus dipakai sebagai gantinya. Larangan yang tidak menawarkan pengganti akan dilanggar.

### Prinsip 4 — Penjaga waktu sebagai perilaku, bukan sebagai fakta

Menjawab pertanyaan yang sering salah: "sejak kapan", "paling awal", "tren per tahun".

Yang **tidak** boleh ditulis adalah fakta yang akan basi ("target hanya 2024", "timeline hanya
2026"). Yang ditulis adalah pemeriksaannya: sebelum menyimpulkan tren atau menyebut periode
terjauh, pastikan sumbernya benar-benar mencakup periode yang ditanya, dan batasi tahun ke rentang
operasional. Kalimat itu tidak pernah menua, dan ia menangkap kasus yang belum terjadi.

### Prinsip 5 — Manifes verifikasi: v2 yang memeriksa dirinya sendiri

Menjawab Pola 3 dan 4, dan ini yang membedakan v2 dari sekadar v1-yang-diperbaiki.

Tiap halaman versi sekarang diakhiri blok manifes yang mendaftar **nama tabel, nama kolom, dan literal nilai**
yang diajarkannya. Satu skrip yang di-commit di repo menjalankan tiga pemeriksaan terhadap
database domainnya sendiri:

1. setiap tabel dan kolom di manifes **ada**;
2. setiap literal nilai **ada persis** di data, termasuk spasi dan kapitalisasinya;
3. setiap kolom berkode di database **muncul di manifes salah satu halaman**, atau terdaftar
   sebagai sengaja-diabaikan.

Pemeriksaan ketiga itulah yang menutup Pola 3: temuan yang belum menyeberang ke context akan
muncul sebagai kolom tak-terdaftar.

Skripnya **wajib memuat kontrol negatif** — nama kolom karangan harus dilaporkan tidak ditemukan.
Tanpa itu angka cakupan tidak bisa dipercaya; versi pertama alat ukur audit ini sempat melaporkan
seluruh kolom tercakup karena bug pemisah kolom, dan hasil mustahil itu nyaris lolos.

---

## Yang sengaja TIDAK diubah

- **Aturan chart, ekspor S3, forecast, dan anomaly** — disalin apa adanya, seperti pada versi sekarang.
- **Struktur gerbang 0-5** dan pola PAGE MAP — terbukti bekerja.
- **Larangan angka di halaman context** — v2 tetap mengajarkan pemetaan, kode filter, dan arti
  istilah; bukan cacah baris, persentase, atau nilai agregat.
- **Halaman yang sudah benar** — daftar berstatus SUDAH di dokumen cakupan berfungsi melindunginya
  dari perubahan yang tidak perlu.

---

## Urutan eksekusi

1. **Perbaiki yang SALAH lebih dulu.** Aturan menyesatkan lebih berbahaya daripada aturan yang
   tidak ada.
2. **Karantina** — mencegah angka tidak sahih keluar sebagai jawaban.
3. **Penjaga waktu dan kebersihan teks di Gate 5** — menutup kelas kesalahan, bukan satu kasusnya.
4. **Matriks operasi** pada kolom yang sudah diketahui berjebakan.
5. **Topik yang belum ada halamannya.**
6. **Manifes + skrip verifikasi**, lalu jalankan untuk membuktikan lima langkah di atas benar.

## Gerbang pilot

| Metrik | Gerbang |
|---|---|
| PASS suite yang ada | **tidak turun** |
| Jawaban pada skenario yang sudah benar | **nol yang bergerak** |
| SQL per turn | **tidak naik** |
| Skrip verifikasi manifes | **nol pelanggaran**, dengan kontrol negatif lulus |
| Pertanyaan yang menyentuh kolom berjebakan | memakai normalisasi yang benar sesuai operasinya |
| Pertanyaan "sejak kapan / paling awal" | membatasi tahun, tidak mengembalikan tahun mustahil |

⚠️ Satu hal yang tidak akan tertangkap suite mana pun: apakah agent benar-benar **membuka** halaman
yang relevan. Manifes memverifikasi isi halaman benar, bukan bahwa halamannya dibaca. Itu tetap
perlu pembacaan manual atas jejak beberapa jawaban.
