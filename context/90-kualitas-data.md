belum · tanpa · kosong · tidak punya · tidak terisi · data tidak ada · null · sentinel · kualitas data

# Kualitas data — kosong, sentinel, teks bebas

## Apa yang halaman ini putuskan

Apakah sebuah "kosong" berarti **tidak ada data**, **tidak berlaku untuk kelompok ini**, atau
**sentinel yang harus dibuang** — diputuskan sebelum kekosongan dipakai menyaring atau menjawab.

## Tabel keputusan — membaca kekosongan sebelum menyaring

| Kolom / istilah | Aturan |
|---|---|
| `no_surat` · `nie` | sentinel teks (`''`, `-`, `0`, `Tanpa Surat Tugas`) → **buang sebelum** `COUNT(DISTINCT ...)` |
| `produk_id` | sering **NULL** (rokok/obat) — daftar produk tetap dari bridge |
| `provinsi_iklan_id` · `kabupaten_iklan_id` | hanya sebagian kasus — sebutkan cakupan |
| `kategori_media` | hampir seluruhnya kosong — jangan dijadikan filter tunggal |
| `kesimpulan_pusat_id` · `kesimpulan_akhir_id` | kolom tertentu saja — sebutkan cakupan |
| `klasifikasiklaim_id` · `ketidaksesuaianhasil_kode` · `uraian_pelanggaran_id` · `tgl_evaluasi_pusat` · `tgl_pengambilan_iklan` | hanya kategori tertentu — sebutkan cakupan |

## Matriks operasi

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `no_surat` | sentinel dibuang dulu | biasa | — | bisa |
| `nama_produk` · `pendaftar` | `ILIKE` **sekali** (P3) lalu nilai persis | hati-hati entity HTML | `dim_produk` (via bridge) | bisa |
| `verifikasi_pusat_sesuai` dsb. | **hanya** bila pertanyaan menyebutnya | idem | — | — |

## Kolom yang praktis kosong — jangan dipakai sebagai penyaring

Menyaring "yang terisi" pada kolom sparsial **diam-diam membuang kelompok** yang memang tidak
memakai kolom itu. Tanyakan: *apa arti kosongnya?* Bila kosong berarti "tidak berlaku bagi
kelompok X", menyaringnya membuang X. Silangkan keterisiannya dengan `kategori` — satu query.

## Cara mencari — periksa per kolom, jangan diasumsikan

```sql
SELECT count(*) FILTER (WHERE no_surat IS NULL OR btrim(no_surat) IN ('','-','0','Tanpa Surat Tugas')) AS no_surat_sentinel,
       count(*) FILTER (WHERE produk_id IS NULL)                                                       AS produk_null,
       count(*) FILTER (WHERE kesimpulan_pusat_id IS NULL)                                             AS pusat_kosong
FROM public.fact_pengawasan;
```

## Teks bebas dan entity HTML

`nama_produk`, `pendaftar`, `catatan` diisi bebas dan sebagian masih memuat entity HTML
(`&amp;` seharusnya `&`; `&#039;` seharusnya `'`). Pola kerja:

- Menampilkan: ubah entity ke karakter aslinya.
- Mencari: cari juga versi entity-nya, atau pakai `ILIKE` potongan kata tanpa tanda baca.

## Kode status tidak berlabel

`status_label` kosong untuk seluruh kode (`45-status-dan-alur.md`). Jawab dengan kode apa adanya;
jangan mengarang artinya. Beberapa kode kamus lain juga belum dikonfirmasi BPOM.

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| "nol" padahal datanya tidak direkam | menganggap kosong = nol | nyatakan "memang tidak terekam" untuk kolom yang tidak diisi kelompok itu |
| angka unik membengkak | sentinel ikut terhitung | buang sentinel sebelum `COUNT(DISTINCT ...)` |
| persentase menyesatkan | penyebut memakai populasi penuh padahal kolom sparsial | sebutkan cakupan pembilang & penyebut |
| pencarian teks nol | entity HTML | cari potongan kata tanpa tanda baca |

## Batas

- Bila kolom yang dipakai hanya terisi sebagian, **sebutkan porsinya sebelum menyajikan peringkat
  atau persentase** — satu kalimat cukup.
- Perilaku kosong berbeda antar kolom (sentinel vs NULL) — **jangan menyalin aturan antar kolom**.

## Rute

- Kembali ke aturan hitung → **naik** ke `00-menghitung.md`
- Batas domain & wilayah → **lihat** `95-batas-domain.md`
- Status → **lihat** `45-status-dan-alur.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `fact_pengawasan` | `no_surat`, `produk_id`, `kategori_media`, `kesimpulan_akhir_id`, `kesimpulan_pusat_id`, `provinsi_iklan_id`, `kabupaten_iklan_id`, `nama_produk`, `pendaftar` | sentinel `no_surat`: `''`, `-`, `0`, `Tanpa Surat Tugas` |
| `dim_status_code` | `status_label` | selalu kosong |
