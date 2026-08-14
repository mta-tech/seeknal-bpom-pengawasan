Status dan alur persetujuan — serta dua tabel yang lebih luas dari tabel fakta.

## `status` di timeline — angka

Kode status di domain ini bertipe **angka**, berjalan dari tahap draft sampai tahap selesai,
ditambah **satu blok kode khusus penolakan** di rentang atas.

Ambil daftar nilainya lewat `SELECT DISTINCT` — jalur **P2**. Jangan mengetik dari ingatan.

## Log alur

`mv_pengawasan_log` memuat satu baris per perpindahan tahap, dengan langkah (`trx_steps`), kode
status, label, pelaku, catatan, dan waktu proses.

⚠️ **`status_label` tidak lengkap.** Blok kode penolakan **tidak punya label** — nilainya kosong.
Mengelompokkan alur berdasarkan `status_label` akan menyembunyikan seluruh penolakan.

> **Untuk mengenali penolakan, pakai `trx_steps`** — langkah penolakan punya penamaan sendiri yang
> jelas. `status_label` hanya untuk menampilkan tahap normal.

## ⚠️ Dua tabel memuat id yang tidak ada di fakta

`mv_pengawasan_log` dan `mv_pengawasan_timeline` punya lebih banyak id daripada tabel fakta.

> Menghitung dari log atau timeline **langsung** melebihi populasi pengawasan. Bila jawabannya
> berbicara tentang populasi pengawasan, **INNER JOIN dari fakta**.

Sifat id tambahan itu belum dipastikan (arsip, atau berkas yang belum masuk fakta) — jangan
menyimpulkan sebabnya; cukup perlakukan sebagai populasi yang berbeda.

## Batas yang harus dihormati

Pertanyaan *"siapa yang menyetujui"*, *"apakah pemisahan tugas berjalan"*, *"apakah ada
self-approval"* → **P5 NOT COVERED**.

Kolom pelaku di log tidak dapat dipastikan artinya dari database ini sendirian — apakah ia pelaku
tahap itu, atau pengirim ke tahap itu. Kedua bacaan menghasilkan angka yang sama dan kesimpulan
yang berlawanan, dan kesimpulannya bersifat tuduhan.

Yang **boleh** dijawab dari log: kapan berkas berpindah tahap, berapa lama tersangkut, dan tahap
mana yang paling banyak menahan berkas — semua tentang **waktu dan volume**, bukan tentang
**siapa**.

## Istilah pengguna

| Istilah | Cara mengikat |
|---|---|
| "sudah selesai" | kode tahap akhir |
| "belum selesai" / "menggantung" | kebalikannya, atau tanggal tahap tertentu masih kosong |
| "ditolak" | langkah penolakan di `trx_steps`, **bukan** `status_label` |
| "belum ada tanggal direktur" | kolom tanggal di timeline yang masih kosong |

## Rute

- Menyebut durasi/SLA → **seberang** `60-waktu-dan-durasi.md`.
- Menyebut vonis → **seberang** `30-vonis.md`.
