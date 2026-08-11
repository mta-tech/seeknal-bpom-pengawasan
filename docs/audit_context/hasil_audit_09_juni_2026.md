# Hasil Audit — 09 Juni 2026

**Sumber:** Verifikasi manual terhadap database NeonDB + Confluence Testing Page

**Tanggal:** 09 Juni 2026

**Database:** NeonDB (production)

**Confluence:** https://mtatech.atlassian.net/wiki/spaces/PD/pages/1083310360

---

## 1. Ringkasan Hasil Test

| Kategori | Total | Passed | Failed | Pass Rate |
|----------|-------|--------|--------|-----------|
| Pertanyaan Analitik | 38 | 36 | 2 | 94.74% |
| NIE/Permohonan/Forecast | 23 | 23 | 0 | 100% |
| **Total** | **61** | **59** | **2** | **96.72%** |

---

## 2. Detail 2 Test yang FAILED

### FAILED #15: Tren produk AMDK berdasarkan skala industri

| Item | System Jawab | Fakta Database |
|------|--------------|----------------|
| Status | ❌ FAILED | - |
| Alasan | "data sumber tidak tersedia" | **ADA** - 297 produk AMDK |
| Skala industri | Tidak ditemukan | **ADA** - di m_trader_rba |

**Masalah:** Query tidak JOIN ke tabel `m_trader_rba` untuk mendapatkan skala industri

**Query yang benar:**
```sql
SELECT 
  SUBSTRING(t.tanggal_aju::TEXT FROM 1 FOR 4) as tahun,
  CASE tr.skala_industri_id
    WHEN '1' THEN 'Mikro'
    WHEN '2' THEN 'Kecil'
    WHEN '3' THEN 'Menengah'
    WHEN '4' THEN 'Besar'
  END as skala_industri,
  COUNT(*) as jml
FROM t_produk_3_erba t
JOIN m_trader_rba tr ON t.trader_id::BIGINT = tr.trader_id
WHERE t.kode_kbli = '11051'
GROUP BY tahun, tr.skala_industri_id
ORDER BY tahun, tr.skala_industri_id;
```

**Hasil aktual:**
| Tahun | Skala Industri | Jumlah |
|-------|----------------|--------|
| 2024 | (kosong) | 54 |
| 2025 | Mikro | 145 |

---

### FAILED #17: Distribusi izin edar 3 dimensi (risiko, skala, tren)

| Item | System Jawab | Masalah |
|------|--------------|---------|
| Status | ❌ FAILED | - |
| Alasan | Jawaban tidak konsisten | Format tidak sesuai pertanyaan |

**Kesimpulan:** Perlu perbaikan parsing pertanyaan multi-dimensi

---

## 3. Verifikasi Pertanyaan Lainnya

### 3.1 Kode 3815 (Label Daerah Tidak Ditemukan)

| Item | Fakta |
|------|-------|
| Kode 3815 ada di database? | ✅ ADA - 1,586 records |
| Kode 3815 ada di data_dictionary? | ❌ TIDAK ADA |
| Provinsi 38 (Bangka Belitung) di dictionary? | ❌ TIDAK ADA |
| Provinsi 37 (Lampung) di dictionary? | ❌ TIDAK ADA |
| Total records terdampak | **3,707 records** |

**Kode daerah yang hilang dari data_dictionary:**

| Kode | Records | Provinsi |
|------|---------|----------|
| 3815 | 1,586 | Bangka Belitung |
| 3878 | 937 | Bangka Belitung |
| 3701 | 251 | Lampung |
| 3716 | 242 | Lampung |
| 3774 | 207 | Lampung |
| 3775 | 156 | Lampung |
| 3771 | 145 | Lampung |
| 3825 | 128 | Bangka Belitung |
| 3773 | 105 | Lampung |
| 3817 | 55 | Bangka Belitung |
| 3804 | 46 | Bangka Belitung |

**Status:** ⚠️ MASALAH SISTEMIK

---

### 3.2 Produk Susu Merk "Sekolah" yang Disetujui

| Item | Database Lama | Database Baru |
|------|---------------|---------------|
| Jumlah produk "Susu Sekolah" | 61 | 0 |
| Status 999 (disetujui) | 0 | 0 |
| Status lain (301, 304, 306, 307) | 61 | - |

**Status Confluence:** ✅ PASSED (jawaban: 25)

**Catatan:** Perlu verifikasi ulang - di NeonDB tidak ada data "Susu Sekolah"

---

### 3.3 Status Komitmen (Pembatalan)

| Kode | Deskripsi | Jumlah |
|------|-----------|--------|
| 0 | Draft Pemenuhan Komitmen | 8,813 |
| 7 | Komitmen Disetujui Dengan Catatan | 338 |
| 1 | Proses Penilaian Kembali Komitmen | 291 |
| 9 | Variasi Komitmen | 246 |
| **5** | **Komitmen Dibatalkan** | **200** |
| **8** | **Validasi Pembatalan** | **112** |

**Total Pembatalan (5+8):** 312 records

---

## 4. Perbandingan Database Lama vs Baru

| Table | Database Lama | Database Baru | Selisih |
|-------|---------------|---------------|---------|
| data_dictionary | 1,141 | 1,002 | -139 |
| forecast_permohonan | 111 | 10,000 | +9,889 |
| m_trader_rba | 14,687 | 10,000 | -4,687 |
| m_trader_rla | 10,284 | 10,000 | -284 |
| t_btp_3_erba | 6,716 | 10,000 | +3,284 |
| t_btp_3_erla | 9,782 | 10,000 | +218 |
| t_produk_3_erba | 246,053 | 10,000 | -236,053 |
| t_produk_3_rilis_erla | 412,622 | 10,000 | -402,622 |
| vw_pemeriksaan_bcc | - | 91,962 | NEW |
| vw_pengujian_bcc | - | 253,685 | NEW |

---

## 5. Tabel Baru di NeonDB

| Table | Rows | Deskripsi |
|-------|------|-----------|
| vw_pemeriksaan_bcc | 91,962 | Data pemeriksaan BCC |
| vw_pengujian_bcc | 253,685 | Data pengujian BCC |

---

## 6. Rekomendasi Perbaikan

| No | Temuan | Aksi | Priority |
|----|--------|------|----------|
| 1 | Query AMDK tidak JOIN ke m_trader_rba | Tambahkan JOIN | High |
| 2 | Data_dictionary tidak lengkap (kode 37, 38) | Tambah 11 kode daerah | High |
| 3 | Parsing pertanyaan multi-dimensi | Perbaiki logic | Medium |
| 4 | Produk Susu Sekolah tidak ada di NeonDB | Verifikasi ulang | Medium |
| 5 | UI belum format tabel | Enhancement | Low |

---

## 7. Kesimpulan

**Pass Rate:** 96.72% (59/61 test)

**Jumlah Temuan:** 5 item

**Status:** ❌ NEEDS FIX

**Rekomendasi Utama:**
1. Perbaiki query untuk pertanyaan yang membutuhkan JOIN
2. Update data_dictionary untuk kode daerah yang hilang
3. Perbaiki parsing pertanyaan multi-dimensi
4. Standarisasi format jawaban
