# FILTER CODE REFERENCE — verifikasi langsung dari `mv_pengawasan*` (snapshot 2026-08-10)

Tidak ada `data_dictionary` di database pengawasan (beda dengan neo). Semua kode sudah punya label di kolom bersangkutan. File ini adalah cheat-sheet hasil query langsung untuk hindari tiap turn jalan probe `SELECT DISTINCT`.

## §0 — Aturan pakai

- **Closed set**: kode di bawah adalah exhaustif untuk snapshot ini. Kalau query menemukan kode baru → data berubah, sebutkan di jawaban sebagai "kode baru terdeteksi, label belum tercatat".
- **Never ILIKE first**: untuk filter, pakai exact value dari tabel ini. ILIKE hanya untuk discover free text.
- **Severity grade hanya di TMK**: `MK` tidak punya grade. Salah menyebut "MK MAYOR" = fabriasi.

## §1 — `komoditi` (exact-match, 7 nilai)

```sql
WHERE komoditi = 'KOSMETIKA'            -- 48.325
WHERE komoditi = 'ROKOK'                -- 40.031
WHERE komoditi = 'PRODUK PANGAN'        -- 33.765
WHERE komoditi = 'OBAT'                 -- 32.180
WHERE komoditi = 'OBAT TRADISIONAL (OT)'-- 19.001
WHERE komoditi = 'SUPLEMEN KESEHATAN'   --  7.820
WHERE komoditi = 'OBAT KUASI'           --  2.831
```

**Istilah informal yang perlu klarifikasi (Gate 1)**:
- "obat" bisa = `OBAT` saja, atau gabungan farmasi (`OBAT` ∪ `OBAT TRADISIONAL (OT)` ∪ `OBAT KUASI` ∪ `SUPLEMEN KESEHATAN`)
- "pangan" bisa = `PRODUK PANGAN` saja
- "rokok" = `ROKOK` (tidak ada ambiguitas)

## §2 — `status_code` ↔ `status_label` (di `mv_pengawasan_log`; timeline uses `status`)

```sql
-- Final state saja (sudah selesai):
WHERE status_code = 999   -- 'Sampel Rujukan Selesai'

-- Intermediate populer:
WHERE status_code = 4     -- 'MT - Pembuatan SPK' (paling ramai, 317.847 log)
WHERE status_code = 0     -- 'Operator - Draft Sampling'
WHERE status_code = 7     -- 'Penguji - Entri Hasil Pengujian'
```

Full mapping (verified):

| code | label | count di log |
|---|---|---|
| 0 | Operator - Draft Sampling | 267.333 |
| 1 | Supervisor - Verifikasi | 238.235 |
| 2 | Supervisor 2 - Verifikasi | 16.623 |
| 3 | TPS - Penerimaan SPU | 228.937 |
| 4 | MT - Pembuatan SPK | 317.847 |
| 5 | Deputi MT - Pembuatan SPK | 245.920 |
| 6 | Penyelia - Pembuatan SPP | 118.654 |
| 7 | Penguji - Entri Hasil Pengujian | 190.104 |
| 990 | (label kosong) | 4 |
| 991 | (label kosong) | 5.774 |
| 992 | (label kosong) | 148 |
| 993 | (label kosong) | 381 |
| 994 | (label kosong) | 1.705 |
| 995 | (label kosong) | 932 |
| 996 | (label kosong) | 92 |
| 997 | (label kosong) | 123 |
| **999** | **Sampel Rujukan Selesai** | **183.962** |

**Anti-pattern**: jangan pernah filter `status_code BETWEEN 0 AND 7` untuk "yg masih diproses" — kode 990–997 juga intermediate (label-nya kosong, tapi status-nya belum selesai). Pakai `status_code <> 999` untuk "yang belum selesai".

## §3 — `kesimpulan_penilaian_*` (3 kolom, populasi beda)

### 3a. `kesimpulan_penilaian_balai` (penilaian awal di balai)
```sql
WHERE kesimpulan_penilaian_balai = 'MK'           -- 111.164
WHERE kesimpulan_penilaian_balai = 'TMK'          --  62.700
WHERE kesimpulan_penilaian_balai = 'TMK MAYOR'    --   3.827
WHERE kesimpulan_penilaian_balai = 'TMK MINOR'    --   3.430
-- NULL: 2.832
```

### 3b. `kesimpulan_penilaian_pusat` (final di pusat, lebih granular)
```sql
WHERE kesimpulan_penilaian_pusat = 'MK'              --  63.722
WHERE kesimpulan_penilaian_pusat = 'TMK'             --  50.931
WHERE kesimpulan_penilaian_pusat = 'TMK KRITIKAL'    --   8.683  ← hanya di pusat
WHERE kesimpulan_penilaian_pusat = 'TMK MAYOR'       --   2.318
WHERE kesimpulan_penilaian_pusat = 'TMK MINOR'       --   2.419
-- NULL: 55.880 (30% tidak dinilai di pusat)
```

### 3c. `kesimpulan_penilaian_akhir` (verdict gabungan final, tanpa grade)
```sql
WHERE kesimpulan_penilaian_akhir = 'MK'    -- 67.920
WHERE kesimpulan_penilaian_akhir = 'TMK'   -- 51.654
-- NULL: 64.379
```

### Closure sets (TIDAK boleh dijahit manual)
```sql
-- "Semua TMK" (family) di kolom balai:
WHERE kesimpulan_penilaian_balai IN ('TMK', 'TMK MAYOR', 'TMK MINOR')

-- "Semua TMK" (family) di kolom pusat:
WHERE kesimpulan_penilaian_pusat IN ('TMK', 'TMK KRITIKAL', 'TMK MAYOR', 'TMK MINOR')

-- "Sudah dinilai" (any non-null):
WHERE kesimpulan_penilaian_akhir IS NOT NULL
```

**Trap**: `MINOR < MAYOR < KRITIKAL` severity. Pusat punya KRITIKAL, balai tidak. Jangan tukar.

## §4 — `media_iklan` (4 nilai + empty)

```sql
WHERE media_iklan = 'ELEKTRONIK'         -- 98.067
WHERE media_iklan = 'MEDIA_LUARRUANG'    -- 56.062
WHERE media_iklan = 'CETAK'              -- 25.027
WHERE media_iklan = 'MEDIA_LAIN'         --  3.825
-- empty/NULL: 972
```

Filter "all non-empty":
```sql
WHERE media_iklan IS NOT NULL AND media_iklan <> ''
```

## §5 — `jenis_pembuat_iklan` (RESTRIBUSI DATA)

```sql
WHERE jenis_pembuat_iklan = 'PELAKU USAHA'    -- 29.281
WHERE jenis_pembuat_iklan = 'PERORANGAN'      --  4.484
-- empty/NULL: 150.188 (82% kosong!)
```

**HINDARI** filter pakai kolom ini kecuali user explicit. Kalau dipaksa, selalu sebutkan di jawaban: "hanya 18% data terisi kolom pembuat iklan".

## §6 — `id_klasifikasi` ketidaksesuaian (6 nilai di `mv_pengawasan_ketidaksesuaian`)

```sql
WHERE id_klasifikasi = 1  -- Iklan produk yang tidak boleh diiklankan
WHERE id_klasifikasi = 2  -- Iklan dengan klaim kesehatan       (3.345, terbesar)
WHERE id_klasifikasi = 3  -- Iklan menyesatkan
WHERE id_klasifikasi = 4  -- Iklan melanggar norma
WHERE id_klasifikasi = 5  -- Iklan superlatif/komparatif/mendiskreditkan
WHERE id_klasifikasi = 6  -- Iklan dengan kata/lambang yang tidak boleh
```

Join ke main:
```sql
SELECT k.id_klasifikasi, k.keterangan_ketidaksesuaian, COUNT(*)
FROM mv_pengawasan_ketidaksesuaian k
LEFT JOIN mv_pengawasan p ON p.id = k.id_pengawasan
GROUP BY 1, 2 ORDER BY 1;
```

## §7 — `nama_balai` (84 nilai, exact-match)

Tidak ada kode — nama langsung. Distinct query:
```sql
SELECT nama_balai, COUNT(*) FROM mv_pengawasan GROUP BY 1 ORDER BY 2 DESC;
```

**Case-sensitive**. Nama resmi uppercase: `BALAI BESAR POM DI BANDUNG`, `BALAI POM DI PALOPO`. Jangan `ILIKE '%bandung%'` untuk aggregate (akan menyamakan balai yang berbeda); discover dulu lalu exact.

**Trap**: 76 distinct target balai names vs 84 main names is not the row-level coverage result. Exact matching currently leaves 22 target names (154 target rows) unmatched. Cross-table achievement requires an approved name mapping or explicit exclusion.

## §8 — Pivot SQL templates

### 8a. Pengawasan per tahun per komoditi
```sql
SELECT date_trunc('year', tgl_start)::date AS tahun, komoditi,
       COUNT(*) AS baris, COUNT(DISTINCT id) AS event_unik
FROM mv_pengawasan
WHERE tgl_start IS NOT NULL
GROUP BY 1, 2 ORDER BY 1, 3 DESC;
```

### 8b. Verdict akhir per balai (exact values)
```sql
SELECT nama_balai,
       COUNT(*) FILTER (WHERE kesimpulan_penilaian_akhir='MK') AS mk,
       COUNT(*) FILTER (WHERE kesimpulan_penilaian_akhir='TMK') AS tmk,
       COUNT(*) FILTER (WHERE kesimpulan_penilaian_akhir IS NULL) AS belum_dinilai
FROM mv_pengawasan
GROUP BY 1 ORDER BY mk+tmk DESC;
```

The query above counts exact `MK` and exact `TMK` only. For a TMK family, use the correct column-specific closure:

```sql
-- Pusat: all non-compliant severities
COUNT(*) FILTER (WHERE kesimpulan_penilaian_pusat IN
  ('TMK','TMK KRITIKAL','TMK MAYOR','TMK MINOR')) AS tmk_family_pusat

-- Balai: center has no KRITIKAL value
COUNT(*) FILTER (WHERE kesimpulan_penilaian_balai IN
  ('TMK','TMK MAYOR','TMK MINOR')) AS tmk_family_balai
```

Exact `TMK` and `TMK family` are different answers and must have different labels.

### 8c. Latest workflow status per main event
```sql
WITH latest AS (
  SELECT DISTINCT ON (id_pengawasan)
         id_pengawasan, status_code, status_label, tanggal_proses
  FROM mv_pengawasan_log
  ORDER BY id_pengawasan, tanggal_proses DESC NULLS LAST
)
SELECT l.status_code, l.status_label, COUNT(*) AS event_unik
FROM latest l
JOIN (SELECT DISTINCT id FROM mv_pengawasan) p
  ON p.id = l.id_pengawasan
GROUP BY 1, 2 ORDER BY 1;
```

This is the current-status contract. A raw log count answers transitions, not current events.

### 8d. Timeline status distribution
```sql
SELECT status, COUNT(*) AS timeline_rows
FROM mv_pengawasan_timeline
GROUP BY 1 ORDER BY 1;
```

The timeline column is `status`; the log column is `status_code`. Timeline rows include historical ids absent from the main table, so state the population.

### 8e. Top 10 pelanggaran by klasifikasi (closure)
```sql
SELECT k.id_klasifikasi, MIN(k.keterangan_ketidaksesuaian) AS klasifikasi, COUNT(*) AS cnt,
       COUNT(DISTINCT k.id_pengawasan) AS event_unik
FROM mv_pengawasan_ketidaksesuaian k
GROUP BY 1 ORDER BY cnt DESC LIMIT 10;
```

### 8f. Realisasi vs target (HANYA tahun 2024)
```sql
SELECT t.nama_balai, t.komoditi, t.target_pengawasan,
       COUNT(DISTINCT p.id) FILTER (WHERE EXTRACT(YEAR FROM p.tgl_start)=2024) AS realisasi_2024
FROM target_balai t
LEFT JOIN mv_pengawasan p
   ON p.nama_balai = t.nama_balai AND UPPER(p.komoditi) = UPPER(t.komoditi)
WHERE t.tahun = 2024
GROUP BY 1, 2, 3 ORDER BY t.target_pengawasan DESC NULLS LAST;
```

## §9 — Decoy anti-patterns (JANGAN)

- `WHERE komoditi ILIKE '%obat%'` — akan menangkap `OBAT`, `OBAT TRADISIONAL (OT)`, `OBAT KUASI` sekaligus, biasanya bukan yang dimaksud user.
- `WHERE status_code < 999` untuk "yg masih berjalan" — menangkap 990-997 yang status-nya tidak jelas.
- `COUNT(DISTINCT pendaftar)` tanpa cleansing — over-count karena string corrupt ETL.
- `WHERE kesimpulan_penilaian_balai = 'TMK KRITIKAL'` — tidak ada di balai, hanya di pusat.
- Headline dari sum-of-breakdown — over-count kalau ada id muncul di 2 komoditi (jarang, tapi verified ada).

## §10 — Refresh protocol

Angka di file ini valid untuk snapshot `sync = 2026-08-10 22:53:15`. ETL pengawasan berjalan harian. Kalau angka hasil query berbeda >5% dengan cheat-sheet ini → data telah refreshed, perbarui cheat-sheet dengan angka baru dan sebutkan tanggal refresh di jawaban.
