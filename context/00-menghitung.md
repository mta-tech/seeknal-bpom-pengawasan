pengawasan · iklan · kasus · event · produk · berapa · jumlah · periode · tanggal

# Cara menghitung — entity, grain, tanggal, eksklusi

Berlaku untuk **setiap** pertanyaan data di domain ini.

## Lingkup — cakupan data ini

- Akun ini memuat **semua balai** (`balai_id` — nama via `dim_balai`), domain **Pengawasan iklan**.
- Titik masuk tiap pertanyaan kasus: **`fact_pengawasan`** (tabel fakta). Riwayat tahapan:
  **`fact_pengawasan_approval`**. Narasi kasus: **`fact_pengawasan_narasi`**.
- Tabel `bridge_*` untuk entity anak (produk, detail media) — join lewat kuncinya (lihat halaman
  terkait). Tabel `dim_*` adalah kamus: untuk menerjemahkan kode, bukan untuk dihitung.
- Pertanyaan per balai = filter `balai_id` — bukan penolakan. Perbandingan antar balai boleh;
  sebutkan lingkupnya.

## Apa yang halaman ini putuskan

Apa yang dihitung (entity), seberapa halus (grain), kolom tanggal mana yang dipakai, dan baris mana
yang wajib dibuang — sebelum satu baris SQL ditulis.

## Tabel keputusan — kata pertanyaan menentukan entity

| Kata dalam pertanyaan | Entity | Tanggal kanonik |
|---|---|---|
| pengawasan · kasus · surat tugas · kegiatan | `COUNT(DISTINCT id)` pada fakta | `tgl_start` |
| produk yang dinilai (baris) | `COUNT(*)` pada `bridge_pengawasan_produk` (setelah join fakta) | dari kasus induk |
| produk unik | `COUNT(DISTINCT produk_id)` | dari kasus induk |
| NIE unik | `COUNT(DISTINCT nie)` dengan sentinel dibuang | dari kasus induk |
| surat | `COUNT(DISTINCT no_surat)` dengan sentinel dibuang | `tgl_surat` |
| pendaftar unik | `COUNT(DISTINCT pendaftar)` — **kehati-hatian**, `50-produk-dan-pendaftar.md` | dari kasus induk |

> View ini **1 baris = 1 event** (`count(*) = count(DISTINCT id)`). "Berapa pengawasan" tetap ambigu
> karena bisa berarti event, produk (baris bridge), atau surat — sebutkan tingkat yang dipakai.

## Matriks operasi — kolom yang sering salah dipakai

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `id` | biasa | biasa | kunci ke seluruh bridge (`pengawasan_id`) | biasa |
| `status_id` | butuh `dim_status_code` + filter `domain` | butuh kamus + domain | `dim_status_code.id AND domain='pengawasan'` | biasa |
| `komoditi_id` | kode langsung | langsung | — (tanpa kamus nama di akun ini) | bisa |
| `kategori` | teks 6 nilai (grain kasar) | langsung | — | jangan dicampur dengan `komoditi_id` |
| `tgl_start` | **rentang berbatas**, bukan `EXTRACT` | `date_trunc` boleh untuk melabeli hasil | — | biasa |
| `provinsi_iklan_id` / `kabupaten_iklan_id` | butuh ID kanonik | butuh ID kanonik | `dim_provinsi` / `dim_kabupaten` | biasa |

## Cara mencari bila nilainya tidak stabil

```sql
-- 1. rentang tanggal yang benar-benar terisi
SELECT min(tgl_start), max(tgl_start), count(*) FILTER (WHERE tgl_start IS NULL)
FROM public.fact_pengawasan;

-- 2. nilai yang dipakai untuk menyaring (jangan hafal)
SELECT DISTINCT kategori FROM public.fact_pengawasan ORDER BY 1;
SELECT DISTINCT status_id FROM public.fact_pengawasan ORDER BY 1;
```

## Eksklusi wajib

| Apa | Aturan | Alasan |
|---|---|---|
| sentinel pada kolom yang dihitung unik (`no_surat`, `nie`) | buang sebelum `COUNT(DISTINCT ...)` | sentinel bukan nilai sebenarnya |

### Uji satu kalimat sebelum menambah `WHERE` apa pun

> **Apakah baris yang dibuang klausa ini bisa menjadi jawaban yang benar?**
> **Bisa → itu PENYEMPITAN**, dan penyempitan hanya sah bila pertanyaan memintanya.
> **Tidak bisa → itu EKSKLUSI**, dan boleh selalu.

Kolom yang kosong **tidak lolos** uji ini: baris berkolom kosong tetap pengawasan sungguhan dan ikut
dihitung, kecuali pertanyaannya memang tentang kolom itu.

## Bentuk angka

- **Angka utama dari query globalnya sendiri**, bukan penjumlahan partisi.
- Setelah join ke bridge, penjumlahan per kelompok bisa melebihi total — satu event muncul di beberapa
  kelompok. Untuk menghitung kasus setelah join, `COUNT(DISTINCT f.id)`.
- Satu statement per panggilan, tanpa `;`.
- Scope yang sudah disetujui harus **terlihat di SQL**, bukan hanya di kalimat jawaban.

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| angka dobel | `COUNT(*)` setelah join ke bridge, lalu disebut jumlah kasus | `COUNT(DISTINCT f.id)` (`00` §bridge) |
| angka kasus membengkak | bridge dibaca tanpa join ke fakta | `INNER JOIN` ke `fact_pengawasan` |
| hasil kosong padahal kasusnya ada | media dibaca dari bridge yang salah | routing media (`20`) |
| filter periode menghilangkan banyak baris | `EXTRACT` di `WHERE`, atau kolom administrasi alih-alih kolom kegiatan | rentang berbatas pada `tgl_start` |
| populasi menyusut tanpa diminta | penjaga keterisian kolom yang tidak diminta | uji penyempitan vs eksklusi di atas |

## Batas & honest gap

- `tgl_start` bisa memuat tanggal **di masa depan** relatif hari pengambilan data — itu jadwal valid,
  bukan data kotor. Kesegaran data dicek lewat `created_at` — periksa nilai maksimumnya setiap sesi, jangan diasumsikan.
- Periode berjalan selalu parsial → sebutkan.

## Rute

- Butuh tahu objek & routing → **lihat** `95-batas-domain.md`
- Media / iklan → **lihat** `20-media-dan-iklan.md`
- Vonis → **lihat** `30-vonis.md`
- Kekosongan kolom → **lihat** `90-kualitas-data.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `fact_pengawasan` | `id`, `balai_id`, `status_id`, `komoditi_id`, `kategori`, `tgl_start`, `tgl_end`, `no_surat`, `produk_id`, `provinsi_iklan_id`, `kabupaten_iklan_id` | — |
| `bridge_pengawasan_produk` | `pengawasan_id`, `produk_id`, `nama_produk`, `nie` | — |
| `dim_status_code` | `id`, `domain` | `domain='pengawasan'` |
