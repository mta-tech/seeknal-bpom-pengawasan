Permohonan & jenis permohonan — baru, perubahan mayor/minor, daftar ulang, notifikasi, disetujui, diterima

`jenis_permohonan` **tidak universal**. Kehadirannya ditentukan kata di pertanyaan, bukan kebiasaan.

**Satu skema untuk kedua sistem** — dictionary mencatat `sumber` = ERBA dan ERLA. Kode yang sama
berarti hal yang sama di kedua tabel; jangan menyusun set berbeda per sistem.

| Kode | Arti | Kelompok |
|---|---|---|
| `301` | Permohonan Baru | **baru** |
| `302` | Perubahan Mayor | perubahan |
| `303` | Perubahan Minor | perubahan |
| `304` | Daftar Ulang | pembaruan berkala — berdiri sendiri |
| `305` | Permohonan Baru Notifikasi | jalur notifikasi — berdiri sendiri |

**"Baru" = `301` saja.** `305` adalah jalur notifikasi yang terpisah; gabungkan hanya bila
pertanyaan menyebut notifikasi, dan sebutkan penggabungannya. `304` Daftar Ulang tidak pernah masuk
"baru" — itu perpanjangan izin lama.

## Cabang — pilih dari kata di pertanyaan

| Maksud | Kata pemicu | Filter |
|---|---|---|
| **Pendaftaran baru** | kata **"baru"** | `= '301'`, kedua sistem sama. Tambah `305` hanya bila pertanyaan menyebut "notifikasi" |
| **Total NIE / terbit di suatu periode** | "total produk terdaftar", "berapa NIE", "NIE yang terbit di {periode}" | **tanpa filter `jenis_permohonan`** — cukup set status sah |
| **Permohonan — default** | "permohonan/registrasi/pengajuan", termasuk "disetujui/diterima/terbit/izin edar" | semua jenis **+ set status sah** |
| **Permohonan — pengajuan mentah** | "berapa yang masuk/mengajukan", "seluruh periode data", tren volume tanpa kata izin | semua jenis, **tanpa filter status** |

**"Terbit" BUKAN pemicu `jenis_permohonan`.** "NIE yang terbit di suatu periode" menghitung SEMUA
jenis permohonan pada periode itu. Hanya kata eksplisit "baru" yang mempersempit.
Alasannya: produk yang NIE aktifnya datang lewat Perubahan tetap memegang NIE aktif — menyaring
ke jenis "baru" tanpa diminta membuang mereka.

**Dua baris permohonan tidak bisa ditukar.** Bacaan pengajuan-mentah mencakup pengajuan apa pun
hasilnya, bacaan disetujui hanya yang berujung terbit — populasinya berbeda, bukan bergeser sedikit.
Default adalah bacaan disetujui; "disetujui", "diterima", "terbit", "izin edar" semuanya menunjuk
ke sana. Lepas filter status hanya bila pertanyaan memang tentang volume pengajuan apa pun hasilnya.

**Perubahan/revisi** = `302` (mayor) + `303` (minor). Bila pertanyaan membandingkan "baru vs
mengubah", sajikan `301` di satu sisi dan `302`+`303` di sisi lain, masing-masing berlabel, dan
sebutkan `304`/`305` sebagai kelompok yang tidak masuk keduanya — membiarkannya hilang tanpa disebut
membuat dua sisi tampak menjumlah seluruh populasi padahal tidak.

**Entity permohonan = `produk_id`, dan tanggalnya `tanggal_bayar` — sepasang.** "Persetujuan",
"diterima", "disetujui" tetap cabang permohonan, jadi tetap pasangan itu; memakai `nomor` atau
`tanggal` (terbit) di cabang ini menukar populasi yang dihitung (`00-menghitung.md` §1).

## Dua pengecualian yang tidak mengambil cabang mana pun

- **Pertanyaan tahapan pipeline** ("berapa nyangkut di Draft", "menunggu verifikasi"): populasinya
  didefinisikan kode statusnya sendiri; menumpuk set NIE sah di atasnya **menghapusnya**.
  → `20-status-pipeline.md`
- **Pertanyaan komitmen Case B** ("berapa komitmen dibatalkan"): populasinya hidup di
  `status_komitmen` dan sebagian besar tidak pernah sampai ke NIE. → `30-risiko-komitmen.md`

## Rute

- Menyebut tahapan proses/antrian → **SEBERANG** `20-status-pipeline.md`
- Menyebut komitmen / pemenuhan / dibatalkan → **SEBERANG** `30-risiko-komitmen.md`
- Menyebut periode, tren, per tahun/bulan → **SEBERANG** `80-waktu-periode.md`
- Entity permohonan = `produk_id`, tanggal kanoniknya `tanggal_bayar` → `00-menghitung.md`
