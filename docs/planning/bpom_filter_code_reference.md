# BPOM Filter Code Reference

**Diverifikasi langsung ke database `rpo_v2` — 2026-07-15**

File ini berisi mapping filter code yang TERVERIFIKASI untuk setiap domain query. Agent harus menggunakan kode-kode ini, BUKAN menebak dari deskripsi di `data_dictionary`.

---

## 1. Test Account Exclusion (WAJIB untuk semua query)

| Sistem | Filter | Keterangan |
|--------|--------|------------|
| ERBA | `trader_id::bigint NOT IN (5, 17, 50, 85)` | Akun uji coba internal BPOM |
| ERLA | `trader_id != 3384` | Akun uji coba ERLA |

**PENTING:** Selalu gunakan filter ini kecuali skenario secara eksplisit meminta SEMUA data (termasuk test accounts).

---

## 2. COUNT Method Rules

| Konteks | Kolom yang Di-hitung | Alasan |
|---------|---------------------|--------|
| NIE aktif / Pipeline | `COUNT(DISTINCT nomor)` | nomor = NIE unik, menghindari duplikasi versi |
| Permohonan masuk | `COUNT(DISTINCT produk_id)` | produk_id = permohonan unik |
| Trader/Perusahaan | `COUNT(DISTINCT trader_id)` | trader_id = perusahaan unik |

**PENTING:** Jangan gunakan `COUNT(*)` — ini menghitung baris termasuk duplikasi versi.

---

## 3. EXACT Codes — Tersedia di `data_dictionary`

### 3.1 Pipeline Status

**Scope ERLA (dikoreksi 2026-07-15):** tabel produk ERLA (`t_produk_3_rilis_erla`) memang beku —
hanya 7 nilai status yang pernah muncul (`0000, 0009, 0099, 0906, 0999, 9999` + 1 baris noise
`0501`), semua kode pipeline = 0 baris. **TAPI ini tidak berlaku untuk BTP ERLA**: `t_btp_3_erla`
masih punya data pipeline aktif (Draft `0910/0912` = 297, Bayar `0907` = 143, Ditolak System
`0908/0911/0918` = 727, dll). Jadi aturannya per-tabel, bukan per-sistem: pipeline produk = ERBA
saja; pipeline BTP = ERBA dan ERLA dua-duanya.

**Scope produk vs BTP (WAJIB dipetakan dua-duanya, jangan pilih diam-diam):** kata
"permohonan"/"produk" di pertanyaan pipeline ambigu terhadap BTP. Dampaknya material — untuk
Ditolak System, mengikutsertakan BTP menggeser jawaban +11,4% (742 ERBA + 727 ERLA di atas 12.820
produk). Jawaban harus menyatakan scope yang dipakai dan dari tabel mana datanya, atau menyajikan
kedua angka (produk-only dan produk+BTP) secara eksplisit.

| Tahap | Kode ERBA | Deskripsi | DB Count (DISTINCT nomor, no test) |
|-------|-----------|-----------|-------------------------------------|
| Evaluator | `0301, 0308` | Proses Penilaian, Proses Data Tambahan | 5.246 |
| Verifikator 1 | `0402, 0403, 0405, 0406, 0407` | Proses Verifikasi, Data Tambahan, Ditolak | 1.503 |
| Verifikator 2 | `0500, 0502, 0504` (live) | Proses Validasi, Verifikasi — **dictionary basi di sini**: dictionary mendaftar `0501,0502,0503`, tapi `0501`/`0503` = 0 baris live, sedangkan `0500`/`0504` (TIDAK ada di dictionary) justru yang dipakai. Menyertakan `0501,0503` tidak mengubah angka (0 baris) tapi framing "exact dari dictionary" salah untuk tahap ini. | 225 |
| Direktur | `0600, 0601, 0666` | Proses Validasi, Ditolak, Pembatalan | 467 |
| Data Tambahan (Eval) | `0308, 0402, 0407` | Cross-cutting dari sisi evaluator | 3.392 |
| Data Tambahan (Pendaftar) | `0901, 0914, 0915, 0917, 0951` | Cross-cutting dari sisi pendaftar | 3.744 |
| Data Tambahan (Gabungan) | `0308, 0402, 0407, 0901, 0914, 0915, 0917, 0951` | Kedua sisi | 7.136 |
| Draft | `0910, 0912` | Pendaftar - Draft | 26.229 |
| Bayar | `0903, 0907` | Pembayaran SPB/HPR | 6.913 |
| Ditolak System | `0908, 0911, 0918` | Ditolak Otomatis | 12.728 |
| Terbit | `0999` | Perizinan Berusaha Terbit | 136.576 |
| Perubahan | `0906` | Perubahan Produk | 23.170 |
| Dibatalkan | `0000, 0009, 0099` | Dihapus/Dicabut/Tidak Berlaku | 5.668 |
| **Total In-Process** | `NOT IN ('0999','0906','9999','0000','0009','0099')` | Semua yang belum final | 58.507 |

**SQL Template Pipeline:**
```sql
SELECT COUNT(DISTINCT nomor) 
FROM t_produk_3_erba 
WHERE status IN ('<kode_tahap>')  -- atau NOT IN untuk in-process
  AND trader_id::bigint NOT IN (5, 17, 50, 85);
```

### 3.2 Kategori Risiko (ERBA)

| Kode | Label | Kolom | DB Count (0999-only, no test) |
|------|-------|-------|-------------------------------|
| `301` | Tinggi | `kategori_dokumen` | 80.547 |
| `302` | Menengah Tinggi | `kategori_dokumen` | 11.888 |
| `303` | Menengah Rendah | `kategori_dokumen` | 41.199 |
| `304` | Tinggi Notifikasi | `kategori_dokumen` | 3.439 |

**Catatan:** 
- Untuk "NIE aktif" gunakan `status = '0999'` saja (bukan 3-status)
- Untuk "semua NIE termasuk perubahan" gunakan `status IN ('0999','0906','9999')`
- ERLA menggunakan kolom `jenis_dokumen` (bukan `kategori_dokumen`) dengan mapping berbeda

### 3.3 Status Produk (ERBA)

| Kode | Deskripsi | DB Count (3-status, no test) |
|------|-----------|------------------------------|
| `301` | Diproduksi Sendiri (MD / Produsen) | — |
| `302` | Impor | 45.166 |
| `304` | Berdasarkan Kontrak (Makloon) | 2.208 |
| `306` | Single MD Induk | 5.830 |
| `307` | Single MD Anak | — |

### 3.4 Jenis Permohonan

| Kode | Deskripsi | Kapan Digunakan |
|------|-----------|-----------------|
| `301` | Permohonan Baru | Query "NIE baru" atau "permohonan baru" |
| `302` | Perubahan Mayor | Query "perubahan mayor" |
| `303` | Perubahan Minor | Query "perubahan minor" |
| `304` | Daftar Ulang | Query "daftar ulang" |
| `305` | Permohonan Baru Notifikasi | Query "notifikasi" atau "baru notifikasi" |

**Aturan JP Filter:**
- Untuk query **"NIE baru yang terbit"** → tambahkan `jenis_permohonan IN ('301','305')`
- Untuk query **"tren NIE"** → periksa apakah note mengharuskan JP filter atau tidak
- Untuk query **"semua permohonan"** → JANGAN tambahkan JP filter

### 3.5 Status Komitmen (ERBA, MR-only `kategori_dokumen='303'`)

| Kode | Deskripsi | DB Count (no test) |
|------|-----------|---------------------|
| `0` | Draft Pemenuhan Komitmen | 27.386 |
| `1` | Proses Penilaian Kembali Komitmen | 9.113 |
| `2` | Verifikasi Pemenuhan Komitmen | — |
| `4` | Komitmen Disetujui | 2.709 |
| `5` | Komitmen Dibatalkan | 5.049 |
| `7` | Komitmen Disetujui Dengan Catatan | 11.783 |
| `8` | Validasi Pembatalan | 168 |
| `9` | Variasi Komitmen (khusus MR) | 4.066 |

**PENTING:** 
- Ada dua representasi: integer (`'5'`) dan decimal (`'5.0'`). Gunakan `ROUND(status_komitmen::numeric)::int::text = '<kode>'` untuk menangkap keduanya.
- **Case A** (NIE + komitmen): gunakan filter NIE status + komitmen
- **Case B** (lifecycle komitmen): JANGAN gunakan filter NIE status

### 3.6 BTP (Bahan Tambahan Pangan)

**Jenis BTP:**

| Kode | Deskripsi | DB Count (3-status, no test) |
|------|-----------|------------------------------|
| `47` | Pewarna | 617 |
| `48` | Antioksidan | 972 |

**Bentuk Sediaan:**

| Kode | Deskripsi | DB Count (3-status, no test) |
|------|-----------|------------------------------|
| `101` | Cair/Pasta | 2.345 |
| `102` | Serbuk | 1.840 |

**Jenis Produk BTP:**

| Kode | Deskripsi | DB Count (3-status, no test) |
|------|-----------|------------------------------|
| `301` | Tunggal | 714 |
| `302` | Campuran | 2.867 |

**SQL Template BTP:**
```sql
SELECT COUNT(DISTINCT nomor) 
FROM t_btp_3_erba 
WHERE jenis_btp = '<kode>'  -- atau bentuk_sediaan / jenis_produk_btp
  AND status IN ('0999', '0906', '9999')
  AND trader_id::bigint NOT IN (5, 17, 50, 85);
```

### 3.7 Kemasan

**ERBA:**

| Kode | Deskripsi | DB Count (3-status, no test) |
|------|-----------|------------------------------|
| `1` | Kaca atau Keramik | 14.451 |
| `2` | Plastik tunggal (monolayer) | 45.619 |
| `3` | Kertas tunggal | 2.399 |
| `4` | Komposit/laminat | 42.087 |
| `5` | Logam | 4.643 |
| `6` | Jenis kemasan lainnya | 794 |
| `7` | Ganda | 30.339 |

**ERLA:**

| Kode | Deskripsi |
|------|-----------|
| `31` | Kaca |
| `32` | Plastik |
| `37` | Komposit |
| `38` | Ganda |

### 3.8 Peruntukan (ERBA)

| Kode | Deskripsi | DB Count (3-status, no test) |
|------|-----------|------------------------------|
| `0201` | Pangan Peruntukan Khusus | 435 |
| `0000` | Pangan Umum | — |

### 3.9 Pemrosesan (ERBA)

| Kode | Deskripsi | DB Count (3-status, no test) |
|------|-----------|------------------------------|
| `301` | Organik | 211 |
| `302` | GMO | — |
| `304` | Iradiasi | — |

---

## 4. String Discovery — Kode Tidak di `data_dictionary`

Beberapa kode produk utama **tidak ada di data_dictionary**. Agent harus menemukannya via query ke tabel data.

### 4.1 Jenis Pangan (Product Segments)

| Segment | ERBA Code | ERLA Code | Discovery Method |
|---------|-----------|-----------|------------------|
| AMDK (Air Minum Dalam Kemasan) | `jenis_pangan = '1401'` | `jenis_pangan IN ('651','652','655')` | `nama_kategori ILIKE '%Air Minum Dalam Kemasan%'` |
| Garam Beryodium | `kategori_pangan = '120101000001'` | `kategori_pangan = '12010103'` | `nama_kategori ILIKE '%Garam Beryodium%'` |
| Formula Bayi | `jenis_pangan IN ('1301','1302')` | `jenis_pangan IN ('604','622')` | `nama_kategori ILIKE '%Formula Bayi%'` |

**PRODUCTION SQL PATTERNS (verified 2026-07-15 from Direktorat Registrasi Pangan Olahan):**

1. **JP filter WAJIB**: `jenis_permohonan IN ('301','305')` (ERBA) / `IN ('301','304','305')` (ERLA) untuk SEMUA query NIE
2. **Risiko Tinggi = 301+304** digabung (bukan terpisah)
3. **AMDK = 1401 single** (bukan 1401+1402)
4. **Garam = kategori_pangan='120101000001'** (specific sub-code)
5. **Komitmen = Case A** (NIE filter + JP 301 only)

**SQL Discovery Template:**
```sql
-- Cari kode untuk segment tertentu
SELECT DISTINCT jenis_pangan, nama_kategori 
FROM t_produk_3_erba 
WHERE nama_kategori ILIKE '%<keyword>%'
LIMIT 20;
```

### 4.2 Catatan Penting untuk Bayi

- `jenis_pangan=1301` = "Formula Bayi" (sub-kategori spesifik)
- Untuk "Produk Bayi & Anak" secara luas, perlu kode lain: 1303, 1305, 1309, 1310-1313, 1321-1322
- ERLA menggunakan kode berbeda: 604, 622, 624

---

## 5. Deprecated Columns — JANGAN DIGUNAKAN

| Kolom | Tabel | Alasan | Alternatif |
|-------|-------|--------|------------|
| `takaran_saji` | `t_produk_3_erba` | Deprecated | — |

**KOREKSI (2026-07-15): `klasifikasi_id` TIDAK deprecated.** Klaim lama di
`business_glossary.md` terbukti salah faktual — kolom ini terisi **100% dari 253.971 baris**
termasuk seluruh data 2026 (diverifikasi per-tahun ke DB), dan tabel §8 file ini sendiri
menunjukkan EXACT match GT justru via `klasifikasi_id` (Berklaim 256, Diet 35).
`business_glossary.md` sudah diperbaiki di varian `v5-predikat-trim` dan
`after-forecast-anomaly-refactor`.

**Decoy yang benar-benar harus dihindari (terverifikasi kuantitatif):**
- "Pangan Berklaim" = `klasifikasi_id='305'`, **bukan** `klaim='1'` — `klaim` adalah flag
  multi-value "punya klaim gizi/kesehatan apapun" (20.637 baris), overlap dengan populasi
  `klasifikasi_id='305'` (2.284 baris) hanya ~10%.
- "Organik" = `pemrosesan='301'`, **bukan** `klasifikasi_id='309'` — kode 309 memang berlabel
  "Organik" di dictionary tapi nyaris tak terpakai (38 baris vs 612 baris `pemrosesan='301'`).

---

## 6. Scope Rules

| Tipe Skenario | ERBA | ERLA | Gabungan |
|---------------|------|------|----------|
| Pipeline/Operasional | ✓ (satu-satunya) | ✗ (tidak ada data) | — |
| Risiko | ✓ (kategori_dokumen) | ✓ (jenis_dokumen, mapping beda) | ✓ (assert_any_of) |
| NIE Aktif | ✓ | ✓ | ✓ (assert_any_of) |
| Permohonan | ✓ | ✓ | ✓ |
| BTP | ✓ | ✓ | ✓ |
| Trader/Perusahaan | ✓ (m_trader_rba) | ✓ (m_trader_rla) | ✓ |

**Untuk skenario "Scope-agnostic":**
- Sistem harus bertanya: "mau ERBA saja, ERLA saja, atau gabungan?" — sesuai hard trigger
  `SEEKNAL_ASK.md` §2: **no default, no exceptions** (tidak ada fallback diam-diam ke gabungan;
  kalau klarifikasi tak terjawab, nyatakan pilihan yang hilang, jangan eksekusi).
- Fixture mungkin expect ERBA-only → cek `assert_any_of` groups saat menilai hasil test.

---

## 7. Status NIE: 0999-only vs 3-status

| Definisi | Filter | Kapan Digunakan |
|----------|--------|-----------------|
| **Terbit (0999-only)** | `status = '0999'` | Query "NIE yang sudah terbit" atau "izin edar aktif" |
| **Aktif (3-status)** | `status IN ('0999','0906','9999')` | Query "NIE aktif termasuk perubahan" |

**Perbedaan dampak (ERBA):**

| Kategori | 0999-only | 3-status | Selisih |
|----------|-----------|----------|---------|
| Tinggi | 80.547 | 83.344 | +3.5% |
| MR | 41.199 | 42.062 | +2.1% |
| MT | 11.888 | 12.087 | +1.7% |
| Notif | 3.439 | 3.685 | +7.2% |

**Aturan:**
- Jika note tidak menyebutkan filter status → gunakan **0999-only** (konsisten dengan mayoritas fixture)
- Jika note menyebutkan "status valid" atau "status aktif" → cek apakah fixture pakai 0999 atau 3-status
- Untuk tren waktu → biasanya 3-status (karena mencakup semua NIE yang pernah terbit di tahun tersebut)

---

## 8. Rekonsiliasi: Expected vs DB Aktual

Berikut perbandingan expected value dari fixture dengan DB aktual menggunakan metodologi yang benar (`COUNT(DISTINCT nomor)` + exclude test accounts):

### Pipeline

| Skenario | Expected | DB Aktual | Selisih | Status |
|----------|----------|-----------|---------|--------|
| EVAL-1 | 5.469 | 5.246 | -4.1% | Fixture basi |
| VERIF-1 | 1.695 | 1.503 | -11.3% | Fixture basi |
| VERIF2-1 | 159 | 225 | +41.5% | Fixture basi |
| DIR-1 | 872 | 467 | -46.5% | Fixture basi |
| BAYAR-1 | 6.988 | 6.913 | -1.1% | Fixture basi (minor) |
| DRAFT-TOTAL-1 | 24.959 | 26.229 | +5.1% | Fixture basi |
| TOTAL-1 (pipeline) | 58.339 | 58.507 | +0.3% | **HAMPIR EXACT** ✓ |
| DATATAMBAHAN-1 | 7.371 | 7.136 | -3.2% | Fixture basi |
| DITOLAK-SISTEM-1 | 12.278 | 12.728 | +3.7% | Fixture basi |

### Risiko (0999-only)

| Skenario | Expected | DB Aktual | Selisih | Status |
|----------|----------|-----------|---------|--------|
| Tinggi | 80.394 | 80.547 | +0.2% | **HAMPIR EXACT** ✓ |
| MR | 41.425 | 41.199 | -0.5% | **HAMPIR EXACT** ✓ |
| MT | 11.919 | 11.888 | -0.3% | **HAMPIR EXACT** ✓ |
| Notif | 3.500 | 3.439 | -1.7% | **HAMPIR EXACT** ✓ |

### Komitmen

| Skenario | Expected | DB Aktual | Selisih | Status |
|----------|----------|-----------|---------|--------|
| Draft (0) | 28.720 | 27.386 | -4.6% | Fixture basi |
| Disetujui Catatan (7) | 11.688 | 11.783 | +0.8% | **HAMPIR EXACT** ✓ |
| Proses (1) | 10.233 | 9.113 | -10.9% | Fixture basi |
| Dibatalkan (5) | 5.198 | 5.049 | -2.9% | Fixture basi |
| Disetujui (4) | 2.717 | 2.709 | -0.3% | **HAMPIR EXACT** ✓ |
| Variasi (9) | 4.099 | 4.066 | -0.8% | **HAMPIR EXACT** ✓ |
| Validasi Pembatalan (8) | 42 | 168 | +300% | **FIXTURE SALAH** |

### Klasifikasi (via klasifikasi_id — kolom VALID, lihat koreksi §5)

| Skenario | Expected | DB Aktual | Selisih | Status |
|----------|----------|-----------|---------|--------|
| Berklaim (305) | 256 | 256 | 0% | **EXACT** ✓ |
| Diet (310) | 35 | 35 | 0% | **EXACT** ✓ |

EXACT match ini sekaligus bukti dua hal: (a) `klasifikasi_id` adalah kolom yang benar dan hidup,
(b) metode hitung fixture adalah `COUNT(DISTINCT nomor)` + 3-status + exclude test account —
verifikasi lama yang memakai `COUNT(DISTINCT produk_id)` itulah yang membuat GT tampak "basi
26–76%" padahal tidak.

### BTP

| Skenario | Expected | DB Aktual | Selisih | Status |
|----------|----------|-----------|---------|--------|
| Antioksidan (48) | 942 | 972 | +3.2% | Fixture basi |
| Pewarna (47) | 600 | 617 | +2.8% | Fixture basi |
| Cair (101) | 2.274 | 2.345 | +3.1% | Fixture basi |
| Serbuk (102) | 1.796 | 1.840 | +2.4% | Fixture basi |
| Campuran (302) | 2.788 | 2.867 | +2.8% | Fixture basi |
| Tunggal (301) | 695 | 714 | +2.7% | Fixture basi |

---

## 9. SQL Template Lengkap

### 9.1 Query Pipeline (ERBA-only)
```sql
SELECT COUNT(DISTINCT nomor) AS jumlah
FROM t_produk_3_erba
WHERE status IN ('<kode_tahap>')
  AND trader_id::bigint NOT IN (5, 17, 50, 85);
```

### 9.2 Query Risiko per Kategori
```sql
SELECT dd.deskripsi, COUNT(DISTINCT t.nomor) AS jumlah
FROM t_produk_3_erba t
LEFT JOIN data_dictionary dd 
  ON dd.kode = t.kategori_dokumen 
  AND dd.kategori = 'KATEGORI_DOKUMEN'
WHERE t.status = '0999'  -- atau IN ('0999','0906','9999')
  AND t.trader_id::bigint NOT IN (5, 17, 50, 85)
GROUP BY 1 ORDER BY 2 DESC;
```

### 9.3 Query Tren per Tahun
```sql
SELECT EXTRACT(YEAR FROM NULLIF(tanggal,'')::timestamp)::int AS tahun,
       COUNT(DISTINCT nomor) AS jumlah
FROM t_produk_3_erba
WHERE kategori_dokumen = '<kode>'
  AND status IN ('0999', '0906', '9999')
  AND trader_id::bigint NOT IN (5, 17, 50, 85)
  AND NULLIF(tanggal,'')::timestamp >= '2000-01-01'
GROUP BY 1 ORDER BY 1;
```

### 9.4 Query Komitmen (Case B — Lifecycle)
```sql
SELECT COUNT(DISTINCT nomor) AS jumlah
FROM t_produk_3_erba
WHERE kategori_dokumen = '303'
  AND ROUND(status_komitmen::numeric)::int::text = '<kode>';
  -- TANPA filter status NIE
```

### 9.5 Query BTP
```sql
SELECT COUNT(DISTINCT nomor) AS jumlah
FROM t_btp_3_erba
WHERE jenis_btp = '<kode>'
  AND status IN ('0999', '0906', '9999')
  AND trader_id::bigint NOT IN (5, 17, 50, 85);
```

### 9.6 Query Gabungan ERBA+ERLA
```sql
SELECT COUNT(DISTINCT nomor) AS jumlah
FROM (
  SELECT nomor FROM t_produk_3_erba
  WHERE status IN ('0999', '0906', '9999')
    AND trader_id::bigint NOT IN (5, 17, 50, 85)
    AND <filter_era>
  UNION ALL
  SELECT nomor FROM t_produk_3_rilis_erla
  WHERE status IN ('0099', '0999', '0906', '9999')
    AND trader_id != 3384
    AND <filter_erla>
) x;
```

---

## 10. Pelengkap coverage — kategori & pola yang semula belum ter-mapping (verifikasi DB 2026-07-15)

Cross-check terhadap 96 fixture menemukan ~19 pola filter yang belum tercakup §1–§9. Semua
diverifikasi ke DB sebelum ditulis di sini. `data_dictionary` punya **tepat 21 kategori** —
string `kategori`-nya EXACT (termasuk yang berbentuk gabungan), jadi lookup TIDAK butuh `%xxx%`:

### 10.1 Kategori dictionary yang belum ter-mapping sebelumnya

| Konsep | `kategori` (string EXACT) | Kolom filter | Catatan verifikasi |
|---|---|---|---|
| Negara asal | `NEGARA_PABRIK dan NEGARA_PRODUSEN` | `negara_pabrik`, `negara_produsen` | 210 kode |
| Daerah/wilayah | `DAERAH_TRADER, DAERAH_PABRIK, DAERAH_PRODUSEN, PROVINSI_ID, KOTAKAB_ID` | `daerah_trader`, `daerah_pabrik`, `daerah_produsen`, `provinsi_id`, `kotakab_id` | 514 kode, satu kategori gabungan |
| Skala industri | `SKALA_INDUSTRI dan SKALA_INDUSTRI_ID` | `m_trader_rba.skala_industri_id` | `1` Mikro ·`2` Kecil ·`3` Menengah ·`4` Besar |
| Status usaha | `STATUS_USAHA` | `31` Produsen · `33` Importir | `m_trader_rba` juga punya boolean `is_status_industri_produsen`/`_importir` — trader bisa KEDUANYA; sebutkan sumber yang dipakai |
| Penolakan komitmen | `JENIS_PENOLAKAN_KOMITMEN` | `jenis_penolakan_komitmen` | ERBA-only, kode 1–10; **MULTI-VALUE pipe-separated** — 785 baris kombinasi (`'1\|3'`=91, `'1\|5'`=66, hingga `'1\|2\|3\|5'`) vs 4.549 single. KOREKSI atas klaim "single-value" sebelumnya — klaim itu salah karena sampling top-8-by-count (nilai pipe mulai muncul di count 91, tepat di bawah cutoff) dan separator output psql `\|` menyamarkan pipe di dalam nilai. Filter equality satu kode MELEWATKAN baris kombinasi — pakai `string_to_array(col,'\|') @> ARRAY['<kode>']` |
| Bidang usaha | `KODE_KBLI` | kolom KBLI di tabel trader | 95 kode |
| Sub-kemasan | `SUB_KEMASAN_ID` | kolom sub-kemasan | 37 kode |
| Akronim BPOM | `AKRONIM` | (label lookup saja) | 72 entri |

### 10.2 Koreksi kode yang kurang di §3.6–§3.7

- `BENTUK_SEDIAAN` lengkapnya 5 kode: `101` Cair/Pasta · `102` Serbuk · `103` Bahan Penolong ·
  `104` Gas · `105` Padat (§3.7 semula hanya 2).
- `JENIS_PRODUK_BTP` lengkapnya 4 kode: `301` Tunggal · `302` Campuran · `303` Perisa ·
  `304` Bahan Penolong (§3.6 semula hanya 2).
- `KEMASAN_ID` ERLA lengkapnya `31`–`39` (§3.7 semula hanya 4): `33` Karton/Kertas ·
  `34` Karton Laminat · `35` Kaleng · `36` Aluminium Foil · `39` Lain-lain, di samping
  `31` Kaca · `32` Plastik · `37` Komposit · `38` Ganda.

### 10.3 Pola identifier & atribut (bukan kode dictionary)

| Pola | Verifikasi | Pemakaian |
|---|---|---|
| `nomor LIKE 'MD %'` | 140.566 baris | produk dalam negeri |
| `nomor LIKE 'ML %'` | 57.034 baris | produk impor |
| `nomor LIKE 'ER%'` | 56.363 baris | id permohonan internal ERBA (nomor MD/ML belum terbit) |
| `jenis_dokumen = '000'` | 30.990 baris | "belum dikategorikan/belum punya kategori risiko" — kode dictionary sungguhan, BUKAN NULL |
| `kategori_dokumen` kosong/NULL | 1.160 baris | artefak data-quality — hanya untuk pertanyaan DQ eksplisit |
| `jenis_pangan` kosong | **0 baris** (ERBA) | fixture DQ-BELUM-KLASIFIKASI-1 **TIDAK perlu diperbaiki** — dicek ke YAML-nya: `assert_contains: ['tidak ada', 'klasifikasi']`, jadi nol baris justru jawaban yang diuji (by-design menguji keberanian menjawab "tidak ada") |
| `tanggal_exp` | ada di kedua tabel produk | filter expiry (EXPIRY-2027, LC-EXP-RISIKO); slice tahun pakai range, ERBA perlu cast |
| `nama ILIKE` / `merk ILIKE` | kolom ada | pencarian teks-bebas (SUSU-1 dll) — tidak ada kode; wajib sebutkan pattern yang dipakai di jawaban |

Padanan agent-facing (tanpa angka): `context/filter_code_reference.md` §4b–§4c di 3 varian.

### 10.4 Verifikasi live-usage untuk item yang semula "belum diverifikasi" (2026-07-15, batch 2)

| Item | Hasil live DB | Status |
|---|---|---|
| BTP `bentuk_sediaan='105'` (Padat) | 18 baris (juga `104` Gas = 2; plus kode tak terdokumentasi `214` = 1) | ✓ terpakai, kecil |
| BTP `jenis_produk_btp='303'` (Perisa) | 932 baris | ✓ terpakai, signifikan |
| BTP `jenis_produk_btp='304'` (Bahan Penolong) | 44 baris | ✓ terpakai |
| ERLA `kemasan_id` `33`–`36`, `39` | 10.030 / 7.497 / 15.641 / 30.145 / 910 baris | ✓ semua terpakai berat |
| `negara_pabrik` | top: `ID`=180.747, `CN`=19.537, `MY`=9.071 | ✓ dictionary `NEGARA_PABRIK dan NEGARA_PRODUSEN` |
| `daerah_trader` | top: `3175`=31.807, `3171`=21.715, `3174`=17.598 | ✓ dictionary kategori DAERAH gabungan |
| `status_usaha` (kolom di t_produk_3_erba) | `31`=180.747, `33`=73.224 | ✓ ada di level PRODUK, bukan cuma trader |
| `m_trader_rba` boolean | produsen-only=13.571 · importir-only=1.224 · **KEDUANYA=88** | ✓ konfirmasi trader bisa dua peran; GT PRODUSEN-1 (13.525/1.300) ≈ boolean+overlap |

Catatan penting `status_usaha`: tersedia di dua level — kolom produk (`status_usaha`) menghitung
PRODUK per jenis usaha, boolean trader (`is_status_industri_*`) menghitung PERUSAHAAN. Dua
pertanyaan berbeda; jangan dicampur.

---

## 11. Kalibrasi terhadap daftar pertanyaan analitik RESMI (spreadsheet Direktorat, sheet "list pertanyaan analitik") — 2026-07-15

Sumber: spreadsheet resmi (drive id `1qhv5CakwmkxYaWj2eCph6WqWKq2Dju5_`, gid 244884468).
Formula kanonik per metrik + nilai expected + catatan toleransi resmi ("Selama bukan satu
periode bias di bawah 5% tidak masalah").

### 11.1 Reproduksi formula resmi ke DB live (COUNT DISTINCT nomor, tanpa test-exclusion, sesuai SQL resmi)

| Metrik resmi | Formula | Nilai sheet | DB live 15 Jul | Drift |
|---|---|---:|---:|---:|
| NIE MR | `kategori_dokumen='303'` + 3-status + JP `('301','305')` | 39.018 | 42.013 | +7,7% |
| NIE MT | `'302'` + sama | 11.452 | 12.086 | +5,5% |
| NIE Tinggi | **`IN ('301','304')`** + sama | 77.382 | 86.224 | +11,4% |
| MR disetujui komitmen | + JP `'301'` + `status_komitmen IN ('4','7')` | 12.648 | 14.843 | +17,4% |

Semua drift searah ke atas → nilai sheet adalah **snapshot lama**; formulanya yang otoritatif.

### 11.2 Keputusan definisi yang diserap ke referensi agent (§5–§6 file context)

- JP filter resmi (ERBA `301,305` / ERLA `301,304,305`) = milik metrik dashboard resmi, BUKAN
  otomatis semua pertanyaan NIE — fixture UAT-OFF-1/3 justru meng-assert angka TANPA JP filter
  untuk pertanyaan free-form, dengan angka ber-JP dicatat sebagai "konflik". Dua bacaan beda
  15–30%; keputusan dinyatakan eksplisit / klarifikasi (RC-2 predikat.md tetap berlaku).
- **Risiko Tinggi resmi = 301+304 gabungan** (Tinggi mencakup Tinggi Notifikasi).
- **Komitmen**: metrik resmi "izin edar … komitmen" = Case A (+JP 301, disetujui = 4+7);
  wording lifecycle ("produk yang dibatalkan") tetap Case B (UAT-OFF-4 = 5.258 tanpa NIE
  filter). Kode 8 = fase TRANSIENT menuju 5 (42→3 dalam 9 hari, UAT-OFF-15).
- **AMDK ERBA = `jenis_pangan IN ('1401','1402')`** — diadjudikasi ke DB: 1401+1402 reproduksi
  EXACT angka fixture UAT-OFF-2 (2024 = 2.667), 1401-saja = 2.638 (gagal). Sheet resmi (lebih
  lama) masih 1401-saja — koreksi user menang, bukti di atas. Baris "AMDK = 1401 only" yang
  sempat tertulis di context sudah dikoreksi.
- **Garam beryodium = `kategori_pangan` dua sistem** (ERBA `'120101000001'` = 1.723 baris,
  ERLA `'12010103'` = 2.332) — BUKAN `jenis_pangan='1204'` (1.848, populasi beda).
- **Formula bayi ERLA = `604,622,624`** (fixture); catatan misclassification Gasol
  (UAT-OFF-9/12/13): kode segmen bisa berisi produk salah-klasifikasi → spot-check nama/merk
  untuk jawaban sensitif.
- **"Masih berlaku"** = status valid AND (tanggal_exp > hari-ini OR kosong); "dicabut" ≠
  "kadaluarsa" (UAT-OFF-6/10: seluruh 5.106 NIE dicabut ERBA masih dalam masa berlaku).
- **Dedup perusahaan lintas sistem**: trader_id ERBA ≠ ERLA; dedup by NAMA, prioritas ERBA.
- **`mv_produk_gabungan`/`mv_btp_gabungan` tidak ada di warehouse ini** (dikonfirmasi
  information_schema) — SQL kolom kanan sheet resmi menarget platform dashboard lain.
- Grouping kategori pangan resmi = `LEFT(kategori_pangan,2)`; sheet memuat referensi nama
  prefix 2-digit (07 bakeri, 08 daging, 13 PKGK, dst).
