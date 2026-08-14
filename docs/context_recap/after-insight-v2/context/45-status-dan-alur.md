Status dan alur persetujuan — serta dua tabel yang lebih luas dari tabel fakta.

## `status` di timeline — angka

Kode status di domain ini bertipe **angka**, berjalan dari tahap draft sampai tahap selesai,
ditambah **satu blok kode khusus penolakan** di rentang atas.

Ambil daftar nilainya lewat `SELECT DISTINCT` — jalur **P2**. Jangan mengetik dari ingatan.

## Log alur

`mv_pengawasan_log` memuat satu baris per perpindahan tahap, dengan langkah (`trx_steps`), kode
status, label, pelaku, catatan, dan waktu proses.

PENTING: **`status_label` tidak lengkap.** Blok kode penolakan **tidak punya label** — nilainya kosong.
Mengelompokkan alur berdasarkan `status_label` akan menyembunyikan seluruh penolakan.

> **Untuk mengenali penolakan, pakai `trx_steps`** — langkah penolakan punya penamaan sendiri yang
> jelas. `status_label` hanya untuk menampilkan tahap normal.

## Dua tabel memuat id yang tidak ada di fakta

`mv_pengawasan_log` dan `mv_pengawasan_timeline` punya lebih banyak id daripada tabel fakta.

> Menghitung dari log atau timeline **langsung** melebihi populasi pengawasan. Bila jawabannya
> berbicara tentang populasi pengawasan, **INNER JOIN dari fakta**.

Sifat id tambahan itu belum dipastikan (arsip, atau berkas yang belum masuk fakta) — jangan
menyimpulkan sebabnya; cukup perlakukan sebagai populasi yang berbeda.

## Batas yang harus dihormati

Pertanyaan *"siapa yang menyetujui"*, *"apakah pemisahan tugas berjalan"*, *"apakah ada
self-approval"* **P5 NOT COVERED**.

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


## Kode tahap di tabel log

Kolom `status_code` berbentuk angka, dan angkanya **tidak berurutan rapat**. Ada blok nilai kecil untuk
tahap normal, lalu **blok nilai besar yang terpisah jauh** untuk jalur penolakan atau pembatalan.

Pemisahan blok itulah yang membuat pertanyaan "berapa yang ditolak dan di tahap mana" bisa dijawab:
jalur penolakan dikenali dari **blok** nilainya, bukan dari satu nilai tunggal.

> **Aturan:** jangan memperlakukan kolom ini sebagai urutan menaik yang rapat, dan jangan menebak
> nilai mana yang berarti "ditolak". Ambil daftar nilainya lebih dulu bersama labelnya, kenali di
> mana blok besar dimulai, lalu filter dengan himpunan nilai persis.

Perhatikan juga: **nilai yang muncul hanya pada segelintir baris** di tengah nilai bervolume besar
biasanya salah ketik, bukan tahap yang benar-benar ada. Saat menyusun daftar tahap, abaikan varian
penulisan bervolume sangat kecil dari nilai bervolume besar — memasukkannya akan menciptakan tahap
yang sebenarnya tidak pernah ada di alur.

## Rute

- Menyebut durasi/SLA: buka `60-waktu-dan-durasi.md`.
- Menyebut vonis: buka `30-vonis.md`.

---

<!-- MANIFES
tabel: mv_pengawasan_log, mv_pengawasan_timeline
kolom: status, status_code, status_label, trx_steps
nilai: -
-->
