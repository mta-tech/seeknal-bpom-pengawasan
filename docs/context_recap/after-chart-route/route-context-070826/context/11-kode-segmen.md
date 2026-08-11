Kode segmen — jenis_pangan & kategori_pangan: AMDK, garam, formula bayi, dan cara menurunkan yang lain

`jenis_pangan` = INDUK · `kategori_pangan` = ANAK dari hierarki yang sama. **Mulai dari induk.**
Keduanya **tidak terdaftar di `data_dictionary` sama sekali** — pemetaannya empiris, nyatakan itu
di jawaban.

## Anchor terverifikasi

| Segmen | ERBA | ERLA |
|---|---|---|
| AMDK | `jenis_pangan IN ('1401','1402')` | `jenis_pangan IN ('651','652','655')` |
| Garam beryodium | `jenis_pangan = '1204'` — kode **INDUK**, mencakup SELURUH varian garam | tidak ada namespace `1204`; pakai `kategori_pangan='12010103'` atau `nama_kategori ILIKE '%garam%'` (lebih lebar, ikut menjaring bumbu) |
| Formula bayi (ketat) | `jenis_pangan IN ('1301','1302')` | `jenis_pangan IN ('604','622','624')` |

"Formula bayi" ≠ "produk bayi & anak" (lebih luas, mencakup jauh lebih banyak kode) — bila
pertanyaan tidak jelas mana yang dimaksud, tanya.

## Dua aturan yang gampang dilanggar tanpa sadar

**Nol irisan namespace.** `jenis_pangan` tidak punya satu nilai pun yang sama antara ERBA dan ERLA —
panjang dan rentangnya berbeda. Tiga anchor di atas hanyalah contoh dari sifat yang berlaku untuk
**seluruh** segmen, termasuk dua ratusan lebih yang tidak terdaftar di sini. Kode yang dibawa
lintas sistem **selalu** mengembalikan 0, dan 0 itu berarti namespace salah.

**Induk sebelum anak.** Kode induk mencakup seluruh keluarganya; kode anak adalah satu varian di
dalamnya dan diam-diam membuang saudara-saudaranya. Turun ke anak hanya bila pertanyaan menyebut
varian spesifik itu. Untuk melihat berapa anak yang dipayungi sebuah induk:
`SELECT kategori_pangan, COUNT(*) … WHERE jenis_pangan='<induk>' GROUP BY 1`.

## Menurunkan segmen yang tidak ada di tabel atas

1. Probe `nama_kategori` untuk menemukan nilai persisnya (`12-nama-kategori.md`).
2. Dari baris yang cocok, lihat `jenis_pangan` / `kategori_pangan` yang menyertainya —
   `SELECT jenis_pangan, kategori_pangan, COUNT(*) … WHERE nama_kategori='<persis>' GROUP BY 1,2`.
3. Bila pemetaannya bersih 1:1, hitung dengan kodenya (lebih murah, bisa dipakai ulang). Bila
   tersebar ke beberapa kode, hitung dengan `nama_kategori` dan sebutkan sebarannya.
   Satu nilai `nama_kategori` bisa bersih 1:1 ke satu kode di satu sistem tetapi tersebar ke
   beberapa kode di sistem lain — periksa tiap sisi, jangan menyimpulkan dari salah satunya.

## Breakdown per kategori pangan

Kelompokkan pada prefiks **2 digit**: `LEFT(kategori_pangan, 2)` (mis. `07` bakeri · `08` daging ·
`13` PKGK). Lebih dalam dari dua digit tidak sebanding antar sistem — ERBA dan ERLA memakai
kedalaman berbeda dan prefiks yang tampak sama bukan kategori yang sama.

## Rute

- **KEMBALI** ke `10-segmen-produk.md` bila ternyata segmennya teks bebas.
- Segmen tidak jatuh ke kode mana pun → **TURUN** `12-nama-kategori.md`, jangan menjawab dengan
  metrik lain.
