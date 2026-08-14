---
name: bpom-pengawasan-timeline
description: "Skill for pengawasan SLA / pipeline duration questions — duration from start→kabalai→direktur→pusat, status milestone dates, slow-balai identification. Source: `mv_pengawasan_timeline` and `mv_pengawasan_log`. Loads alongside bpom-pengawasan-analyst when duration/SLA is the subject."
tags: [bpom, pengawasan, timeline, sla, gated]
version: "1.0.0"
---

# BPOM Pengawasan Timeline — pipeline SLA executor

Load skill ini ketika pertanyaan mengandung: "berapa lama", "durasi", "SLA", "timbal balik", "kapan sampai pusat", "kapan selesai", "mana balai paling lambat", atau eksplisit tentang tanggal milestone workflow.

## Source tables

- **`mv_pengawasan_timeline`** (236.856 baris) — kolom durasi siap pakai (dalam HARI):
  - `mulai_kabalai`: dari start sampai `tanggal_kirim_kabalai` (median **8 hari**, max 740)
  - `kabalai_direktur`: kabalai ke direktur (median **18 hari**, max 1.551 — ada outlier 4 tahun!)
  - `direktur_pusat`: direktur ke pusat (median **0**, max 1 — JANGAN DIARTIKAN "sangat cepat", lihat trap)
- **`mv_pengawasan_log`** (1.816.774 baris) — log per status transition dengan `tanggal_proses`. Untuk analisa "berapa lama di status X" atau "urutan transisi".

## Critical traps (read before query)

### Trap 1: timeline/log punya lebih banyak id dari main
- `mv_pengawasan` distinct id = 172.165
- `mv_pengawasan_timeline` distinct id = 236.856
- Selisih = id historis yang sudah tidak ada di main (kemungkinan soft-delete atau superseded).
- **Konsekuensi**: `INNER JOIN` dari timeline/log akan menampilkan id yang tidak ada di main. Untuk konsistensi dengan angka main, gunakan `WHERE id_pengawasan IN (SELECT id FROM mv_pengawasan)` atau INNER JOIN dari main sebagai sisi kiri.

### Trap 2: `direktur_pusat` median 0 ≠ proses cepat
Median 0 dengan max 1 sangat tidak masuk akal untuk duration bisnis nyata. Kemungkinan:
- Kolom ini auto-filled dengan 0 di mayoritas baris karena `tanggal_kirim_pusat` belum terisi (proses belum sampai pusat).
- Atau definisi kolom berbeda (mungkin selisih tanggal, bukan durasi kerja).

**WAJIB** sebelum stat summary:
```sql
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE tanggal_kirim_pusat IS NULL) AS pusat_null,
  COUNT(*) FILTER (WHERE direktur_pusat = 0) AS dp_zero,
  COUNT(*) FILTER (WHERE direktur_pusat > 0) AS dp_positive
FROM mv_pengawasan_timeline;
```
Laporkan distribusi NULL vs 0 vs positive di jawaban, jangan langsung avg/median.

### Trap 3: outlier `kabalai_direktur` max 1.551 hari
1.551 hari ≈ 4.2 tahun. Jelas ada data quality issue (mungkin salah input tanggal). Untuk summary stats:
```sql
SELECT
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY kabalai_direktur) AS median,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY kabalai_direktur) AS p95,
  AVG(kabalai_direktur) FILTER (WHERE kabalai_direktur < 365) AS avg_under_1year
FROM mv_pengawasan_timeline;
```
Selalu sebut "median X, p95 Y" — jangan avg saja karena outlier skew parah.

## Budget ledger (per turn)

- Discovery (NULL count, distribusi 0): max 1.
- Stat summary (median/p95/avg): max 2.
- Cross-tab (per balai, per komoditi, per bulan): max 2.
- Final detail listing: max 1.
- **TOTAL evidence SQL ceiling: 4**: two discovery/verification, one final, one corrected retry.

## Pivot SQL cepat

### Median durasi keseluruhan
```sql
SELECT
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY mulai_kabalai) AS med_mulai_kb,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY kabalai_direktur) AS med_kb_dr,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY direktur_pusat) AS med_dr_pu
FROM mv_pengawasan_timeline;
```

### Per-balai median durasi (slow-balai ranking)
```sql
WITH main_event AS (
  SELECT id, MIN(nama_balai) AS nama_balai
  FROM mv_pengawasan
  GROUP BY id
)
SELECT p.nama_balai,
       COUNT(*) AS event_count,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.mulai_kabalai) AS med_mulai_kb,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.kabalai_direktur) AS med_kb_dr
FROM mv_pengawasan_timeline t
JOIN main_event p ON p.id = t.id_pengawasan
WHERE t.mulai_kabalai IS NOT NULL
GROUP BY 1 HAVING COUNT(*) >= 50  -- exclude balai kecil
ORDER BY med_kb_dr DESC NULLS LAST LIMIT 20;
```

The deduplicated `main_event` CTE is mandatory. Joining timeline to raw `mv_pengawasan` weights a duration once per product row and changes the percentile.

### Threshold query (for example, duration greater than 3 days)
```sql
SELECT
  COUNT(*) FILTER (WHERE mulai_kabalai > 3) AS mulai_kabalai_gt3,
  COUNT(*) FILTER (WHERE kabalai_direktur > 3) AS kabalai_direktur_gt3,
  COUNT(*) FILTER (WHERE direktur_pusat > 3) AS direktur_pusat_gt3
FROM mv_pengawasan_timeline;
```

Clarify whether the user means one stage or any stage. If "any stage", use one explicit OR predicate and state that the source population is timeline rows/events.

### Time-in-status (dari log, untuk satu status tertentu)
```sql
-- Untuk satu id, urutan status & gap
SELECT id_pengawasan, status_code, status_label, tanggal_proses,
       tanggal_proses - LAG(tanggal_proses) OVER (PARTITION BY id_pengawasan ORDER BY tanggal_proses) AS gap_hari
FROM mv_pengawasan_log
WHERE id_pengawasan = <id>
ORDER BY tanggal_proses;
```

### Distribusi status final vs intermediate
```sql
SELECT status, COUNT(*) FROM mv_pengawasan_timeline GROUP BY 1 ORDER BY 1;
```
`status=999` = final (Sampel Rujukan Selesai). Other values are intermediate or transitional. Do not hardcode a row count; it changes with refresh. For log status, use `status_code`, not `status`.

## CHECK sebelum jawab

- **Sample size disebut**: "dari 172.165 event, 150.234 punya data `mulai_kabalai`". Jangan stat dari N kecil tanpa konteks.
- **NULL/zero disclosed**: kalau `direktur_pusat` median 0, sebut "median 0 terindikasi mayoritas data belum sampai pusat, bukan durasi cepat".
- **Outlier handling**: sebut p95 atau avg-dengan-trim, jangan avg mentah.
- **Per-balai ranking disertai threshold**: balai dengan <50 deduplicated events tidak reliable untuk perbandingan median.
- **Beda sumber = beda angka**: count dari timeline (236.856 id) vs count dari main (172.165 id) → selalu sebut dari mana angka berasal.

## Stop rules

- Probe 0 baris 2x → stop honest, jangan brute force.
- `tanggal_kirim_pusat` hampir semua NULL → jangan fabriase angka. Jawab "data belum tersedia untuk mayoritas event".
- Question tentang forecast timeline (predict berapa lama next case) → BUKAN skill ini. Jawab honest "skill forecast belum ada untuk timeline pengawasan".

## Presentation

- Bahasa user.
- Setiap durasi disertai unit: "median 18 hari", bukan "18" mentah.
- Sebutkan kolom sumber: "berdasarkan `kabalai_direktur` di `mv_pengawasan_timeline`".
- Visualisasi chart direkomendasikan (load `visualize-chart` skill kalau tersedia).
- Boxplot untuk distribusi durasi lebih baik dari bar chart untuk data dengan outlier.
