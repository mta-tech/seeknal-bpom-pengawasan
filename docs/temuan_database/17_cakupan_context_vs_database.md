# 17. Cakupan context terhadap kondisi database `pengawasan`

Dokumen ini menjawab satu pertanyaan: **apakah yang diajarkan ke agent sudah menutup**
**kondisi database yang sebenarnya.** Sumbernya profiling langsung ke warehouse, bukan
pembacaan skema. Seluruh isi dokumen ini khusus domain `pengawasan`; istilah, kode, dan
perilaku kolom di sini **tidak berlaku untuk domain lain** dan tidak boleh dipinjam.

## Cara membacanya

Tiap kolom data ditempatkan di salah satu dari empat kuadran, dari dua pertanyaan:
apakah **context/skill menyebutnya**, dan apakah **SQL sistem lama pernah memakainya**.

| Kuadran | Arti | Tindakan |
|---|---|---|
| **A — aman** | diajarkan, dan pernah dipakai | tidak ada |
| **B — berlebih** | diajarkan, tapi tak pernah dipakai | biarkan; menyiapkan pertanyaan yang belum muncul |
| **C — regresi** | **tidak** diajarkan, padahal SQL lama memakainya | tutup; kemampuan yang hilang saat migrasi |
| **D — titik buta** | tidak diajarkan, dan tak pernah dipakai siapa pun | nilai satu per satu; sebagian memang tak perlu |

Dari **68 kolom data** di **7 tabel** (kolom pembukuan ETL `sync`/`last_updated` tidak dihitung):

| Kuadran | Jumlah | Porsi |
|---|--:|--:|
| A | 31 | 45% |
| B | 7 | 10% |
| C | 11 | 16% |
| D | 19 | 27% |

> Angka di tabel ini menggambarkan **cakupan dokumen**, bukan isi data. Angka isi data
> tidak dibawa ke halaman `context/` — halaman itu mengajarkan pemetaan, bukan nilai.

## Batas alat ukur ini — wajib dibaca sebelum menindak kuadran C dan D

Penempatan kuadran dihitung dengan mencocokkan **nama kolom** ke teks context. Cara itu punya dua
kelemahan yang sudah terbukti, dan keduanya membuat kuadran C dan D **melebih-lebihkan** lubang.

**Pertama, aturan tingkat tabel tidak terdeteksi.** Kalau context mengajarkan sebuah aturan tentang
satu tabel tanpa menyebut kolomnya satu per satu, semua kolom tabel itu jatuh ke kuadran D seolah
tak dikenal. Kasus nyatanya di domain ini adalah aturan kubus agregasi — bahwa `periode_type`
bernilai dua dan wajib disaring salah satu — yang **sudah tertulis dengan benar** di
`00-menghitung.md`, namun kolom-kolom kubusnya tetap muncul di kuadran D. Itu artefak pengukuran,
**bukan lubang**.

**Kedua, alat ukur bisa gagal diam-diam.** Versi pertama pengukuran ini melaporkan seluruh kolom
tercakup — hasil yang mustahil. Sebabnya pemisah kolom tertulis sebagai teks literal, bukan tab,
sehingga nama kolom menjadi string kosong dan pola pencarian cocok ke apa saja. Setiap pengukuran
ulang wajib menyertakan **kontrol negatif**: nama kolom yang sengaja dikarang harus dilaporkan
tidak ditemukan. Tanpa itu, angka cakupan tidak boleh dipercaya.

**Karena itu:** perlakukan kuadran C dan D sebagai **daftar kandidat**, bukan vonis. Yang sudah
diverifikasi satu per satu terhadap warehouse ada di bagian *Lubang yang terbukti* di bawah —
hanya itu yang layak ditindak.

## C — Regresi: dipakai sistem lama, tidak diajarkan sekarang

Ini kelompok paling mendesak. SQL sistem lama membuktikan kolomnya **memang dipakai untuk**
**menjawab pertanyaan nyata**; kalau context sekarang tidak menyebutnya, kemampuan itu hilang
tanpa ada yang sadar.

| Tabel | Kolom | Kondisi data |
|---|---|---|
| `coverage_balai` | `kabupaten_kota` | kardinalitas 77% dari baris |
| `mv_pengawasan_agg` | `jumlah_pengawasan` | ±61 nilai |
| `mv_pengawasan_ketidaksesuaian` | `id_klasifikasi` | berkode, ±6 nilai |
| `mv_pengawasan_ketidaksesuaian` | `keterangan_ketidaksesuaian` | berkode, ±6 nilai |
| `mv_pengawasan_timeline` | `direktur_pusat` | berkode, ±2 nilai · kosong 20% |
| `mv_pengawasan_timeline` | `kabalai_direktur` | ±427 nilai · kosong 20% |
| `mv_pengawasan_timeline` | `mulai_kabalai` | ±243 nilai · kosong 4% |
| `mv_pengawasan_timeline` | `tanggal_kirim_direktur` | ±834 nilai · kosong 20% |
| `mv_pengawasan_timeline` | `tanggal_kirim_kabalai` | ±1836 nilai · kosong 4% |
| `mv_pengawasan_timeline` | `tanggal_kirim_pusat` | ±1730 nilai · kosong 4% |
| `target_balai` | `target_pengawasan` | berkode, ±53 nilai |

## D — Titik buta: tak dikenal context maupun sistem lama

Sebagian memang tidak perlu diajarkan (id internal, indeks posisi array, stempel waktu baris).
Sisanya adalah kemampuan yang belum pernah dipakai siapa pun.

| Tabel | Kolom | Kondisi data | Perlu? |
|---|---|---|---|
| `coverage_balai` | `id_balai` | kardinalitas 13% dari baris | tidak — teknis |
| `coverage_balai` | `id_kabupaten` | kardinalitas 77% dari baris | tidak — teknis |
| `mv_pengawasan_agg` | `avg_durasi_hari` | ±451 nilai | nilai manual |
| `mv_pengawasan_agg` | `jumlah_nie_unik` | berkode, ±43 nilai | nilai manual |
| `mv_pengawasan_agg` | `jumlah_pendaftar_unik` | berkode, ±34 nilai | nilai manual |
| `mv_pengawasan_agg` | `jumlah_produk_unik` | berkode, ±48 nilai | nilai manual |
| `mv_pengawasan_agg` | `jumlah_surat_unik` | berkode, ±22 nilai | nilai manual |
| `mv_pengawasan_agg` | `max_durasi_hari` | ±61 nilai | nilai manual |
| `mv_pengawasan_agg` | `min_durasi_hari` | berkode, ±53 nilai | nilai manual |
| `mv_pengawasan_agg` | `tanggal_periode` | ±1276 nilai | nilai manual |
| `mv_pengawasan_log` | `fullname` | ±1334 nilai | nilai manual |
| `mv_pengawasan_log` | `status_code` | berkode, ±16 nilai | nilai manual |
| `mv_pengawasan_log` | `tanggal_proses` | ±70632 nilai · kosong 16% | nilai manual |
| `target_balai` | `target_penandaan` | kardinalitas 48% dari baris | nilai manual |
| `target_balai` | `target_pengujian` | kardinalitas 48% dari baris | nilai manual |
| `target_balai` | `target_pengujian_pangan` | kardinalitas 13% dari baris · kosong 3% | nilai manual |
| `target_balai` | `target_pengujian_pangan_fortifikasi` | berkode, ±19 nilai · kosong 3% | nilai manual |
| `target_balai` | `target_sarana_distribusi` | kardinalitas 33% dari baris | nilai manual |
| `target_balai` | `target_sarana_produksi` | kardinalitas 14% dari baris | nilai manual |

## Katalog nilai kolom berkode

Kolom yang nilainya terbatas dikatalogkan penuh di bawah — inilah "kode filter" yang boleh
diajarkan. Yang tidak boleh dibawa ke `context/` adalah **cacah barisnya**, karena itu
bergeser tiap ETL; karena itu di sini hanya nilainya yang didaftar, tanpa jumlah.

### `mv_pengawasan` . `jenis_pembuat_iklan`  ·  kuadran B

_(string kosong)_, `PELAKU USAHA`, `PERORANGAN`

⚠️ Penanda kosong di kolom ini: string kosong — perlakukan sebagai "belum diisi", bukan sebagai kategori.

### `mv_pengawasan` . `kesimpulan_penilaian_akhir`  ·  kuadran A

`MK`, `Null`, `TMK`

⚠️ Penanda kosong di kolom ini: `Null` — perlakukan sebagai "belum diisi", bukan sebagai kategori.

### `mv_pengawasan` . `kesimpulan_penilaian_balai`  ·  kuadran A

`MK`, `TMK`, `TMK MAYOR`, `TMK MINOR`, `Null`

⚠️ Penanda kosong di kolom ini: `Null` — perlakukan sebagai "belum diisi", bukan sebagai kategori.

### `mv_pengawasan` . `kesimpulan_penilaian_pusat`  ·  kuadran A

`MK`, `Null`, `TMK`, `TMK KRITIKAL`, `TMK MINOR`, `TMK MAYOR`

⚠️ Penanda kosong di kolom ini: `Null` — perlakukan sebagai "belum diisi", bukan sebagai kategori.

### `mv_pengawasan` . `komoditi`  ·  kuadran A

`KOSMETIKA`, `ROKOK`, `PRODUK PANGAN`, `OBAT`, `OBAT TRADISIONAL (OT)`, `SUPLEMEN KESEHATAN`, `OBAT KUASI`

### `mv_pengawasan` . `media_iklan`  ·  kuadran A

`ELEKTRONIK`, `MEDIA_LUARRUANG`, `CETAK`, `MEDIA_LAIN`, _(string kosong)_

⚠️ Penanda kosong di kolom ini: string kosong — perlakukan sebagai "belum diisi", bukan sebagai kategori.

### `mv_pengawasan_agg` . `jenis_pembuat_iklan`  ·  kuadran B

_(string kosong)_, `PELAKU USAHA`, `PERORANGAN`

⚠️ Penanda kosong di kolom ini: string kosong — perlakukan sebagai "belum diisi", bukan sebagai kategori.

### `mv_pengawasan_agg` . `kesimpulan_penilaian_akhir`  ·  kuadran A

`Null`, `MK`, `TMK`

⚠️ Penanda kosong di kolom ini: `Null` — perlakukan sebagai "belum diisi", bukan sebagai kategori.

### `mv_pengawasan_agg` . `kesimpulan_penilaian_balai`  ·  kuadran A

`MK`, `TMK`, `TMK MAYOR`, `TMK MINOR`, `Null`

⚠️ Penanda kosong di kolom ini: `Null` — perlakukan sebagai "belum diisi", bukan sebagai kategori.

### `mv_pengawasan_agg` . `kesimpulan_penilaian_pusat`  ·  kuadran A

`MK`, `Null`, `TMK`, `TMK KRITIKAL`, `TMK MINOR`, `TMK MAYOR`

⚠️ Penanda kosong di kolom ini: `Null` — perlakukan sebagai "belum diisi", bukan sebagai kategori.

### `mv_pengawasan_agg` . `komoditi`  ·  kuadran A

`PRODUK PANGAN`, `KOSMETIKA`, `OBAT`, `OBAT TRADISIONAL (OT)`, `ROKOK`, `SUPLEMEN KESEHATAN`, `OBAT KUASI`

### `mv_pengawasan_agg` . `media_iklan`  ·  kuadran A

`ELEKTRONIK`, `MEDIA_LUARRUANG`, `CETAK`, `MEDIA_LAIN`, _(string kosong)_

⚠️ Penanda kosong di kolom ini: string kosong — perlakukan sebagai "belum diisi", bukan sebagai kategori.

### `mv_pengawasan_agg` . `periode_type`  ·  kuadran B

`day`, `month`

### `mv_pengawasan_ketidaksesuaian` . `keterangan_ketidaksesuaian`  ·  kuadran C

`Iklan dengan klaim kesehatan – Iklan yang tidak sesuai dengan ketentuan`, `Iklan dengan kalimat superlatif, komparatif, & mendiskreditkan (kecuali membandingkan dengan produk sendiri)`, `Iklan menyesatkan karena tidak sesuai dengan karakteristik/komposisi produk`, `Iklan dengan kata-kata, figure, logo, lambang yang tidak boleh diiklankan`, `Iklan produk yang tidak boleh diiklankan (produk minuman beralkohol, Pangan Olahan untuk Keperluan Medis Khusus (PKMK), formula bayi dan formula lanjutan)`, `Iklan yang melanggar norma-norma yang berlaku (adegan berbahaya, SARA, dll)`

### `mv_pengawasan_log` . `status_label`  ·  kuadran B

`MT - Pembuatan SPK`, `Operator - Draft Sampling`, `Deputi MT - Pembuatan SPK`, `Supervisor - Verifikasi`, `TPS - Penerimaan SPU`, `Penguji - Entri Hasil Pengujian`, `Sampel Rujukan Selesai`, `Penyelia - Pembuatan SPP`, `Supervisor 2 - Verifikasi`, _(SQL NULL)_

⚠️ Penanda kosong di kolom ini: SQL NULL — perlakukan sebagai "belum diisi", bukan sebagai kategori.

### `mv_pengawasan_log` . `trx_steps`  ·  kuadran B

`pusat`, `draft`, `spv_1_pusat`, `spv_1`, `kepala_balai`, `direktur`, `selesai`, `spv_2_pusat`, `spv_2`, `ditolak_spv_1`, `ditolak_pusat`, `ditolak_spv_1_pusat`, `ditolak_kepala_balai`, `ditolak_spv_2`, `ditolak_direktur`, `ditolak_spv_2_pusat`

### `target_balai` . `komoditi`  ·  kuadran A

`Obat Kuasi`, `Produk Pangan`, `Obat Tradisional (OT)`, `Obat`, `Kosmetika`, `Suplemen Kesehatan`, `Rokok`


---

## Apa yang diceritakan database ini

`pengawasan` merekam **penilaian terhadap iklan produk** — apakah sebuah iklan memenuhi ketentuan,
di media mana ia tayang, dan klausul apa yang dilanggar kalau tidak.

| Lapis | Cerita | Tabel |
|---|---|---|
| Peristiwa | iklan produk apa yang dinilai, di media apa, oleh balai mana, vonisnya apa | `mv_pengawasan` |
| Pelanggaran | klausul mana yang dilanggar | `mv_pengawasan_ketidaksesuaian` |
| Perjalanan berkas | tahap demi tahap sampai disetujui | `mv_pengawasan_log` + `mv_pengawasan_timeline` |
| Rencana vs capaian | target dan cakupan wilayah | `target_balai` + `coverage_balai` |
| Kubus | agregasi siap pakai dari lapis peristiwa | `mv_pengawasan_agg` |

**Ciri khas domain ini yang tidak berlaku di tempat lain:** tabel peristiwanya **tidak memuat SQL
NULL sama sekali** — kekosongan selalu ditulis sebagai teks penanda. Karena itu setiap filter
berbasis `IS NULL` di sini tidak akan pernah menyaring apa pun.

Ciri kedua: penilaian direkam di **tiga kolom vonis berbeda** (balai, pusat, akhir) yang himpunan
nilainya tidak sama. Satu tingkat gradasi hanya ada di kolom pusat. Karena itu "berapa yang TMK"
tidak punya jawaban tunggal sampai ditentukan kolom mana yang dimaksud.

---

## Lubang yang terbukti — dan sifatnya: PENYALURAN, bukan penemuan

Satu hal yang harus dibaca sebelum daftar di bawah, karena ia mengubah ke mana perbaikan diarahkan.

Sebagian besar lubang di bawah **bukan** berarti temuannya belum pernah dibuat. Diperiksa ulang
14 Agustus 2026, mayoritasnya **sudah terdokumentasi dengan benar di direktori ini sejak awal** —
lengkap dengan katalog nilai, grain, dan jebakannya. Yang gagal adalah **penyalurannya ke
`context/`**: halaman context menyebut nama tabelnya lalu berhenti, sehingga pengetahuan yang sudah
dimiliki repositori ini tidak pernah sampai ke agent yang menjawab pertanyaan.

Karena itu tiap butir di bawah mencantumkan **berkas topik** tempat rinciannya tinggal. Dokumen ini
mencatat **pengukurannya**; rincian datanya tetap di berkas topiknya masing-masing, dan di sanalah
pembaruan berikutnya harus ditulis.

Implikasinya untuk cara kerja: menambah dokumen temuan **tidak dengan sendirinya** menutup lubang.
Setiap temuan yang mengubah cara menjawab harus punya pasangan di `context/` atau di skill.

### Daftar temuan

### 1. Klausul pelanggaran punya katalog kode, dan katalognya tidak diajarkan

> 📄 Rincian datanya tinggal di `06_tabel_ketidaksesuaian.md` — katalog enam klausul lengkap dengan korelasinya

Halaman `40-ketidaksesuaian.md` menyebut nama tabel dan kunci join-nya, lalu berhenti. Ia **tidak
pernah menyebut dua kolom yang memuat isinya**: `id_klasifikasi` dan `keterangan_ketidaksesuaian`.

**Bukti kondisi:** kolom itu berisi tepat **enam klausul**, dan pemetaannya tetap:

| Kode | Klausul |
|---|---|
| 1 | Iklan produk yang tidak boleh diiklankan (minuman beralkohol, PKMK, formula bayi dan formula lanjutan) |
| 2 | Iklan dengan klaim kesehatan — iklan yang tidak sesuai dengan ketentuan |
| 3 | Iklan menyesatkan karena tidak sesuai dengan karakteristik/komposisi produk |
| 4 | Iklan yang melanggar norma-norma yang berlaku (adegan berbahaya, SARA, dan sejenisnya) |
| 5 | Iklan dengan kalimat superlatif, komparatif, dan mendiskreditkan (kecuali membandingkan dengan produk sendiri) |
| 6 | Iklan dengan kata-kata, figur, logo, lambang yang tidak boleh diiklankan |

**Akibatnya:** pertanyaan seperti *"berapa iklan dengan klaim kesehatan yang melanggar"* atau
*"pelanggaran superlatif terbanyak di balai mana"* tidak bisa diresolusi langsung — agent harus
menebak atau memakai kuota probe untuk menemukan sesuatu yang sebenarnya tetap dan boleh diajarkan.
Ini justru bentuk "kode filter" yang memang boleh masuk context.

### 2. `target_balai` — tabelnya disebut, kolom targetnya tidak

> 📄 Rincian datanya tinggal di `07_tabel_coverage_target.md` — grain, batas tahun, dan tujuh kolom target

Halaman `85-target-capaian.md` menyebut nama tabel dan kunci join, lalu berhenti.

**Bukti kondisi:** grain-nya **balai × komoditi** (76 balai × 7 komoditi), bukan satu baris per
balai. `tahun` hanya berisi **2024**. Ada **tujuh kolom target berbeda**; untuk domain ini yang
relevan adalah `target_pengawasan`, sisanya milik kegiatan lain dan **tidak boleh dipakai di sini**.

**Akibatnya:** pertanyaan capaian tidak bisa dijawab tanpa menebak kolom, dan menjumlahkan tanpa
sadar grain-nya akan melipatgandakan target tujuh kali. Untuk tahun selain 2024 tidak ada
pembanding sama sekali — itu harus dikatakan, bukan dijawab nol.

### 3. Kolom tahap di `mv_pengawasan_timeline` tidak diajarkan

> 📄 Rincian datanya tinggal di `04_tabel_timeline_durasi.md` — kolom tahap, termasuk yang ternyata flag biner

`tanggal_kirim_kabalai`, `tanggal_kirim_pusat`, `tanggal_kirim_direktur`, `mulai_kabalai`,
`kabalai_direktur`, `direktur_pusat` — kolom-kolom inilah yang menjawab "berkas tertahan di tahap
mana". SQL sistem lama memakainya; context sekarang hanya menyebut nama tabelnya.

**Bukti kondisi:** kolom tahap direktur kosong pada sekitar seperlima baris, sedangkan tahap awal
hampir selalu terisi. Kekosongan itu **deterministik** — berkas yang tidak pernah naik ke tahap itu
memang tidak punya tanggalnya. Rata-rata yang menyertakan baris kosong akan salah.

### 4. `status_code` di log tidak diajarkan

> 📄 Rincian datanya tinggal di `03_tabel_log_workflow.md` — dictionary lengkap `status_code` × `status_label`

Log memakai `status_code` numerik dengan blok nilai kecil untuk tahap normal dan **blok nilai besar
yang terpisah jauh** untuk jalur penolakan. Pemisahan blok itulah yang membuat pertanyaan "berapa
yang ditolak dan di tahap mana" bisa dijawab. Context tidak menyebut kolom ini sama sekali.

---

## Yang sudah benar dan tidak perlu diubah

Agar audit ini jujur dua arah: aturan kubus agregasi di domain ini **sudah diajarkan dengan benar**.
Context sudah menyatakan bahwa `periode_type` bernilai dua dan wajib disaring salah satu, dan bahwa
kubus beragregasi berdasarkan tanggal selesai sehingga trennya tidak sebanding dengan tren dari
tabel fakta. Pemeriksaan ulang terhadap warehouse membenarkan keduanya.

---

## Yang TIDAK ditutupi oleh daftar pertanyaan mana pun

Ini menjawab langsung pertanyaan "apakah pertanyaan yang ada sudah mencakup semua kondisi": **tidak.**

Terbukti nol penyebutan di kedua korpus pertanyaan — seluruh kolom hitungan unik di kubus
(`jumlah_nie_unik`, `jumlah_pendaftar_unik`, `jumlah_produk_unik`, `jumlah_surat_unik`), kolom
durasi ringkas di kubus, serta identitas pelaku di log.

Konsekuensinya untuk cara kerja kita: **daftar pertanyaan tidak bisa dipakai sebagai ukuran
kelengkapan context.** Kalau context hanya menutupi yang pernah ditanyakan, ia akan gagal pada
pertanyaan pertama yang keluar dari kebiasaan. Ukuran yang benar adalah kuadran C dan D di atas.

---

## Pencocokan temuan konsistensi terhadap `context/` yang hidup sekarang

Diverifikasi 14 Agustus 2026, dengan **kondisi database sebagai acuan mutlak**. Tiap temuan
konsistensi penulisan dan anomali tanggal — rinciannya di berkas kualitas data domain ini —
dicocokkan ke apa yang benar-benar tertulis di `context/` dan `skills/` saat ini.

Kolom **Status** memakai tiga nilai, dan bedanya penting:

| Status | Arti |
|---|---|
| **SUDAH** | aturannya ada dan benar — jangan diubah |
| **BELUM** | aturannya tidak ada di mana pun — perlu ditambahkan |
| **SALAH ARAH** | ada aturan, tetapi isinya menyesatkan terhadap kondisi database — **perbaiki lebih dulu daripada menambah apa pun** |


| Temuan | Status | Yang tertulis sekarang | Perubahan yang dibutuhkan |
|---|---|---|---|
| Spasi ekor pada nama balai membuat filter kesamaan persis nol baris | **BELUM** | `85-target-capaian.md` mengajarkan `lower(trim(...))` **hanya untuk join** ke tabel target | Tambahkan aturan: filter kesamaan persis pada `nama_balai` wajib lewat `trim()`, atau memakai nilai hasil probe apa adanya |
| Nama pelaku di log terpecah oleh cara menulis gelar | **BELUM** | `45-status-dan-alur.md` sudah membatasi pertanyaan "siapa menyetujui", tetapi alasannya semantik — bukan karena nama terpecah | Tambahkan sebagai alasan kedua: peringkat berbasis nama orang tidak sahih karena satu orang muncul sebagai beberapa entri |
| Nilai media memakai garis bawah, tidak cocok dengan frasa berspasi milik pengguna | **SUDAH** | `20-media-dan-iklan.md` sudah memperingatkan `ILIKE '%luar ruang%'` tidak akan cocok, dan menyuruh ambil daftar nilainya lebih dulu | — |
| Kolom berkode lain **bersih** — vonis, komoditi, media, status, klausul tanpa kembaran | **SUDAH memadai** | context memakai kesamaan persis pada kode-kode itu | Tidak perlu diubah. Catat sebagai keputusan sadar supaya domain ini tidak ikut diberi aturan pembersihan yang tidak diperlukan |
| Tanggal bersih, tanpa lubang maupun tanggal mustahil | **SUDAH memadai** | tidak ada aturan pembersihan tanggal, dan memang tidak dibutuhkan | Tidak perlu diubah |

### Urutan yang disarankan

**SALAH ARAH lebih dulu.** Aturan yang menyesatkan lebih berbahaya daripada aturan yang tidak ada:
kalau tidak ada aturan, agent akan memakai kuota probe dan sering menemukan sendiri; kalau ada
aturan yang salah, ia akan mengikutinya dengan yakin dan hasilnya terlihat masuk akal.

Sesudah itu baru **BELUM**, didahulukan yang paling sering mengubah angka jawaban.

Yang berstatus **SUDAH** tidak boleh disentuh — daftar ini juga berfungsi melindunginya dari
perubahan yang tidak perlu.

> Dokumen ini adalah **acuan perubahan** untuk `context/` dan `skills/`. Perubahan itu sendiri
> belum dikerjakan; tidak ada satu pun berkas context atau skill yang diubah saat dokumen ini
> ditulis.
