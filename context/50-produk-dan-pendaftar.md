Produk, NIE, dan pendaftar — semuanya teks bebas.

## Kolom

| Kolom | Isi |
|---|---|
| `nama_produk` | nama produk yang diiklankan |
| `nie` | nomor izin edar produk |
| `pendaftar` | pemilik/pendaftar produk |
| `nomor_surat` | penomoran surat pengawasan |

## ⚠️ `pendaftar` memuat string rusak

Sebagian nilai `pendaftar` adalah **teks yang tergandakan tanpa pemisah** — nama perusahaan yang
sama tertulis dua kali menyambung, hasil artefak proses penyalinan data.

> Akibatnya `COUNT(DISTINCT pendaftar)` **melebihkan** jumlah perusahaan: satu perusahaan terpecah
> menjadi beberapa varian rusak.

**Aturan:** perlakukan cacah pendaftar sebagai **diagnostik kasar**, bukan metrik perusahaan.
Bila pertanyaannya benar-benar tentang jumlah perusahaan, sebutkan keterbatasan ini. Untuk mencari
satu perusahaan tertentu, `ILIKE` dengan potongan nama yang cukup pendek agar menangkap varian
rusaknya juga (jalur **P3**).

## Sentinel

`nomor_surat`, `nie`, dan `pendaftar` sama-sama punya nilai bersentinel dalam porsi yang tidak
kecil. Bentuk sentinelnya berupa string kosong dan tanda hubung — dengan panjang yang berbeda antar
kolom.

> Buang sentinel **sebelum** `COUNT(DISTINCT ...)`, dan sebutkan porsi yang dibuang bila
> pertanyaannya tentang cakupan.

Sentinel pada `nie` punya makna tersendiri: produk diiklankan **tanpa nomor izin edar tercatat**.
Itu bukan kesalahan data — dan bisa jadi justru hal yang ingin ditanyakan. Jangan membuangnya
diam-diam bila pertanyaannya menyangkut produk tanpa NIE.

## Yang tidak ada

| Diminta | Status |
|---|---|
| **provinsi / kabupaten produsen** | **tidak ada kolomnya** — `95-batas-domain.md` |
| **golongan obat** (keras/bebas) | tidak ada penandanya |
| **jenis pangan** | tidak ada di tabel ini |
| **industri farmasi** sebagai entitas terpisah | hanya ada `pendaftar` sebagai teks |

## Rute

- Menyebut media/lokasi → **seberang** `20-media-dan-iklan.md`.
- Menyebut wilayah → **seberang** `95-batas-domain.md`.
