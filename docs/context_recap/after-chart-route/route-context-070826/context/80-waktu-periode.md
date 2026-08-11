Waktu & periode — tahun, bulan, tren, terbit, kedaluwarsa, masa berlaku, sejak, sampai, per tahun

## Empat kolom tanggal — pilih dari apa yang ditanya

| Kolom | Menjawab |
|---|---|
| `tanggal` | **terbit NIE** — "izin edarnya terbit", "NIE tahun X" |
| `tanggal_bayar` | **permohonan** — tanggal kanonik pengajuan |
| `tanggal_aju` | pengajuan/submission saja |
| `tanggal_exp` | **kedaluwarsa** — kondisi tentang berakhirnya masa berlaku |

`tanggal_berkas`, `tanggal_diambil` = tanggal proses, **tidak pernah** untuk menghitung.
Memakai `tanggal_aju`/`tanggal_bayar` untuk pertanyaan "terbit" menggeser hasil dan mencampur
permohonan yang belum terbit. **Tidak ada kolom "tanggal rilis ke pasar"** — yang terdekat adalah
`tanggal`; katakan keterbatasan itu apa adanya, jangan mengarang kolom.

**Keterisiannya tidak sama.** Kolom terbit hanya terisi untuk baris yang memang sudah terbit, jadi
memfilternya diam-diam membuang permohonan yang belum selesai. Bila lingkupnya penting, periksa dulu:
`COUNT(*) FILTER (WHERE NULLIF(<kolom>,'') IS NOT NULL)` dibanding `COUNT(*)`.

## Bentuk query periode

- **Rentang berbatas**, bukan `EXTRACT(YEAR …)` — `EXTRACT` memaksa transfer seluruh tabel dan
  hanya boleh untuk melabeli hasil yang sudah dikelompokkan.
- Cast di sisi ERBA saja: `NULLIF(tanggal,'')::timestamp` (`00-menghitung.md` §4).
- Tren: `date_trunc('year'|'month', …)` dengan SATU `GROUP BY` yang bentuknya sama dengan jawaban —
  jangan merakit tabel dari hasil terpisah.
- **Headline tetap dari query global sendiri.** `GROUP BY periode` lalu menjumlahkan partisi
  menghitung ganda `nomor` yang muncul di lebih dari satu periode.

⚠️ **Jangan menambahkan rentang tanggal yang tidak diminta.** Guard "sanity" seperti
`>= '2000-01-01'` terasa aman tetapi menyaring — dan pada pertanyaan kualitas data ia membuang
justru baris yang dicari. Rentang hanya ada bila pertanyaan menyebutnya.

⚠️ **Kolom tanggal bisa memuat nilai sentinel** jauh di luar rentang operasional (mis. tahun 1900
atau 1970 sebagai penanda "tidak diketahui"). Tren tanpa batas bawah akan menampilkannya sebagai
bucket tersendiri. Periksa sekali sebelum membuat tren:
`SELECT MIN(<kolom>), MAX(<kolom>) FROM <tabel>` — bila minimumnya mendahului umur sistem, beri
batas bawah atau sebutkan sebagai catatan.

## "Masih berlaku" — dua tafsir yang sama-sama sah

| Tafsir | Filter | Sumber aturan |
|---|---|---|
| **Status aktif** | `status='0999'` | `00-menghitung.md` §2 |
| **Aktif DAN belum kedaluwarsa** | `status='0999'` AND (`tanggal_exp` > hari ini OR `tanggal_exp` kosong) | halaman ini |

Bila pertanyaan menanyakan keduanya sekaligus ("masih berlaku semua atau ada yang sudah lewat"),
jawaban WAJIB menyebut **dua angka berlabel** — bukan memilih satu diam-diam.

Kedua tafsir bisa berjauhan, dan selisihnya **terkonsentrasi di sistem lama**: sistem yang menyimpan
riwayat bertahun-tahun punya banyak NIE yang statusnya tidak pernah diperbarui meski tanggalnya
sudah lewat. Karena itu **pecah per sistem** — jawaban gabungan menyembunyikan bahwa persoalannya
khas satu sistem. Untuk melihat besarnya sekali jalan:
`COUNT(DISTINCT nomor) FILTER (WHERE <belum kedaluwarsa>)` di samping cacah aktif, per sistem.

**Status dan masa berlaku dua dimensi terpisah.** `0099` "Tidak Berlaku" adalah penanda status,
BUKAN hasil perhitungan tanggal — jangan mencampurnya ke hitungan kedaluwarsa berbasis
`tanggal_exp`, dan jangan menyimpulkan sebuah NIE dicabut hanya karena `tanggal_exp`-nya lewat.

## Rute

- Pertanyaan "kapan paling banyak berakhir" → kelompokkan `tanggal_exp` dengan SATU `GROUP BY`,
  jangan memilih tahun dengan tangan.
- Menyebut status/tahapan → **SEBERANG** `20-status-pipeline.md`
- Menyebut jenis permohonan → **SEBERANG** `15-permohonan.md` (kolom tanggalnya `tanggal_bayar`)
- Menyebut segmen → **SEBERANG** `10-segmen-produk.md`
