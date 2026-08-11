# UAT-OFF-15 — Analisis Hasil Uji Coba

> **Tanggal uji:** 2026-07-01  
> **Variant:** `pre-refactor-1dd55d9-notsystemprompt`  
> **File hasil:** `variant_compare_results_20260701_020450.json` (UAT-5) dan `variant_compare_results_20260701_021418.json` (UAT-6)  
> **Database:** `rpo_v2` via SSH tunnel localhost:5533

---

## Ringkasan Eksekutif

| Run | Skenario | Passed | Failed | Catatan |
|-----|----------|--------|--------|---------|
| UAT-5 | 15 | 10 | 5 | 5 gagal semua karena clarification flow |
| UAT-6 | 15 | 14 | 1 | Perbaikan besar; hanya 1 tersisa |

**Temuan utama:** Semua kegagalan bukan salah jawaban *secara logika SQL*, melainkan **perbedaan filter scope** antara jawaban agent dan ekspektasi test setelah trigger clarification otomatis.

---

## Pola Kegagalan: Clarification Flow

Setiap skenario memiliki 2 turn:
1. **Turn 1** — Agent menerima prompt user → meminta clarification (`ask_user`)
2. **Turn 2** `[AUTO]` — Harness otomatis memilih opsi → agent menghasilkan jawaban akhir

Jawaban Turn 1 + Turn 2 adalah **satu kesatuan** menjawab prompt asli. Yang di-evaluasi adalah jawaban akhir di Turn 2.

---

## Detail 5 Skenario Gagal (UAT-5)

### UAT-OFF-1 — NIE Terbit Mei 2026

| | Detail |
|---|---|
| **Prompt** | `berapa NIE yang terbit selama bulan Mei 2026?` |
| **Clarification** | Agent bertanya: "Data dari sistem mana?" → Harness pilih `ERBA (RPO Baru)` |
| **Expected** | `5.085` (SEMUA jenis_permohonan) |
| **Actual** | `3.775` |
| **Mengapa salah** | Agent menambahkan filter `jenis_permohonan IN (301, 305)` (baru + notifikasi saja). Padahal expected mencakup SEMUA jenis permohonan (301/302/303/304/305). Filter agent **terlalu sempit** — mengecualikan perubahan mayor (302), minor (303), dan daftar ulang (304). |

```
Expected query (benar):
  SELECT COUNT(DISTINCT nomor) FROM t_produk_3_erba
  WHERE tanggal >= '2026-05-01' AND tanggal < '2026-06-01'
    AND status IN ('0999','0906','9999')
  -- tanpa filter jenis_permohonan → 5.085

Agent query (terlalu sempit):
  ... AND jenis_permohonan IN ('301','305')  → 3.775
```

---

### UAT-OFF-2 — AMDK 2024–2025

| | Detail |
|---|---|
| **Prompt** | `Kita ambil data ereg RBA saja. Tampilkan jumlah persetujuan produk AMDK pada tahun 2024 sampai 2025` |
| **Clarification** | Tidak ada clarification (langsung query) |
| **Expected** | `2024=2.301`, `2025=2.049` |
| **Actual** | `2024=2.208`, `2025=1.952` |
| **Mengapa salah** | Agent menambahkan filter `jenis_permohonan IN (301, 305)` (baru + notifikasi). Expected mencakup SEMUA jenis permohonan. Filter **terlalu sempit**, kehilangan ~93 produk/tahun dari perubahan dan daftar ulang. |

```
DB verification (semua JP, expected):
  2024 = 2.301 ✓
  2025 = 2.049 ✓

Agent (JP 301/305 saja):
  2024 = 2.208  (selisih -93)
  2025 = 1.952  (selisih -97)
```

---

### UAT-OFF-3 — NIE Terbit 2025

| | Detail |
|---|---|
| **Prompt** | `berapa jumlah NIE yang terbit di tahun 2025 di aplikasi ereg RBA` |
| **Clarification** | Agent bertanya: "Cakupan produk?" + "Definisi terbit?" → Harness pilih `Pangan Olahan; Baru Diterbitkan di 2025` |
| **Expected** | `53.535` |
| **Actual** | `45.087` |
| **Mengapa salah** | Agent menambahkan filter `jenis_permohonan IN (301, 305)` + exclude test accounts (`trader_id NOT IN (5,17,50,85)`). Expected mencakup SEMUA jenis permohonan. Filter **terlalu sempit**, kehilangan ~8.448 NIE dari perubahan/daftar ulang. |

```
DB verification:
  Semua JP (expected): 53.535 ✓
  JP 301/305 saja:      45.087 ✓ (selisih -8.448)
```

---

### UAT-OFF-5 — Total NIE Formula Bayi

| | Detail |
|---|---|
| **Prompt** | `berapa jumlah produk formula bayi yang telah memiliki izin edar` |
| **Clarification** | Agent bertanya: "Sistem mana? Cakupan? Status?" → Harness pilih `ERBA; Formula Bayi saja; Semua NIE pernah terbit` |
| **Expected** | `917` (ERBA 103 + ERLA 814) |
| **Actual** | `60` |
| **Mengapa salah** | Agent hanya query **ERBA** (sesuai clarification) + filter `status IN (0999,0906,9999)` (valid saja). Expected mencakup **ERBA + ERLA** gabungan dan SEMUA status (termasuk expired/dicabut). Perbedaan **ganda**: (1) scope sistem terlalu sempit, (2) filter status terlalu ketat. |

```
DB verification:
  ERBA (semua status, all-time): 103
  ERLA (semua status, all-time): 814
  Total: 917 ✓

  Agent (ERBA + status valid): 60
  Selisih: -857 (hilang: 43 ERBA non-valid + 814 ERLA)
```

---

### UAT-OFF-9 — Formula Bayi Dicabut

| | Detail |
|---|---|
| **Prompt** | `apakah ada izin edar formula bayi yang dibatalkan` |
| **Clarification** | Agent bertanya: "Sistem? Cakupan? Status?" → Harness pilih `ERBA; Formula Bayi Saja` |
| **Expected** | `10` (ERLA, semua merk Gasol — misclassified) |
| **Actual** | `0` |
| **Mengapa salah** | Agent hanya query **ERBA** (sesuai clarification). Padahal 10 record yang dibatalkan ada di **ERLA** (jenis_pangan 622/604/624). Di ERBA memang 0 formula bayi dicabut. Scope **terlalu sempit** — clarification "ERBA" menutup data ERLA yang justru berisi jawaban. |

---

## Perbaikan dari UAT-5 → UAT-6

Dari 5 gagal, 4 membaik di UAT-6:

| Skenario | UAT-5 | UAT-6 | Perbaikan |
|----------|-------|-------|-----------|
| OFF-1 | 3.775 ❌ | 5.085 ✅ | Agent berhenti filter JP → semua JP |
| OFF-2 | 2.208/1.952 ❌ | 2.301/2.049 ✅ | Agent berhenti filter JP |
| OFF-3 | 45.087 ❌ | 53.535 ✅ | Agent berhenti filter JP |
| OFF-5 | 60 ❌ | 26 ❌ | Masih salah (scope berbeda) |
| OFF-9 | 0 ❌ | 10 ✅ | Agent query ERLA juga |

**Yang tersisa gagal di UAT-6:**

### UAT-OFF-5 — Masih Gagal (26 vs 917)

| | Detail |
|---|---|
| **UAT-6 Actual** | `26` |
| **Expected** | `917` |
| **Mengapa masih salah** | Agent tetap hanya query ERBA + filter `jenis_permohonan 301/305` + status valid + test accounts excluded. Scope dan filter tetap **terlalu sempit**. |

---

## Catatan: Drift Data (Snapshot vs Live)

Expected values di test berdasarkan snapshot **26 Jun 2026**. DB live per **1 Jul 2026** sedikit berbeda karena data terus bertambah:

| Skenario | Expected (26 Jun) | DB Live (1 Jul) | Selisih | Penyebab |
|----------|-------------------|-----------------|---------|----------|
| OFF-5 (Total FB) | 917 (ERBA 103 + ERLA 814) | 925 (ERBA 107 + ERLA 818) | +8 | Registrasi baru |
| OFF-9 (FB Dicabut) | 10 (ERLA) | 11 (ERLA) | +1 | NUTRAMIGEN LGG baru (status 0000) |

Drift ini tidak mempengaruhi analisis karena penyebab kegagalan adalah **filter scope**, bukan angka.

---

## Ringkasan Akar Penyebab

| # | Akar Penyebab | Skenario Terdampak | Pola |
|---|---|---|---|
| 1 | **Filter JP terlalu sempit** | OFF-1, OFF-2, OFF-3 | Agent tambah `jenis_permohonan IN (301,305)` padahal test ingin SEMUA JP |
| 2 | **Scope sistem terlalu sempit** | OFF-5, OFF-9 | Agent hanya query ERBA padahal data ada di ERLA |
| 3 | **Filter status terlalu ketat** | OFF-5 | Agent filter `status IN (0999,0906,9999)` padahal test ingin SEMUA status (termasuk expired/dicabut) |
| 4 | **Clarification mempersempit scope** | Semua yang gagal | Harness auto-select memilih opsi yang menutup data relevan |

---

## Rekomendasi

1. **Clarification harness** — Opsi clarification harus mempertahankan scope yang mencakup expected data (misal: "Gabungan" bukan "ERBA saja")
2. **Agent prompt** — Kurangi kecenderungan menambah filter `jenis_permohonan` otomatis; biarkan SEMUA JP kecuali user eksplisit minta filter
3. **Test assertion** — Tambah `assert_not_contains` untuk memastikan agent TIDAK menambah filter yang tidak diminta
4. **Expected values** — Pertimbangkan untuk mendokumentasikan expected per kombinasi scope/filter agar test lebih robust
