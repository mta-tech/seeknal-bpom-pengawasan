---
name: bpom-pengawasan-target
description: "Skill for target vs realisasi questions on BPOM pengawasan/penandaan/pengujian — yearly target per balai per komoditi, achievement rate. Source: `target_balai` (only tahun 2024) + `mv_pengawasan`. Loads alongside bpom-pengawasan-analyst when target/achievment is the subject."
tags: [bpom, pengawasan, target, achievement, gated]
version: "1.0.0"
---

# BPOM Pengawasan Target — achievement executor

Load skill ini ketika pertanyaan mengandung: "target", "capaian", "realisasi vs target", "achievement", "seberapa capai", "sisa target", atau eksplisit tentang angka target tahunan.

## Source tables

- **`target_balai`** (532 baris) — target tahunan per `(nama_balai, komoditi, tahun)`.
  - **Cakupan: HANYA tahun 2024.** Tidak ada target 2023, 2025, 2026. Verified: `SELECT DISTINCT tahun FROM target_balai` → `{2024}`.
  - 76 balai × 7 komoditi × 1 tahun = 532 baris.
  - Exact name matching leaves **22 target balai names** without a main-table match (154 target rows, 22 names × 7 commodities). Do not call these "8 balai"; the 84-vs-76 distinct count is not enough to establish row-level coverage because names differ.
- **7 kolom target**:
  - `target_penandaan`
  - `target_pengawasan`
  - `target_pengujian`
  - `target_pengujian_pangan`
  - `target_pengujian_pangan_fortifikasi`
  - `target_sarana_distribusi`
  - `target_sarana_produksi`
- Realisasi pengawasan dihitung dari `mv_pengawasan` (count distinct `id` atau count baris per `(nama_balai, komoditi, EXTRACT(YEAR FROM tgl_start))`).

## Critical traps

### Trap 1: Tahun 2024 only
**JANGAN** jawab pertanyaan target 2025 atau 2026. Kalau user nanya target 2025, jawab honest: "data target hanya tersedia tahun 2024; target 2025/2026 belum ada di database."

### Trap 2: Kolom mana untuk realisasi mana?
Pemetaan kolom target → realisasi:
- `target_pengawasan` ↔ count dari `mv_pengawasan` dengan filter komoditi & balai sesuai baris target
- `target_penandaan`, `target_pengujian`, dst ↔ TIDAK ada realisasi langsung di `mv_pengawasan` (skill ini hanya covers pengawasan). Untuk yang lain, jawab honest "realisasi penandaan/pengujian tidak ada di database ini".

### Trap 3: Join by name and commodity
`nama_balai` currently requires an approved exact mapping; do not silently fuzzy-match names. Commodity casing differs, so compare it case-insensitively. Always test both dimensions first:
```sql
-- Balai di target tapi tidak di main (atau sebaliknya):
SELECT t.nama_balai, t.komoditi FROM target_balai t
WHERE NOT EXISTS (
  SELECT 1 FROM mv_pengawasan p
  WHERE p.nama_balai = t.nama_balai
    AND UPPER(p.komoditi) = UPPER(t.komoditi)
)
GROUP BY 1, 2;
```

If an approved mapping is unavailable, report unmatched target rows separately and do not infer achievement for them.

### Trap 4: Komoditi casing
`target_balai.komoditi` (Title Case: `Kosmetika`) **vs** `mv_pengawasan.komoditi` (UPPER: `KOSMETIKA`). Verified:
```sql
SELECT DISTINCT komoditi FROM target_balai;     -- Kosmetika, Obat, ...
SELECT DISTINCT komoditi FROM mv_pengawasan;    -- KOSMETIKA, OBAT, ...
```
**WAJIB uppercase-kan satu sisi** sebelum join:
```sql
JOIN mv_pengawasan p ON UPPER(p.komoditi) = UPPER(t.komoditi)
```

## Budget ledger (per turn)

- Sanity check (distinct tahun, distinct komoditi, balai mismatch): max 2.
- Realisasi aggregation per balai per komoditi: max 2.
- Achievement summary + ranking: max 2.
- **TOTAL ceiling: 6 SQL.**

## Pivot SQL cepat

### Achievement rate per balai (pengawasan 2024)
```sql
WITH realisasi AS (
  SELECT nama_balai, UPPER(komoditi) AS komoditi,
         COUNT(DISTINCT id) AS realisasi_event,
         COUNT(*) AS realisasi_baris
  FROM mv_pengawasan
  WHERE EXTRACT(YEAR FROM tgl_start) = 2024
  GROUP BY 1, 2
)
SELECT t.nama_balai, t.komoditi, t.target_pengawasan,
       COALESCE(r.realisasi_event, 0) AS realisasi_event,
       ROUND(COALESCE(r.realisasi_event, 0)::numeric / NULLIF(t.target_pengawasan,0) * 100, 2) AS achievement_pct
FROM target_balai t
LEFT JOIN realisasi r ON r.nama_balai = t.nama_balai AND r.komoditi = UPPER(t.komoditi)
WHERE t.tahun = 2024
  AND t.target_pengawasan > 0
  AND EXISTS (
    SELECT 1 FROM mv_pengawasan p
    WHERE p.nama_balai = t.nama_balai
      AND UPPER(p.komoditi) = UPPER(t.komoditi)
  )
ORDER BY achievement_pct DESC NULLS LAST;
```

### Nasional aggregate (target-covered population only)
```sql
WITH target_pairs AS (
  SELECT DISTINCT nama_balai, UPPER(komoditi) AS komoditi, target_pengawasan
  FROM target_balai
  WHERE tahun = 2024
    AND target_pengawasan > 0
    AND EXISTS (
      SELECT 1 FROM mv_pengawasan p
      WHERE p.nama_balai = target_balai.nama_balai
        AND UPPER(p.komoditi) = UPPER(target_balai.komoditi)
    )
),
realisasi AS (
  SELECT COUNT(DISTINCT p.id) AS event_unik
  FROM mv_pengawasan p
  JOIN target_pairs t
    ON t.nama_balai = p.nama_balai
   AND t.komoditi = UPPER(p.komoditi)
  WHERE p.tgl_start >= DATE '2024-01-01'
    AND p.tgl_start < DATE '2025-01-01'
)
SELECT
  SUM(t.target_pengawasan) AS total_target,
  r.event_unik AS total_realisasi_event,
  ROUND(
    r.event_unik::numeric /
    NULLIF(SUM(t.target_pengawasan), 0) * 100, 2
  ) AS achievement_pct_nasional
FROM target_pairs t CROSS JOIN realisasi r
GROUP BY r.event_unik;
```

This percentage is only for target-covered balai/commodity pairs. A separate national all-main-data count may be reported, but it must not be called the achievement numerator for this denominator.

### Top 5 under-performing balai
```sql
-- Same CTE as above, then:
ORDER BY (t.target_pengawasan - COALESCE(r.realisasi_event, 0)) DESC
LIMIT 5;
```

### Top 5 over-performing balai (realisasi > target)
```sql
ORDER BY (COALESCE(r.realisasi_event, 0) - t.target_pengawasan) DESC
LIMIT 5;
```

## CHECK sebelum jawab

- **Tahun disebut eksplisit**: "target tahun 2024" — jangan generalize ke "tahun lalu" atau "tahun ini".
- **Komoditi casing di-handle**: sebut "join dilakukan dengan UPPER pada kedua sisi karena target Title-Case dan pengawasan UPPERCASE".
- **Unmatched target rows disebut**: 22 target balai names (154 target rows) have no exact main match and are excluded until an approved mapping exists.
- **Realisasi entity consistent**: kalau target adalah angka pengawasan, realisasi juga count pengawasan (`DISTINCT id`), bukan count baris produk.
- **NULL target diexclude**: beberapa baris mungkin `target_pengawasan = 0` atau NULL → di-`FILTER (WHERE target_pengawasan > 0)` sebelum achievement rate.
- **Sum-of-breakdown ≠ headline**: total realisasi target-covered harus dari query sendiri, bukan dijumlah dari per-balai.

## Stop rules

- Probe 0 baris 2x → stop honest.
- Target tahun selain 2024 → jawab honest "tidak ada".
- Question tentang target penandaan/pengujian realisasinya → jawab honest "realisasi tidak di database ini, hanya target".

## Presentation

- Bahasa user.
- Tabel: nama_balai | komoditi | target | realisasi | achievement%.
- Highlight under-performing (achievement < 50%) dan over-performing (> 100%) secara visual.
- Sebut total nasional sebagai headline.
- Disclaimer partial: "Target hanya tahun 2024; analisa trend multi-tahun tidak tersedia di database ini."

## Cross-reference

- Untuk detail pengawasan per balai tanpa konteks target → `bpom-pengawasan-analyst`.
- Untuk pertanyaan tentang durasi pipeline → `bpom-pengawasan-timeline`.
