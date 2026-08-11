Kualitas data — belum, tanpa, kosong, tidak punya, belum ditetapkan, belum dikategorikan, tidak terisi

Pertanyaan berkata "belum / tanpa / kosong / tidak punya" menanyakan **keadaan mentah populasi**.

## Aturan tunggal yang mengatur seluruh kelas ini

**LEPAS filter status NIE sah. LEPAS `jenis_permohonan`. LEPAS rentang tanggal yang tidak diminta.**

Alasannya struktural: baris yang belum berkategori umumnya **belum sampai terbit NIE**, jadi
menumpuk filter NIE sah menyaring habis justru baris yang dicari.

Entity mengikuti subjek seperti biasa (`00-menghitung.md` §1); eksklusi akun uji tetap berlaku.

## Kolom mana untuk "belum dikategorikan" — jawab pada kolom yang DISEBUT pengguna

Beberapa kolom sama-sama bisa berarti "kategori", dan **keterisiannya sangat berbeda** — jawaban
yang sama bisa berbunyi "tidak ada" atau "ratusan ribu" hanya karena kolom yang dibaca berbeda.
Karena itu: petakan istilah pengguna ke kolomnya, lalu periksa keterisian kolom itu.

| Istilah pengguna | Kolom |
|---|---|
| "belum ditetapkan **kategori risiko**" | `jenis_dokumen = '000'` — ini konsep bisnisnya, bukan kolom kosong |
| "belum dikategorikan **jenis pangan**" | `jenis_pangan` / `kategori_pangan` kosong |
| katalog teks bebasnya belum diisi | `nama_kategori` kosong |
| artefak data | `kategori_dokumen` kosong — tersimpan **NULL, bukan string kosong**; uji dengan `IS NULL` |

Periksa sebelum menjawab:
```sql
SELECT COUNT(*) total,
       COUNT(*) FILTER (WHERE NULLIF(TRIM(<kolom>),'') IS NULL) kosong
FROM <tabel>;
```

**Sebutkan kolom yang dipakai** — itu yang membuat jawaban bisa diperiksa. Dan bedakan **artefak
migrasi** dari **keadaan bisnis**: kolom yang kosong di hampir seluruh tabel sistem lama biasanya
tidak pernah diisi saat migrasi, bukan berarti produknya benar-benar belum dikategorikan. Bila
polanya seperti itu, katakan.

## Nol adalah jawaban

Query yang benar mengembalikan nol baris → katakan "tidak ada / tidak ditemukan" dengan lugas.
Itu hasil yang jujur, bukan kegagalan yang harus diperbaiki. Jangan mengarang angka untuk
mengisi kekosongan, dan jangan melebarkan filter sampai "ada sesuatu" muncul.

## Sentinel bukan kategori

Nilai seperti `'0'`, `''`, deskripsi `'-'`, atau tanggal jauh sebelum umur sistem adalah **penanda
belum diisi**, bukan kategori — dan sering **memuncaki peringkat**.

Cara mengenalinya, bukan menghafalnya:
- tidak punya baris di `data_dictionary` untuk kategori kolom itu, **atau** deskripsinya kosong/`-`;
- maknanya "tidak ada perlakuan tertentu" atau menyebut unit organisasi, bukan sifat produk;
- cacahnya besar dan tidak proporsional dibanding anggota lain (`GROUP BY` sekali memperlihatkannya).

Kecualikan dari peringkat; laporkan terpisah sebagai catatan kualitas data. Peringkat yang dibuat
tanpa mengecualikannya melaporkan "belum diisi" sebagai juara — jawaban yang tidak berarti apa-apa.

## Rute

- Konsepnya kategori risiko → **SEBERANG** `30-risiko-komitmen.md` (kolomnya `jenis_dokumen`,
  bukan `kategori_dokumen`)
- Konsepnya segmen pangan → **SEBERANG** `10-segmen-produk.md`
- Kolom yang ditanya tidak ada di halaman mana pun → `95-dimensi-lain.md`
