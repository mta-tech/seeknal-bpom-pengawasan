# Katalog Nilai Unik — database `pengawasan` (live 2026-08-13)

Dihasilkan dengan `GROUP BY` penuh atas seluruh baris (bukan sampel `categories` KAI).
Angka absolut bergeser karena ETL harian; **struktur nilainya** yang stabil.
Tanda ⟵ menandai nilai sentinel (kosong / `-` / `Null` / SQL NULL).

---
### mv_pengawasan

  **komoditi** — 7 nilai unik
      `KOSMETIKA` = 48,325 (26.3%)
      `ROKOK` = 40,031 (21.8%)
      `PRODUK PANGAN` = 33,777 (18.4%)
      `OBAT` = 32,180 (17.5%)
      `OBAT TRADISIONAL (OT)` = 19,003 (10.3%)
      `SUPLEMEN KESEHATAN` = 7,821 (4.3%)
      `OBAT KUASI` = 2,831 (1.5%)

  **media_iklan** — 5 nilai unik
      `ELEKTRONIK` = 98,079 (53.3%)
      `MEDIA_LUARRUANG` = 56,064 (30.5%)
      `CETAK` = 25,028 (13.6%)
      `MEDIA_LAIN` = 3,825 (2.1%)
      `` = 972 (0.5%) ⟵ kosong/sentinel

  **jenis_pembuat_iklan** — 3 nilai unik
      `` = 150,191 (81.6%) ⟵ kosong/sentinel
      `PELAKU USAHA` = 29,290 (15.9%)
      `PERORANGAN` = 4,487 (2.4%)

  **kesimpulan_penilaian_akhir** — 3 nilai unik
      `MK` = 67,920 (36.9%)
      `Null` = 64,391 (35.0%) ⟵ kosong/sentinel
      `TMK` = 51,657 (28.1%)

  **kesimpulan_penilaian_balai** — 5 nilai unik
      `MK` = 111,175 (60.4%)
      `TMK` = 62,702 (34.1%)
      `TMK MAYOR` = 3,828 (2.1%)
      `TMK MINOR` = 3,431 (1.9%)
      `Null` = 2,832 (1.5%) ⟵ kosong/sentinel

  **kesimpulan_penilaian_pusat** — 6 nilai unik
      `MK` = 63,723 (34.6%)
      `Null` = 55,889 (30.4%) ⟵ kosong/sentinel
      `TMK` = 50,934 (27.7%)
      `TMK KRITIKAL` = 8,684 (4.7%)
      `TMK MINOR` = 2,420 (1.3%)
      `TMK MAYOR` = 2,318 (1.3%)

### mv_pengawasan_log

  **trx_steps** — 16 nilai unik
      `pusat` = 317,862 (17.5%)
      `draft` = 267,474 (14.7%)
      `spv_1_pusat` = 245,915 (13.5%)
      `spv_1` = 238,298 (13.1%)
      `kepala_balai` = 228,955 (12.6%)
      `direktur` = 190,321 (10.5%)
      `selesai` = 183,962 (10.1%)
      `spv_2_pusat` = 118,670 (6.5%)
      `spv_2` = 16,622 (0.9%)
      `ditolak_spv_1` = 5,743 (0.3%)
      `ditolak_pusat` = 1,705 (0.1%)
      `ditolak_spv_1_pusat` = 932 (0.1%)
      `ditolak_kepala_balai` = 411 (0.0%)
      `ditolak_spv_2` = 148 (0.0%)
      `ditolak_direktur` = 123 (0.0%)
      `ditolak_spv_2_pusat` = 92 (0.0%)

  **status_label** — 10 nilai unik
      `MT - Pembuatan SPK` = 317,862 (17.5%)
      `Operator - Draft Sampling` = 267,469 (14.7%)
      `Deputi MT - Pembuatan SPK` = 245,931 (13.5%)
      `Supervisor - Verifikasi` = 238,297 (13.1%)
      `TPS - Penerimaan SPU` = 228,955 (12.6%)
      `Penguji - Entri Hasil Pengujian` = 190,321 (10.5%)
      `Sampel Rujukan Selesai` = 183,962 (10.1%)
      `Penyelia - Pembuatan SPP` = 118,654 (6.5%)
      `Supervisor 2 - Verifikasi` = 16,623 (0.9%)
      `<SQL NULL>` = 9,159 (0.5%) ⟵ kosong/sentinel

### mv_pengawasan_ketidaksesuaian

  **id_klasifikasi** — 6 nilai unik
      `2` = 3,346 (36.9%)
      `5` = 2,068 (22.8%)
      `3` = 1,866 (20.6%)
      `6` = 1,203 (13.3%)
      `1` = 499 (5.5%)
      `4` = 88 (1.0%)
