# 08 — Capstone: Komoditi sebagai Sumbu Master

> **Ini dokumen paling penting untuk data understanding.** Komoditi (`komoditi`) BUKAN sekadar kategori — ia **menentukan perilaku HAMPIR SEMUA kolom lain**. Setiap kolom berperilaku beda per komoditi. Analisis apa pun yang tak dipisah per komoditi akan menyesatkan.

## Matriks master: 7 komoditi × semua dimensi

| Komoditi | baris / event | NIE unik | NIE kosong | `akhir` terisi | `balai` terisi | `pusat` terisi | media dominan | multi-produk? | `jenis_pembuat` | khusus |
|---|---|---|---|---|---|---|---|---|---|---|
| KOSMETIKA | 48.325 / 42.562 | 20.191 | 2.135 (4,4%) | ✓ 47.366 | ✓ 48.325 | ✓ 47.366 | ELEKTRONIK 82% | ✓ (sweep) | – | reversal MK→TMK tinggi |
| ROKOK | 40.031 / 40.031 | **0** | **40.031 (100%)** | ✓ 40.031 | ✓ 40.031 | ✓ 39.228 | **LUARRUANG 91%** | ✗ | – | cliff Jan 2025, 100% selesai |
| PRODUK PANGAN | 33.777 / 33.777 | 12.473 | 667 (2,0%) | **'Null' 100%** | ✓ 33.777 | 6.744 (20%) | ELEKTRONIK 60% | ✗ | **✓ 100%** | stop status 4, ketidaksesuaian |
| OBAT | 32.180 / 26.155 | 3.036 | 40 (0,1%) | ✓ 32.180 | ✓ 32.180 | 5.225 (16%) | ELEKTRONIK 48% | ✓ (sweep apotek) | – | pusat jarang terisi |
| OBAT TRADISIONAL | 19.003 / 19.003 | 3.745 | 3.970 (21%) | 'Null' 100% | ✓ 19.002 | ✓ 18.903 | ELEKTRONIK 77% | ✗ | – | TMK KRITIKAL 7.018 di pusat |
| SUPLEMEN KESEHATAN | 7.821 / 7.821 | 1.413 | 1.406 (18%) | 'Null' 100% | ✓ 7.821 | ✓ 7.796 | ELEKTRONIK 74% | ✗ | – | – |
| OBAT KUASI | 2.831 / 2.831 | 433 | 430 (15%) | 'Null' 100% | **'Null' 100%** | ✓ 2.817 (99,5%) | ELEKTRONIK 81% | ✗ | – | verdict HANYA di pusat |

## Cara user production mengelompokkan komoditi (dari 340 pertanyaan KAI)

User TIDAK memakai label database. Kelompok operasional mereka (frek ditunjukkan di `14`):

| Kelompok user | Komoditi DB | Frek user | Notes |
|---|---|---|---|
| **"obat"** / "obat keras" | `OBAT` | 90 (26,5%) | 1 komoditi saja; istilah farmasi |
| **"obat tradisional; suplemen kesehatan; obat kuasi"** | 3 komoditi | 28+21+22 | **SELALU digabung jadi satu** — persis Cluster B+C, direktorat OTSK (Lia Amalia) |
| **"kosmetik" / "kosmetika"** | `KOSMETIKA` | 31 (9,1%) | istilah tunggal |
| **"label pangan"** / "pangan" | `PRODUK PANGAN` | 25 (7,4%) | user sebut "label" |
| **"rokok"** | `ROKOK` | **1 (0,3%)** | nyaris tak ditanya — konsisten dengan cliff |

**Implikasi query**: bila user menulis *"tren iklan obat tradisional; suplemen kesehatan; obat kuasi"*, satu query:

```sql
SELECT komoditi, COUNT(DISTINCT id) AS event
FROM mv_pengawasan
WHERE komoditi IN ('OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN','OBAT KUASI')
GROUP BY 1;
```

**Terkait**: user natural grouping ini adalah **validasi eksternal** bahwa Cluster B+C memang satu dunia bisnis (lihat `09` aturan verdict & temuan direktur Lia Amalia).

## Tiga cluster perilaku verdict

Berdasarkan kolom mana yang terisi, komoditi terbagi **3 cluster**:

### Cluster A — `akhir` terisi (verdict final sinkron ETL)
- **ROKOK, OBAT, KOSMETIKA**
- `akhir` = `COALESCE(pusat, balai)` (lihat `09`)
- Compliance rate dihitung dari `akhir` AMAN untuk cluster ini

### Cluster B — `akhir`='Null', verdict di `balai`
- **PRODUK PANGAN, OBAT TRADISIONAL, SUPLEMEN KESEHATAN**
- Workflow komplit (selesai 999) TAPI `akhir` tak pernah sinkron
- Compliance rate dihitung dari `balai` (untuk pangan) atau `pusat` (untuk OT/SUPLEMEN, karena pusat terisi)

### Cluster C — `akhir`='Null', `balai`='Null', verdict HANYA di `pusat`
- **OBAT KUASI** (komoditi kontrarian)
- Verdict eksklusif di `pusat`, `balai` 100% 'Null'
- Compliance dihitung dari `pusat`

**Aturan praktis**: rumus compliance berbeda per komoditi. Satu rumus untuk semua = **salah**.

## Completion rate workflow per komoditi

Dihitung dari "apakah event punya baris status 999 di log" (bebas urutan tanggal):

| Komoditi | event main | punya 999 | % selesai |
|---|---|---|---|
| ROKOK | 40.031 | 40.031 | **100%** |
| OBAT KUASI | 2.831 | 2.826 | 99,8% |
| OBAT TRADISIONAL | 19.003 | 18.967 | 99,8% |
| SUPLEMEN | 7.821 | 7.805 | 99,8% |
| OBAT | 26.155 | 25.587 | 97,8% |
| KOSMETIKA | 42.562 | 33.918 | 79,7% |
| **PRODUK PANGAN** | **33.777** | **0** | **0%** |

**PRODUK PANGAN 0% punya baris 999** — workflow terminal di status 4, tidak pernah final.

### ⚠️ Klarifikasi penting: `akhir` ≠ kontingensi completion

Awalnya muncul teori "`akhir` terisi hanya saat workflow tuntas". **Teori ini SALAH.** Bukti:
- OT/SUPLEMEN/KUASI: **99,8% tuntas** TAPI `akhir`='Null' **100%**.

Jadi `akhir` diisi berdasarkan **aturan ETL per komoditi** (Cluster A vs B/C), bukan berdasarkan status completion.

## Reversal asimetris per komoditi (balai ↔ pusat berbeda putusan)

| Komoditi | balai MK→pusat TMK | balai TMK→pusat MK | total reversal | arah dominan |
|---|---|---|---|---|
| KOSMETIKA | **3.203** | 2.319 | 5.522 (11,4%) | pusat **lebih ketat** |
| ROKOK | 1.522 | 643 | 2.165 | pusat lebih ketat |
| OBAT | 219 | **1.835** | 2.054 | pusat **lebih lunak** |
| OBAT TRADISIONAL | 0 | 279 | 279 | pusat lebih lunak |
| SUPLEMEN | 0 | 103 | 103 | pusat lebih lunak |
| PRODUK PANGAN | 0 | 0 | 0 | (tak ada pusat-final) |
| OBAT KUASI | 0 | 0 | 0 | (tak ada balai) |

**Insight**: dua direktorat berbeda "strictness bias".
- **KOSMETIKA**: pusat mengoreksi MK→TMK (lebih ketat dari balai)
- **OBAT**: pusat mengoreksi TMK→MK (lebih lunak dari balai)

Ini indikator **budaya penilaian berbeda per direktorat**.

## Severity grade per komoditi (hanya di kolom pusat/balai)

| Komoditi | MK | TMK | TMK MAYOR | TMK MINOR | TMK KRITIKAL |
|---|---|---|---|---|---|
| **balai** | | | | | |
| PRODUK PANGAN | 26.518 | 0 | 3.828 | 3.431 | 0 |
| KOSMETIKA | 31.268 | 17.057 | 0 | 0 | 0 |
| ROKOK | 10.047 | 29.984 | 0 | 0 | 0 |
| OBAT | 27.226 | 4.954 | 0 | 0 | 0 |
| OT | 10.316 | 8.686 | 0 | 0 | 0 |
| SUPLEMEN | 5.800 | 2.021 | 0 | 0 | 0 |
| **pusat** | | | | | |
| OT | 9.963 | 0 | 906 | 1.016 | **7.018** (paling banyak KRITIKAL) |
| OBAT KUASI | 2.332 | 0 | 59 | 168 | 258 |
| PRODUK PANGAN | 4.892 | 0 | 1.042 | 810 | 0 |
| SUPLEMEN | 5.651 | 0 | 311 | 426 | 1.408 |
| ROKOK | 8.795 | 30.433 | 0 | 0 | 0 |
| KOSMETIKA | 29.910 | 17.456 | 0 | 0 | 0 |
| OBAT | 2.180 | 3.045 | 0 | 0 | 0 |

**Pola severity**:
- Hanya PRODUK PANGAN yang `balai` pakai MAYOR/MINOR (lainnya balai cuma MK/TMK).
- **TMK KRITIKAL HANYA di pusat** — eskalasi berat hanya bisa diputus pusat.
- **OT paling banyak KRITIKAL** di pusat (7.018) — severity tinggi terkonsentrasi di komoditi tradisional.

## Self-approve per komoditi (segregation of duties)

| Komoditi | event dgn draft+spv_1 | orang SAMA | % |
|---|---|---|---|
| OBAT KUASI | 2.831 | 2.831 | **100%** |
| OBAT TRADISIONAL | 19.003 | 19.003 | **100%** |
| SUPLEMEN | 7.821 | 7.821 | **100%** |
| ROKOK | 40.031 | 39.336 | 98,3% |
| OBAT | 26.155 | 25.681 | 98,2% |
| KOSMETIKA | 42.562 | 39.669 | 93,2% |
| PRODUK PANGAN | 33.777 | 30.843 | 91,3% |

Cluster B & C (yang macet/kecil) 100% self-approve. Cluster A (besar) 91-98%. **Institusional di semua komoditi.**

## Konsentrasi pemutus final per komoditi (key-person risk)

| Komoditi | pemutus utama (direktur) | n | % |
|---|---|---|---|
| ROKOK | Daryani, S.Si, M.Sc | 37.967 | ~95% |
| KOSMETIKA | Sulistyowati + Dra. Tita Nursjafrida | 25.603 + 19.909 | dua orang |
| OBAT | Rina Apriani + Franciska | 13.432 + 9.670 | dua orang |
| OBAT TRADISIONAL | **Lia Amalia** | 19.048 | 1 orang |
| OBAT KUASI | **Lia Amalia** | 2.836 | 1 orang (sama) |
| SUPLEMEN | **Lia Amalia** | 7.855 | 1 orang (sama) |

**Lia Amalia memutuskan 3 komoditi (29.739 event)**. Jika tidak available, 3 rantai direktorat OTSK macet. **Single point of failure.**

## Trend tahunan per komoditi (event unik, basis tgl_start)

| Komoditi | 2023 | 2024 | 2025 | 2026 YTD |
|---|---|---|---|---|
| KOSMETIKA | 2.973 | 13.548 | 15.653 | 10.388 |
| ROKOK | 18.817 | 21.015 | **199** | **15** |
| PRODUK PANGAN | 328 | 13.482 | 12.632 | 7.323 |
| OBAT | 6.315 | 7.440 | 7.697 | 4.703 |
| OBAT TRADISIONAL | 5.352 | 5.401 | 5.134 | 3.114 |
| SUPLEMEN | 1.885 | 2.175 | 2.106 | 1.654 |
| OBAT KUASI | 204 | 1.124 | 1.080 | 423 |

**Dua anomali temporal**:
1. **ROKOK cliff Jan 2025** — dari 1.665 event/Desember 2024 menjadi 18/Januari 2025 (drop 98,9% dalam satu bulan). Breakpoint kebijakan, bukan tren.
2. **PRODUK PANGAN ramp-up** — dari 328 (2023) menjadi 13.482 (2024). 41× lipat dalam setahun — komoditi baru diintensifkan.

## TMK rate ELEKTRONIK vs LUARRUANG per komoditi

| Komoditi | TMK rate ELEKTRONIK | TMK rate LUARRUANG |
|---|---|---|
| OBAT TRADISIONAL | 51,1% | 15,7% |
| KOSMETIKA | 38,9% | 17,1% |
| SUPLEMEN | 30,7% | 7,8% |
| PRODUK PANGAN | 26,2% | 12,9% |
| OBAT | 16,8% | 10,4% |
| ROKOK | – | 76,6% |

**Pola universal**: ELEKTRONIK selalu lebih rawan TMK daripada LUARRUANG. **ROKOK LUARRUANG 76,6% TMK** — paling tinggi (pelanggaran rokok di baliho dominan).

## Bukti SQL

Matriks master dihasilkan dari satu query:
```sql
SELECT komoditi,
  COUNT(*) AS baris,
  COUNT(DISTINCT id) AS event,
  COUNT(DISTINCT nama_balai) AS balai,
  COUNT(DISTINCT nie) FILTER (WHERE nie NOT IN ('','--','-')) AS nie_unik,
  COUNT(*) FILTER (WHERE nie IN ('','--','-')) AS nie_kosong,
  COUNT(*) FILTER (WHERE kesimpulan_penilaian_akhir<>'Null') AS akhir_isi,
  COUNT(*) FILTER (WHERE kesimpulan_penilaian_balai<>'Null') AS balai_isi,
  COUNT(*) FILTER (WHERE kesimpulan_penilaian_pusat<>'Null') AS pusat_isi,
  COUNT(*) FILTER (WHERE media_iklan='ELEKTRONIK') AS elektronik,
  COUNT(*) FILTER (WHERE media_iklan='MEDIA_LUARRUANG') AS luar_ruang,
  COUNT(*) FILTER (WHERE jenis_pembuat_iklan<>'') AS pembuat_isi
FROM mv_pengawasan GROUP BY 1 ORDER BY 2 DESC;
```

Lihat `13_sql_audit_trail.md` §08 untuk query-query pendukung lainnya.
