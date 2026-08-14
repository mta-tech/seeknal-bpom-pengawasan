Waktu, periode, durasi, dan ketepatan waktu pelaporan.

## Periode

`tgl_start` adalah tanggal kanonik untuk periode dan tren; `tgl_end` untuk pertanyaan penyelesaian
dan untuk membandingkan dengan kubus pra-agregasi (`00-menghitung.md` §7).

Pakai **rentang berbatas**. Jangan `EXTRACT(YEAR …)` sebagai penyaring — tidak ada indeks.

PENTING: `tgl_start` memuat tanggal **di masa depan** relatif hari pengambilan data. Untuk mengetahui
kesegaran data, pakai kolom `sync`, bukan nilai maksimum kolom tanggal.

**Periode berjalan selalu parsial** — setiap tren wajib menyebutnya.

## Tabel timeline

`mv_pengawasan_timeline` memuat tanggal milestone (mulai, kirim ke kepala balai, kirim ke direktur,
kirim ke pusat) dan beberapa kolom selisih.

PENTING: **Tabel ini memuat id yang tidak ada di fakta** — INNER JOIN dari fakta bila jawabannya tentang
populasi pengawasan (`45-status-dan-alur.md`).

### Satu kolom "durasi" sebenarnya bukan durasi

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


## Kolom tahap di tabel timeline — inilah yang menjawab "tertahan di tahap mana"

Tabel timeline bukan sekadar penyimpan tanggal mulai dan selesai. Ia memuat **tanggal tiap tahap**
dan **kolom selisih antar tahap**:

| Bentuk kolom | Contoh namanya | Isinya |
|---|---|---|
| Tanggal tahap | `tanggal_kirim_kabalai`, `tanggal_kirim_pusat`, `tanggal_kirim_direktur` | kapan berkas dikirim ke tahap berikutnya |
| Selisih antar tahap | `mulai_kabalai`, `kabalai_direktur`, `direktur_pusat` | jarak antar dua tahap |

> PENTING: **Kolom bernama seperti selisih belum tentu berisi jumlah hari.** Sebagian di antaranya hanya
> punya sedikit kemungkinan nilai — itu **penanda**, bukan durasi. Sebelum memakai kolom selisih
> untuk menghitung rata-rata lama proses, **periksa dulu sebaran nilainya**. Kalau nilainya hanya
> beberapa kemungkinan, ia menandai terjadi/tidaknya sesuatu, dan merata-ratakannya tidak berarti.

**Kekosongan di kolom tahap bersifat deterministik.** Berkas yang tidak pernah naik ke suatu tahap
memang tidak punya tanggal untuk tahap itu — bukan data yang hilang, melainkan tahap yang belum
terjadi.

> **Aturan:** rata-rata lama tahap **hanya dihitung dari berkas yang benar-benar melewati tahap
> itu**. Menyertakan baris kosong akan menurunkan rata-rata secara keliru. Dan karena porsi berkas
> yang mencapai tahap akhir jauh lebih kecil daripada yang mencapai tahap awal, **sebutkan populasi
> mana yang dihitung** di kalimat jawaban.
>
> Pertanyaan "di tahap mana berkas paling lama tertahan" dijawab dengan membandingkan antar tahap
> **pada populasi yang sama** — yaitu berkas yang melewati semua tahap yang dibandingkan.

## Rute

- Menyebut alur/tahapan: buka `45-status-dan-alur.md`.
- Menyebut target/capaian: buka `85-target-capaian.md`.

---

<!-- MANIFES
tabel: mv_pengawasan_timeline
kolom: direktur_pusat, kabalai_direktur, mulai_kabalai, sync, tanggal_kirim_direktur, tanggal_kirim_kabalai, tanggal_kirim_pusat, tgl_end, tgl_start
nilai: -
-->
