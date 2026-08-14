Media, lokasi, dan pembuat iklan.

## `media_iklan` — perhatikan bentuk penulisannya

Berisi kanal tempat iklan tayang. Nilainya mencakup kanal elektronik, cetak, luar ruang, dan satu
nilai untuk kanal lainnya — ditambah **string kosong** pada sebagian baris.

⚠️ **Penulisannya tidak seragam gayanya:** sebagian nilai memakai **garis bawah** sebagai
pemisah kata, sebagian tidak.

> Pertanyaan pengguna menulis "media luar ruang" dengan spasi, sedangkan nilainya memakai garis
> bawah tanpa spasi. `ILIKE '%luar ruang%'` **tidak akan cocok**. Ambil daftar nilainya lebih dulu
> (jalur **P2**) dan pakai nilai persis.

## `lokasi_iklan` — teks bebas, jangan dikelompokkan

Berisi keterangan lokasi/penempatan iklan, diisi bebas. Nilainya nyaris unik per baris, sebagian
berkutip, dan **sebagian sangat panjang** — memuat rekaman multi-kolom yang tergabung menjadi satu
teks.

> **Jangan pernah `GROUP BY lokasi_iklan`** untuk membuat peringkat. Hasilnya sebanyak barisnya.
> Kolom ini hanya untuk lookup satuan atau pencarian `ILIKE` (jalur **P3**).

Bila pertanyaannya meminta pengelompokan "materi yang sama", kolom ini bukan jawabannya — tidak
ada dua baris yang benar-benar sama. Klarifikasi apa yang dimaksud "materi".

## `jenis_pembuat_iklan` — terkunci satu komoditi

Berisi apakah iklan dibuat pelaku usaha atau perorangan. **Sebagian besar barisnya kosong**, dan
yang terisi **hanya untuk satu komoditi**.

> `WHERE jenis_pembuat_iklan <> ''` karena itu **identik dengan memfilter komoditi itu** — sebuah
> filter tersembunyi.

Pertanyaan yang meminta pengelompokan berdasarkan pembuat iklan **hanya bisa dijawab untuk komoditi
tersebut**. Sebutkan batasnya; jangan menyajikannya sebagai angka lintas komoditi.

Cara memastikan komoditi mana: silangkan keterisian kolom ini dengan `komoditi` — jalur **P2**.

## Yang tidak ada di kolom mana pun

| Diminta pengguna | Status |
|---|---|
| **materi iklan** (isi/naskah iklan) | tidak ada — hanya keterangan lokasi |
| **gambar iklan** | tidak ada |
| **golongan obat pada iklan** (keras/bebas) | tidak ada penandanya |
| **jenis pangan pada iklan pangan** | tidak ada di tabel ini |

Semuanya **P5 NOT COVERED** — lihat `95-batas-domain.md`.

## Rute

- Menyebut komoditi → **naik** ke `10-komoditi.md`.
- Menyebut klausul pelanggaran → **seberang** `40-ketidaksesuaian.md`.
- Menyebut produk/pendaftar → **seberang** `50-produk-dan-pendaftar.md`.
