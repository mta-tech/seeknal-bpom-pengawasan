Waktu, periode, durasi, dan ketepatan waktu pelaporan.

## Periode

`tgl_start` adalah tanggal kanonik untuk periode dan tren; `tgl_end` untuk pertanyaan penyelesaian
dan untuk membandingkan dengan kubus pra-agregasi (`00-menghitung.md` §7).

Pakai **rentang berbatas**. Jangan `EXTRACT(YEAR …)` sebagai penyaring — tidak ada indeks.

⚠️ `tgl_start` memuat tanggal **di masa depan** relatif hari pengambilan data. Untuk mengetahui
kesegaran data, pakai kolom `sync`, bukan nilai maksimum kolom tanggal.

**Periode berjalan selalu parsial** — setiap tren wajib menyebutnya.

## Tabel timeline

`mv_pengawasan_timeline` memuat tanggal milestone (mulai, kirim ke kepala balai, kirim ke direktur,
kirim ke pusat) dan beberapa kolom selisih.

⚠️ **Tabel ini memuat id yang tidak ada di fakta** — INNER JOIN dari fakta bila jawabannya tentang
populasi pengawasan (`45-status-dan-alur.md`).

### ⚠️ Satu kolom "durasi" sebenarnya bukan durasi

Salah satu kolom selisih di tabel ini **hanya bernilai dua kemungkinan plus kosong** — ia berfungsi
sebagai **penanda sudah/belum**, bukan jumlah hari.

> Menghitung rata-rata atau median dari kolom itu menghasilkan angka yang tampak masuk akal tetapi
> **tidak berarti apa-apa**. Periksa sebaran nilai kolom durasi mana pun sebelum meratakannya —
> bila nilainya hanya beberapa, itu penanda, bukan durasi.

Kolom selisih lain memang berisi jumlah hari, tetapi **kosong pada tahap yang belum tercapai**.
Merata-ratakan tanpa menyaring mencampur "cepat" dengan "belum sampai" — dan hasilnya bias ke
bawah.

> **Aturan:** sebelum menghitung durasi tahap mana pun, saring baris yang tanggal tahap tujuannya
> sudah terisi, dan sebutkan berapa bagian populasi yang belum mencapai tahap itu.

## Ketepatan waktu pelaporan

Pertanyaan bentuk *"laporan yang dikirim sebelum tanggal N bulan berikutnya"* dijawab dengan
membandingkan tanggal kirim terhadap batas yang diturunkan dari bulan pengawasannya.

Dua hal yang harus dinyatakan:

1. **Batas tanggalnya berasal dari aturan unit**, bukan dari data — sebutkan batas yang dipakai.
   Bila pengguna tidak menyebutnya, tanya.
2. **Baris yang tanggal kirimnya kosong** bukan "terlambat" — ia belum dikirim. Pisahkan menjadi
   kategori sendiri, jangan digabungkan ke salah satu sisi.

## Durasi pengawasan itu sendiri

Selisih `tgl_end - tgl_start` memberi lama pengawasan. Sebagian barisnya bernilai nol (mulai dan
selesai di hari yang sama) dan sebagian sangat panjang.

Untuk pertanyaan "berapa yang durasinya lebih dari N hari", bandingkan selisihnya langsung.
Perhatikan bahwa kata "pemeriksaan" dalam pertanyaan pengguna kadang merujuk ke **kegiatan
pengawasan di domain ini**, kadang ke **domain pemeriksaan sarana** — klarifikasi bila konteksnya
tidak jelas (`95-batas-domain.md`).

## Rute

- Menyebut alur/tahapan → **seberang** `45-status-dan-alur.md`.
- Menyebut target/capaian → **seberang** `85-target-capaian.md`.
