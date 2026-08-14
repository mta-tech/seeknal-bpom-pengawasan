# Test case — domain `pengawasan`

**Dibuat:** 14 Agustus 2026 · **Total:** 149 test dalam 11 folder.
**Skema berkas:** mengikuti pola UAT `seeknal-bpom-neo/seeknal/tests/v1/singleturn/UAT-v2-compact`.

## Tujuan

Mengevaluasi apakah agent mampu menjawab **dengan membaca context dan skill** yang ada — bukan
menebak. Angka pada `assert_any_of` seluruhnya diambil dari eksekusi SQL langsung ke database
domain ini pada tanggal verifikasi, bukan ditulis tangan.

## Dua kelas test

**Kelas A — regresi.** Diambil dari SQL pair sistem lama yang sudah terbukti jalan, SQL-nya
dijalankan ulang untuk mendapat nilai assert. Tugasnya membuktikan context baru **tidak merusak**
jawaban yang selama ini benar. Folder bernomor 11 ke atas.

**Kelas B — diskriminasi.** Ditulis dari temuan audit, menyasar aturan yang versi context sekarang
belum atau salah mengajarkan. Ciri khasnya: versi lama gagal, versi baru harus lolos. Folder
berawalan `0x-B-`.

Kelas A saja tidak cukup: pemetaan menunjukkan SQL pair nyaris tidak menyentuh target/capaian,
kode tahap log, sentinel, maupun kolom tahap timeline — persis yang diperbaiki versi baru. Tanpa
kelas B, seluruh test akan lolos di kedua versi dan tidak membuktikan apa pun.

## Semantik assert

| Kunci | Arti |
|---|---|
| `assert_contains` | semua token wajib muncul (DAN). Token bertanda `\|` = daftar sinonim, cukup salah satu |
| `assert_any_of` | daftar grup; lolos bila **minimal satu grup** cocok penuh |
| `tolerance_pct` | hanya berlaku untuk token numerik di `assert_any_of`. `0` = cocok persis |

Angka tidak pernah ditaruh di `assert_contains` karena di sana toleransi tidak berlaku.

Beberapa test sengaja **tanpa angka**: yang diuji apakah agent menyatakan keterbatasan data dengan
benar. Perilaku itu tidak menua ketika data bertambah.

## Isi `note`

Tiap `note` memuat SQL yang menghasilkan angka assert, kode filter beserta tabel dan kolomnya,
sebab jebakannya, dan — untuk kelas B — apa yang membuat versi lama gagal.

## Folder

| Folder | Kelas | Test | Menguji |
|---|---|--:|---|
| `01-aturan-baru-balai-dan-balai-trim` | A | 14 | Kubus agregasi menggandakan bila periode_type tidak disaring, dan beragregasi pada tangga... |
| `02-bulan-dan-balai` | A | 14 | Cacah pengawasan iklan untuk satu balai pada satu tahun; menguji normalisasi nama balai d... |
| `03-gap-balai-pusat-dan-kesimpula` | A | 14 | Cacah pengawasan iklan untuk satu bulan; menguji pembatasan rentang tanggal yang benar. |
| `04-kesimpula-dan-kesimpulan-penilaian-balai` | A | 14 | Silang `kesimpulan_penilaian_pusat` dengan periode; menguji kelengkapan filter dari perta... |
| `05-kesimpulan-penilaian-pusat-dan-kom-kosmetika` | A | 14 | Cacah pengawasan iklan untuk satu nilai `kesimpulan_penilaian_pusat`; menguji pemetaan is... |
| `06-komoditi-dan-kom-rokok` | A | 14 | Silang komoditi dengan periode; menguji apakah kedua komponen pertanyaan masuk ke filter. |
| `07-komoditi-dan-media-iklan` | A | 13 | Silang `komoditi` dengan periode; menguji kelengkapan filter dari pertanyaan majemuk. |
| `08-mediaikl-dan-produk-dan-produsen` | A | 13 | Silang `media_iklan` dengan periode; menguji kelengkapan filter dari pertanyaan majemuk. |
| `09-tahun-dan-rekap-laporan-upt` | A | 13 | Peringkat balai; menguji normalisasi nama balai sebelum pengelompokan. |
| `10-upt-tidak-melaporkan-dan-vonis-per-komoditi` | A | 13 | Regresi dari pertanyaan nyata sistem lama; angka diverifikasi ulang ke database. |
| `11-x-dan-vonis-per-komoditi` | A | 13 | Regresi dari pertanyaan nyata sistem lama; angka diverifikasi ulang ke database. |

## Catatan pemeliharaan

Angka kelas A akan bergeser seiring ETL. `verification_date` menandai kapan diverifikasi;
`tolerance_pct` menyerap pergeseran wajar. Bila sebuah test gagal, periksa dulu apakah datanya
yang bergerak atau jawabannya yang salah — jangan langsung menurunkan toleransi.
