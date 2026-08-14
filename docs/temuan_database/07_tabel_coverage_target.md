# 07 — Tabel Referensi: `coverage_balai` & `target_balai`

## `coverage_balai` (668 baris, 104 KB)

> Grain: **banyak-ke-banyak** antara balai dan kabupaten/kota.

### Profil 5 kolom

| Kolom | Distinct | Catatan |
|---|---|---|
| `id_balai` | 88 | 1:1 dengan nama_balai |
| `nama_balai` | 88 | UPPERCASE |
| `id_kabupaten` | 514 | 1:1 dengan kabupaten_kota |
| `kabupaten_kota` | 514 | Title Case (`Kabupaten Aceh Barat`) |
| `sync` | 1 | 2026-08-10 22:54:25 |

### Distribusi kabupaten per balai

| Bucket kabupaten/balai | Jumlah balai |
|---|---|
| 1 kabupaten | 2 |
| 2-5 | 45 |
| 6-10 | 23 |
| 11-20 | 13 |
| >20 | 5 |

Top 5 balai dengan cakupan terluas:
| nama_balai | kabupaten |
|---|---|
| BALAI BESAR POM DI SURABAYA | 38 |
| BALAI BESAR POM DI SEMARANG | 35 |
| BALAI BESAR POM DI BANDUNG | 27 |
| BALAI BESAR POM DI MEDAN | 26 |
| BALAI BESAR POM DI JAYAPURA | 22 |

### Coverage terhadap main

- 84/84 balai di main cocok dengan coverage (case-insensitive match).
- **1 blind spot**: `DIREKTORAT PENGAWASAN KMEI ONPPZA` ada di main tapi tak ada di coverage (ini pusat, bukan balai geografis — wajar).
- **5 balai di coverage TIDAK ada di main**: 3 DEMO + 2 PENGUJIAN → **data uji bocor ke referensi**.

### Pivot SQL
```sql
-- Balai di main tanpa coverage (blind spot)
SELECT DISTINCT p.nama_balai FROM mv_pengawasan p
WHERE NOT EXISTS (
  SELECT 1 FROM coverage_balai c WHERE UPPER(c.nama_balai) = UPPER(p.nama_balai)
);

-- Balai di coverage tak ada di main (data uji)
SELECT DISTINCT c.nama_balai FROM coverage_balai c
WHERE NOT EXISTS (
  SELECT 1 FROM mv_pengawasan p WHERE UPPER(p.nama_balai) = UPPER(c.nama_balai)
);
```

## `target_balai` (532 baris, 112 KB)

> Grain: **1 baris = 1 (nama_balai, komoditi, tahun)** target.

### Profil 12 kolom

| Kelompok | Kolom |
|---|---|
| Identitas | `id`, `nama_balai` (76 distinct, Title Case), `komoditi` (7 distinct, Title Case), `tahun` |
| **7 kolom target** | `target_penandaan`, `target_pengawasan`, `target_pengujian`, `target_pengujian_pangan`, `target_pengujian_pangan_fortifikasi`, `target_sarana_distribusi`, `target_sarana_produksi` |
| Meta | `sync` |

### ⚠️ Cakupan: HANYA tahun 2024

```sql
SELECT DISTINCT tahun FROM target_balai;  -- {2024}
```

**TIDAK ada target 2023, 2025, 2026.** Untuk pertanyaan target tahun selain 2024, jawab honest: "data target hanya tersedia tahun 2024".

### 76 balai × 7 komoditi = 532 baris

`nama_balai` Title Case (`Kosmetika`) vs main UPPERCASE (`KOSMETIKA`). **Wajib UPPER() kanan-kiri saat join.**

### Match terhadap main — KOREKSI PENTING

Banyak dokumentasi lama menyatakan "22 target balai names unmatched". **SALAH**. Verifikasi:

```sql
SELECT nama_balai FROM target_balai t
WHERE NOT EXISTS (
  SELECT 1 FROM mv_pengawasan p WHERE UPPER(p.nama_balai) = UPPER(t.nama_balai)
)
GROUP BY 1;
-- Hasil: 0 baris (SEMUA match dengan UPPER())
```

**Dengan `UPPER()` di kedua sisi: 0 unmatched.** Klaim 22-unmatched adalah error persisten yang harus dihapus.

### 7 kolom target — struktur mengkodekan regulasi

| komoditi | target_penandaan | target_pengawasan | target_pengujian |
|---|---|---|---|
| PRODUK PANGAN | **25.820** (terbesar) | 13.124 | 25.820 |
| KOSMETIKA | 24.901 | 15.000 | 24.901 |
| OBAT | 16.981 | **0** | 16.981 |
| OBAT TRADISIONAL | 12.527 | 5.000 | 12.527 |
| ROKOK | 8.340 | **21.504** (terbesar) | **0** |
| SUPLEMEN KESEHATAN | 3.389 | 2.000 | 3.389 |
| OBAT KUASI | 880 | 1.000 | 880 |

**Pola regulasi embedded**:
- **OBAT `target_pengawasan=0`** — obat iklan TIDAK dirutin-monitor pengawasan (fokus penandaan/pengujian).
- **ROKOK `target_pengujian=0`** — rokok TIDAK diuji lab (diatur cukai/Kemenkes, bukan BPOM pengujian).
- **ROKOK `target_pengawasan=21.504` tertinggi** — paling banyak diawasi iklannya (karena MEDIA_LUARRUANG dominan + regulasi ketat).
- **PRODUK PANGAN `target_penandaan=25.820` tertinggi** — pangan paling banyak ditandai (klaim kesehatan pangan pelanggaran terbanyak).
- **Hanya PANGAN punya `target_pengujian_pangan` & `_fortifikasi`** (17 baris NULL).

### Kolom target NULL/zero

| Kolom | NULL | zero |
|---|---|---|
| `target_penandaan` | 0 | 0 |
| `target_pengawasan` | 0 | 76 (semua OBAT) |
| `target_pengujian` | 0 | 76 (semua ROKOK) |
| `target_pengujian_pangan` | **17** | 439 |
| `target_pengujian_pangan_fortifikasi` | **17** | 462 |
| `target_sarana_produksi` | 0 | 327 |
| `target_sarana_distribusi` | 0 | 152 |

### Realisasi vs target 2024 (pengawasan ROKOK, sampel)

Realisasi (= `COUNT(DISTINCT id)` dari main 2024) vs `target_pengawasan` per balai-komoditi:

| nama_balai | komoditi | target | realisasi | % |
|---|---|---|---|---|
| BALAI BESAR POM DI PALANGKARAYA | Rokok | 432 | 521 | 121% |
| Loka POM di Kabupaten Tanah Bumbu | Rokok | 120 | 144 | 120% |
| BALAI POM DI TABALONG | Rokok | 120 | 140 | 117% |
| ... | ... | ... | ... | ... |
| BALAI BESAR POM DI PADANG | Rokok | 576 | 584 | 101% |

**Pola**: realisasi ROKOK 2024 umumnya **>100%** target (101-121%) — target under-estimated, atau realisasi overshoot.

### Pivot SQL — achievement rate
```sql
WITH realisasi AS (
  SELECT UPPER(nama_balai) nb, UPPER(komoditi) km, COUNT(DISTINCT id) r
  FROM mv_pengawasan
  WHERE tgl_start >= '2024-01-01' AND tgl_start < '2025-01-01'
  GROUP BY 1, 2
)
SELECT t.nama_balai, t.komoditi, t.target_pengawasan,
       COALESCE(r.r, 0) AS realisasi,
       ROUND(COALESCE(r.r,0)::numeric / NULLIF(t.target_pengawasan,0) * 100, 1) AS pct
FROM target_balai t
LEFT JOIN realisasi r ON r.nb = UPPER(t.nama_balai) AND r.km = UPPER(t.komoditi)
WHERE t.komoditi = 'Rokok' AND t.target_pengawasan > 0
ORDER BY pct DESC NULLS LAST;
```

## Jebakan

1. **`target_balai` HANYA 2024** — jangan jawab target 2025/2026.
2. **Klaim "22 unmatched" SALAH** — 0 unmatched dengan UPPER().
3. **Casing beda** — target Title Case, main UPPERCASE. Wajib UPPER() saat join.
4. **`target_pengawasan` OBAT = 0** — bukan error, by design (obat tidak dirutin pengawasan).
5. **`target_pengujian` ROKOK = 0** — bukan error, by design (rokok tak diuji BPOM).
6. **Realisasi hanya untuk `target_pengawasan`** — penandaan/pengujian/sarana realisasinya tidak ada di `mv_pengawasan`. Jawab honest.
7. **`coverage_balai` 5 balai DEMO/PENGUJIAN** bocor ke referensi — jangan dipakai sebagai balai aktif.

## Bukti SQL
Lihat `13_sql_audit_trail.md` §07.

---

## Join `target_balai` — sebabnya kapitalisasi, dan cara memperbaikinya (verifikasi 2026-08-13)

`data_architecture.md` mencatat *"exact match currently leaves 22 target names unmatched"* tanpa
menyebut penyebabnya. Penyebabnya **kapitalisasi**, bukan nama yang berbeda:

```sql
SELECT nama_balai FROM (
  SELECT DISTINCT nama_balai FROM mv_pengawasan
  EXCEPT SELECT DISTINCT nama_balai FROM target_balai) x ORDER BY 1 LIMIT 6;
--  DIREKTORAT PENGAWASAN KMEI ONPPZA
--  LOKA POM DI KAB. BELU
--  LOKA POM DI KAB. SAMBAS
--  LOKA POM DI KAB. SUMBA TIMUR
--  LOKA POM DI KABUPATEN ACEH SELATAN
--  LOKA POM DI KABUPATEN ACEH TENGAH
```

Fakta memakai **HURUF BESAR** (`LOKA POM DI KAB. BELU`); `target_balai` memakai campuran
(`Loka POM di Kab. Belu`). Setelah dinormalisasi, join berhasil penuh:

```sql
WITH ld AS (
  SELECT nama_balai, komoditi, count(*) AS jml FROM mv_pengawasan
  WHERE extract(year FROM tgl_start) = 2025 GROUP BY 1,2)
SELECT count(*) AS pasangan, count(tb.id) AS ketemu_target,
       count(*) - count(tb.id) AS tanpa_target
FROM ld LEFT JOIN target_balai tb
  ON lower(trim(tb.nama_balai)) = lower(trim(ld.nama_balai))
 AND lower(trim(tb.komoditi))   = lower(trim(ld.komoditi))
 AND tb.tahun = 2024;
--  457 | 457 | 0
```

**457 dari 457 pasangan (balai × komoditi) ketemu.** Berbeda dengan domain `pemeriksaan`, di sini
`komoditi` bisa dijoin **langsung** karena kedua sisi memakai tujuh nilai yang sama
(`Produk Pangan`, `Obat`, `Kosmetika`, `Obat Tradisional (OT)`, `Suplemen Kesehatan`,
`Obat Kuasi`, `Rokok`) — tidak perlu kolom jembatan seperti `mapping_komoditi_target_balai`
di `pemeriksaan`.

**Satu-satunya entitas yang benar-benar tanpa target** adalah `DIREKTORAT PENGAWASAN KMEI ONPPZA` —
itu unit pusat, bukan balai, jadi memang tidak punya target balai. Laporkan terpisah, jangan
dipaksa punya target dan jangan dibuang diam-diam.

**Aturan untuk skill target:**
1. Selalu `lower(trim())` di kedua sisi join.
2. Filter `tb.tahun = 2024` secara eksplisit — **hanya tahun itu yang ada** (532 baris = 76 balai ×
   7 komoditi × 1 tahun). Untuk realisasi 2025/2026, sebut bahwa pembandingnya target 2024 atau
   sajikan realisasi tanpa capaian.
3. Pisahkan baris DIREKTORAT sebelum menghitung persentase capaian nasional.

---

## ⚠️ Status penyaluran ke `context/` — kolom target: BELUM

Diverifikasi 14 Agustus 2026 terhadap warehouse dan terhadap `context/85-target-capaian.md`.

Halaman itu menyebut nama tabel `target_balai` dan kunci join-nya, lalu berhenti — padahal dokumen ini sudah memuat ketujuh kolom target, grain balai × komoditi, dan batas tahunnya dengan benar. Untuk domain ini kolom yang relevan adalah `target_pengawasan`; enam kolom lain milik kegiatan lain dan tidak boleh dipakai. Pengetahuannya sudah ada di sini sejak awal; yang kurang adalah salinannya di context.

Pengukuran cakupan lengkapnya di dokumen `cakupan_context_vs_database` di direktori ini.
