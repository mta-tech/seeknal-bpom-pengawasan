Target, capaian, dan pertanyaan "UPT mana yang belum melaporkan".

## `target_balai`

Memuat target tahunan per `(nama_balai, komoditi, tahun)`, dengan kolom target terpisah per jenis
kegiatan — pakai kolom target pengawasan untuk domain ini.

### Tiga batas struktural

**1. Hanya satu tahun.** Periksa dulu (`SELECT DISTINCT tahun FROM target_balai`). Untuk realisasi
di tahun yang tidak ada targetnya: sajikan realisasi **tanpa** persentase capaian, atau bandingkan
terhadap tahun yang tersedia **sambil menyatakan bahwa tahunnya berbeda**.

**2. Nama balai beda kapitalisasi.** Tabel fakta menulis huruf besar, tabel target huruf campuran.
**Join persis akan gagal** untuk sebagian besar nama.

> Selalu `lower(trim(...)) = lower(trim(...))` di kedua sisi. Dengan normalisasi itu, hampir seluruh
> pasangan balai×komoditi menemukan targetnya.

**3. Unit pusat tidak punya target.** Nilai `nama_balai` yang berupa direktorat adalah unit pusat,
bukan balai — memang tidak bertarget. Laporkan terpisah; jangan menghitung capaian nol untuknya,
dan jangan membuangnya diam-diam dari agregat nasional tanpa menyebutkannya.

Komoditi di kedua sisi bisa dijoin langsung di domain ini — nilainya sepadan. (Domain pemeriksaan
memerlukan kolom jembatan; domain ini tidak.)

## Bentuk jawaban capaian

Sebelum menyajikan capaian:

1. sebutkan **tahun target** yang dipakai;
2. sebutkan **entity realisasi** — baris produk, event, atau surat (`00-menghitung.md` §1);
3. keluarkan unit pusat dari agregat nasional, dan katakan;
4. bila periodenya berjalan, sebutkan bahwa realisasinya belum lengkap.

## Pertanyaan "UPT mana yang TIDAK melaporkan"

Bentuk anti-join (`EXCEPT` atau `NOT EXISTS`) sering menghasilkan **himpunan kosong** — karena
praktis setiap balai punya minimal satu laporan pada kategori apa pun.

> Nol baris di sini **adalah jawaban yang benar**, tetapi jarang berguna bagi penanya. Bentuk yang
> menjawab maksudnya adalah **peringkat porsi**: cacah dan persentase per balai, diurutkan dari
> yang paling rendah.

Sampaikan keduanya: "tidak ada balai yang sama sekali tidak melaporkan; berikut yang porsinya
paling rendah."

## Cakupan wilayah

`coverage_balai` memuat wilayah kerja balai. Perhatikan bahwa jumlah balai di cakupan dan di fakta
**tidak sama** — balai yang punya wilayah kerja tetapi tidak punya pengawasan pada periode itu harus
tampil sebagai nol, bukan hilang. Pakai LEFT JOIN dari sisi cakupan.

⚠️ `coverage_balai` adalah **wilayah kerja balai**, bukan lokasi produsen. Pertanyaan tentang
wilayah produsen tidak bisa dijawab dengannya — lihat `95-batas-domain.md`.

## Rute

- Menyebut komoditi → **seberang** `10-komoditi.md`.
- Menyebut periode → **seberang** `60-waktu-dan-durasi.md`.
