# 05 — Tabel `mv_pengawasan_agg` (Kubus Pre-Aggregated)

> **118.133 baris · 18 kolom · 20 MB · `last_updated` 2026-08-12 23:23:50**
> Grain: **1 baris = 1 kombinasi dimensi × periode**. TIDAK punya `id`.

## Profil 18 kolom

| Kelompok | Kolom | Catatan |
|---|---|---|
| **Periode** | `periode_type` (day/month), `tanggal_periode` | 2 hierarki paralel |
| **Dimensi** | `komoditi`, `nama_balai`, `media_iklan`, `jenis_pembuat_iklan`, `kesimpulan_penilaian_akhir`, `kesimpulan_penilaian_balai`, `kesimpulan_penilaian_pusat` | 7 dimensi |
| **Measures** | `jumlah_pengawasan`, `jumlah_surat_unik`, `jumlah_produk_unik`, `jumlah_nie_unik`, `jumlah_pendaftar_unik` | 5 measure count |
| **Durasi** | `avg_durasi_hari`, `min_durasi_hari`, `max_durasi_hari` | pre-computed |
| **Meta** | `last_updated` | timestamp refresh |

## Dua hierarki paralel (Bukan parent-child)

| `periode_type` | baris | `tanggal_periode` range | distinct periode |
|---|---|---|---|
| `day` | 70.746 | 2023-01-01 → 2026-08-31 | 1.314 |
| `month` | 47.387 | 2023-01-01 → 2026-08-01 | 44 |

**Kedua hierarki INDEPENDEN — masing-masing menjumlah ke 183.968 (= main total)**. Jangan dijumlah-naik: `SUM(jumlah_pengawasan)` atas seluruh agg = 367.936 = 2× main (karena day+month dihitung ganda).

```sql
-- Benar: filter 1 periode_type dulu
SELECT SUM(jumlah_pengawasan) FROM mv_pengawasan_agg WHERE periode_type='month'; -- 183.968
SELECT SUM(jumlah_pengawasan) FROM mv_pengawasan_agg WHERE periode_type='day';   -- 183.968
```

## ⚠️ Temuan KRITIS: basis tanggal agg = `tgl_end`, BUKAN `tgl_start`

Banyak asumsi menyatakan agg roll-up by `tgl_start`. **SALAH**. Bukti tiga lapis:

### Bukti 1 — total global cocok, tapi per-bulan beda jika pakai tgl_start
```
agg 2023-01 month: 2.248
main tgl_start 2023-01: 2.286  (selisih -38)
main tgl_end   2023-01: 2.248  (COCOK PERSIS)
```

### Bukti 2 — cocok 100% per-bulan dengan `tgl_end`
```sql
-- Query: bandingkan agg vs main (basis tgl_end), cari selisih
WITH m AS (SELECT date_trunc('month',tgl_end)::date b, COUNT(*) c FROM mv_pengawasan GROUP BY 1)
SELECT a.tanggal_periode, a.s AS agg_sum, m.c AS main_count
FROM (SELECT tanggal_periode, SUM(jumlah_pengawasan) s FROM mv_pengawasan_agg
      WHERE periode_type='month' GROUP BY 1) a
JOIN m ON m.b=a.tanggal_periode
WHERE a.s <> m.c;
-- Hasil: 0 baris (cocok 100% di SEMUA bulan)
```

### Bukti 3 — validasi verdict rollup match dengan main
```
agg_month verdict akhir: MK 67.920 / Null 64.391 / TMK 51.657
main      verdict akhir: MK 67.920 / Null 64.391 / TMK 51.657
→ MATCH 100%
```

**Implikasi**: trend bulanan dari agg diagregasi per **tanggal SELESAI** pengawasan. Event yang dimulai Desember tapi selesai Januari akan tercatat di bulan Januari di agg. Untuk trend "aktivitas dimulai", pakai `mv_pengawasan.tgl_start` langsung. Untuk trend "throughput selesai", agg cocok.

## Dimensi — coverage

| Dimensi | distinct |
|---|---|
| `komoditi` | 7 |
| `nama_balai` | 84 |
| `media_iklan` | 5 (incl. empty) |
| `jenis_pembuat_iklan` | 3 (incl. empty) |
| `kesimpulan_penilaian_akhir` | 3 |
| `kesimpulan_penilaian_balai` | 5 |
| `kesimpulan_penilaian_pusat` | 6 |

## Measure stats (basis month, 47.387 baris)

| Measure | Min | Median | Max |
|---|---|---|---|
| `jumlah_pengawasan` | 1 | 2 | 170 |
| `jumlah_surat_unik` | 1 | 1 | 34 |
| `jumlah_produk_unik` | 1 | 2 | 100 |
| `jumlah_nie_unik` | 1 | 1 | 102 |
| `jumlah_pendaftar_unik` | 1 | 1 | 46 |
| `avg_durasi_hari` | 0.02 | ~5 | 364 |

## Verdict rollup (match 100% dengan main)

| verdict kolom | nilai | n (month) |
|---|---|---|
| `kesimpulan_penilaian_akhir` | MK | 67.920 |
| | Null | 64.391 |
| | TMK | 51.657 |
| `kesimpulan_penilaian_balai` | MK | 111.175 |
| | TMK | 62.702 |
| | TMK MAYOR | 3.828 |
| | TMK MINOR | 3.431 |
| | Null | 2.832 |
| `kesimpulan_penilaian_pusat` | MK | 63.723 |
| | Null | 55.889 |
| | TMK | 50.934 |
| | TMK KRITIKAL | 8.684 |
| | TMK MINOR | 2.420 |
| | TMK MAYOR | 2.318 |

## Sebaran baris per komoditi (month grain)

| Komoditi | baris month |
|---|---|
| PRODUK PANGAN | 11.014 |
| KOSMETIKA | 9.744 |
| OBAT | 7.719 |
| OBAT TRADISIONAL | 7.593 |
| ROKOK | 4.950 |
| SUPLEMEN KESEHATAN | 4.423 |
| OBAT KUASI | 1.935 |

## Avg durasi per komoditi (pre-computed di agg)

| Komoditi | avg_durasi | max_durasi |
|---|---|---|
| PRODUK PANGAN | 5.3 | 364 |
| OBAT | 5.3 | 335 |
| ROKOK | 4.8 | 153 |
| OBAT KUASI | 4.8 | 47 |
| OBAT TRADISIONAL | 4.9 | 60 |
| SUPLEMEN | 4.7 | 90 |
| KOSMETIKA | 3.6 | 65 |

Catatan: avg durasi di agg adalah `tgl_end - tgl_start` rata-rata. Sebagian besar event (78%) selesai same-day (0 hari) → avg rendah.

## `last_updated` lebih baru dari `sync` main

| Tabel | timestamp refresh |
|---|---|
| `mv_pengawasan.sync` | 2026-08-12 23:23:43 |
| `mv_pengawasan_agg.last_updated` | 2026-08-12 23:23:50 (7 detik lebih baru) |
| `mv_pengawasan_log.sync` | 2026-08-12 23:23:59 |
| `mv_pengawasan_timeline.sync` | 2026-08-12 23:24:35 |
| `mv_pengawasan_ketidaksesuaian.sync` | 2026-08-12 23:24:49 |

**Urutan refresh ETL**: main → agg → log → timeline → ketidaksesuaian. Semua dalam ~1 menit. Refresh batch harian.

## Kapan pakai agg vs main

| Skenario | Pakai |
|---|---|
| Trend bulanan throughput (event selesai per bulan) | `agg` month (sudah pre-agg, cepat) |
| Trend bulanan aktivitas mulai | `main` dgn `date_trunc('month', tgl_start)` (bukan agg!) |
| Breakdown verdict × komoditi × bulan | `agg` month (lebih cepat dari GROUP BY main) |
| Hitung distinct event, distinct surat nasional | `main` langsung (agg bisa over-count kalau tidak hati) |
| Cross-tab kompleks dengan filter dinamis | `main` (agg tidak fleksibel) |

## Jebakan

1. **Basis agg = `tgl_end`**, bukan `tgl_start`. Trend "aktivitas" salah kalau pakai agg.
2. **Dua periode_type paralel** — jangan SUM tanpa filter `periode_type` (akan 2× lipat).
3. **agg TIDAK punya `id`** — join hanya via kombinasi dimensi.
4. **`avg_durasi_hari` kecil** bukan berarti proses cepat — 78% event same-day (0 hari) menarik avg turun.
5. **agg verdict match 100% main** — andal untuk breakdown verdict cepat.

## Bukti SQL
Lihat `13_sql_audit_trail.md` §05.
