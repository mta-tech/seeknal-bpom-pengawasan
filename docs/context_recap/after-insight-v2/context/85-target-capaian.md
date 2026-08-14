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

PENTING: `coverage_balai` adalah **wilayah kerja balai**, bukan lokasi produsen. Pertanyaan tentang
wilayah produsen tidak bisa dijawab dengannya — lihat `95-batas-domain.md`.


## Tabel target memuat TUJUH kolom target — hanya sebagian milik domain ini

Ini penyebab kesalahan yang paling mudah terjadi di halaman ini, karena semua kolomnya bernama
mirip dan semuanya berisi angka yang masuk akal.

`target_balai` melayani beberapa kegiatan pengawasan sekaligus. Kolom targetnya:
`target_penandaan`, `target_pengawasan`, `target_pengujian`, `target_pengujian_pangan`,
`target_pengujian_pangan_fortifikasi`, `target_sarana_distribusi`, `target_sarana_produksi`.

**Untuk domain ini yang dipakai adalah `target_pengawasan`.** Satu kolom saja untuk domain ini.

> **Aturan:** kolom target dipilih berdasarkan **kegiatan yang ditanya**, bukan berdasarkan angka
> mana yang terlihat wajar. Kolom milik kegiatan lain **tidak boleh dipakai di sini** meskipun
> terisi — angkanya nyata, tetapi menjawab pertanyaan yang berbeda.

## Grain tabel target: satu baris = satu balai × satu komoditi × satu tahun

Bukan satu baris per balai. Setiap balai punya beberapa baris, satu untuk tiap komoditi.

Konsekuensinya:

| Yang ingin dijawab | Yang harus dilakukan |
|---|---|
| Target satu balai untuk satu komoditi | ambil barisnya langsung |
| Target satu balai keseluruhan | jumlahkan seluruh komoditinya |
| Target nasional | jumlahkan seluruh balai **dan** seluruh komoditi |
| Membandingkan dengan capaian per komoditi | agregasi capaian juga harus per komoditi |

> **Aturan:** menjumlahkan kolom target tanpa menyadari grain-nya akan **melipatgandakan** hasilnya
> sebanyak jumlah komoditi. Selalu tentukan lebih dulu apakah pertanyaannya per komoditi atau
> gabungan, lalu samakan tingkat agregasi kedua sisi — target dan capaian.

## Tabel target tidak mencakup semua tahun

Kolom `tahun` di tabel ini **tidak berisi seluruh tahun operasional**. Jangan berasumsi tahun yang
diminta pengguna tersedia.

> **Aturan:** sebelum menjawab pertanyaan capaian, **periksa dulu tahun apa saja yang ada** di
> tabel target. Bila tahun yang diminta tidak ada, jawab bahwa pembandingnya tidak tersedia untuk
> tahun itu — **jangan** menjawab capaian nol, dan **jangan** diam-diam memakai tahun lain sebagai
> pengganti.
>
> Ini pemeriksaan, bukan fakta yang dihafal: isi tabel bisa bertambah kapan saja, jadi periksa
> setiap kali alih-alih mengandalkan apa yang pernah benar.

## Nama balai punya spasi tersembunyi di ujung

Sebagian nilai nama balai tersimpan dengan spasi menempel di belakang. Spasi itu konsisten di semua
tabel yang memuat nama balai, jadi join antar tabel tetap jalan. Yang gagal adalah filter kesamaan
persis.

Menulis `nama_balai = 'BALAI POM DI ...'` dengan nama yang disalin dari dokumen atau diketik dari
ingatan akan mengembalikan nol baris tanpa pesan kesalahan, seolah balai itu tidak punya data.

Aturan: filter kesamaan persis pada nama balai wajib memakai `trim()` di kedua sisi, atau memakai
nilai hasil probe `SELECT DISTINCT` apa adanya termasuk spasinya. Jangan mengetik nama balai dari
ingatan.

## Rute

- Menyebut komoditi: buka `10-komoditi.md`.
- Menyebut periode: buka `60-waktu-dan-durasi.md`.

---

<!-- MANIFES
tabel: coverage_balai, target_balai
kolom: nama_balai, tahun, target_penandaan, target_pengawasan, target_pengujian, target_pengujian_pangan, target_pengujian_pangan_fortifikasi, target_sarana_distribusi, target_sarana_produksi
nilai: -
-->
