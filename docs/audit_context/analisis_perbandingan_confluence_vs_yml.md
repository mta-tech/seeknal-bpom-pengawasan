# Analisis Perbandingan: Confluence vs YML Test Files

**Tanggal:** 09 Juni 2026

**Sumber:**
- Confluence: https://mtatech.atlassian.net/wiki/spaces/PD/pages/1083310360
- YML Folder: `seeknal/tests/v1/singleturn/`

---

## Ringkasan

| Sumber | Total | Status |
|--------|-------|--------|
| Confluence | 61 | 38 CB + 23 NIE |
| YML Files (original) | 61 | 38 CB + 23 NIE |
| YML Files (new Confluence version) | 22 | 19 CREATE + 3 UPDATE |
| **Total YML sekarang** | **83** | 61 original + 22 new |

---

## Status Pembuatan File

### 22 File Baru (Confluence Version) — SUDAH DIBUAT

| File | Status | Prompt | Expected Result (DB) |
|------|--------|--------|---------------------|
| NIE-2a.yml | ✅ CREATE | Berapa prediksi jumlah permohonan bulan Juni 2027? | N/A (forecast DMY-FOR) |
| NIE-3a.yml | ✅ CREATE | Berapa jumlah permohonan pangan olahan di sistem ERBA tahun 2023? | 2,467 |
| NIE-4a.yml | ✅ CREATE | Berapa jumlah NIE produk BTP di ERBA tahun 2023? | 2,604 |
| NIE-5a.yml | ✅ CREATE | Berapa jumlah NIE produk BTP di sistem ERLA tahun 2023? | 220 |
| NIE-6a.yml | ✅ CREATE | Berapa total NIE pangan olahan di sistem ERBA yang terbit tahun 2022? | 263 |
| NIE-7a.yml | ✅ CREATE | Berapa total NIE pangan olahan yang terbit tahun 2022 dari semua sistem registrasi? | 1,470 |
| NIE-8a.yml | ✅ CREATE | Berapa total NIE pangan olahan yang terbit tahun 2023 dari semua sistem registrasi? | 2,754 |
| NIE-9a.yml | ✅ CREATE | Berapa jumlah NIE produk Garam Beryodium di ERBA tahun 2023? | 0 (data hanya 2024-2025) |
| NIE-10a.yml | ✅ CREATE | Berapa jumlah NIE Risiko Menengah Rendah di ERBA tahun 2023? | 700 |
| NIE-11a.yml | ✅ CREATE | Berapa NIE MR dibatalkan komitmen tahun 2023? | 155 |
| NIE-12a.yml | ✅ CREATE | Berapa NIE MR disetujui komitmen tahun 2023? | 103 |
| NIE-13a.yml | ✅ CREATE | Berapa jumlah NIE Risiko Menengah Tinggi di ERBA tahun 2023? | 110 |
| NIE-14a.yml | ✅ CREATE | Berapa jumlah NIE per kategori risiko di ERBA tahun 2023? | 301:1794, 302:110, 303:700 |
| NIE-15a.yml | ✅ CREATE | Berapa jumlah NIE pangan olahan per skala industri di ERBA tahun 2023? | 1:1071, 2:138, 4:64 |
| NIE-16a.yml | ✅ CREATE | Berapa jumlah NIE Risiko Tinggi di ERBA tahun 2023? | 1,794 |
| NIE-17a.yml | ✅ CREATE | Berapa total NIE pangan olahan di sistem ERBA yang terbit tahun 2023? | 2,604 |
| NIE-18a.yml | ✅ CREATE | Berapa jumlah NIE pangan olahan untuk UMKM di ERBA tahun 2023? | 1,209 |
| NIE-19a.yml | ✅ CREATE | Berapa total permohonan pangan olahan tahun 2023 dari semua sistem registrasi? | 2,754 |
| NIE-20a.yml | ✅ CREATE | Berapa permohonan per jenis permohonan di ERBA tahun 2023? | 301:2,366, 302:101 |
| NIE-21a.yml | ✅ CREATE | Tampilkan query SQL untuk hitung total NIE ERBA 2023 | Meta (SQL transparency) |
| NIE-22a.yml | ✅ CREATE | Berapa jumlah NIE produk AMDK di ERBA tahun 2023? | 51 |
| NIE-23a.yml | ✅ CREATE | Bagaimana tren NIE pangan olahan di ERBA dari 2020-2023? | 2022:263, 2023:2,604 |

---

## Perbedaan Old vs New (Same Context)

| Old File | New File | Perbedaan | Expected Result |
|----------|----------|-----------|-----------------|
| NIE-2: "Prediksi forecast tahun 2027" | NIE-2a: "Berapa prediksi jumlah permohonan bulan Juni 2027?" | Lebih spesifik (bulan Juni) | Sama (2027, forecast) |
| NIE-3: "Berapa jumlah permohonan?" | NIE-3a: "Berapa jumlah permohonan pangan olahan di sistem ERBA tahun 2023?" | Lebih spesifik (ERBA, 2023) | Beda (generic vs specific) |
| NIE-4: "Berapa NIE BTP tahun 2023?" | NIE-4a: "Berapa jumlah NIE produk BTP di ERBA tahun 2023?" | Tambah "ERBA" | Beda (all vs ERBA only) |
| NIE-10: "Apa itu NIE MR?" | NIE-10a: "Berapa jumlah NIE MR di ERBA tahun 2023?" | Definisi vs Kuantitatif | Beda total |
| NIE-13: "Apa itu NIE MT?" | NIE-13a: "Berapa jumlah NIE MT di ERBA tahun 2023?" | Definisi vs Kuantitatif | Beda total |
| NIE-16: "Apa itu NIE T?" | NIE-16a: "Berapa jumlah NIE T di ERBA tahun 2023?" | Definisi vs Kuantitatif | Beda total |

---

## Data Verification (NeonDB 2026-06-09)

### Kategori Dokumen (Risiko)
| Kode | Deskripsi | Jumlah (2023) |
|------|-----------|---------------|
| 301 | Tinggi | 1,794 |
| 302 | Menengah Tinggi | 110 |
| 303 | Menengah Rendah | 700 |

### Skala Industri
| Kode | Deskripsi | Jumlah (2023) |
|------|-----------|---------------|
| 1 | Mikro | 1,071 |
| 2 | Kecil | 138 |
| 4 | Besar | 64 |
| NULL | Tidak diketahui | 155 |

### Status Komitmen
| Kode | Deskripsi | Jumlah (2023, MR) |
|------|-----------|-------------------|
| 5 | Dibatalkan | 155 |
| 4, 7 | Disetujui | 103 |

---

## Rekomendasi

1. **File lama tetap dipertahankan** — untuk backward compatibility
2. **File baru (suffix "a")** — mengikuti format Confluence
3. **Tolerance ±5%** — karena data berubah setiap hari
4. **Sinkronisasi expected result** — old dan new dengan konteks sama harus konsisten
