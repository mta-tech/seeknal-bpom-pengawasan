# Pair per Pertanyaan — database `pengawasan`

Setiap pasangan pertanyaan→SQL dari `context_stores` KAI, ditembakkan ke database live **2026-08-13**, lalu didiagnosis sebabnya. Total **88 pertanyaan**, **81 menghasilkan data (92%)**.

## Sebaran diagnosa

| Kode | Arti | Jumlah |
|---|---|--:|
| `PULIH_RELASI` | 🔧 Pulih: ganti nama relasi | 44 |
| `OK_LANGSUNG` | ✅ Jalan apa adanya | 31 |
| `ERR_SQL_RUSAK` | ⛔ Gagal — SQL rusak sejak asalnya | 3 |
| `PULIH_RELASI_NILAI` | 🔧 Pulih: relasi + nilai | 3 |
| `OK_TAPI_RAKSASA` | ⚠️ Jalan tapi >100rb baris tanpa agregasi | 3 |
| `NOL_ANTIJOIN_KOSONG` | ○ Nol baris — anti-join memang kosong (jawaban sah) | 2 |
| `NOL_PLACEHOLDER` | 🔴 Nol baris — literal masih placeholder template | 1 |
| `ERR_KOLOM_DIHAPUS` | ⛔ Gagal — kolom dihapus dari skema (NOT COVERED) | 1 |

> Berkas pendamping: `pair_ringkas.csv` (tabel, satu baris per pertanyaan) dan `pair_detail_sql.csv` (SQL diratakan satu baris).

---

## Generasi v1 — koneksi awal (Jul 2025), SQL menunjuk view `vw_*`

26 pertanyaan.

### [1] "buatkan data perbedaan hasil pengawasan iklan obat antara hasil verifikasi balai dan hasil verifikasi pusat dalam bentuk grafik dan narasi."

| | |
|---|---|
| Bentuk NER | `"buatkan data perbedaan hasil pengawasan iklan obat antara hasil verifikasi <HALL NAME> dan hasil verifikasi <HALL NAME> dalam bentuk grafik dan naras` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 25 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah FROM vw_pengawasan_v2 GROUP BY kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat ORDER BY kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat;
-- DIPAKAI: SELECT kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah FROM mv_pengawasan GROUP BY kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat ORDER BY kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat;
```

### [2] "buatkan pengelompokan iklan obat mk/tmk berdasarkan materi yang sama dari semua upt yang melaporkan materi iklan tersebut."

| | |
|---|---|
| Bentuk NER | `"buatkan pengelompokan iklan obat <PRODUCT NAME> berdasarkan materi yang sama dari semua upt yang melaporkan materi iklan tersebut."` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 481 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT media_iklan, nama_balai, kesimpulan_penilaian_akhir , count(*) FROM vw_pengawasan_v2 WHERE lower(komoditi) IN ('obat') GROUP BY media_iklan, nama_balai, kesimpulan_penilaian_akhir ORDER BY media_iklan;
-- DIPAKAI: SELECT media_iklan, nama_balai, kesimpulan_penilaian_akhir , count(*) FROM mv_pengawasan WHERE lower(komoditi) IN ('obat') GROUP BY media_iklan, nama_balai, kesimpulan_penilaian_akhir ORDER BY media_iklan;
```

### [3] "buatkan pengelompokan iklan obat tradisional; suplemen kesehatan; obat kuasi mk/tmk berdasarkan materi yang sama dari semua upt yang melaporkan materi iklan yang sama."

| | |
|---|---|
| Bentuk NER | `"buatkan pengelompokan iklan <CLASSIFICATION>; <CLASSIFICATION>; <CLASSIFICATION> berdasarkan materi yang sama dari semua upt yang melaporkan materi i` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 25,063 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_produk, media_iklan, nama_balai FROM vw_pengawasan_v2 WHERE lower(komoditi) IN ('obat tradisional (ot)', 'suplemen kesehatan', 'obat kuasi') GROUP BY nama_produk, media_iklan, nama_balai
-- DIPAKAI: SELECT nama_produk, media_iklan, nama_balai FROM mv_pengawasan WHERE lower(komoditi) IN ('obat tradisional (ot)', 'suplemen kesehatan', 'obat kuasi') GROUP BY nama_produk, media_iklan, nama_balai
```

### [4] "tampilkan data hasil kesimpulan tmk berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai mk pada rentang waktu antara tanggal mulai dan tanggal selesai 2 minggu."

| | |
|---|---|
| Bentuk NER | `"tampilkan data hasil <CONCLUSION TYPE> berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai mk pada rentang waktu antara tanggal mulai da` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 35 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT * FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_pusat = kesimpulan_penilaian_balai AND kesimpulan_penilaian_pusat = 'TMK' AND tgl_start >= (SELECT (current_date - interval '2 week')) AND tgl_end <= current_date
-- DIPAKAI: SELECT * FROM mv_pengawasan WHERE kesimpulan_penilaian_pusat = kesimpulan_penilaian_balai AND kesimpulan_penilaian_pusat = 'TMK' AND tgl_start >= (SELECT (current_date - interval '2 week')) AND tgl_end <= current_date
```

### [5] "tampilkan data hasil kesimpulan tmk berdasarkan hasil verifikasi pusat pada rentang waktu antara tanggal mulai dan tanggal selesai 2 minggu."

| | |
|---|---|
| Bentuk NER | `"tampilkan data hasil <CONCLUSION TYPE> berdasarkan hasil verifikasi pusat pada rentang waktu antara tanggal mulai dan tanggal selesai 2 minggu."` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 88 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT * FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_pusat = 'TMK' AND tgl_start = tgl_end - INTERVAL '14 days';
-- DIPAKAI: SELECT * FROM mv_pengawasan WHERE kesimpulan_penilaian_pusat = 'TMK' AND tgl_start = tgl_end - INTERVAL '14 days';
```

### [6] "tampilkan data hasil kesimpulan tmk berdasarkan hasil verifikasi pusat pada rentang waktu antara tanggal mulai dan tanggal selesai 2 minggu."

| | |
|---|---|
| Bentuk NER | `"tampilkan data hasil <CONCLUSION TYPE> berdasarkan hasil verifikasi pusat pada rentang waktu antara tanggal mulai dan tanggal selesai 2 minggu."` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 42,725 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT * FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_pusat = 'TMK' AND tgl_end <= tgl_start + INTERVAL '14 days';
-- DIPAKAI: SELECT * FROM mv_pengawasan WHERE kesimpulan_penilaian_pusat = 'TMK' AND tgl_end <= tgl_start + INTERVAL '14 days';
```

### [7] "tampilkan data iklan yang dilaporkan mk/tmk dari masing-masing upt berdasarkan nama produk, jenis pangan, produsen, kabupaten/provinsi produsen, media iklan, jenis pembuat iklan (pelaku usaha/peroran

| | |
|---|---|
| Bentuk NER | `"tampilkan data iklan yang dilaporkan mk/tmk dari masing-masing upt berdasarkan nama produk, jenis pangan, produsen, kabupaten/provinsi produsen, medi` |
| Tabel | `mv_pengawasan + tgl_end` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 23,692 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_balai, nama_produk, media_iklan, komoditi, SUM(CASE WHEN kesimpulan_penilaian_akhir = 'MK' THEN 1 ELSE 0 END) AS jumlah_mk, SUM(CASE WHEN kesimpulan_penilaian_akhir = 'TMK' THEN 1 ELSE 0 END) AS jumlah_tmk FROM vw_pengawasan_v2 WHERE extract(year from tgl_end) = 2025 AND kesimpulan_penilaian_akhir IN ('MK', 'TMK') GROUP BY -- Mengelompokkan berdasarkan semua kategori yang diminta nama_balai, nama_produk, 
-- DIPAKAI: SELECT nama_balai, nama_produk, media_iklan, komoditi, SUM(CASE WHEN kesimpulan_penilaian_akhir = 'MK' THEN 1 ELSE 0 END) AS jumlah_mk, SUM(CASE WHEN kesimpulan_penilaian_akhir = 'TMK' THEN 1 ELSE 0 END) AS jumlah_tmk FROM mv_pengawasan WHERE extract(year from tgl_end) = 2025 AND kesimpulan_penilaian_akhir IN ('MK', 'TMK') GROUP BY -- Mengelompokkan berdasarkan semua kategori yang diminta nama_balai, nama_produk, med
```

### [8] "tampilkan data iklan yang dilaporkan mk/tmk dari masing-masing upt yang dikategorikan berdasarkan nama produk, industri farmasi, media publikasi, dan golongan obat dengan status selesai pada rentang 

| | |
|---|---|
| Bentuk NER | `"tampilkan data iklan yang dilaporkan mk/tmk dari masing-masing upt yang dikategorikan berdasarkan nama produk, <PRODUCT NAME>, media publikasi, dan <` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 1,794 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_produk, pendaftar AS industri_farmasi, media_iklan, lower(komoditi) AS golongan_obat, nama_balai AS upt, kesimpulan_penilaian_balai AS kesimpulan_upt FROM public.vw_pengawasan_v2 WHERE tgl_start >= '2024-06-25' AND tgl_end <= '2024-06-30'
-- DIPAKAI: SELECT nama_produk, pendaftar AS industri_farmasi, media_iklan, lower(komoditi) AS golongan_obat, nama_balai AS upt, kesimpulan_penilaian_balai AS kesimpulan_upt FROM mv_pengawasan WHERE tgl_start >= '2024-06-25' AND tgl_end <= '2024-06-30'
```

### [9] "tampilkan persentase kategori pangan yang tmk pada rentang waktu antara tanggal mulai dan tanggal selesai 2 minggu (baik secara nasional maupun per upt)."

| | |
|---|---|
| Bentuk NER | `"tampilkan persentase <CLASSIFICATION> yang tmk pada rentang waktu antara tanggal mulai dan tanggal selesai 2 minggu (baik secara nasional maupun per ` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 79 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_balai, COUNT(CASE WHEN kesimpulan_penilaian_akhir = 'TMK' THEN 1 END) AS jumlah_pemeriksaan_tmk, COUNT(*) AS jumlah_pemeriksaan_total, CASE WHEN COUNT(*) > 0 THEN ROUND( (CAST(COUNT(CASE WHEN kesimpulan_penilaian_akhir = 'TMK' THEN 1 END) AS NUMERIC) * 100.0) / COUNT(*), 2 ) ELSE 0.00 END AS persentase_tmk FROM public.vw_pengawasan_v2 WHERE tgl_end - INTERVAL '14 days' > tgl_start GROUP BY 1
-- DIPAKAI: SELECT nama_balai, COUNT(CASE WHEN kesimpulan_penilaian_akhir = 'TMK' THEN 1 END) AS jumlah_pemeriksaan_tmk, COUNT(*) AS jumlah_pemeriksaan_total, CASE WHEN COUNT(*) > 0 THEN ROUND( (CAST(COUNT(CASE WHEN kesimpulan_penilaian_akhir = 'TMK' THEN 1 END) AS NUMERIC) * 100.0) / COUNT(*), 2 ) ELSE 0.00 END AS persentase_tmk FROM mv_pengawasan WHERE tgl_end - INTERVAL '14 days' > tgl_start GROUP BY 1
```

### [10] "tampilkan tren data hasil pengawasan iklan obat tradisional; suplemen kesehatan; obat kuasi pada rentang tahun 2024-2025 berdasarkan hasil verifikasi pusat mk/tmk"

| | |
|---|---|
| Bentuk NER | `"tampilkan tren data hasil pengawasan iklan <CLASSIFICATION>; <CLASSIFICATION>; <CLASSIFICATION> pada rentang tahun <YEAR> berdasarkan hasil verifikas` |
| Tabel | `tgl_start + mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 30 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT EXTRACT( YEAR from tgl_start ) AS tahun, komoditi, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah FROM vw_pengawasan_v2 WHERE EXTRACT( YEAR from tgl_start ) BETWEEN 2024 AND 2025 AND lower(komoditi) IN ('obat tradisional (ot)', 'suplemen kesehatan', 'obat kuasi') AND kesimpulan_penilaian_pusat != '' GROUP BY tahun, komoditi, kesimpulan_penilaian_pusat ORDER BY tahun, komoditi;
-- DIPAKAI: SELECT EXTRACT( YEAR from tgl_start ) AS tahun, komoditi, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah FROM mv_pengawasan WHERE EXTRACT( YEAR from tgl_start ) BETWEEN 2024 AND 2025 AND lower(komoditi) IN ('obat tradisional (ot)', 'suplemen kesehatan', 'obat kuasi') AND kesimpulan_penilaian_pusat != '' GROUP BY tahun, komoditi, kesimpulan_penilaian_pusat ORDER BY tahun, komoditi;
```

### [11] "tampilkan tren data hasil pengawasan iklan pangan (mk/tmk) pada rentang tahun 2025 berdasarkan hasil verifikasi upt"

| | |
|---|---|
| Bentuk NER | `"tampilkan tren data hasil pengawasan iklan pangan (mk/tmk) pada rentang tahun <YEAR> berdasarkan hasil verifikasi upt"` |
| Tabel | `tgl_end + mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 60 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : select extract(month from tgl_end) as bulan, extract(year from tgl_end) as tahun, kesimpulan_penilaian_balai, count(*) jumlah_pengawasan from vw_pengawasan_v2 where kesimpulan_penilaian_balai != '' and extract(year from tgl_end) = 2025 group by extract(month from tgl_end), extract(year from tgl_end), kesimpulan_penilaian_balai order by kesimpulan_penilaian_balai, extract(month from tgl_end), extract(year from tgl_end
-- DIPAKAI: select extract(month from tgl_end) as bulan, extract(year from tgl_end) as tahun, kesimpulan_penilaian_balai, count(*) jumlah_pengawasan from mv_pengawasan where kesimpulan_penilaian_balai != '' and extract(year from tgl_end) = 2025 group by extract(month from tgl_end), extract(year from tgl_end), kesimpulan_penilaian_balai order by kesimpulan_penilaian_balai, extract(month from tgl_end), extract(year from tgl_end)
```

### [12] tampilkan data berapa jumlah iklan obat tradisional; suplemen kesehatan; obat kuasi yang dilaporkan oleh upt dengan hasil verifikasi pusat mk/tmk.

| | |
|---|---|
| Bentuk NER | `tampilkan data berapa jumlah iklan <COMMODITY NAME>; <COMMODITY NAME>; <COMMODITY NAME> yang dilaporkan oleh upt dengan hasil verifikasi pusat mk/tmk.` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 1 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT COUNT(*) FROM vw_pengawasan_v2 WHERE lower(komoditi) IN ('obat tradisional (ot)', 'suplemen kesehatan', 'obat kuasi') AND kesimpulan_penilaian_pusat = 'TMK';
-- DIPAKAI: SELECT COUNT(*) FROM mv_pengawasan WHERE lower(komoditi) IN ('obat tradisional (ot)', 'suplemen kesehatan', 'obat kuasi') AND kesimpulan_penilaian_pusat = 'TMK';
```

### [13] tampilkan data iklan yang dilaporkan mk/tmk dari masing-masing upt yang dikategorikan berdasarkan nama produk, sarana produksi, media publikasi, dan klaim dalam promosi/iklan dengan status selesai pad

| | |
|---|---|
| Bentuk NER | `tampilkan data iklan yang dilaporkan <CLASSIFICATION> dari masing-masing upt yang dikategorikan berdasarkan <PRODUCT NAME>, <FACILITY TYPE>, <CLASSIFI` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 46,147 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_balai, nama_produk, SUM(CASE WHEN kesimpulan_penilaian_akhir = 'MK' THEN 1 ELSE 0 END) AS jumlah_mk, SUM(CASE WHEN kesimpulan_penilaian_akhir = 'TMK' THEN 1 ELSE 0 END) AS jumlah_tmk FROM vw_pengawasan_v2 WHERE tgl_start >= '2024-06-10' AND tgl_end <= '2025-06-20' AND kesimpulan_penilaian_akhir IS NOT NULL AND kesimpulan_penilaian_akhir <> '' GROUP BY nama_balai, nama_produk ORDER BY nama_balai, nama_prod
-- DIPAKAI: SELECT nama_balai, nama_produk, SUM(CASE WHEN kesimpulan_penilaian_akhir = 'MK' THEN 1 ELSE 0 END) AS jumlah_mk, SUM(CASE WHEN kesimpulan_penilaian_akhir = 'TMK' THEN 1 ELSE 0 END) AS jumlah_tmk FROM mv_pengawasan WHERE tgl_start >= '2024-06-10' AND tgl_end <= '2025-06-20' AND kesimpulan_penilaian_akhir IS NOT NULL AND kesimpulan_penilaian_akhir <> '' GROUP BY nama_balai, nama_produk ORDER BY nama_balai, nama_produk;
```

### [14] tampilkan data ketepatan waktu pelaporan oleh upt yang dihitung berdasarkan laporan yang dikirimkan tanggal kepala balai sebelum batas tanggal 9 bulan berikutnya.

| | |
|---|---|
| Bentuk NER | `tampilkan data ketepatan waktu pelaporan oleh upt yang dihitung berdasarkan laporan yang dikirimkan tanggal kepala balai sebelum batas tanggal <MONTH>` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 25,943 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_balai, tgl_start , (DATE_TRUNC('month', tgl_end) + INTERVAL '1 month' + INTERVAL '8 days')::date AS batas_waktu_pelaporan, CASE -- Check if tanggal_start is on or before the 9th day of the next month WHEN tgl_start <= (DATE_TRUNC('month', tgl_end) + INTERVAL '1 month' + INTERVAL '8 days')::date THEN 'Tepat Waktu' ELSE 'Terlambat' END AS status_ketepatan_waktu, count(*) FROM public.vw_pengawasan_v2 -- Past
-- DIPAKAI: SELECT nama_balai, tgl_start , (DATE_TRUNC('month', tgl_end) + INTERVAL '1 month' + INTERVAL '8 days')::date AS batas_waktu_pelaporan, CASE -- Check if tanggal_start is on or before the 9th day of the next month WHEN tgl_start <= (DATE_TRUNC('month', tgl_end) + INTERVAL '1 month' + INTERVAL '8 days')::date THEN 'Tepat Waktu' ELSE 'Terlambat' END AS status_ketepatan_waktu, count(*) FROM mv_pengawasan -- Pastikan ini a
```

### [15] tampilkan data label dengan tanggal sampling pada bulan januari 2025 yang dilaporkan ke pusat melewati batas waktu tanggal 15 februari 2025 (data label tidak tepat waktu).

| | |
|---|---|
| Bentuk NER | `tampilkan data label dengan tanggal sampling pada bulan <MONTH> <YEAR> yang dilaporkan ke pusat melewati batas waktu tanggal 15 <MONTH> <YEAR> (data l` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SYNTAX → **ERR_SYNTAX** |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **⛔ Gagal — SQL rusak sejak asalnya** |
| Sebab | SQL rusak sejak asalnya (mis. ";" di tengah komentar) — perlu ditulis ulang |

```sql
-- ASLI   : SELECT * -- Select all columns for the specific label data FROM public.vw_pengawasan_v2 WHERE tgl_start >= '2025-01-01'::date -- Sampling in January 2025 (start) AND tgl_start <= '2025-01-31'::date -- Sampling in January 2025 (end) AND tgl_end > '2025-02-15'::date; -- Report sent AFTER February 15, 2025 (untimely)
-- DIPAKAI: SELECT * -- Select all columns for the specific label data FROM mv_pengawasan WHERE tgl_start >= '2025-01-01'::date -- Sampling in January 2025 (start) AND tgl_start <= '2025-01-31'::date -- Sampling in January 2025 (end) AND tgl_end > '2025-02-15'::date; -- Report sent AFTER February 15, 2025 (untimely)
```

> ERROR: `ERROR: syntax error at or near ";"`

### [16] tampilkan data label yang dilaporkan mk/tmk dari masing-masing upt yang dikategorikan berdasarkan nama produk, jenis pangan, kategori pangan, produsen, kabupaten/provinsi produsen, pada rentang waktu 

| | |
|---|---|
| Bentuk NER | `tampilkan data label yang dilaporkan <CONCLUSION TYPE> dari masing-masing upt yang dikategorikan berdasarkan <PRODUCT NAME>, <COMMODITY NAME>, <CLASSI` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 41,836 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_produk, lower(komoditi), pendaftar, nama_balai FROM public.vw_pengawasan_v2 WHERE tgl_start >= '2025-01-01' AND tgl_end <= '2025-12-31' GROUP BY nama_produk, lower(komoditi), pendaftar, nama_balai;
-- DIPAKAI: SELECT nama_produk, lower(komoditi), pendaftar, nama_balai FROM mv_pengawasan WHERE tgl_start >= '2025-01-01' AND tgl_end <= '2025-12-31' GROUP BY nama_produk, lower(komoditi), pendaftar, nama_balai;
```

### [17] tampilkan data upt yang tidak melaporkan iklan obat tradisional; suplemen kesehatan; obat kuasi.

| | |
|---|---|
| Bentuk NER | `tampilkan data upt yang tidak melaporkan <COMMODITY NAME>; <COMMODITY NAME>; <COMMODITY NAME>.` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 84 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 WHERE lower(komoditi) NOT IN ('obat tradisional (ot)', 'suplemen kesehatan', 'obat kuasi');
-- DIPAKAI: SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE lower(komoditi) NOT IN ('obat tradisional (ot)', 'suplemen kesehatan', 'obat kuasi');
```

### [18] tampilkan jumlah iklan tepat waktu yang telah dikirimkan ke pusat pada upt [nama upt] pada rentang waktu 2025 (ketentuan : hasil pengawasan iklan dikirimkan ke pusat maksimal tanggal 10 bulan berikutn

| | |
|---|---|
| Bentuk NER | `tampilkan jumlah iklan tepat waktu yang telah dikirimkan ke pusat pada upt [nama upt] pada rentang waktu <YEAR> (ketentuan : hasil pengawasan iklan di` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 1 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT CASE WHEN tgl_end <= (DATE_TRUNC('month', tgl_start) + INTERVAL '1 month' + INTERVAL '9 days')::date THEN 'Tepat Waktu' ELSE 'Terlambat' END AS status_ketepatan_waktu, count(*) FROM public.vw_pengawasan_v2 WHERE lower(nama_balai) like '%jakarta%' AND EXTRACT(YEAR FROM tgl_start) = 2025 -- Filter for the year 2025 GROUP BY 1;
-- DIPAKAI: SELECT CASE WHEN tgl_end <= (DATE_TRUNC('month', tgl_start) + INTERVAL '1 month' + INTERVAL '9 days')::date THEN 'Tepat Waktu' ELSE 'Terlambat' END AS status_ketepatan_waktu, count(*) FROM mv_pengawasan WHERE lower(nama_balai) like '%jakarta%' AND EXTRACT(YEAR FROM tgl_start) = 2025 -- Filter for the year 2025 GROUP BY 1;
```

### [19] tampilkan jumlah label tepat waktu yang telah dikirimkan ke pusat pada upt dengan nama 'balai pom di jakarta' pada rentang periode 2025 (ketentuan : hasil pengawasan label dikirimkan ke pusat maksimal

| | |
|---|---|
| Bentuk NER | `tampilkan jumlah label tepat waktu yang telah dikirimkan ke pusat pada upt dengan nama '<HALL NAME>' pada rentang periode <YEAR> (ketentuan : hasil pe` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 1 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT CASE WHEN tgl_end <= (DATE_TRUNC('month', tgl_start) + INTERVAL '1 month' + INTERVAL '14 days')::date THEN 'Tepat Waktu' ELSE 'Terlambat' END AS status_ketepatan_waktu, count(*) FROM public.vw_pengawasan_v2 WHERE lower(nama_balai) like '%jakarta%' AND EXTRACT(YEAR FROM tgl_start) = 2025 -- Filter for the year 2025 GROUP BY 1;
-- DIPAKAI: SELECT CASE WHEN tgl_end <= (DATE_TRUNC('month', tgl_start) + INTERVAL '1 month' + INTERVAL '14 days')::date THEN 'Tepat Waktu' ELSE 'Terlambat' END AS status_ketepatan_waktu, count(*) FROM mv_pengawasan WHERE lower(nama_balai) like '%jakarta%' AND EXTRACT(YEAR FROM tgl_start) = 2025 -- Filter for the year 2025 GROUP BY 1;
```

### [20] tampilkan persentase media iklan (dibandingkan seluruh iklan yang diawasi pada rentang waktu tertentu) yang diawasi pada upt dengan nama 'balai pom di jakarta' pada rentang waktu antara tanggal '2025-

| | |
|---|---|
| Bentuk NER | `tampilkan persentase media iklan (dibandingkan seluruh iklan yang diawasi pada rentang waktu tertentu) yang diawasi pada upt dengan nama '<HALL NAME>'` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 3 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT media_iklan, count(*) FROM vw_pengawasan_v2 vpv WHERE lower(nama_balai) like '%jakarta%' AND EXTRACT(YEAR FROM tgl_start) = 2025 -- Filter for the year 2025 GROUP BY media_iklan
-- DIPAKAI: SELECT media_iklan, count(*) FROM mv_pengawasan vpv WHERE lower(nama_balai) like '%jakarta%' AND EXTRACT(YEAR FROM tgl_start) = 2025 -- Filter for the year 2025 GROUP BY media_iklan
```

### [21] tampilkan rekapitulasi jumlah laporan pengawasan iklan obat masing-masing upt yang telah dikirim ke pusat (berdasarkan tanggal kepala balai) pada periode waktu antara tanggal mulai 20 Juni 2024 hingga

| | |
|---|---|
| Bentuk NER | `tampilkan rekapitulasi jumlah laporan pengawasan iklan obat masing-masing upt yang telah dikirim ke pusat (berdasarkan tanggal kepala balai) pada peri` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 56 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_balai, COUNT(*) AS jumlah_laporan_dikirim FROM public.vw_pengawasan_v2 vpv WHERE tgl_end >= '2024-06-20'::date AND tgl_end <= '2024-06-30'::date AND lower(komoditi) LIKE 'obat' GROUP BY nama_balai, komoditi ORDER BY count(*);
-- DIPAKAI: SELECT nama_balai, COUNT(*) AS jumlah_laporan_dikirim FROM mv_pengawasan vpv WHERE tgl_end >= '2024-06-20'::date AND tgl_end <= '2024-06-30'::date AND lower(komoditi) LIKE 'obat' GROUP BY nama_balai, komoditi ORDER BY count(*);
```

### [22] tampilkan rekapitulasi jumlah laporan pengawasan iklan obat tradisional; suplemen kesehatan; obat kuasi masing-masing upt yang telah dikirim ke pusat (berdasarkan tanggal kepala balai) pada periode wa

| | |
|---|---|
| Bentuk NER | `tampilkan rekapitulasi jumlah laporan pengawasan iklan <COMMODITY NAME>; <COMMODITY NAME>; <COMMODITY NAME> masing-masing upt yang telah dikirim ke pu` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 7 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_balai, SUM(CASE WHEN komoditi = 'OBAT TRADISIONAL (OT)' THEN 1 ELSE 0 END) AS jumlah_obat_tradisional, SUM(CASE WHEN komoditi = 'SUPLEMEN KESEHATAN' THEN 1 ELSE 0 END) AS jumlah_suplemen_kesehatan, SUM(CASE WHEN komoditi = 'OBAT KUASI' THEN 1 ELSE 0 END) AS jumlah_obat_kuasi, COUNT(*) AS total_laporan FROM vw_pengawasan_v2 -- atau tabel/view yang sesuai WHERE kesimpulan_penilaian_pusat != '' -- Filter 2: 
-- DIPAKAI: SELECT nama_balai, SUM(CASE WHEN komoditi = 'OBAT TRADISIONAL (OT)' THEN 1 ELSE 0 END) AS jumlah_obat_tradisional, SUM(CASE WHEN komoditi = 'SUPLEMEN KESEHATAN' THEN 1 ELSE 0 END) AS jumlah_suplemen_kesehatan, SUM(CASE WHEN komoditi = 'OBAT KUASI' THEN 1 ELSE 0 END) AS jumlah_obat_kuasi, COUNT(*) AS total_laporan FROM mv_pengawasan -- atau tabel/view yang sesuai WHERE kesimpulan_penilaian_pusat != '' -- Filter 2: Han
```

### [23] tampilkan rekapitulasi jumlah laporan pengawasan iklan pangan masing-masing upt yang telah dikirim ke pusat pada periode waktu antara tanggal 1 januari 2023 dan 31 desember 2025.

| | |
|---|---|
| Bentuk NER | `tampilkan rekapitulasi jumlah laporan pengawasan iklan pangan masing-masing upt yang telah dikirim ke pusat pada periode waktu antara tanggal 1 januar` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 77 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_balai, COUNT(*) AS jumlah_laporan FROM vw_pengawasan_v2 WHERE tgl_start >= '2023-01-01' AND tgl_end <= '2025-12-31' GROUP BY nama_balai;
-- DIPAKAI: SELECT nama_balai, COUNT(*) AS jumlah_laporan FROM mv_pengawasan WHERE tgl_start >= '2023-01-01' AND tgl_end <= '2025-12-31' GROUP BY nama_balai;
```

### [24] tampilkan rekapitulasi jumlah laporan pengawasan label pangan masing-masing upt yang telah dikirim ke pusat pada periode waktu antara tanggal mulai dan tanggal selesai 2 minggu

| | |
|---|---|
| Bentuk NER | `tampilkan <PURPOSE TYPE> masing-masing upt yang telah dikirim ke pusat pada periode waktu antara tanggal mulai dan tanggal selesai 2 minggu` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 72 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_balai, COUNT(*) AS jumlah_laporan FROM vw_pengawasan_v2 WHERE tgl_start >= '2025-07-15' AND tgl_start <= '2025-07-29' GROUP BY nama_balai;
-- DIPAKAI: SELECT nama_balai, COUNT(*) AS jumlah_laporan FROM mv_pengawasan WHERE tgl_start >= '2025-07-15' AND tgl_start <= '2025-07-29' GROUP BY nama_balai;
```

### [25] tampilkan tren data hasil pengawasan iklan obat pada rentang tahun 2024-2025 berdasarkan hasil verifikasi pusat mk/tmk.

| | |
|---|---|
| Bentuk NER | `tampilkan tren data hasil pengawasan iklan obat pada rentang tahun <YEAR>-<YEAR> berdasarkan hasil verifikasi pusat mk/tmk.` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 6 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT kesimpulan_penilaian_pusat, COUNT(*) AS jumlah FROM public.vw_pengawasan_v2 WHERE tgl_start BETWEEN '2024-01-01' AND '2025-01-01' GROUP BY kesimpulan_penilaian_pusat ORDER BY jumlah DESC;
-- DIPAKAI: SELECT kesimpulan_penilaian_pusat, COUNT(*) AS jumlah FROM mv_pengawasan WHERE tgl_start BETWEEN '2024-01-01' AND '2025-01-01' GROUP BY kesimpulan_penilaian_pusat ORDER BY jumlah DESC;
```

### [26] tampilkan visualisasi data berupa urutan data yang paling besar iklan yang dilaporkan mk/tmk dari masing-masing upt berdasarkan nama produk, jenis pangan, produsen, kabupaten/provinsi produsen, media 

| | |
|---|---|
| Bentuk NER | `tampilkan visualisasi data berupa urutan data yang paling besar <PRODUCT NAME> yang dilaporkan mk/tmk dari masing-masing upt berdasarkan nama produk, ` |
| Tabel | `mv_pengawasan + tgl_end` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 23,692 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_balai, nama_produk, media_iklan, komoditi, SUM(CASE WHEN kesimpulan_penilaian_akhir = 'MK' THEN 1 ELSE 0 END) AS jumlah_mk, SUM(CASE WHEN kesimpulan_penilaian_akhir = 'TMK' THEN 1 ELSE 0 END) AS jumlah_tmk FROM vw_pengawasan_v2 WHERE extract(year from tgl_end) = 2025 AND kesimpulan_penilaian_akhir IN ('MK', 'TMK') GROUP BY -- Mengelompokkan berdasarkan semua kategori yang diminta nama_balai, nama_produk, 
-- DIPAKAI: SELECT nama_balai, nama_produk, media_iklan, komoditi, SUM(CASE WHEN kesimpulan_penilaian_akhir = 'MK' THEN 1 ELSE 0 END) AS jumlah_mk, SUM(CASE WHEN kesimpulan_penilaian_akhir = 'TMK' THEN 1 ELSE 0 END) AS jumlah_tmk FROM mv_pengawasan WHERE extract(year from tgl_end) = 2025 AND kesimpulan_penilaian_akhir IN ('MK', 'TMK') GROUP BY -- Mengelompokkan berdasarkan semua kategori yang diminta nama_balai, nama_produk, med
```

---

## Generasi v2 — koneksi `_all` (Ags 2025)

26 pertanyaan.

### [27] buatkan data perbedaan hasil pengawasan iklan obat antara hasil verifikasi balai dan hasil verifikasi pusat dalam bentuk grafik dan narasi.

| | |
|---|---|
| Bentuk NER | `buatkan data perbedaan hasil pengawasan iklan obat antara hasil verifikasi balai dan hasil verifikasi pusat dalam bentuk grafik dan narasi.` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 4 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan ; nilai 'Obat'→'OBAT' |
| Diagnosa | **🔧 Pulih: relasi + nilai** |
| Sebab | Pulih setelah penyesuaian relasi + nilai ke skema live |

```sql
-- ASLI   : SELECT kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah_perbedaan FROM public.vw_pengawasan_v2 WHERE komoditi = 'OBAT' AND kesimpulan_penilaian_balai IS NOT NULL AND kesimpulan_penilaian_pusat IS NOT NULL AND kesimpulan_penilaian_balai <> kesimpulan_penilaian_pusat GROUP BY kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat ORDER BY jumlah_perbedaan DESC;
-- DIPAKAI: SELECT kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah_perbedaan FROM mv_pengawasan WHERE komoditi = 'OBAT' AND kesimpulan_penilaian_balai IS NOT NULL AND kesimpulan_penilaian_pusat IS NOT NULL AND kesimpulan_penilaian_balai <> kesimpulan_penilaian_pusat GROUP BY kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat ORDER BY jumlah_perbedaan DESC;
```

### [28] buatkan data perbedaan hasil pengawasan iklan obat tradisional; suplemen kesehatan; obat kuasi antara hasil verifikasi balai dan hasil verifikasi pusat dalam bentuk grafik dan narasi untuk periode wak

| | |
|---|---|
| Bentuk NER | `buatkan data perbedaan hasil pengawasan iklan <COMMODITY NAME>; <COMMODITY NAME>; <COMMODITY NAME> antara hasil verifikasi balai dan hasil verifikasi ` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **ERR_LAIN** |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **⛔ Gagal — SQL rusak sejak asalnya** |
| Sebab | SQL rusak sejak asalnya: ERROR: argument of AND must be type boolean, not type record |

```sql
-- ASLI   : SELECT kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah_perbedaan FROM public.vw_pengawasan_v2 WHERE ('OBAT TRADISIONAL (OT)', 'SUPLEMEN KESEHATAN', 'OBAT KUASI') AND kesimpulan_penilaian_balai IS NOT NULL AND kesimpulan_penilaian_pusat IS NOT NULL AND kesimpulan_penilaian_balai <> kesimpulan_penilaian_pusat GROUP BY kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat ORDER BY jumlah_perb
-- DIPAKAI: SELECT kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah_perbedaan FROM mv_pengawasan WHERE ('OBAT TRADISIONAL (OT)', 'SUPLEMEN KESEHATAN', 'OBAT KUASI') AND kesimpulan_penilaian_balai IS NOT NULL AND kesimpulan_penilaian_pusat IS NOT NULL AND kesimpulan_penilaian_balai <> kesimpulan_penilaian_pusat GROUP BY kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat ORDER BY jumlah_perbedaan DESC
```

> ERROR: `ERROR: argument of AND must be type boolean, not type record`

### [29] tampilkan data berapa jumlah iklan obat tradisional; suplemen kesehatan; obat kuasi yang dilaporkan oleh upt dengan hasil verifikasi pusat mk/tmk.

| | |
|---|---|
| Bentuk NER | `tampilkan data berapa jumlah iklan <COMMODITY NAME>; <COMMODITY NAME>; <COMMODITY NAME> yang dilaporkan oleh upt dengan hasil verifikasi pusat mk/tmk.` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 3 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : select komoditi, kesimpulan_penilaian_pusat, COUNT(*) FROM public.vw_pengawasan_v2 WHERE komoditi IN ('OBAT KUASI','OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN') AND kesimpulan_penilaian_pusat IN ('MK', 'TMK') group by komoditi, kesimpulan_penilaian_pusat order by komoditi, kesimpulan_penilaian_pusat;
-- DIPAKAI: select komoditi, kesimpulan_penilaian_pusat, COUNT(*) FROM mv_pengawasan WHERE komoditi IN ('OBAT KUASI','OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN') AND kesimpulan_penilaian_pusat IN ('MK', 'TMK') group by komoditi, kesimpulan_penilaian_pusat order by komoditi, kesimpulan_penilaian_pusat;
```

### [30] tampilkan data hasil kesimpulan tmk berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai mk pada rentang waktu antara tanggal mulai dan tanggal selesai 2 minggu.

| | |
|---|---|
| Bentuk NER | `tampilkan data <CONCLUSION TYPE> berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai mk pada rentang waktu antara tanggal mulai dan tangg` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 9 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT * FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_pusat = 'TMK' and kesimpulan_penilaian_balai ='MK' AND (tgl_end - tgl_start) = 14;
-- DIPAKAI: SELECT * FROM mv_pengawasan WHERE kesimpulan_penilaian_pusat = 'TMK' and kesimpulan_penilaian_balai ='MK' AND (tgl_end - tgl_start) = 14;
```

### [31] tampilkan data hasil kesimpulan tmk berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai mk pada rentang waktu Januari hingga Juni 2025

| | |
|---|---|
| Bentuk NER | `tampilkan data <CONCLUSION TYPE> berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai mk pada rentang waktu <MONTH> hingga <MONTH> <YEAR>` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 622 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT * FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_pusat = 'TMK' AND kesimpulan_penilaian_balai = 'MK' AND tgl_start >= '2025-01-01' AND tgl_end <= '2025-06-30';
-- DIPAKAI: SELECT * FROM mv_pengawasan WHERE kesimpulan_penilaian_pusat = 'TMK' AND kesimpulan_penilaian_balai = 'MK' AND tgl_start >= '2025-01-01' AND tgl_end <= '2025-06-30';
```

### [32] tampilkan data hasil kesimpulan tmk berdasarkan hasil verifikasi pusat pada rentang waktu antara tanggal mulai dan tanggal selesai 2 minggu.

| | |
|---|---|
| Bentuk NER | `tampilkan data hasil kesimpulan <CONCLUSION TYPE> berdasarkan hasil verifikasi pusat pada rentang waktu antara tanggal mulai dan tanggal selesai 2 min` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 88 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT * FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_pusat = 'TMK' AND (tgl_end - tgl_start) = 14;
-- DIPAKAI: SELECT * FROM mv_pengawasan WHERE kesimpulan_penilaian_pusat = 'TMK' AND (tgl_end - tgl_start) = 14;
```

### [33] tampilkan data hasil kesimpulan tmk berdasarkan hasil verifikasi pusat pada rentang waktu Januari hingga Juni 2025

| | |
|---|---|
| Bentuk NER | `tampilkan data hasil kesimpulan <CONCLUSION TYPE> berdasarkan hasil verifikasi pusat pada rentang waktu <MONTH> hingga <MONTH> <YEAR>` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 3,331 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT * FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_pusat = 'TMK' AND tgl_start >= '2025-01-01' AND tgl_end <= '2025-06-30';
-- DIPAKAI: SELECT * FROM mv_pengawasan WHERE kesimpulan_penilaian_pusat = 'TMK' AND tgl_start >= '2025-01-01' AND tgl_end <= '2025-06-30';
```

### [34] tampilkan data iklan yang dilaporkan mk/tmk dari masing-masing upt yang dikategorikan berdasarkan nama produk, industri farmasi, media publikasi, dan golongan obat dengan status selesai pada rentang w

| | |
|---|---|
| Bentuk NER | `tampilkan data iklan yang dilaporkan mk/tmk dari masing-masing upt yang dikategorikan berdasarkan <PRODUCT NAME>, <CLASSIFICATION>, <CLASSIFICATION>, ` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 677 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan ; nilai 'Obat'→'OBAT' ; nilai 'Kosmetika'→'KOSMETIKA' |
| Diagnosa | **🔧 Pulih: relasi + nilai** |
| Sebab | Pulih setelah penyesuaian relasi + nilai ke skema live |

```sql
-- ASLI   : SELECT nama_balai, nama_produk, pendaftar, media_iklan, komoditi FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_pusat IN ('MK', 'TMK') and komoditi IN ('KOSMETIKA','OBAT','OBAT KUASI','OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN') AND tgl_start >= '2024-06-25' AND tgl_end <= '2024-06-30'
-- DIPAKAI: SELECT nama_balai, nama_produk, pendaftar, media_iklan, komoditi FROM mv_pengawasan WHERE kesimpulan_penilaian_pusat IN ('MK', 'TMK') and komoditi IN ('KOSMETIKA','OBAT','OBAT KUASI','OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN') AND tgl_start >= '2024-06-25' AND tgl_end <= '2024-06-30'
```

### [35] tampilkan data label yang dilaporkan mk/tmk dari masing-masing upt yang dikategorikan berdasarkan nama produk, jenis pangan, kategori pangan, produsen, kabupaten/provinsi produsen, pada rentang waktu 

| | |
|---|---|
| Bentuk NER | `tampilkan data label yang dilaporkan <CONCLUSION TYPE> dari masing-masing upt yang dikategorikan berdasarkan <PRODUCT NAME>, <COMMODITY NAME>, <CLASSI` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 27,460 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_balai, nama_produk, komoditi, pendaftar, kesimpulan_penilaian_akhir, tgl_start, tgl_end FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_akhir IN ('MK', 'TMK') AND tgl_start <= '2025-12-31' AND tgl_end >= '2025-01-01' ORDER BY nama_balai, nama_produk, komoditi, pendaftar;
-- DIPAKAI: SELECT nama_balai, nama_produk, komoditi, pendaftar, kesimpulan_penilaian_akhir, tgl_start, tgl_end FROM mv_pengawasan WHERE kesimpulan_penilaian_akhir IN ('MK', 'TMK') AND tgl_start <= '2025-12-31' AND tgl_end >= '2025-01-01' ORDER BY nama_balai, nama_produk, komoditi, pendaftar;
```

### [36] tampilkan data materi iklan berdasarkan nama produk 'buah' dan nama industri farmasi 'nutrifood' dari masing-masing upt.

| | |
|---|---|
| Bentuk NER | `tampilkan data materi iklan berdasarkan nama produk '<PRODUCT NAME>' dan nama industri farmasi '<COMPANY NAME>' dari masing-masing upt.` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 20 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT * FROM public.vw_pengawasan_v2 WHERE lower(nama_produk) like '%buah%' AND lower(pendaftar) like '%nutrifood%';
-- DIPAKAI: SELECT * FROM mv_pengawasan WHERE lower(nama_produk) like '%buah%' AND lower(pendaftar) like '%nutrifood%';
```

### [37] tampilkan data materi iklan berdasarkan nama produk tertentu dan nama industri farmasi tertentu dari masing-masing upt.

| | |
|---|---|
| Bentuk NER | `tampilkan data <PRODUCT NAME> berdasarkan nama produk tertentu dan nama industri farmasi tertentu dari masing-masing upt.` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **NOL_BARIS** · 0 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔴 Nol baris — literal masih placeholder template** |
| Sebab | Literal masih berupa placeholder template (mis. NAMA_PRODUK_TERTENTU) — pair tidak pernah disubstitusi |

```sql
-- ASLI   : SELECT * FROM public.vw_pengawasan_v2 WHERE nama_produk = 'NAMA_PRODUK_TERTENTU' AND pendaftar = 'NAMA_INDUSTRI_FARMASI_TERTENTU' AND nama_balai = 'NAMA_UPT_TERTENTU';
-- DIPAKAI: SELECT * FROM mv_pengawasan WHERE nama_produk = 'NAMA_PRODUK_TERTENTU' AND pendaftar = 'NAMA_INDUSTRI_FARMASI_TERTENTU' AND nama_balai = 'NAMA_UPT_TERTENTU';
```

### [38] tampilkan data upt yang tidak melaporkan hasil pengawasan iklan dengan hasil verifikasi balai tmk pada tahun 2023.

| | |
|---|---|
| Bentuk NER | `tampilkan data upt yang tidak melaporkan hasil pengawasan iklan dengan hasil verifikasi balai tmk pada tahun <YEAR>.` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 11 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 WHERE nama_balai NOT IN ( SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_balai = 'TMK' AND EXTRACT(YEAR FROM tgl_start) = 2023 );
-- DIPAKAI: SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE nama_balai NOT IN ( SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE kesimpulan_penilaian_balai = 'TMK' AND EXTRACT(YEAR FROM tgl_start) = 2023 );
```

### [39] tampilkan data upt yang tidak melaporkan hasil pengawasan iklan dengan hasil verifikasi balai tmk.

| | |
|---|---|
| Bentuk NER | `tampilkan data upt yang tidak melaporkan hasil pengawasan iklan dengan hasil verifikasi <HALL NAME>.` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **NOL_BARIS** · 0 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **○ Nol baris — anti-join memang kosong (jawaban sah)** |
| Sebab | Anti-join: himpunan "yang tidak pernah" memang kosong. Nol baris = jawaban benar; ubah bentuk jadi peringkat porsi |

```sql
-- ASLI   : SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 EXCEPT SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_balai = 'TMK'
-- DIPAKAI: SELECT DISTINCT nama_balai FROM mv_pengawasan EXCEPT SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE kesimpulan_penilaian_balai = 'TMK'
```

### [40] tampilkan data upt yang tidak melaporkan hasil pengawasan iklan dengan hasil verifikasi balai tmk.

| | |
|---|---|
| Bentuk NER | `tampilkan data upt yang tidak melaporkan hasil pengawasan iklan dengan hasil verifikasi <HALL NAME>.` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **NOL_BARIS** · 0 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **○ Nol baris — anti-join memang kosong (jawaban sah)** |
| Sebab | Anti-join: himpunan "yang tidak pernah" memang kosong. Nol baris = jawaban benar; ubah bentuk jadi peringkat porsi |

```sql
-- ASLI   : SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 EXCEPT SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_balai = 'TMK'
-- DIPAKAI: SELECT DISTINCT nama_balai FROM mv_pengawasan EXCEPT SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE kesimpulan_penilaian_balai = 'TMK'
```

### [41] tampilkan data upt yang tidak melaporkan hasil pengawasan iklan pada media cetak / media luar ruang pada tahun 2022.

| | |
|---|---|
| Bentuk NER | `tampilkan data upt yang tidak melaporkan hasil pengawasan iklan pada media cetak / media luar ruang pada tahun <YEAR>.` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 84 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 WHERE nama_balai NOT IN ( SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 WHERE media_iklan IN ('CETAK', 'MEDIA_LUARRUANG') AND EXTRACT(YEAR FROM tgl_start) = 2022 );
-- DIPAKAI: SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE nama_balai NOT IN ( SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE media_iklan IN ('CETAK', 'MEDIA_LUARRUANG') AND EXTRACT(YEAR FROM tgl_start) = 2022 );
```

### [42] tampilkan data upt yang tidak melaporkan hasil pengawasan iklan pada media cetak / media luar ruang.

| | |
|---|---|
| Bentuk NER | `tampilkan data <CLASSIFICATION> yang tidak melaporkan hasil pengawasan iklan pada media cetak / media luar ruang.` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 1 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 EXCEPT SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 WHERE media_iklan IN ('CETAK','MEDIA_LUARRUANG') AND kesimpulan_penilaian_akhir IS NOT NULL;
-- DIPAKAI: SELECT DISTINCT nama_balai FROM mv_pengawasan EXCEPT SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE media_iklan IN ('CETAK','MEDIA_LUARRUANG') AND kesimpulan_penilaian_akhir IS NOT NULL;
```

### [43] tampilkan data upt yang tidak melaporkan hasil pengawasan iklan pada media cetak / media luar ruang.

| | |
|---|---|
| Bentuk NER | `tampilkan data <CLASSIFICATION> yang tidak melaporkan hasil pengawasan iklan pada media cetak / media luar ruang.` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 1 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 EXCEPT SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 WHERE media_iklan IN ('CETAK','MEDIA_LUARRUANG') AND kesimpulan_penilaian_akhir IS NOT NULL;
-- DIPAKAI: SELECT DISTINCT nama_balai FROM mv_pengawasan EXCEPT SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE media_iklan IN ('CETAK','MEDIA_LUARRUANG') AND kesimpulan_penilaian_akhir IS NOT NULL;
```

### [44] tampilkan data upt yang tidak melaporkan iklan obat tradisional; suplemen kesehatan; obat kuasi pada tahun 2023.

| | |
|---|---|
| Bentuk NER | `tampilkan data upt yang tidak melaporkan <COMMODITY NAME>; <COMMODITY NAME>; <COMMODITY NAME> pada tahun <YEAR>.` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 11 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 WHERE nama_balai NOT IN ( SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 WHERE komoditi IN ('OBAT KUASI','OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN') AND EXTRACT(YEAR FROM tgl_start) = 2023 );
-- DIPAKAI: SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE nama_balai NOT IN ( SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE komoditi IN ('OBAT KUASI','OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN') AND EXTRACT(YEAR FROM tgl_start) = 2023 );
```

### [45] tampilkan data upt yang tidak melaporkan iklan obat tradisional; suplemen kesehatan; obat kuasi.

| | |
|---|---|
| Bentuk NER | `tampilkan data upt yang tidak melaporkan <COMMODITY NAME>; <COMMODITY NAME>; <COMMODITY NAME>.` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | ERR_SCHEMA → **OK** · 1 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 EXCEPT SELECT DISTINCT nama_balai FROM public.vw_pengawasan_v2 WHERE komoditi IN ('OBAT KUASI','OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN')
-- DIPAKAI: SELECT DISTINCT nama_balai FROM mv_pengawasan EXCEPT SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE komoditi IN ('OBAT KUASI','OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN')
```

### [46] tampilkan list data lokasi iklan yang diperiksa lebih dari sekali

| | |
|---|---|
| Bentuk NER | `tampilkan list data <CLASSIFICATION> yang diperiksa lebih dari sekali` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 20,525 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT lokasi_iklan FROM public.vw_pengawasan_v2 GROUP BY lokasi_iklan HAVING COUNT(*) > 1;
-- DIPAKAI: SELECT lokasi_iklan FROM mv_pengawasan GROUP BY lokasi_iklan HAVING COUNT(*) > 1;
```

### [47] tampilkan persentase kategori pangan yang tmk pada rentang waktu 2025 (baik secara nasional maupun per upt).

| | |
|---|---|
| Bentuk NER | `tampilkan persentase <CLASSIFICATION> yang tmk pada rentang waktu <YEAR> (baik secara nasional maupun per upt).` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 4 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT kesimpulan_penilaian_pusat, COUNT(*) AS jumlah_laporan, ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS persentase -- 0–100 FROM vw_pengawasan_v2 WHERE komoditi ='PRODUK PANGAN' AND tgl_start >= DATE '2025-01-01' AND tgl_end < DATE '2026-01-01' -- half-open range, covers all of 2025 GROUP BY kesimpulan_penilaian_pusat ORDER BY jumlah_laporan DESC;
-- DIPAKAI: SELECT kesimpulan_penilaian_pusat, COUNT(*) AS jumlah_laporan, ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS persentase -- 0–100 FROM mv_pengawasan WHERE komoditi ='PRODUK PANGAN' AND tgl_start >= DATE '2025-01-01' AND tgl_end < DATE '2026-01-01' -- half-open range, covers all of 2025 GROUP BY kesimpulan_penilaian_pusat ORDER BY jumlah_laporan DESC;
```

### [48] tampilkan persentase media iklan (dibandingkan seluruh iklan yang diawasi pada rentang waktu tertentu) yang diawasi pada upt dengan nama 'balai pom di jakarta' pada rentang waktu antara tanggal '2025-

| | |
|---|---|
| Bentuk NER | `tampilkan persentase media iklan (dibandingkan seluruh iklan yang diawasi pada rentang waktu tertentu) yang diawasi pada upt dengan nama '<HALL NAME>'` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 3 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT media_iklan, COUNT(*) AS jumlah_laporan, ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS persentase -- 0–100 FROM vw_pengawasan_v2 WHERE nama_balai = 'BALAI BESAR POM DI JAKARTA' AND tgl_start >= DATE '2025-01-01' AND tgl_end < DATE '2026-01-01' -- half-open range, covers all of 2025 GROUP BY media_iklan ORDER BY jumlah_laporan DESC;
-- DIPAKAI: SELECT media_iklan, COUNT(*) AS jumlah_laporan, ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS persentase -- 0–100 FROM mv_pengawasan WHERE nama_balai = 'BALAI BESAR POM DI JAKARTA' AND tgl_start >= DATE '2025-01-01' AND tgl_end < DATE '2026-01-01' -- half-open range, covers all of 2025 GROUP BY media_iklan ORDER BY jumlah_laporan DESC;
```

### [49] tampilkan tren data hasil pengawasan iklan obat pada rentang tahun 2024-2025 berdasarkan hasil verifikasi pusat mk/tmk.

| | |
|---|---|
| Bentuk NER | `tampilkan tren data hasil pengawasan iklan obat pada rentang tahun <YEAR>-<YEAR> berdasarkan hasil verifikasi pusat mk/tmk.` |
| Tabel | `tgl_start + mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 4 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan ; nilai 'Obat'→'OBAT' |
| Diagnosa | **🔧 Pulih: relasi + nilai** |
| Sebab | Pulih setelah penyesuaian relasi + nilai ke skema live |

```sql
-- ASLI   : SELECT EXTRACT(YEAR FROM tgl_start) AS year, kesimpulan_penilaian_pusat, COUNT(*) AS total_count FROM public.vw_pengawasan_v2 WHERE komoditi IN ('OBAT', 'OBAT KUASI', 'OBAT TRADISIONAL (OT)') AND kesimpulan_penilaian_pusat IN ('MK', 'TMK') AND EXTRACT(YEAR FROM tgl_start) BETWEEN 2024 AND 2025 GROUP BY year, kesimpulan_penilaian_pusat ORDER BY year, kesimpulan_penilaian_pusat;
-- DIPAKAI: SELECT EXTRACT(YEAR FROM tgl_start) AS year, kesimpulan_penilaian_pusat, COUNT(*) AS total_count FROM mv_pengawasan WHERE komoditi IN ('OBAT', 'OBAT KUASI', 'OBAT TRADISIONAL (OT)') AND kesimpulan_penilaian_pusat IN ('MK', 'TMK') AND EXTRACT(YEAR FROM tgl_start) BETWEEN 2024 AND 2025 GROUP BY year, kesimpulan_penilaian_pusat ORDER BY year, kesimpulan_penilaian_pusat;
```

### [50] tampilkan tren data hasil pengawasan iklan obat tradisional; suplemen kesehatan; obat kuasi pada rentang tahun 2024-2025 berdasarkan hasil verifikasi pusat mk/tmk

| | |
|---|---|
| Bentuk NER | `tampilkan tren data hasil pengawasan iklan <COMMODITY NAME>; <COMMODITY NAME>; <COMMODITY NAME> pada rentang tahun <YEAR> berdasarkan hasil verifikasi` |
| Tabel | `tgl_start + mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 2 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT EXTRACT( YEAR FROM tgl_start ) AS tahun, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah_pengawasan FROM public.vw_pengawasan_v2 WHERE komoditi IN ('OBAT TRADISIONAL (OT)', 'SUPLEMEN KESEHATAN', 'OBAT KUASI') AND EXTRACT( YEAR FROM tgl_start ) BETWEEN 2024 AND 2025 AND kesimpulan_penilaian_pusat IN ('MK', 'TMK') GROUP by kesimpulan_penilaian_pusat, tahun ORDER by kesimpulan_penilaian_pusat, tahun;
-- DIPAKAI: SELECT EXTRACT( YEAR FROM tgl_start ) AS tahun, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah_pengawasan FROM mv_pengawasan WHERE komoditi IN ('OBAT TRADISIONAL (OT)', 'SUPLEMEN KESEHATAN', 'OBAT KUASI') AND EXTRACT( YEAR FROM tgl_start ) BETWEEN 2024 AND 2025 AND kesimpulan_penilaian_pusat IN ('MK', 'TMK') GROUP by kesimpulan_penilaian_pusat, tahun ORDER by kesimpulan_penilaian_pusat, tahun;
```

### [51] tampilkan tren data hasil pengawasan iklan pangan (mk/tmk) pada rentang tahun 2025 berdasarkan hasil verifikasi upt

| | |
|---|---|
| Bentuk NER | `tampilkan tren data hasil pengawasan iklan pangan (mk/tmk) pada rentang tahun <YEAR> berdasarkan hasil verifikasi upt` |
| Tabel | `tgl_start + mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 36 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : select EXTRACT(YEAR FROM tgl_start) AS tahun, EXTRACT(MONTH FROM tgl_start) AS bulan, kesimpulan_penilaian_balai, COUNT(*) AS jumlah_pengawasan FROM public.vw_pengawasan_v2 WHERE lower(komoditi) like '%produk pangan%' AND EXTRACT(YEAR FROM tgl_start) = 2025 GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;
-- DIPAKAI: select EXTRACT(YEAR FROM tgl_start) AS tahun, EXTRACT(MONTH FROM tgl_start) AS bulan, kesimpulan_penilaian_balai, COUNT(*) AS jumlah_pengawasan FROM mv_pengawasan WHERE lower(komoditi) like '%produk pangan%' AND EXTRACT(YEAR FROM tgl_start) = 2025 GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;
```

### [52] tampilkan visualisasi data berupa urutan data yang paling besar dari hasil pengawasan label pangan yang dilaporkan tmk dari masing-masing upt yang dikategorikan berdasarkan nama produk, jenis pangan, 

| | |
|---|---|
| Bentuk NER | `tampilkan visualisasi data berupa urutan data yang paling besar dari hasil pengawasan label pangan yang dilaporkan tmk dari masing-masing upt yang dik` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: ya |
| Status | ERR_SCHEMA → **OK** · 7,156 baris |
| Lapis terjemahan | relasi vw_pengawasan_v2→mv_pengawasan |
| Diagnosa | **🔧 Pulih: ganti nama relasi** |
| Sebab | Pulih setelah penyesuaian relasi ke skema live |

```sql
-- ASLI   : SELECT nama_balai, nama_produk, COUNT(*) AS jumlah_tmk_laporan FROM public.vw_pengawasan_v2 WHERE kesimpulan_penilaian_akhir = 'TMK' AND EXTRACT(YEAR FROM tgl_start) = 2025 GROUP BY nama_balai, nama_produk ORDER BY jumlah_tmk_laporan DESC;
-- DIPAKAI: SELECT nama_balai, nama_produk, COUNT(*) AS jumlah_tmk_laporan FROM mv_pengawasan WHERE kesimpulan_penilaian_akhir = 'TMK' AND EXTRACT(YEAR FROM tgl_start) = 2025 GROUP BY nama_balai, nama_produk ORDER BY jumlah_tmk_laporan DESC;
```

---

## Generasi v3 — koneksi `_all_v2` (Nov 2025), skema berlaku

36 pertanyaan.

### [53] Berdasarkan kabupaten/kota, tampilkan jumlah perbedaan kesimpulan balai dengan pusat saat kesimpulan penilaian akhir = TMK

| | |
|---|---|
| Bentuk NER | `Berdasarkan kabupaten/kota, tampilkan jumlah perbedaan kesimpulan balai dengan pusat saat kesimpulan penilaian akhir = <CONCLUSION TYPE>` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_SCHEMA → **ERR_SCHEMA** |
| Lapis terjemahan | - |
| Diagnosa | **⛔ Gagal — kolom dihapus dari skema (NOT COVERED)** |
| Sebab | Kolom mp.kabupaten sudah dihapus dari skema live (provinsi/kabupaten) — tidak bisa ditulis ulang, NOT COVERED |

```sql
SELECT mp.kabupaten, COUNT(*) AS jumlah_perbedaan FROM mv_pengawasan mp WHERE mp.kesimpulan_penilaian_balai IS NOT NULL AND mp.kesimpulan_penilaian_pusat IS NOT NULL AND LOWER(mp.kesimpulan_penilaian_balai) <> LOWER(mp.kesimpulan_penilaian_pusat) and mp.kesimpulan_penilaian_akhir = 'TMK' GROUP BY mp.kabupaten ORDER BY jumlah_perbedaan DESC;
```

> ERROR: `ERROR: column mp.kabupaten does not exist`

### [54] Berdasarkan produsen Kao Indonesia, tampilkan berapa jumlah iklan yang dilaporkan MK atau TMK beserta jumlah perbedaan antara kesimpulan balai dengan pusat

| | |
|---|---|
| Bentuk NER | `Berdasarkan produsen <COMPANY NAME>, tampilkan berapa jumlah iklan yang dilaporkan MK atau TMK beserta jumlah perbedaan antara kesimpulan balai dengan` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | OK → **OK** · 10 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
select mp.pendaftar, count(*) as total_laporan, sum(case when lower(mp.kesimpulan_penilaian_pusat) = 'mk' then 1 else 0 end) as jumlah_mk_pusat, sum(case when lower(mp.kesimpulan_penilaian_pusat) = 'tmk' then 1 else 0 end) as jumlah_tmk_pusat, sum(case when lower(mp.kesimpulan_penilaian_balai) = 'mk' then 1 else 0 end) as jumlah_mk_balai, sum(case when lower(mp.kesimpulan_penilaian_balai) = 'tmk' then 1 else 0 end) a
```

### [55] buatkan data perbedaan hasil pengawasan iklan obat antara hasil verifikasi balai dan hasil verifikasi pusat dalam bentuk grafik dan narasi.

| | |
|---|---|
| Bentuk NER | `buatkan data perbedaan hasil pengawasan iklan obat antara hasil verifikasi balai dan hasil verifikasi pusat dalam bentuk grafik dan narasi.` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | OK → **OK** · 4 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah_perbedaan FROM public.mv_pengawasan WHERE komoditi = 'OBAT' AND kesimpulan_penilaian_balai IS NOT NULL AND kesimpulan_penilaian_pusat IS NOT NULL AND kesimpulan_penilaian_balai <> kesimpulan_penilaian_pusat GROUP BY kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat ORDER BY jumlah_perbedaan DESC;
```

### [56] buatkan data perbedaan hasil pengawasan iklan obat tradisional; suplemen kesehatan; obat kuasi antara hasil verifikasi balai dan hasil verifikasi pusat dalam bentuk grafik dan narasi untuk periode wak

| | |
|---|---|
| Bentuk NER | `buatkan data perbedaan hasil pengawasan iklan <COMMODITY NAME>; <COMMODITY NAME>; <COMMODITY NAME> antara hasil verifikasi balai dan hasil verifikasi ` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | ERR_LAIN → **ERR_LAIN** |
| Lapis terjemahan | - |
| Diagnosa | **⛔ Gagal — SQL rusak sejak asalnya** |
| Sebab | SQL rusak sejak asalnya: ERROR: argument of AND must be type boolean, not type record |

```sql
SELECT kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah_perbedaan FROM public.mv_pengawasan WHERE ('OBAT TRADISIONAL (OT)', 'SUPLEMEN KESEHATAN', 'OBAT KUASI') AND kesimpulan_penilaian_balai IS NOT NULL AND kesimpulan_penilaian_pusat IS NOT NULL AND kesimpulan_penilaian_balai <> kesimpulan_penilaian_pusat GROUP BY kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat ORDER BY jumlah_perbeda
```

> ERROR: `ERROR: argument of AND must be type boolean, not type record`

### [57] tampilkan data berapa jumlah iklan obat tradisional; suplemen kesehatan; obat kuasi yang dilaporkan oleh upt dengan hasil verifikasi pusat mk/tmk.

| | |
|---|---|
| Bentuk NER | `tampilkan data berapa jumlah iklan <COMMODITY NAME>; <COMMODITY NAME>; <COMMODITY NAME> yang dilaporkan oleh upt dengan hasil verifikasi pusat mk/tmk.` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | OK → **OK** · 3 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
select komoditi, kesimpulan_penilaian_pusat, COUNT(*) FROM public.mv_pengawasan WHERE komoditi IN ('OBAT KUASI','OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN') AND kesimpulan_penilaian_pusat IN ('MK', 'TMK') group by komoditi, kesimpulan_penilaian_pusat order by komoditi, kesimpulan_penilaian_pusat;
```

### [58] Tampilkan data berupa jumlah iklan obat keras yang dilaporkan oleh UPT dengan hasil verifikasi pusat MK/TMK pada tahun 2025

| | |
|---|---|
| Bentuk NER | `Tampilkan data berupa jumlah iklan obat keras yang dilaporkan oleh UPT dengan hasil verifikasi pusat MK/TMK pada tahun <YEAR>` |
| Tabel | `mv_pengawasan + mp` · agregasi: ya |
| Status | OK → **OK** · 611 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
select mp.nama_balai , mp.komoditi, mp.kesimpulan_penilaian_pusat, count(*) from mv_pengawasan mp where lower(mp.komoditi) like '%obat%' and extract(year from mp.tgl_start) = 2025 group by 1, 2, 3 order by 1, 2, 3;
```

### [59] Tampilkan data capaian UPT berdasarkan jumlah laporan yang dikirimkan ke pusat (tanggal kepala balai) dibandingkan dengan target yang sudah ditetapkan untuk masing-masing UPT

| | |
|---|---|
| Bentuk NER | `Tampilkan data capaian <HALL NAME> berdasarkan jumlah laporan yang dikirimkan ke pusat (tanggal kepala balai) dibandingkan dengan target yang sudah di` |
| Tabel | `target_balai + mp + mv_pengawasan + current_date + laporan_dikirim + latest_target_year` · agregasi: ya |
| Status | OK → **OK** · 494 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
WITH latest_target_year AS ( SELECT MAX(tahun) AS tahun_terbaru FROM target_balai ), laporan_dikirim AS ( SELECT mp.nama_balai, mp.komoditi, EXTRACT(YEAR FROM mp.tgl_start) AS tahun, COUNT(*) AS jumlah_laporan FROM mv_pengawasan mp WHERE mp.tgl_start IS NOT NULL AND EXTRACT(YEAR FROM mp.tgl_start) = EXTRACT(YEAR FROM CURRENT_DATE) GROUP BY mp.nama_balai, mp.komoditi, EXTRACT(YEAR FROM mp.tgl_start) ) SELECT ld.nama_b
```

### [60] tampilkan data hasil kesimpulan tmk berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai mk pada rentang waktu antara tanggal mulai dan tanggal selesai 2 minggu.

| | |
|---|---|
| Bentuk NER | `tampilkan data <CONCLUSION TYPE> berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai mk pada rentang waktu antara tanggal mulai dan tangg` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | OK → **OK** · 9 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT * FROM public.mv_pengawasan WHERE kesimpulan_penilaian_pusat = 'TMK' and kesimpulan_penilaian_balai ='MK' AND (tgl_end - tgl_start) = 14;
```

### [61] tampilkan data hasil kesimpulan tmk berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai mk pada rentang waktu Januari hingga Juni 2025

| | |
|---|---|
| Bentuk NER | `tampilkan data <CONCLUSION TYPE> berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai mk pada rentang waktu <MONTH> hingga <MONTH> <YEAR>` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | OK → **OK** · 622 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT * FROM public.mv_pengawasan WHERE kesimpulan_penilaian_pusat = 'TMK' AND kesimpulan_penilaian_balai = 'MK' AND tgl_start >= '2025-01-01' AND tgl_end <= '2025-06-30';
```

### [62] tampilkan data hasil kesimpulan tmk berdasarkan hasil verifikasi pusat pada rentang waktu antara tanggal mulai dan tanggal selesai 2 minggu.

| | |
|---|---|
| Bentuk NER | `tampilkan data hasil kesimpulan <CONCLUSION TYPE> berdasarkan hasil verifikasi pusat pada rentang waktu antara tanggal mulai dan tanggal selesai 2 min` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | OK → **OK** · 88 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT * FROM public.mv_pengawasan WHERE kesimpulan_penilaian_pusat = 'TMK' AND (tgl_end - tgl_start) = 14;
```

### [63] tampilkan data hasil kesimpulan tmk berdasarkan hasil verifikasi pusat pada rentang waktu Januari hingga Juni 2025

| | |
|---|---|
| Bentuk NER | `tampilkan data hasil kesimpulan <CONCLUSION TYPE> berdasarkan hasil verifikasi pusat pada rentang waktu <MONTH> hingga <MONTH> <YEAR>` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | OK → **OK** · 3,331 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT * FROM public.mv_pengawasan WHERE kesimpulan_penilaian_pusat = 'TMK' AND tgl_start >= '2025-01-01' AND tgl_end <= '2025-06-30';
```

### [64] Tampilkan data hasil pengawasan iklan berdasarkan hasil verifikasi balai TMK yang statusnya belum ada tanggal direktur (belum selesai) pada tahun 2025

| | |
|---|---|
| Bentuk NER | `Tampilkan data hasil pengawasan iklan berdasarkan hasil verifikasi <HALL NAME> yang statusnya belum ada tanggal direktur (belum selesai) pada tahun <Y` |
| Tabel | `mv_pengawasan + mv_pengawasan_timeline + mp` · agregasi: tidak |
| Status | OK → **OK** · 11 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
select mp.tgl_start, mp.id, mp.komoditi, mp.nama_balai, mp.nama_produk, mp.media_iklan, mp.kesimpulan_penilaian_balai from mv_pengawasan mp join mv_pengawasan_timeline mpt on mp.id = mpt.id_pengawasan where mpt.tanggal_kirim_direktur is null and mp.kesimpulan_penilaian_balai = 'TMK' and extract(year from mp.tgl_start) = 2025 order by 1, 2, 3, 4, 5, 6
```

### [65] Tampilkan data hasil pengawasan TMK berdasarkan klausul pelanggaran secara keseluruhan, masing-masing UPT, media iklan pada komoditi pangan dan rentang waktu 2025

| | |
|---|---|
| Bentuk NER | `Tampilkan data hasil pengawasan TMK berdasarkan klausul pelanggaran secara keseluruhan, masing-masing UPT, media iklan pada <COMMODITY NAME> dan renta` |
| Tabel | `mv_pengawasan + mv_pengawasan_ketidaksesuaian + mp` · agregasi: ya |
| Status | OK → **OK** · 720 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
select mp.nama_balai, mp.media_iklan, mpk.id_klasifikasi, mpk.keterangan_ketidaksesuaian, mp.kesimpulan_penilaian_balai, count(*) from mv_pengawasan mp join mv_pengawasan_ketidaksesuaian mpk on mp.id = mpk.id_pengawasan where lower(mp.komoditi) like '%produk pangan%' and extract(year from mp.tgl_end) = 2025 and lower(mp.kesimpulan_penilaian_balai) like '%tmk%' group by 1, 2, 3, 4, 5 order by 1, 2, 3, 4, 5;
```

### [66] tampilkan data iklan yang dilaporkan mk/tmk dari masing-masing upt yang dikategorikan berdasarkan nama produk, industri farmasi, media publikasi, dan golongan obat dengan status selesai pada rentang w

| | |
|---|---|
| Bentuk NER | `tampilkan data iklan yang dilaporkan mk/tmk dari masing-masing upt yang dikategorikan berdasarkan <PRODUCT NAME>, <CLASSIFICATION>, <CLASSIFICATION>, ` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | OK → **OK** · 677 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT nama_balai, nama_produk, pendaftar, media_iklan, komoditi FROM public.mv_pengawasan WHERE kesimpulan_penilaian_pusat IN ('MK', 'TMK') and komoditi IN ('KOSMETIKA','OBAT','OBAT KUASI','OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN') AND tgl_start >= '2024-06-25' AND tgl_end <= '2024-06-30'
```

### [67] Tampilkan data ketepatan waktu pelaporan oleh UPT yang dihitung berdasarkan laporan yang dikirimkan tanggal kepala balai sebelum batas tanggal 9 bulan berikutnya untuk tahun 2025

| | |
|---|---|
| Bentuk NER | `Tampilkan data ketepatan waktu pelaporan oleh UPT yang dihitung berdasarkan laporan yang dikirimkan tanggal kepala balai sebelum batas tanggal <MONTH>` |
| Tabel | `mv_pengawasan + mv_pengawasan_timeline + mpt` · agregasi: ya |
| Status | OK → **OK** · 76 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT mp.nama_balai, COUNT(*) AS jumlah_laporan, SUM( CASE WHEN mpt.tanggal_kirim_kabalai < (DATE_TRUNC('month', mp.tgl_start) + INTERVAL '1 month' + INTERVAL '8 day') THEN 1 ELSE 0 END ) AS laporan_tepat_waktu, ROUND( SUM( CASE WHEN mpt.tanggal_kirim_kabalai < (DATE_TRUNC('month', mp.tgl_start) + INTERVAL '1 month' + INTERVAL '8 day') THEN 1 ELSE 0 END )::DECIMAL / COUNT(*) * 100, 2 ) AS persentase_tepat_waktu FROM
```

### [68] tampilkan data label yang dilaporkan mk/tmk dari masing-masing upt yang dikategorikan berdasarkan nama produk, jenis pangan, kategori pangan, produsen, kabupaten/provinsi produsen, pada rentang waktu 

| | |
|---|---|
| Bentuk NER | `tampilkan data label yang dilaporkan <CONCLUSION TYPE> dari masing-masing upt yang dikategorikan berdasarkan <PRODUCT NAME>, <COMMODITY NAME>, <CLASSI` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | OK → **OK** · 27,460 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT nama_balai, nama_produk, komoditi, pendaftar, kesimpulan_penilaian_akhir, tgl_start, tgl_end FROM public.mv_pengawasan WHERE kesimpulan_penilaian_akhir IN ('MK', 'TMK') AND tgl_start <= '2025-12-31' AND tgl_end >= '2025-01-01' ORDER BY nama_balai, nama_produk, komoditi, pendaftar;
```

### [69] tampilkan data materi iklan berdasarkan nama produk 'buah' dan nama industri farmasi 'nutrifood' dari masing-masing upt.

| | |
|---|---|
| Bentuk NER | `tampilkan data materi iklan berdasarkan nama produk '<PRODUCT NAME>' dan nama industri farmasi '<COMPANY NAME>' dari masing-masing upt.` |
| Tabel | `mv_pengawasan` · agregasi: tidak |
| Status | OK → **OK** · 20 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT * FROM public.mv_pengawasan WHERE lower(nama_produk) like '%buah%' AND lower(pendaftar) like '%nutrifood%';
```

### [70] Tampilkan data pemenuhan timeline pengawasan oleh masing-masing UPT yang dapat diukur sejak tanggal pemeriksaan sampai dengan tanggal laporan dikirim ke Pusat oleh Kepala UPT

| | |
|---|---|
| Bentuk NER | `Tampilkan data pemenuhan timeline pengawasan oleh masing-masing UPT yang dapat diukur sejak tanggal pemeriksaan sampai dengan tanggal laporan dikirim ` |
| Tabel | `mv_pengawasan_timeline` · agregasi: tidak |
| Status | OK → **OK** · 228,278 baris |
| Lapis terjemahan | - |
| Diagnosa | **⚠️ Jalan tapi >100rb baris tanpa agregasi** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah. TAPI hasilnya 228,278 baris tanpa agregasi — jalan, bukan jawaban |

```sql
select id_pengawasan, tgl_start, mpt.tanggal_kirim_pusat, (mpt.mulai_kabalai + mpt.kabalai_direktur + mpt.direktur_pusat) as durasi_hari from mv_pengawasan_timeline mpt where mpt.tanggal_kirim_pusat is not null order by 2
```

### [71] Tampilkan data pemenuhan timeline untuk masing-masing laporan pengawasan iklan yang dihitung dari tanggal kepala balai hingga tanggal direktur

| | |
|---|---|
| Bentuk NER | `Tampilkan data pemenuhan timeline untuk masing-masing laporan pengawasan iklan yang dihitung dari tanggal <HALL NAME> hingga tanggal direktur` |
| Tabel | `mv_pengawasan_timeline` · agregasi: tidak |
| Status | OK → **OK** · 190,017 baris |
| Lapis terjemahan | - |
| Diagnosa | **⚠️ Jalan tapi >100rb baris tanpa agregasi** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah. TAPI hasilnya 190,017 baris tanpa agregasi — jalan, bukan jawaban |

```sql
select id_pengawasan, tanggal_kirim_kabalai , tanggal_kirim_direktur, (mpt.kabalai_direktur) as durasi_hari from mv_pengawasan_timeline mpt where tanggal_kirim_direktur is not null order by 2
```

### [72] Tampilkan data pemenuhan timeline untuk masing-masing laporan pengawasan iklan yang dihitung dari tanggal sampling/pemeriksaan hingga tanggal direktur

| | |
|---|---|
| Bentuk NER | `Tampilkan data pemenuhan timeline untuk masing-masing laporan pengawasan iklan yang dihitung dari tanggal sampling/pemeriksaan hingga tanggal direktur` |
| Tabel | `mv_pengawasan_timeline` · agregasi: tidak |
| Status | OK → **OK** · 190,017 baris |
| Lapis terjemahan | - |
| Diagnosa | **⚠️ Jalan tapi >100rb baris tanpa agregasi** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah. TAPI hasilnya 190,017 baris tanpa agregasi — jalan, bukan jawaban |

```sql
select id_pengawasan, tgl_start, tanggal_kirim_direktur, (mpt.mulai_kabalai + mpt.kabalai_direktur) as durasi_hari from mv_pengawasan_timeline mpt where tanggal_kirim_direktur is not null order by 2
```

### [73] tampilkan data upt yang tidak melaporkan hasil pengawasan iklan dengan hasil verifikasi balai tmk pada tahun 2023.

| | |
|---|---|
| Bentuk NER | `tampilkan data upt yang tidak melaporkan hasil pengawasan iklan dengan hasil verifikasi balai tmk pada tahun <YEAR>.` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: tidak |
| Status | OK → **OK** · 11 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT DISTINCT nama_balai FROM public.mv_pengawasan WHERE nama_balai NOT IN ( SELECT DISTINCT nama_balai FROM public.mv_pengawasan WHERE kesimpulan_penilaian_balai = 'TMK' AND EXTRACT(YEAR FROM tgl_start) = 2023 );
```

### [74] tampilkan data upt yang tidak melaporkan hasil pengawasan iklan dengan hasil verifikasi balai tmk pada tahun 2023.

| | |
|---|---|
| Bentuk NER | `tampilkan data upt yang tidak melaporkan hasil pengawasan iklan dengan hasil verifikasi balai tmk pada tahun <YEAR>.` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: tidak |
| Status | OK → **OK** · 11 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT DISTINCT nama_balai FROM public.mv_pengawasan WHERE nama_balai NOT IN ( SELECT DISTINCT nama_balai FROM public.mv_pengawasan WHERE kesimpulan_penilaian_balai = 'TMK' AND EXTRACT(YEAR FROM tgl_start) = 2023 );
```

### [75] tampilkan data upt yang tidak melaporkan hasil pengawasan iklan pada media cetak / media luar ruang pada tahun 2022.

| | |
|---|---|
| Bentuk NER | `tampilkan data upt yang tidak melaporkan hasil pengawasan iklan pada media cetak / media luar ruang pada tahun <YEAR>.` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: tidak |
| Status | OK → **OK** · 84 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT DISTINCT nama_balai FROM public.mv_pengawasan WHERE nama_balai NOT IN ( SELECT DISTINCT nama_balai FROM public.mv_pengawasan WHERE media_iklan IN ('CETAK', 'MEDIA_LUARRUANG') AND EXTRACT(YEAR FROM tgl_start) = 2022 );
```

### [76] tampilkan data upt yang tidak melaporkan hasil pengawasan iklan pada media cetak / media luar ruang pada tahun 2022.

| | |
|---|---|
| Bentuk NER | `tampilkan data upt yang tidak melaporkan hasil pengawasan iklan pada media cetak / media luar ruang pada tahun <YEAR>.` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: tidak |
| Status | OK → **OK** · 84 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT DISTINCT nama_balai FROM public.mv_pengawasan WHERE nama_balai NOT IN ( SELECT DISTINCT nama_balai FROM public.mv_pengawasan WHERE media_iklan IN ('CETAK', 'MEDIA_LUARRUANG') AND EXTRACT(YEAR FROM tgl_start) = 2022 );
```

### [77] tampilkan data upt yang tidak melaporkan iklan obat tradisional; suplemen kesehatan; obat kuasi pada tahun 2023.

| | |
|---|---|
| Bentuk NER | `tampilkan data upt yang tidak melaporkan <COMMODITY NAME>; <COMMODITY NAME>; <COMMODITY NAME> pada tahun <YEAR>.` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: tidak |
| Status | OK → **OK** · 11 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT DISTINCT nama_balai FROM public.mv_pengawasan WHERE nama_balai NOT IN ( SELECT DISTINCT nama_balai FROM public.mv_pengawasan WHERE komoditi IN ('OBAT KUASI','OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN') AND EXTRACT(YEAR FROM tgl_start) = 2023 );
```

### [78] Tampilkan jumlah iklan tepat waktu yang telah dikirimkan ke pusat pada UPT tertentu pada tahun 2025 Hasil pengawasan iklan dikirimkan ke pusat maksimal tanggal 10 bulan berikutnya

| | |
|---|---|
| Bentuk NER | `Tampilkan jumlah iklan tepat waktu yang telah dikirimkan ke pusat pada UPT tertentu pada tahun <YEAR> Hasil pengawasan iklan dikirimkan ke pusat maksi` |
| Tabel | `mv_pengawasan + mv_pengawasan_timeline + mpt` · agregasi: ya |
| Status | OK → **OK** · 76 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT mp.nama_balai, COUNT(*) AS jumlah_laporan, SUM( CASE WHEN mpt.tanggal_kirim_kabalai < (DATE_TRUNC('month', mp.tgl_start) + INTERVAL '1 month' + INTERVAL '9 day') THEN 1 ELSE 0 END ) AS laporan_tepat_waktu, ROUND( SUM( CASE WHEN mpt.tanggal_kirim_kabalai < (DATE_TRUNC('month', mp.tgl_start) + INTERVAL '1 month' + INTERVAL '9 day') THEN 1 ELSE 0 END )::DECIMAL / COUNT(*) * 100, 2 ) AS persentase_tepat_waktu FROM
```

### [79] tampilkan list data lokasi iklan yang diperiksa lebih dari sekali

| | |
|---|---|
| Bentuk NER | `tampilkan list data <CLASSIFICATION> yang diperiksa lebih dari sekali` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | OK → **OK** · 20,525 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT lokasi_iklan FROM public.mv_pengawasan GROUP BY lokasi_iklan HAVING COUNT(*) > 1;
```

### [80] tampilkan persentase kategori pangan yang tmk pada rentang waktu 2025 (baik secara nasional maupun per upt).

| | |
|---|---|
| Bentuk NER | `tampilkan persentase <CLASSIFICATION> yang tmk pada rentang waktu <YEAR> (baik secara nasional maupun per upt).` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | OK → **OK** · 4 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT kesimpulan_penilaian_pusat, COUNT(*) AS jumlah_laporan, ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS persentase -- 0–100 FROM mv_pengawasan WHERE komoditi ='PRODUK PANGAN' AND tgl_start >= DATE '2025-01-01' AND tgl_end < DATE '2026-01-01' -- half-open range, covers all of 2025 GROUP BY kesimpulan_penilaian_pusat ORDER BY jumlah_laporan DESC;
```

### [81] tampilkan persentase media iklan (dibandingkan seluruh iklan yang diawasi pada rentang waktu tertentu) yang diawasi pada upt dengan nama 'balai pom di jakarta' pada rentang waktu antara tanggal '2025-

| | |
|---|---|
| Bentuk NER | `tampilkan persentase media iklan (dibandingkan seluruh iklan yang diawasi pada rentang waktu tertentu) yang diawasi pada upt dengan nama '<HALL NAME>'` |
| Tabel | `mv_pengawasan` · agregasi: ya |
| Status | OK → **OK** · 3 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT media_iklan, COUNT(*) AS jumlah_laporan, ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS persentase -- 0–100 FROM mv_pengawasan WHERE nama_balai = 'BALAI BESAR POM DI JAKARTA' AND tgl_start >= DATE '2025-01-01' AND tgl_end < DATE '2026-01-01' -- half-open range, covers all of 2025 GROUP BY media_iklan ORDER BY jumlah_laporan DESC;
```

### [82] Tampilkan persentase penilaian UPT (MK, TMK, TMK Mayor, TMK Minor) untuk komoditi pangan pada tiap UPT

| | |
|---|---|
| Bentuk NER | `Tampilkan persentase penilaian UPT (MK, TMK, TMK Mayor, TMK Minor) untuk komoditi <COMMODITY NAME> pada tiap UPT` |
| Tabel | `mv_pengawasan + data_penilaian` · agregasi: ya |
| Status | OK → **OK** · 244 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
WITH data_penilaian AS ( SELECT mp.nama_balai, UPPER(mp.kesimpulan_penilaian_balai) AS kesimpulan_penilaian, COUNT(*) AS jumlah FROM mv_pengawasan mp WHERE LOWER(mp.komoditi) LIKE '%pangan%' AND mp.kesimpulan_penilaian_pusat IS NOT NULL AND mp.kesimpulan_penilaian_balai IS NOT NULL GROUP BY mp.nama_balai, UPPER(mp.kesimpulan_penilaian_balai) ) SELECT dp.nama_balai, dp.kesimpulan_penilaian, dp.jumlah, ROUND( (dp.jumla
```

### [83] Tampilkan rekapitulasi jumlah laporan pengawasan iklan obat masing-masing UPT yang telah dikirim Pusat (berdasarkan tanggal kepala balai) pada tahun 2025

| | |
|---|---|
| Bentuk NER | `Tampilkan rekapitulasi jumlah laporan pengawasan iklan obat masing-masing UPT yang telah dikirim Pusat (berdasarkan tanggal kepala balai) pada tahun <` |
| Tabel | `mv_pengawasan + mv_pengawasan_timeline + mp` · agregasi: ya |
| Status | OK → **OK** · 2,929 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
select mpt.tanggal_kirim_kabalai, mp.nama_balai, mp.komoditi, count(*) from mv_pengawasan mp join mv_pengawasan_timeline mpt on mp.id = mpt.id_pengawasan where lower(komoditi) like '%obat%' and extract(year from mp.tgl_start) = 2025 and mpt.tanggal_kirim_kabalai is not null group by 1, 2, 3 order by 1, 2, 3
```

### [84] tampilkan tren data hasil pengawasan iklan obat pada rentang tahun 2024-2025 berdasarkan hasil verifikasi pusat mk/tmk.

| | |
|---|---|
| Bentuk NER | `tampilkan tren data hasil pengawasan iklan obat pada rentang tahun <YEAR>-<YEAR> berdasarkan hasil verifikasi pusat mk/tmk.` |
| Tabel | `tgl_start + mv_pengawasan` · agregasi: ya |
| Status | OK → **OK** · 4 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT EXTRACT(YEAR FROM tgl_start) AS year, kesimpulan_penilaian_pusat, COUNT(*) AS total_count FROM public.mv_pengawasan WHERE komoditi IN ('OBAT', 'OBAT KUASI', 'OBAT TRADISIONAL (OT)') AND kesimpulan_penilaian_pusat IN ('MK', 'TMK') AND EXTRACT(YEAR FROM tgl_start) BETWEEN 2024 AND 2025 GROUP BY year, kesimpulan_penilaian_pusat ORDER BY year, kesimpulan_penilaian_pusat;
```

### [85] tampilkan tren data hasil pengawasan iklan obat tradisional; suplemen kesehatan; obat kuasi pada rentang tahun 2024-2025 berdasarkan hasil verifikasi pusat mk/tmk

| | |
|---|---|
| Bentuk NER | `tampilkan tren data hasil pengawasan iklan <COMMODITY NAME>; <COMMODITY NAME>; <COMMODITY NAME> pada rentang tahun <YEAR> berdasarkan hasil verifikasi` |
| Tabel | `tgl_start + mv_pengawasan` · agregasi: ya |
| Status | OK → **OK** · 2 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT EXTRACT( YEAR FROM tgl_start ) AS tahun, kesimpulan_penilaian_pusat, COUNT(*) AS jumlah_pengawasan FROM public.mv_pengawasan WHERE komoditi IN ('OBAT TRADISIONAL (OT)', 'SUPLEMEN KESEHATAN', 'OBAT KUASI') AND EXTRACT( YEAR FROM tgl_start ) BETWEEN 2024 AND 2025 AND kesimpulan_penilaian_pusat IN ('MK', 'TMK') GROUP by kesimpulan_penilaian_pusat, tahun ORDER by kesimpulan_penilaian_pusat, tahun;
```

### [86] tampilkan tren data hasil pengawasan iklan pangan (mk/tmk) pada rentang tahun 2025 berdasarkan hasil verifikasi upt

| | |
|---|---|
| Bentuk NER | `tampilkan tren data hasil pengawasan iklan pangan (mk/tmk) pada rentang tahun <YEAR> berdasarkan hasil verifikasi upt` |
| Tabel | `tgl_start + mv_pengawasan` · agregasi: ya |
| Status | OK → **OK** · 36 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
select EXTRACT(YEAR FROM tgl_start) AS tahun, EXTRACT(MONTH FROM tgl_start) AS bulan, kesimpulan_penilaian_balai, COUNT(*) AS jumlah_pengawasan FROM public.mv_pengawasan WHERE lower(komoditi) like '%produk pangan%' AND EXTRACT(YEAR FROM tgl_start) = 2025 GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;
```

### [87] tampilkan tren data hasil pengawasan iklan pangan (mk/tmk) pada rentang tahun 2025 berdasarkan hasil verifikasi upt

| | |
|---|---|
| Bentuk NER | `tampilkan tren data hasil pengawasan iklan pangan (mk/tmk) pada rentang tahun <YEAR> berdasarkan hasil verifikasi upt` |
| Tabel | `tgl_start + mv_pengawasan` · agregasi: ya |
| Status | OK → **OK** · 36 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
select EXTRACT(YEAR FROM tgl_start) AS tahun, EXTRACT(MONTH FROM tgl_start) AS bulan, kesimpulan_penilaian_balai, COUNT(*) AS jumlah_pengawasan FROM public.mv_pengawasan WHERE lower(komoditi) like '%produk pangan%' AND EXTRACT(YEAR FROM tgl_start) = 2025 GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;
```

### [88] tampilkan visualisasi data berupa urutan data yang paling besar dari hasil pengawasan label pangan yang dilaporkan tmk dari masing-masing upt yang dikategorikan berdasarkan nama produk, jenis pangan, 

| | |
|---|---|
| Bentuk NER | `tampilkan visualisasi data berupa urutan data yang paling besar dari hasil pengawasan label pangan yang dilaporkan tmk dari masing-masing upt yang dik` |
| Tabel | `mv_pengawasan + tgl_start` · agregasi: ya |
| Status | OK → **OK** · 7,156 baris |
| Lapis terjemahan | - |
| Diagnosa | **✅ Jalan apa adanya** |
| Sebab | SQL generasi berjalan sudah cocok dengan skema live; tidak perlu diubah |

```sql
SELECT nama_balai, nama_produk, COUNT(*) AS jumlah_tmk_laporan FROM public.mv_pengawasan WHERE kesimpulan_penilaian_akhir = 'TMK' AND EXTRACT(YEAR FROM tgl_start) = 2025 GROUP BY nama_balai, nama_produk ORDER BY jumlah_tmk_laporan DESC;
```
