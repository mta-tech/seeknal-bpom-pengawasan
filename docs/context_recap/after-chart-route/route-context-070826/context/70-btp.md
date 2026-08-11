BTP — bahan tambahan pangan, pewarna, pengawet, antioksidan, perisa, bentuk sediaan, tunggal, campuran

BTP hidup di tabel **terpisah**: `t_btp_3_erba` dan `t_btp_3_erla`. Secara penghitungan keduanya
tabel produk — entity dan tier status sama (`00-menghitung.md`).

| Konsep | Kolom | Kode |
|---|---|---|
| Jenis BTP | `jenis_btp` | resolusi lewat dictionary — **lihat peringatan namespace di bawah** |
| Bentuk sediaan | `bentuk_sediaan` | `101` cair/pasta · `102` serbuk · `103` bahan penolong · `104` gas · `105` padat |
| Jenis produk BTP | `jenis_produk_btp` | `301` tunggal · `302` campuran · `303` perisa · `304` bahan penolong |

## Namespace `jenis_btp` — jebakan terbesar di halaman ini

Dictionary mengatalogkan `JENIS_BTP` sebagai "ERLA dan ERBA" dengan kode **13–52**. Kenyataannya
`t_btp_3_erla.jenis_btp` **tidak memakai rentang itu sama sekali** — ia memakai **777–805**, nilai
yang tidak dideskripsikan kategori dictionary mana pun.

Menjalankan `jenis_btp='47'` (Pewarna) pada tabel ERLA memberi **0 baris**. Dibaca mentah itu
berarti "ERLA tidak punya pewarna" — dan itu salah; artinya "sistem kode yang salah untuk tabel ini".

→ Sebelum melaporkan 0 atau "tidak ada" untuk satu sistem:
`SELECT DISTINCT jenis_btp, COUNT(*) FROM <tabel itu> GROUP BY 1`.
→ Rentang 777–805 **tidak punya label di mana pun**, sehingga konsepnya tidak bisa difilter di sisi
itu. Jawab untuk sistem yang bisa dipetakan dan **sebutkan batasnya**. Melaporkan sisi yang tak
terpetakan sebagai nol mengubah celah katalog menjadi klaim tentang bisnis.

## Perbedaan lain dari tabel produk

- **Tipe kolom.** `t_btp_3_erba` **bukan** all-TEXT: empat kolom tanggal sudah `timestamp` dan
  `trader_id` sudah `bigint`. Membawa cast produk ke sana **menggagalkan query**
  (`00-menghitung.md` §4). `t_btp_3_erla` native seluruhnya.
- **Set status lebih kecil.** `t_btp_3_erba` tanpa `0009`; `t_btp_3_erla` tanpa `0099` dan membawa
  `0299` (kode namespace ERLA). Dari trio Verifikator 2 hanya `0502` yang muncul.
  Jangan menyalin daftar tahapan dari tabel produk tanpa memeriksa (`20-status-pipeline.md`).
- **Pipeline BTP hidup di KEDUA tabel** — tidak seperti tabel produk ERLA yang hanya final.
- Sebagian kode `JENIS_BTP` yang terdaftar tidak memegang baris sama sekali (sekitar sepertiganya).
  Boleh tetap di filter, tetapi jangan disajikan sebagai anggota penyumbang.

## Lingkup produk vs produk+BTP

"Berapa permohonan/produk" tanpa keterangan **ambigu** soal BTP. Sajikan dua angka berlabel
(produk-saja dan produk+BTP, masing-masing dengan tabel sumbernya), atau nyatakan lingkup yang
dipakai dan alasannya. Menambahkan tabel BTP tanpa diminta adalah penyebab selisih yang berulang.

## Rute

- Konsep BTP majemuk ("pewarna atau pengawet") → baca seluruh kategori dictionary, bukan satu kode
  (jalur P2 Gate 2); deskripsi berulang membuat satu kode kehilangan saudaranya.
- Pertanyaan menyebut tahapan proses BTP → **SEBERANG** `20-status-pipeline.md`
- Pertanyaan menyebut kemasan BTP → **SEBERANG** `40-kemasan.md`
  (`sub_kemasan_id` ada di `t_btp_3_erba`, tidak di `t_btp_3_erla`)
