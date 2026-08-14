# 04 — Tabel `mv_pengawasan_timeline` (Milestone & Durasi)

> **236.982 baris · 11 kolom · 20 MB · snapshot 2026-08-12 23:24:35**
> Grain: **1 baris = 1 event** (1:1 dengan `id_pengawasan`, 0 duplikat).

## Profil 11 kolom

| Kolom | Tipe | NULL | Catatan |
|---|---|---|---|
| `id_pengawasan` | bigint | 0 | 1:1 (236.982 distinct = rows); 64.982 id hantu tak di main |
| `tgl_start` | date | 0 | 2019-09-21 → 2026-08-31 (lebih awal dari main yang mulai 2023) |
| `tgl_end` | date | 0 | cocok 100% dengan main `tgl_end` untuk id yang sama |
| `tanggal_kirim_kabalai` | date | 8.403 (3,5%) | milestone kirim ke kepala balai |
| `tanggal_kirim_direktur` | date | **47.121 (19,9%)** | event belum sampai direktur |
| `tanggal_kirim_pusat` | date | 8.663 (3,7%) | milestone kirim ke pusat |
| `status` | bigint | 0 | **18 distinct** — beda nama kolom dari log (`status_code`) |
| `mulai_kabalai` | integer | 8.403 | durasi HARI; median 8, max 740 |
| `kabalai_direktur` | integer | 47.121 | durasi HARI; median 18, max 1.551 (outlier 4,2 thn) |
| `direktur_pusat` | integer | 47.121 | **FLAG BINER {0,1}** — BUKAN durasi! |
| `sync` | timestamp | 0 | 2026-08-12 23:24:35 |

## ⚠️ Temuan KRITIS: `direktur_pusat` adalah FLAG BINER, bukan durasi

Banyak dokumentasi lama menyebut `direktur_pusat` sebagai "durasi direktur ke pusat (median 0, max 1)". **Ini MENYESATKAN.**

| `direktur_pusat` | n baris | ada `tanggal_kirim_pusat` | ada `tanggal_kirim_direktur` |
|---|---|---|---|
| 0 | 187.556 | 187.556 | 187.556 |
| 1 | 2.244 | 2.244 | 2.244 |
| NULL | 47.121 | 38.458 | 0 |

**Bukti ini flag biner**:
- Hanya 2 nilai non-NULL: {0, 1}. Tidak ada nilai 2, 3, dst. (mustahil untuk durasi bisnis nyata)
- `direktur_pusat=1` SELALU berkorelasi dengan `tanggal_kirim_pusat IS NOT NULL`
- `direktur_pusat IS NULL` (47.121) = `tanggal_kirim_direktur IS NULL` (47.121) — sinkron 100% (event belum sampai direktur)

**Tafsir yang benar**: `direktur_pusat` = flag **"sudah sampai pusat"** (1) atau "belum" (0). NULL = belum sampai direktur. **Bukan durasi hari.**

**Siapa pun yang menghitung avg/median "durasi direktur→pusat" dari kolom ini akan keliru total** — akan menyimpulkan "tahap ini instan (median 0)" padahal itu hanya arti flag.

## Null sinkron — ketiga kolom direktur null bersamaan

| Yang null | Baris |
|---|---|
| `tanggal_kirim_direktur` null | 47.121 |
| `kabalai_direktur` null | 47.121 |
| `direktur_pusat` null | 47.121 |

**Ketiganya null bersamaan** untuk event yang belum mencapai direktur. Null-nya **konsisten, bukan acak**. Mayoritas = PRODUK PANGAN yang macet di status 4.

## Distribusi `status` (kolom ini beda nama dari log `status_code`)

| status | n |
|---|---|
| 999 | 183.845 |
| 4 | 35.587 |
| 0 | 6.644 |
| 7 | 5.986 |
| 991 | 1.363 |
| 994 | 1.197 |
| 5 | 1.095 |
| 6 | 422 |
| 1 | 220 |
| 2 | 180 |
| 993 | 125 |
| 992 | 94 |
| 995 | 69 |
| 996 | 46 |
| 3 | 41 |
| 990 | 4 |
| **9** | **2** ⚠️ tidak ada di log |
| **8** | **1** ⚠️ tidak ada di log |

**Anomali**: timeline punya kode `8` (1 baris) dan `9` (2 baris) yang TIDAK ada di log. Status 9 di log = "990-997 rejection", tapi di timeline status 9 muncul sbg nilai tersendiri. Detail ketiga event aneh:

| id | tgl_start | status | mulai_kabalai | kabalai_direktur |
|---|---|---|---|---|
| 184603 | 2025-06-02 | 9 | 1 | 8 |
| 73307 | 2023-06-25 | 8 | 10 | 16 |
| 98994 | 2024-02-05 | 9 | 3 | 52 |

Ketiganya event normal (ada durasi, ada kabalai_direktur), tapi status 8/9 tak terdaftar di dictionary log. **Artefak langka — bisa diabaikan tapi dilaporkan.**

## Konsistensi tanggal vs main

Untuk 183.968 id yang ada di kedua tabel:
- `tgl_start` beda: **0** (100% cocok)
- `tgl_end` beda: **0** (100% cocok)

**Timeline adalah turunan SAH dari main** untuk id yang sama. Aman dipakai sebagai sumber tanggal.

## Durasi end-to-end per komoditi (basis `tgl_end - tgl_start`)

| Komoditi | median hari | p90 hari | belum ke direktur | % backlog |
|---|---|---|---|---|
| ROKOK | 43 | 99 | 0 | 0% |
| OBAT | 23 | 51 | 740 | 2,3% |
| KOSMETIKA | 19 | 50 | 2.816 | 5,8% |
| OBAT TRADISIONAL | 18 | 49 | 36 | 0,2% |
| SUPLEMEN | 18 | 50 | 16 | 0,2% |
| OBAT KUASI | 17 | 38 | 5 | 0,2% |
| **PRODUK PANGAN** | **NULL** | **NULL** | **33.777** | **100%** |

**PRODUK PANGAN 100% belum sampai direktur** — semua 33.777 event macet di status 4. Backlog tersembunyi yang tak terlihat dari kolom `akhir` (yang 100% 'Null' untuk pangan).

## Outlier durasi ekstrem

`kabalai_direktur` max 1.551 hari (4,2 tahun). 2.071 baris punya `kabalai_direktur > 365`.

Sampel outlier terbesar:
| id | tgl_start | status | mulai_kabalai | kabalai_direktur |
|---|---|---|---|---|
| 1277 | 2020-01-23 | 999 | 67 | **1.551** |
| 1270 | 2020-01-23 | 999 | 67 | 1.551 |
| 1271 | 2020-01-23 | 999 | 67 | 1.551 |
| 1276 | 2020-01-23 | 999 | 67 | 1.551 |
| 1288 | 2020-01-23 | 999 | 67 | 1.551 |

Outlier terkonsentrasi di **batch id 1270-1288** (Januari 2020, selesai 999). Bisa jadi kasus nyata terlantar ATAU data entry tanggal salah. Untuk summary, **selalu pakai median + p95**, jangan avg (skew parah).

## Lag: tgl_start vs tanggal_kirim_kabalai

| Lag | Baris |
|---|---|
| ≤ 7 hari | 68.831 |
| 8-30 hari | 98.410 |
| > 30 hari | 61.088 |
| NULL | 8.403 |

Mayoritas event dikirim ke kabalai dalam ≤30 hari, tapi **61.088 event lebih dari sebulan** — backlog lokal di tahap awal.

## Sebaran tahun timeline (lebih luas dari main)

| Tahun | n |
|---|---|
| 2019 | 7 |
| 2020 | ~6.550 |
| 2021 | ~24.912 |
| 2022 | ~25.929 |
| 2023+ | sisa (overlaps dengan main) |

Timeline mulai **2019-09-21**, main mulai **2023-01-01**. Timeline menyimpan sejarah lengkap 2019-2022 yang tak ada di main.

## Pemenuhan timeline (use case #1 user production)

Dari 340 pertanyaan user KAI, **template #1 paling sering** = *"pemenuhan timeline dihitung dari tanggal sampling/pemeriksaan hingga tanggal direktur"* (11x+) dan *"ketepatan waktu pelaporan"* (4x).

### Mapping milestone (apa arti tiap tanggal)

| Tanggal | Arti | Ketersediaan |
|---|---|---|
| `tgl_start` | **tanggal sampling / pemeriksaan dimulai** (user: "tanggal sampling/pemeriksaan") | 100% terisi |
| `tgl_end` | tanggal selesai kegiatan lapangan | 100% terisi (cocok main) |
| `tanggal_kirim_kabalai` | laporan ditandatangani kepala balai | 96,5% terisi |
| `tanggal_kirim_direktur` | laporan diterima direktur | 80,1% terisi (19,9% NULL = backlog) |
| `tanggal_kirim_pusat` | laporan diterima pusat | 96,3% terisi |

### Durasi yang DAPAT dihitung pasti (tanpa asumsi)

```sql
-- Durasi sampling → kepala balai
tanggal_kirim_kabalai - tgl_start
-- Durasi kepala balai → direktur (kolom kabalai_direktur sudah tersedia)
kabalai_direktur
-- Durasi sampling → direktur
tanggal_kirim_direktur - tgl_start
```

### ⚠️ Rule "9 bulan berikutnya" — BELUM terdokumentasi di DB

User production bertanya: *"ketepatan waktu pelaporan oleh UPT yang dihitung berdasarkan laporan yang dikirimkan tanggal kepala balai sebelum batas tanggal 9 bulan berikutnya"*.

**Database TIDAK menyimpan rule deadline.** Kolom yang ada hanya tanggal milestone (fakta), bukan perbandingan terhadap batas waktu. Artinya:

- Deadline "9 bulan berikutnya" = **business rule organisasi eksternal**
- Basis penghitungan deadline (dari `tgl_start`? `tgl_end`? `tgl_sampling`?) **belum dikonfirmasi**
- **JANGAN hardcode `+ INTERVAL '9 months'` sebagai final** — SQL-nya harus diberi label "ASUMSI, butuh konfirmasi" (lihat `16` Pair 9 dan `15` honest response #8)
- Jika user bertanya ketepatan waktu, jawab data fakta (tanggal milestone, durasi) + minta klarifikasi rule

### Contoh SQL pemenuhan (tanpa rule asumsi, fakta saja)

```sql
-- Pemenuhan: berapa event sudah sampai direktur, berapa belum, per UPT
SELECT p.nama_balai,
       COUNT(DISTINCT p.id) AS event_total,
       COUNT(DISTINCT p.id) FILTER (WHERE t.tanggal_kirim_direktur IS NOT NULL) AS sampai_direktur,
       COUNT(DISTINCT p.id) FILTER (WHERE t.tanggal_kirim_direktur IS NULL) AS belum_direktur
FROM mv_pengawasan p
LEFT JOIN mv_pengawasan_timeline t ON t.id_pengawasan = p.id
GROUP BY 1 ORDER BY 2 DESC;
```

**Caveat**: `LEFT JOIN` + `COUNT(DISTINCT id)` — jangan `COUNT(*)` (timeline 1:1, tapi main bisa multi-baris per id).

## Pivot SQL

### Konfirmasi `direktur_pusat` = flag (wajib sebelum stat summary)
```sql
SELECT direktur_pusat, COUNT(*),
       COUNT(*) FILTER (WHERE tanggal_kirim_pusat IS NOT NULL) AS ada_tgl_pusat
FROM mv_pengawasan_timeline GROUP BY 1 ORDER BY 1;
```

### Median durasi per komoditi (basis `tgl_end - tgl_start`)
```sql
SELECT p.komoditi,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (t.tgl_end - t.tgl_start)) AS med_hari,
  PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY (t.tgl_end - t.tgl_start)) AS p90_hari,
  COUNT(*) FILTER (WHERE t.kabalai_direktur IS NULL) AS belum_ke_direktur
FROM mv_pengawasan_timeline t
JOIN mv_pengawasan p ON p.id = t.id_pengawasan
GROUP BY 1 ORDER BY 2 NULLS LAST;
```

### Slow-balai ranking (median durasi, deduplikasi event)
```sql
WITH main_event AS (
  SELECT id, MIN(nama_balai) AS nama_balai FROM mv_pengawasan GROUP BY id
)
SELECT p.nama_balai, COUNT(*) AS event_count,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.kabalai_direktur) AS med_kb_dr
FROM mv_pengawasan_timeline t
JOIN main_event p ON p.id = t.id_pengawasan
WHERE t.kabalai_direktur IS NOT NULL
GROUP BY 1 HAVING COUNT(*) >= 50
ORDER BY med_kb_dr DESC NULLS LAST LIMIT 20;
```

**CTE `main_event` wajib** — join timeline ke raw `mv_pengawasan` akan menimbang durasi sekali per baris produk dan mengubah percentile.

## Jebakan

1. **`direktur_pusat` BUKAN durasi** — flag biner. Jangan avg/median.
2. **Timeline punya lebih banyak id dari main** (236.982 vs 172.180) — `INNER JOIN` timeline→main akan drop 64.982 baris. Untuk populasi main, filter `WHERE id_pengawasan IN (SELECT id FROM mv_pengawasan)`.
3. **Kolom `status` di timeline ≠ `status_code` di log** — nama beda, populasi beda (timeline termasuk id historis).
4. **Status 8 & 9 (3 baris) tak ada di log** — artefak langka.
5. **Outlier durasi skew parah** — selalu median + p95, jangan avg.

## Bukti SQL
Lihat `13_sql_audit_trail.md` §04.
