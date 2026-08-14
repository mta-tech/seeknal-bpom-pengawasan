---
name: bpom-pengawasan-analyst
description: "Analytical skill for factual data questions on Pengawasan Iklan BPOM — counting pengawasan/surat/produk, breakdowns by komoditi/balai/verdict/media, ketidaksesuaian ranking. Uses structured 5-gate procedure with SQL budget control. Source: live `mv_pengawasan*` tables only."
tags: [bpom, pengawasan, text-to-sql, analyst, gated]
version: "1.0.0"
---

# BPOM Pengawasan Analyst — gated executor

Follow `SEEKNAL_ASK.md` Gates 0–5 literally. Skill ini menambahkan enforcement detail.

## Budget ledger (per turn)

- Discovery/probe lookups: max 2 — untuk free text (`nama_produk`, `pendaftar`) atau dimensi yang belum ada di context.
- These are the same two discovery/verification slots, not an additional budget.
- Final SQL: 1. Corrected retry: 1.
- **TOTAL evidence SQL ceiling per turn: 4**: two discovery/verification, one final, and one corrected retry. Mencapai ceiling tanpa angka defensible = STOP dan laporkan jujur.

## Stop rules (override urge to keep querying)

- Probe 0 baris 2x untuk konsep yang sama → binding salah; balik ke Gate 2 atau Gate 1, jangan brute-force variasi.
- Error di final query → ONE corrected retry berbasis error text. Error kedua → STOP.
- Hasil berbeda jauh dari ekspektasi → cek counting entity + scope filter SEKALI, lalu stand by result atau STOP. **Jangan tune filter ke arah angka yang "terasa benar".**
- Free-text search (`nama_produk`, `pendaftar`): pakai exact value kalau ada di `filter_code_reference.md`; baru ILIKE untuk discover, lalu exact filter. Maks 2 probe (ikut budget).
- `pendaftar` PUNYA CORRUPT-STRING TRAP — baca `predikat.md` §6 sebelum `COUNT(DISTINCT pendaftar)`.
- Clarification lewat `request_clarification`/`ask_user` SAJA — pertanyaan klarifikasi sebagai plain text tidak pernah dijawab dan membunuh turn.
- "Pengawasan" tanpa grain is ambiguous: ask whether the user means rows/products, distinct events, or letters. Do not silently use a default.
- Question tentang **target** (bukan realisasi) → load `bpom-pengawasan-target` skill, bukan ini.
- Question tentang **durasi/SLA pipeline** (kabalai→direktur→pusat) → load `bpom-pengawasan-timeline` skill.

## CHECK sebelum jawab (Gate 5) — running list, bukan feeling

Setiap item pernah salah di real case:

- **Counting entity = subject pertanyaan.** Lihat `predikat.md` §1: `COUNT(*)` (baris produk), `COUNT(DISTINCT id)` (event), `COUNT(DISTINCT nomor_surat)` (surat) — semua berbeda, semua legitimate, semua harus disebut.
- **Kode set adalah closed.** Konsep compound ("TMK", "obat", "yang sudah selesai") ambil setiap anggota dari closure table (`filter_code_reference.md` §1–§5). Jangan ambil single keyword ILIKE pertama yang hit — sibling yang di-drop tidak terlihat di hasil.
- **Headline total dari OWN DISTINCT query**, BUKAN dijumlah dari breakdown. Per-komoditi, per-balai, per-status bisa over-count id yang muncul di 2 kategori (rare, tapi verified).
- **Status filter = population yang ditanya.** Jangan stack `status_code = 999` di atas populasi yang sudah defined oleh workflow state lain.
- **Verdict kolom sesuai pertanyaan.** `kesimpulan_penilaian_balai` vs `pusat` vs `akhir` punya populasi & granularity beda (`predikat.md` §3). Pilih yang tepat, sebutkan di jawaban.
- **Exclusions applied**:
  - sentinel `nie='--'` untuk count NIE unik
  - sentinel `nomor_surat IN ('','-')` untuk count surat
  - `tgl_start IS NOT NULL` untuk time-series GROUP BY
  - `pendaftar` raw distinct is diagnostic only; do not present it as a cleansed company count
- **Final SQL touch tabel yang sesuai scope.** Side yang sengaja dikecualikan → sebutkan. Side yang accidentally ketinggalan → undercount terbesar yang available.
- **Kode → label.** `MK` → "Memenuhi Keputusan". `TMK MAYOR` → "Tidak Memenuhi Keputusan, severity Mayor". Sekali per angka.
- **Partial-year disclosure.** Data 2026 hanya sampai Agustus. Jangan tampilkan "2026: 12.345" tanpa label "(YTD Agustus)".

## Domain yang TIDAK dicakup skill ini (Gate 0 redirect)

- **Target/realisasi tahunan** → `bpom-pengawasan-target` (sumber: `target_balai`).
- **Durasi pipeline, SLA, tanggal milestone** → `bpom-pengawasan-timeline` (sumber: `mv_pengawasan_timeline`).
- **Registrasi pangan / NIE produk pangan olahan** → bukan domain ini, redirect ke `seeknal-bpom-neo` (beda database).
- **Pemeriksaan/Pengujian/Sampling** → belum ada skill, sumber data belum terkoneksi di skill ini. Jawab honest "tidak terkoneksi".

## Pivot SQL cepat (verified, copy-paste starting point)

### Counting 5 entities
```sql
SELECT COUNT(*) AS baris,
       COUNT(DISTINCT id) AS event_unik,
       COUNT(DISTINCT NULLIF(NULLIF(NULLIF(nomor_surat,'-'),''),'')) AS surat_unik,
       COUNT(DISTINCT nama_produk) AS produk_unik,
       COUNT(DISTINCT nie) FILTER (WHERE nie <> '--') AS nie_unik,
       COUNT(DISTINCT pendaftar) AS pendaftar_raw
FROM mv_pengawasan;
```

### Cross-tab komoditi × verdict akhir
```sql
SELECT komoditi,
       COUNT(*) FILTER (WHERE kesimpulan_penilaian_akhir='MK') AS mk,
       COUNT(*) FILTER (WHERE kesimpulan_penilaian_akhir='TMK') AS tmk,
       COUNT(*) FILTER (WHERE kesimpulan_penilaian_akhir IS NULL) AS belum_dinilai
FROM mv_pengawasan GROUP BY 1 ORDER BY mk+tmk DESC;
```

This exact-value pivot is only for `MK` and exact `TMK`. For the TMK family use the closure set from `filter_code_reference.md`; do not silently mix exact and family counts.

### Latest workflow status per event
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

Use `COUNT(*)` on the deduplicated `latest` CTE for current event status. Use the raw log only when the question explicitly asks for transitions or log records.

### Detail dengan filter balai + komoditi + range tanggal
```sql
SELECT id, nomor_surat, nama_produk, nie, kesimpulan_penilaian_akhir, tgl_start, tgl_end
FROM mv_pengawasan
WHERE nama_balai = 'BALAI BESAR POM DI BANDUNG'
  AND komoditi = 'KOSMETIKA'
  AND tgl_start >= '2025-01-01' AND tgl_start < '2026-01-01'
ORDER BY tgl_start DESC LIMIT 50;
```

## Presentation

- Bahasa user.
- Gate 3 commitment block = INTERNAL, jangan print.
- Bullets pakai `-`.
- Query failed/empty/timeout → laporkan failure plainly, jangan dibungkus.
- Setiap angka dilabeli kode+deskripsi: **"`MK` (Memenuhi Keputusan): 67.920 baris"**, bukan "MK: 67.920" mentah.
- Period × kategori table dari SATU closing GROUP BY — hygiene applied silently.
- Follow-up: baca turn sebelumnya, carry-over entity/scope/range, ubah hanya yang disebut di turn ini.

## CSV Store Contract

Sama dengan neo — export adalah LAST tool call di turn. Self-check: scan tool calls di turn ini, kalau `upload_to_s3` sudah muncul (filename apapun), jangan panggil lagi. Maks 1 export per turn. Jangan paste raw URL.
