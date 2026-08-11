Asal & cara produksi — negara asal, impor, lokal, dalam negeri, makloon, single MD, nama negara mana pun

## Negara asal — dua kolom kandidat, pilih dengan memeriksa keterisiannya

`negara_pabrik` dan `negara_produsen` sama-sama ada dan sama-sama terdengar benar. **Yang membedakan
bukan namanya, tapi seberapa terisi** — dan itu harus diperiksa, bukan diingat:

```sql
SELECT '<sistem>' sys,
       COUNT(*) FILTER (WHERE NULLIF(TRIM(negara_pabrik),'')   IS NOT NULL) pabrik,
       COUNT(*) FILTER (WHERE NULLIF(TRIM(negara_produsen),'') IS NOT NULL) produsen,
       COUNT(*) total
FROM <tabel itu>;
```

Pilih kolom yang terisi luas. Memakai kolom yang jarang terisi membuang sebagian besar populasi dan
memberi angka yang jauh terlalu kecil — tanpa error, tanpa peringatan. **Sebutkan kolom yang dipakai
di jawaban.** Kalau ternyata tiap sistem memakai kolom yang berbeda untuk konsep yang sama, itu bukan
alasan menggabungkan keduanya di satu ekspresi — resolusikan tiap sisi pada kolomnya sendiri dan
katakan.

Isinya kode ISO 2 huruf. Dictionary kategori `NEGARA_PABRIK dan NEGARA_PRODUSEN`, sumber
"ERLA dan ERBA" — **kode sama di kedua sistem**; ini salah satu dari sedikit kolom yang begitu, jadi
jangan menganggapnya berlaku umum. Beberapa baris muncul dua kali di dictionary; duplikat itu tidak
berbahaya.

`ID` = Indonesia/dalam negeri · selain `ID` = impor.

**Jawaban menuliskan NAMA negara, bukan kode mentah** — pengguna tidak membaca ISO.
Terjemahkan lewat dictionary sebelum menyajikan.

## Cara produksi — kolom `status_produk`

| Kode | Arti |
|---|---|
| `301` | Produsen sendiri |
| `302` | Impor |
| `304` | Makloon (kontrak) |
| `306` | Single MD Induk |
| `307` | Single MD Anak |

Dikatalogkan ERBA-only, **tetapi ERLA mengisinya juga dengan makna yang sama**, ditambah `303` dan
`305` yang tidak dideskripsikan baris dictionary mana pun. Sebelum melaporkan 0 atau "tidak ada"
untuk satu sistem, daftar dulu nilai milik sistem itu sendiri.

⚠️ **Ini kasus yang BERBEDA dari `kategori_dokumen`** (`30-risiko-komitmen.md`), dan bedanya
menentukan boleh-tidaknya UNION. Di sana kolom dikatalogkan ERBA dan nilai ERLA-nya **skema lain**;
di sini kolom dikatalogkan ERBA dan nilai ERLA-nya **skema yang sama**. Keduanya terlihat identik
dari `information_schema` dan dari keterisian.

**Cara membedakannya: silangkan dengan kolom independen yang seharusnya sejalan.** `status_produk`
`302` Impor harus sejalan dengan `negara_pabrik` bukan-Indonesia — bila kedua himpunan itu berimpit,
kodenya memang berarti apa yang tertulis di sisi itu. Bila tidak ada kolom independen untuk
menyilang (seperti pada risiko), **anggap skemanya berbeda dan jangan UNION** — asumsi yang salah
ke arah ini hanya membuat jawaban lebih sempit, sedangkan ke arah sebaliknya membuatnya keliru.

**`status_produk` bukan pengganti `negara_pabrik`.** "Asal Indonesia" ditentukan **tempat pabriknya**,
bukan status produksinya. Memakai `status_produk <> '302'` sebagai proksi "bukan impor" menjaring
populasi yang berbeda dan lebih lebar. Bila pertanyaan menyebut **cara produksi** (makloon, single
MD, produsen sendiri), barulah `status_produk` yang dipakai; bila menyebut **asal**, pakai kolom negara.

## Lingkup sering timpang antar sistem — periksa, lalu pecah

Sistem lama menyimpan riwayat pendaftaran bertahun-tahun sementara sistem baru berjalan belakangan,
sehingga banyak segmen — terutama impor — berat sebelah. Sebagian segmen bahkan **struktural satu
sistem**: nol baris di sisi satunya.

Buktikan dari data sebelum melabeli jawaban "gabungan":

```sql
SELECT 'ERBA' sys, COUNT(DISTINCT nomor) FROM t_produk_3_erba WHERE <filter>
UNION ALL
SELECT 'ERLA', COUNT(DISTINCT nomor) FROM t_produk_3_rilis_erla WHERE <filter sisi ERLA>;
```

- Satu sisi nol → katakan seluruh data berasal dari sisi satunya. Menjalankan UNION tetap memberi
  angka yang benar, tetapi menyebut "gabungan" tanpa keterangan membuat pengguna mengira kedua
  sistem menyumbang.
- Timpang berat → sajikan pecahannya, jangan hanya angka gabungan; ketimpangan itu sendiri sering
  merupakan informasi yang dicari (perpindahan sistem, bukan perubahan pasar).

**Buktikan lingkup dari data, jangan mengasumsikan gabungan selalu tepat.**

## Rute

- Pertanyaan menggabung asal dengan segmen produk ("kopi instan asal Indonesia") →
  **SEBERANG** `10-segmen-produk.md`; selesaikan tiap bagian di kolomnya sendiri lalu AND-kan
  dalam SATU WHERE — jangan menjatuhkan salah satu.
- Pertanyaan tentang pabrik/perusahaan asal negara tertentu → **SEBERANG** `50-pihak-wilayah.md`
- Kode negara belum diketahui → dictionary kategori `NEGARA_PABRIK dan NEGARA_PRODUSEN`,
  `deskripsi ILIKE '%<nama negara>%'` DI DALAM kategori itu (jalur P3 Gate 2).
