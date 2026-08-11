# Audit Report — Multiturn Test Run 18 Juni 2026
**Test File:** `seeknal/tests/outputs/2026-06-18/v1/multiturn_results_20260618_043252.json`  
**Test Mode:** multiturn-v3  
**Run Timestamp:** 2026-06-18T04:32:52 UTC  
**Skenario Total:** 238  
**Audit Date:** 18 Juni 2026  

---

## 1. Ringkasan Eksekutif

Test run ini adalah **pengujian pertama pasca implementasi** dari dua planning doc utama:
- `2026-06-17-dictionary-grounded-code-translation.md` — perbaikan code translation
- `2026-06-18-llm-forecaster-skill.md` — implementasi bpom-forecaster skill

### Hasil Permukaan (Misleading jika Dibaca Mentah)

| Kategori | Jumlah | % |
|---|---|---|
| PASS | 143 | 60.1% |
| FAIL | 95 | 39.9% |

### Realita Setelah Diaudit

Dari 143 PASS: **45 skenario adalah cache dari sesi sebelumnya** — tidak dieksekusi ulang pada run ini. Angka sebenarnya:

| Kategori Sebenarnya | Jumlah | % dari yang Dijalankan |
|---|---|---|
| Cached / Skipped (tidak dijalankan) | 45 | — |
| **Dari 193 yang benar-benar dijalankan:** | | |
| Infra Crash — tool error sebelum agent bisa berpikir | 8 | 4.1% |
| Warehouse gagal konek → jawaban gagal | 40 | 20.7% |
| Warehouse gagal konek → fallback berhasil (PASS) | 2 | 1.0% |
| Warehouse konek, SQL jalan, jawaban SALAH | 54 | 28.0% |
| **Genuine PASS — konek, SQL jalan, jawaban BENAR** | **96** | **49.7%** |

**Pass rate sesungguhnya dari yang dijalankan: 49.7%** — hampir separuh, bukan 60%.

**Faktor dominan kegagalan bukan logic agent, tapi koneksi warehouse** — 40 skenario (21%) gagal semata karena database tidak bisa diakses.

---

## 2. Temuan #1: Infra Crash — 8 Skenario Gagal Total

### Apa yang Terjadi

Tool `execute_sql` atau `execute_python` melebihi batas retry sebelum agent sempat menghasilkan apapun. `llm_requests = 0`, `tool_calls = 0`, tidak ada SQL, tidak ada jawaban. Agent tidak pernah bisa bergerak.

```
[ERROR] UnexpectedModelBehavior: Tool 'execute_sql' exceeded max retries count of 1
[ERROR] UnexpectedModelBehavior: Tool 'execute_python' exceeded max retries count of 1
```

### Skenario Terdampak

| Scenario ID | Tool Crash | Elapsed | Keterangan |
|---|---|---|---|
| CB-22 | `execute_python` | 371.98s | Pertanyaan registrasi berdasarkan lokasi pabrik 2025 |
| CB-28 | `execute_sql` | **21.2s** | Wilayah AMDK — crash sangat cepat |
| CB-30 | `execute_sql` | **22.03s** | Wilayah UMKM terbanyak — crash sangat cepat |
| UAT-BAYI-JP-BREAKDOWN-1 | `execute_python` | ~300s | Formula bayi JP breakdown |
| UAT-DQ-BELUM-RISIKO-1 | `execute_python` | ~324s | Data quality check risiko |
| UAT-JP-BARU-VS-REVISI-1 | `execute_sql` | ~400s | Permohonan baru vs revisi |
| UAT-KOMITMEN-DRAFT-MR-1 | `execute_sql` | ~350s | Draft komitmen MR |
| UAT-SKALA-1 | `execute_sql` | ~350s | Perusahaan mikro |

### Analisis

CB-28 dan CB-30 dengan elapsed hanya 21-22 detik menunjukkan bahwa **crash terjadi di first tool call** — bukan setelah agent mencoba lama. Ini menandakan masalah di level koneksi awal (connection timeout atau authentication failure yang langsung gagal).

CB-22 yang elapsed-nya 371 detik tetapi tool_calls = 0 menunjukkan ada overhead di sisi framework sebelum tool pertama dipanggil.

### Dampak pada Analisis

8 skenario ini **tidak bisa dievaluasi untuk kualitas agent** — mereka gagal di level infrastruktur. Failure-nya bukan cerminan kemampuan reasoning agent.

---

## 3. Temuan #2: Warehouse Connection — Problem Sistemik Terbesar

### Skala Masalah

**40 dari 193 skenario yang dijalankan** (21%) gagal karena warehouse tidak bisa diakses. Ini adalah **root cause terbesar** dari seluruh kegagalan dalam run ini.

Ditambah 2 skenario yang tetap PASS meskipun warehouse gagal (dengan fallback methodology).

**Total terdampak koneksi: 42 skenario.**

### Bagaimana Koneksi Bekerja (dan Gagal)

Sistem menggunakan DuckDB sebagai query engine dengan PostgreSQL extension untuk menjembatani ke database `rpo_v2`. Ada **dua mekanisme akses**:

**Mekanisme A (yang seharusnya): Catalog pre-attached**
```sql
SELECT * FROM warehouse.public.t_produk_3_erba LIMIT 1;
```
Ini bekerja hanya jika catalog `warehouse` sudah ter-attach saat sesi DuckDB dimulai.

**Mekanisme B (fallback yang ditemukan agent): Manual ATTACH**
```sql
INSTALL postgres;
LOAD postgres;
ATTACH 'postgresql://readonly_user:read_only_seeknal@host.docker.internal:5533/rpo_v2' 
  AS warehouse (TYPE POSTGRES, READ_ONLY);
```

Atau menggunakan env var:
```sql
ATTACH 'env:WAREHOUSE_URL' AS warehouse (TYPE POSTGRES, READ_ONLY);
```

### Pola: Apa yang Terjadi Saat Catalog Tidak Ter-Attach

Ketika agent tidak bisa menemukan `warehouse.public.*`, ia masuk ke **schema discovery loop** — mencoba puluhan cara berbeda untuk menemukan tabel. Ini menghabiskan hampir seluruh tool call budget.

**Data dari seluruh run:**

| Kategori SQL | Jumlah | Persentase |
|---|---|---|
| **Schema discovery / table hunting** | **2.371** | **78.1%** |
| Business query sesungguhnya | 667 | 21.9% |
| **Total SQL dieksekusi** | **3.038** | 100% |

**Top schema discovery queries yang diulang-ulang:**

| Query | Frekuensi |
|---|---|
| `SELECT * FROM duckdb_databases()` | 72x |
| `SELECT * FROM information_schema.tables` | 72x |
| `SHOW ALL TABLES` | 68x |
| `SELECT schema_name FROM information_schema.schemata` | 61x |
| `SELECT * FROM information_schema.schemata` | 52x |
| `PRAGMA show_databases` | 50x |
| `SELECT * FROM pg_catalog.pg_tables` | 44x |
| `SELECT * FROM duckdb_tables()` | 33x |

Artinya: di **setiap skenario**, agent rata-rata menjalankan 12-15 query hanya untuk mencari "di mana database saya?" sebelum bisa menulis satu pun business query.

### Dua Hasil yang Berbeda dari Koneksi Gagal

**Hasil A: Fallback berhasil (2 skenario PASS)**

CAP-2 (Top 10 kategori pangan) dan FORECAST-5 berhasil PASS meskipun warehouse tidak ter-attach. Agent memberikan:
- Metodologi yang benar
- SQL template yang bisa dijalankan
- Penjelasan kontekstual yang cukup

Test assertion untuk kedua skenario ini ternyata memeriksa metodologi, bukan angka aktual — sehingga fallback memadai.

**Hasil B: Gagal jawab (40 skenario FAIL)**

Agent mencoba koneksi, gagal, lalu memberikan satu dari dua respons:
1. *"Koneksi ke database warehouse tidak tersedia di sesi ini"* — jujur tapi tidak berguna
2. Menggunakan angka dari dokumentasi/konteks sebagai pengganti — ini berbahaya

Contoh tipe berbahaya (UAT-ERLA-1):
```
Expected: 400.784 (dari live query dengan filter benar)
Agent answer: 412.607
```
Agent menggunakan angka `412.607` yang ada di `data_architecture.md` sebagai "row count" 
dokumentasi — bukan dari query live. Angka dokumentasi lebih besar karena tidak menerapkan 
filter test account dan tahun tidak valid.

### Skenario Warehouse Fail yang Paling Signifikan

| Scenario | Alasan Penting |
|---|---|
| FORECAST-1 | Semua 7-block output hilang — tidak bisa forecast tanpa data |
| UAT-MT-1 | MT = 11.919 tidak bisa dibuktikan — agent memberikan penjelasan konseptual |
| UAT-NIE25-1 | Total NIE 2025 = 57.206 tidak bisa dikonfirmasi |
| UAT-TOTAL-1 | Total NIE aktif = 312.337 tidak bisa dikonfirmasi |
| UAT-INVESTIGASI-KOMITMEN-1 | Semua 4 angka komitmen hilang |

---

## 4. Temuan #3: SQL Quality — Analisis Mendalam

### 4.1 Kasus yang Terhubung tapi Salah (54 Skenario)

Ini adalah kategori paling instruktif: warehouse berhasil diakses, SQL berhasil dieksekusi, tapi jawabannya tetap salah. Ini murni **logic dan code resolution error**.

### 4.2 Pola A: ERBA-Only Padahal Harus UNION ERLA

**Kasus: UAT-AMDK-1**

| | Nilai |
|---|---|
| Expected | **2.166** (ERBA 1.743 + ERLA 423) |
| Agent answer | **1.743** — ERBA saja |

SQL yang digunakan:
```sql
SELECT COUNT(DISTINCT nomor) as jumlah_nie
FROM warehouse.public.t_produk_3_erba
WHERE tanggal::timestamp >= '2023-01-01' AND tanggal::timestamp < '2024-01-01'
  AND jenis_pangan = '1401'
  AND status IN ('0999', '0906', '9999')
  AND NULLIF(TRIM(trader_id), '')::bigint NOT IN (5, 17, 50, 85)
```

Agent bahkan secara eksplisit menulis: *"Seluruh jumlah tersebut tercatat pada sistem ERBA, yang merupakan sistem pendaftaran utama yang digunakan BPOM sejak tahun 2023."*

Ini menunjukkan agent membuat keputusan sadar untuk menggunakan ERBA-only berdasarkan framing "sistem utama 2023" — padahal pertanyaan tentang AMDK harus selalu UNION ERBA+ERLA karena ada warisan NIE dari ERLA yang masih berlaku.

**Kasus serupa:** UAT-AMDK-3 (expected 2024=2.514, 2025=2.140 — agent membuat UNION query tapi kode ERLA salah atau scope berbeda).

### 4.3 Pola B: Off-By-One — Data Timing atau Filter Subtil

**Kasus: BUGFIX-3 — BTP ERBA 2023**

| | Nilai |
|---|---|
| Expected | **950** |
| Agent answer | **951** |

SQL agent:
```sql
SELECT COUNT(DISTINCT nomor) AS jumlah_nie_btp_2023
FROM warehouse.public.t_btp_3_erba
WHERE tanggal::timestamp >= '2023-01-01' AND tanggal::timestamp < '2024-01-01'
  AND status IN ('0999', '0906', '9999')
  AND trader_id::bigint NOT IN (5, 17, 50, 85)
  AND tanggal IS NOT NULL AND tanggal != ''
```

Perbedaan 1 unit pada data historis 2023 (data closed/static) membuktikan bahwa SQL-nya slightly berbeda dari yang benar. Note di test case menyebutkan: *"Agent harus gunakan `trader_id`, bukan `user_id` untuk exclude test accounts."*

Artinya: ada 1 test account yang perlu di-exclude yang teridentifikasi lewat `user_id` tapi agent hanya exclude via `trader_id`. Keduanya adalah kolom yang berbeda — `trader_id` adalah ID perusahaan, `user_id` adalah ID user sistem yang submit. Satu test account mungkin punya `user_id` test tapi `trader_id` yang valid.

**Kasus: UAT-GARAM-1 — Garam Beryodium 2023**

| | Nilai |
|---|---|
| Expected | **199** |
| Agent answer | **198** |

SQL agent menggunakan `jenis_pangan = '1204'` — ini sudah benar (parent category). 
Tapi hasilnya 198, bukan 199. Kemungkinan: agent mengaplikasikan `jenis_permohonan IN ('301','305')` atau filter tambahan lain yang membuang 1 produk Garam yang didaftarkan lewat jalur perubahan.

Ini menunjukkan bahwa meskipun kode segmen (jenis_pangan) sudah benar, **filter jenis_permohonan masih sesekali ditambahkan secara implisit** oleh agent.

**Kasus: BUGFIX-4 — Total Permohonan 2023**

| | Nilai |
|---|---|
| Expected | **61.217** |
| Agent answer | **61.213** |

Perbedaan hanya 4 unit. Ini kemungkinan data drift antara saat expected value ditetapkan dan saat test dijalankan, atau minor filter inconsistency. Secara konseptual SQL-nya sudah benar (ERBA+ERLA tanpa BTP).

### 4.4 Pola C: Risk Code Resolution Masih Belum Sempurna

**Kasus: BUGFIX-5 — NIE Risiko Tinggi All-Time**

| | Nilai |
|---|---|
| Expected | **103.698** (ERBA 83.143 + ERLA 20.555) |
| Agent answer | **119.314** |

SQL akhir agent:
```sql
SELECT COUNT(DISTINCT nomor) AS total_nie_risiko_tinggi
FROM (
  SELECT nomor FROM warehouse.public.t_produk_3_erba
  WHERE kategori_dokumen IN ('301', '304')   -- Tinggi + TinggiNotif
    AND status IN ('0999', '0906', '9999')
    AND trader_id NOT IN (5, 17, 50, 85)
  UNION ALL
  SELECT nomor FROM warehouse.public.t_produk_3_rilis_erla
  WHERE jenis_dokumen = '302'                -- ERLA High Risk
    AND status IN ('0099', '0999', '0906', '9999')
    AND trader_id != 3384
) AS gabungan
```

Kode yang dipakai secara individual sudah benar (`kategori_dokumen IN ('301','304')` untuk ERBA, `jenis_dokumen='302'` untuk ERLA). Tapi angkanya tetap meleset: 119.314 vs expected 103.698 (selisih ~16.000).

Kemungkinan penyebab:
1. Agent tidak mengaplikasikan date range filter (`tanggal >= '2000-01-01'`) yang membuang bad data years
2. ERBA `jenis_permohonan` filter tidak digunakan, sehingga termasuk beberapa record yang seharusnya tidak dihitung sebagai NIE

**Kasus: CB-3 — NIE Risiko Tinggi dengan Expected ~102.000**

| | Nilai |
|---|---|
| Expected | angka yang mengandung '102' |
| Agent answer | **106.068** |

Serupa dengan BUGFIX-5 — gap di ERBA scope vs yang seharusnya.

**Kasus: CB-1 — NIE MR ERBA 2023**

| | Nilai |
|---|---|
| Expected | **118** (mengandung '118') |
| Agent answer | **9.649** |

Ini adalah kasus yang lebih serius. Agent menjawab 9.649 NIE MR ERBA 2023 — tapi expected adalah sesuatu yang mengandung '118'. 

Kemungkinan interpretasi: pertanyaan "Berapa izin edar produk pangan olahan risiko menengah rendah" yang datanya 2023 dimaksudkan untuk ERBA-only dengan filter jenis_permohonan baru → 118 NIE baru MR ERBA 2023. Agent menjawab total MR ERBA 2023 tanpa filter "baru" → 9.649.

Ini adalah ambiguitas scope yang belum sepenuhnya diresolusi.

### 4.5 Pola D: Case A vs Case B Komitmen — Bug Paling Signifikan yang Masih Ada

**Kasus: UAT-KOMITMEN-DISETUJUI-1**

| | Nilai |
|---|---|
| Expected | **2.717** |
| Agent answer | **14.312** |

**Selisih 5× lipat.** Agent menggunakan Case A (dengan NIE status filter):
```sql
WHERE kategori_dokumen='303'
  AND status IN ('0999', '0906', '9999')  -- filter NIE aktif
  AND ROUND(status_komitmen::numeric)::int::text = '2'
```

Yang seharusnya Case B (tanpa NIE status filter) untuk menghitung semua produk yang komitmennya disetujui:
```sql
WHERE kategori_dokumen='303'
  AND ROUND(status_komitmen::numeric)::int::text = '2'
  -- tanpa status filter — komitmen bisa terjadi sebelum/sesudah NIE aktif
```

Ini persis bug yang sama dengan RC-4 dari `uat_audit_report_15jun2026.md` — **planning doc 2026-06-17 sudah mendiagnosis ini, tapi implementasinya belum sepenuhnya efektif di runtime.**

**Kasus: UAT-COM-1 (MR Dibatalkan = 5.198)**

| | Nilai |
|---|---|
| Expected | **5.198** |
| Agent answer | Angka berbeda (tidak mengandung 5.198) |

Sama — Case B komitmen masih salah.

### 4.6 Pola E: Cached Value dari Dokumentasi, Bukan Live Query

**Kasus: UAT-ERLA-1 — Total Permohonan ERLA All-Time**

| | Nilai |
|---|---|
| Expected | **400.784** (live query dengan filter benar) |
| Agent answer | **412.607** |

Angka 412.607 ini BUKAN dari live query — ini adalah angka yang tersimpan di `data_architecture.md` sebagai row count perkiraan saat dokumen ditulis. Agent tidak bisa konek database, lalu mengambil angka dari konteks sebagai "data historis yang tercatat di sistem".

Ini adalah **bukti paling jelas dari masalah yang didiagnosis planning doc 2026-06-17**: ketika koneksi gagal, agent fall back ke cached values dari dokumentasi — yang bisa basi atau tidak terfilter.

---

## 5. Temuan #4: Format Compliance — Forecast Output Tidak Lengkap

### 5.1 Konteks

Skill `bpom-forecaster` mensyaratkan **7-block output mandatory** dengan 12-item self-check gate sebelum deliver jawaban. FORECAST series menguji apakah format ini diikuti.

### 5.2 Hasil FORECAST Series

| Scenario | Status | Missing Blocks |
|---|---|---|
| FORECAST-1 | ❌ FAIL | Ringkasan, Rata-rata 3 bulan terakhir, Rata-rata 3 bulan ke depan, **Kondisi Data**, **Historis & Proyeksi**, **Proyeksi Detail**, **Rentang Realistis**, Tingkat Keyakinan, Apa Artinya, **Metodologi**, Moving Average |
| FORECAST-2 | ✅ PASS | — |
| FORECAST-3 | ✅ PASS | — |
| FORECAST-4 | ✅ PASS | — |
| FORECAST-5 | ✅ PASS | — |
| FORECAST-6 | ❌ FAIL | **Proyeksi Detail**, **Rentang Realistis** |
| FORECAST-7 | ❌ FAIL | **Rentang Realistis**, Historis & Proyeksi, Apa Artinya, **Metodologi** |
| FORECAST-8 | ❌ FAIL | TinggiNotif (eligibility explanation) |
| FORECAST-9 | ✅ PASS | — |
| FORECAST-10 | ❌ FAIL | **Proyeksi Detail**, Tinggi, **Metodologi** |
| FORECAST-11 | ❌ FAIL | **Metodologi** |
| FORECAST-12 | ❌ FAIL | **Kondisi Data**, Apa Artinya |

**7 dari 12 FORECAST scenarios FAIL.** Yang PASS (2,3,4,5,9) adalah skenario yang menguji aspek non-format: refusal (ERLA ditolak), konsistensi data, TOLAK karena event-driven.

### 5.3 Pattern Kegagalan Forecast

**FORECAST-1**: Warehouse tidak ter-attach. Agent tidak bisa menjalankan RECIPE-F1 sampai F6. Hasilnya adalah penolakan berbasis *"koneksi warehouse tidak tersedia"* tanpa format sama sekali.

**FORECAST-6**: Warehouse konek, tapi output tidak lengkap — missing `Proyeksi Detail` dan `Rentang Realistis`. Agent menghitung forecast tapi memotong output sebelum tabel proyeksi per bulan.

**FORECAST-7**: Missing beberapa blok kritis. Ini menunjukkan agent menjalankan kalkulasi tapi self-check 12-item tidak memblokir output meskipun blok tidak lengkap.

**FORECAST-11**: Hanya missing `Metodologi`. Agent hampir sempurna tapi melupakan blok terakhir (satu-satunya tempat MAPE dan weights boleh ditampilkan).

**FORECAST-12**: Missing `Kondisi Data` dan `Apa Artinya`. Dua blok yang berbeda posisi (awal dan akhir) — ini menunjukkan bukan truncation, tapi selective omission.

### 5.4 Root Cause Format Failures

Self-check 12-item ada di SKILL.md sebagai instruksi, tapi agent memperlakukannya sebagai **checklist yang dibaca, bukan gate yang memblokir**. Agent menandai semua item "sudah" tanpa memverifikasi output sebenarnya.

Ini adalah perbedaan antara:
- **Soft gate**: "Cek list ini sebelum deliver" → agent membaca instruksi, anggap sudah, deliver
- **Hard gate**: "Jika block X tidak ada dalam output → STOP, tambahkan dulu" → enforcement nyata

---

## 6. Temuan #5: Anomali dan Observasi Tambahan

### 6.1 BTP-1 dan AMDK-1 — False Positive Assertion

**BTP-1 FAIL: missing 'per tahun'**

Padahal jawaban agent:
```
| 2023  | 950        |
| 2024  | 1.089      |
| 2025  | 1.523      |
| Total | 3.562      |
```

Data per tahun ada dan benar. Yang "missing" adalah literal string `'per tahun'` dalam teks — agent tidak menulis frasa itu di heading atau narasi. Ini adalah **false positive assertion**: jawaban benar secara substansi, tapi assertion terlalu ketat secara string matching.

Sama untuk **AMDK-1** — tabel per tahun ada, angkanya benar, tapi frasa `'per tahun'` tidak muncul.

**Implikasi**: Jumlah genuine failure mungkin 2 lebih sedikit dari yang terlihat.

### 6.2 CB-25 — 95 Tool Calls untuk Forecast

CB-25 "Forecasting izin edar 2026-2027 per tingkat risiko" menggunakan **95 tool calls** — tertinggi dalam seluruh run. Agent mencoba berbagai pendekatan forecast, menjalankan query historis, menghitung proyeksi, tapi tetap FAIL karena output tidak mengandung kata 'forecast'.

Ini menunjukkan: agent bekerja keras (95 tool calls), menghasilkan proyeksi, tapi tidak memanggil `bpom-forecaster` skill secara eksplisit atau tidak menggunakan format yang benar. Routing dari pertanyaan forecast ke forecaster skill mungkin tidak ter-trigger dengan benar.

### 6.3 CB-33 — Susu Merk Sekolah, Expected 25

| | Nilai |
|---|---|
| Expected | mengandung '25' |
| Agent answer | Tidak mengandung '25' |

Note: *"missing: '25'"* — pertanyaan ini berhubungan dengan susu merk sekolah. Test case sebelumnya (UAT-SUSU-1) mengkonfirmasi bahwa data Mei 2026 adalah 0. Tapi CB-33 mungkin menanyakan hal berbeda (mungkin all-time atau 2025). Warehouse tidak konek untuk CB-33 sehingga agent tidak bisa memberikan angka aktual.

### 6.4 Scenarios dengan Elapsed Sangat Panjang

| Scenario | Elapsed | Tool Calls | Keterangan |
|---|---|---|---|
| CB-25 | Sangat panjang | 95 | Schema hunt + forecast attempt berulang |
| BUGFIX-5 | 652.73s | 71 | Risk code resolution + fallback attempts |
| FORECAST-12 | — | 73 | Multi-phase forecast yang hampir lengkap |
| UAT-BTP-1 | 680.69s | Besar | Schema hunt berat |

Pola umum: skenario dengan elapsed > 600s hampir seluruhnya dihabiskan untuk schema discovery dan connection attempts, bukan untuk business logic.

---

## 7. Korelasi dengan Planning Documents

### 7.1 Status Implementasi: 2026-06-17-dictionary-grounded-code-translation.md

Planning doc ini mendefinisikan 5 hipotesis kegagalan (H1-H5). Status berdasarkan hasil test:

| Hipotesis | Diagnosis | Status di Test 18 Jun |
|---|---|---|
| H1: Cached meanings defeat lookup | Kode di-resolve dari memori bukan live dictionary | **Masih terjadi** — UAT-ERLA-1 (412.607 dari docs vs 400.784 live) |
| H2: Sumber-blind resolution | Fan-out karena tidak filter sumber di data_dictionary | **Sebagian diperbaiki** — agent kini filter sumber, tapi ERBA-only bias masih ada |
| H3: Cross-system equivalence assumed | ERLA 303 ≠ ERBA MT | **Membaik** — BUGFIX-5 kini pakai `jenis_dokumen='302'` untuk ERLA, bukan '303' |
| H4: Filter scope baked | `jenis_permohonan` dipakai di semua query | **Masih terjadi** — UAT-GARAM-1 off-by-1, CB-1 overcount |
| H5: Segment codes hardcoded | Kode AMDK/Garam dari memory bukan discovery | **Membaik** — UAT-GARAM-1 kini pakai `jenis_pangan='1204'`, tapi off-by-1 |

**Kesimpulan**: Implementasi berjalan, tapi belum sepenuhnya efektif. Banyak yang "arah benar, eksekusi belum tepat".

### 7.2 Status Implementasi: 2026-06-18-llm-forecaster-skill.md

| Requirement | Status |
|---|---|
| 7-block output format | **Tidak konsisten** — 7 dari 12 scenario fail |
| Self-check 12-item gate | **Tidak blocking** — agent tidak berhenti jika blok hilang |
| ERLA refusal | ✅ Berfungsi — FORECAST-4 PASS |
| Event-driven refusal | ✅ Berfungsi — FORECAST-9 PASS |
| Interval widening dengan √H | ✅ Berfungsi — FORECAST-3 PASS |
| Routing FORECAST → bpom-forecaster | **Tidak konsisten** — CB-25 tidak ter-route dengan benar |

---

## 8. Ringkasan Root Cause Per Kategori

### RC-A: Warehouse Connection (Impact: 40+ skenario)

**Penyebab**: Catalog `warehouse` tidak ter-attach secara otomatis di setiap DuckDB session. Agent harus ATTACH manual tapi prosedurnya tidak reliabel — kadang `env:WAREHOUSE_URL` tidak tersedia, kadang `host.docker.internal:5533` tidak reachable.

**Bukti**: 78% dari semua SQL adalah schema discovery. Agent rata-rata menjalankan 12-15 query hanya untuk menemukan database sebelum bisa menulis business query.

**Dampak pada agent**: Ketika gagal connect, agent menggunakan nilai dari dokumentasi context sebagai pengganti — ini **melanggar prinsip "setiap angka harus dari query"**.

### RC-B: Case A vs Case B Komitmen (Impact: ~6 skenario)

**Penyebab**: Agent masih mencampur dua definisi yang berbeda:
- Case A: "NIE aktif yang komitmennya berstatus X" → perlu NIE filter
- Case B: "Permohonan yang dibatalkan di stage komitmen" → tidak perlu NIE filter

Perbaikan di `data_quality_rules.md` ada secara teks, tapi tidak cukup kuat memandu agent untuk memilih case yang benar saat runtime.

### RC-C: ERBA-Only Bias (Impact: ~5 skenario)

**Penyebab**: Agent terlalu sering memutuskan ERBA-only untuk pertanyaan yang seharusnya UNION. Framing "ERBA adalah sistem utama sejak 2023" diinterpretasi terlalu luas sebagai "ERBA saja cukup untuk pertanyaan 2023+".

### RC-D: Format Gate Tidak Memblokir (Impact: 7 FORECAST skenario)

**Penyebab**: Self-check di bpom-forecaster/SKILL.md adalah "run checklist" bukan "blocking gate". Agent membaca checklist, lalu deliver output tanpa memverifikasi bahwa semua blok benar-benar ada.

### RC-E: jenis_permohonan Filter Masih Muncul Implisit (Impact: ~3 skenario)

**Penyebab**: Meskipun ada perbaikan di `data_quality_rules.md`, agent sesekali masih menambahkan `jenis_permohonan IN ('301','305')` secara implisit untuk pertanyaan yang tidak memerlukannya — menyebabkan off-by-1 atau undercounting kecil.

---

## 9. Apa yang Sudah Bekerja dengan Baik

### 9.1 Genuine Pass — 96 Skenario

Sebagian besar skenario CB (Core Business) berhasil: CB-2 sampai CB-21 banyak yang PASS dengan angka tepat. Ini menunjukkan:
- Query pattern untuk business questions umum sudah solid
- UNION ERBA+ERLA untuk pertanyaan standar berjalan baik
- Code resolution via data_dictionary bekerja ketika warehouse ter-attach

### 9.2 Fallback Mechanism Bekerja Sebagian

CAP-2 dan FORECAST-5 menunjukkan bahwa ketika koneksi gagal, agent bisa memberikan jawaban berkualitas tinggi berbasis metodologi — dan test assertions yang mengukur metodologi (bukan angka) berhasil lulus.

### 9.3 Honest Behavior Dipertahankan

Agent tidak fabricate angka dari udara. Ketika tidak bisa connect, ia **mengakui** ketidakmampuannya (biasanya) dan menawarkan SQL template. UAT-SUSU-1 tetap mengembalikan 0 dengan benar. Prinsip "tidak mengarang angka" berfungsi.

### 9.4 Dictionary Lookup Sudah Sumber-Aware

Pada banyak skenario yang berhasil, agent melakukan lookup seperti:
```sql
SELECT sumber, kode, deskripsi
FROM warehouse.public.data_dictionary
WHERE kategori = 'KATEGORI_DOKUMEN'
  AND sumber = 'ERBA'
  AND deskripsi ILIKE '%menengah tinggi%'
```

Ini menunjukkan `code_translation_protocol.md` sudah diimplementasikan — agent kini filter per sumber.

---

## 10. Angka Kunci untuk Cross-Check Database Aktual

Berikut adalah skenario yang masih menunjukkan discrepancy dan perlu diverifikasi langsung ke database untuk memastikan expected value masih valid:

### Prioritas Tinggi — Angka Sangat Berbeda

| Test | Expected | Agent Answer | Selisih | Perlu Cek |
|---|---|---|---|---|
| UAT-KOMITMEN-DISETUJUI-1 | 2.717 | 14.312 | 5× lipat | Konfirmasi Case B logic |
| BUGFIX-5 / CB-3 | 103.698 / ~102.xxx | 119.314 / 106.068 | ~15% | Filter scope ERBA Tinggi+TinggiNotif |
| CB-1 | ~118 (baru MR 2023) | 9.649 (total MR 2023) | Scope beda | Klarifikasi intent CB-1 |
| UAT-ERLA-1 | 400.784 | 412.607 | 3% | Verify live vs docs value |

### Prioritas Sedang — Off-By-Small tapi Static Data

| Test | Expected | Agent Answer | Delta | Keterangan |
|---|---|---|---|---|
| BUGFIX-3 | 950 | 951 | +1 | BTP 2023 — cek user_id vs trader_id exclusion |
| UAT-GARAM-1 | 199 | 198 | -1 | Garam 2023 — cek jenis_permohonan filter implicit |
| BUGFIX-4 | 61.217 | 61.213 | -4 | Kemungkinan data drift, bukan logic error |

### Prioritas untuk Validasi Forecast

| Test | Failing Blocks | Perlu Diverifikasi |
|---|---|---|
| FORECAST-1 | Semua blok | Pastikan warehouse connect sebelum run |
| FORECAST-6 | Proyeksi Detail, Rentang Realistis | Verifikasi output format |
| FORECAST-7 | 4 blok | Verifikasi self-check blocking |

---

## 11. Rekomendasi Perbaikan

### P0: Fix Warehouse Connection (Dampak: 40+ skenario)

**Masalah**: Catalog `warehouse` tidak auto-attach, agent menghabiskan 78% SQL budget untuk schema discovery.

**Solusi**: Pastikan session DuckDB selalu dimulai dengan:
```sql
INSTALL postgres;
LOAD postgres;
ATTACH 'postgresql://readonly_user:read_only_seeknal@host.docker.internal:5533/rpo_v2' 
  AS warehouse (TYPE POSTGRES, READ_ONLY);
```
Atau via environment variable yang reliabel. Ini harus di-setup di level infrastruktur test runner, bukan di-handle agent.

**Alternatif**: Tambahkan ke `database-analyst/SKILL.md` dan `bpom-analyst/SKILL.md` sebagai PHASE 0 mandatory:
```
BEFORE any query:
1. Verify: SELECT 1 FROM warehouse.public.t_produk_3_erba LIMIT 1
2. If fails: ATTACH 'postgresql://...' AS warehouse (TYPE POSTGRES)
3. If still fails: report connection failure explicitly, do NOT use documentation values
```

### P1: Ubah Self-Check Forecaster Jadi Hard Gate (Dampak: 7 skenario)

**Masalah**: Self-check 12-item adalah instruksi, bukan gate.

**Perubahan di `bpom-forecaster/SKILL.md` PHASE 6**:
```
BEFORE delivering output:
1. Scan your output. Verify EACH of these strings is present:
   - "Kondisi Data"    → if missing: GO BACK to PHASE 2, add block
   - "Historis & Proyeksi" → if missing: GO BACK, add block
   - "Proyeksi Detail" → if missing: GO BACK, add block
   - "Rentang Realistis" → if missing: GO BACK, add block
   - "Metodologi"      → if missing: ADD IT before delivering

2. If ANY check fails: DO NOT DELIVER. Return to relevant PHASE.
3. Only deliver when ALL 5 mandatory sections are confirmed present.
```

### P2: Perkuat Case A vs Case B di Runtime (Dampak: ~6 skenario)

**Masalah**: Distinction Case A/B ada di docs tapi tidak memandu agent cukup kuat.

**Tambahkan ke `bpom-analyst/SKILL.md` PHASE 2 (RESOLVE)**:
```
COMMITMENT QUERY GATE — Run this before any status_komitmen query:

Q: Is the user asking about...
(A) Products that HAVE a valid NIE and also have commitment status X?
    → Signal: "berapa NIE yang...", "berapa produk aktif yang..."
    → Use: status IN ('0999',...) AND status_komitmen = X
    
(B) Applications whose commitment was processed at any lifecycle stage?
    → Signal: "berapa yang dibatalkan", "berapa yang disetujui", "berapa draft"
    → Use: status_komitmen = X ONLY — no NIE status filter
    → Most commitment events happen BEFORE NIE is issued

State your choice and reasoning in RESOLVED CONSTRUCTS.
```

### P3: Perkuat ERBA+ERLA Union Rule untuk Segmen Produk (Dampak: ~5 skenario)

**Perubahan di `business_glossary.md` dan `intent_mapping.md`**:
```
SEGMENT QUERY RULE:
For product segments (AMDK, Garam Beryodium, BTP, Formula Bayi):
→ ALWAYS query ERBA + ERLA UNION unless user explicitly says "ERBA saja" / "ERLA saja"
→ "Sistem utama 2023+" means PRIMARY volume, NOT exclusive source
→ ERLA may have concurrent entries even in 2023-2025

AMDK: ERBA jenis_pangan='1401' UNION ERLA jenis_pangan IN ('651','652','655')
Garam: ERBA jenis_pangan='1204' UNION ERLA kategori_pangan='12010103'
```

### P4: Hapus Angka Spesifik dari Dokumentasi Context (Dampak: cached value risk)

**File terdampak**: `data_architecture.md`

Angka seperti "412.607 catatan produk" yang ada di dokumentasi sebagai row count estimasi harus dihapus atau diberi label jelas sebagai estimasi stale:
```
❌ JANGAN: "ERLA memiliki ±412.607 catatan produk"
✅ SEBAIKNYA: "ERLA: jalankan SELECT COUNT(DISTINCT produk_id) FROM warehouse.public.t_produk_3_rilis_erla untuk angka aktual"
```

---

## 12. Benchmark: Sebelum vs Sesudah Perubahan 17 Jun 2026

| Metrik | Sebelum (15 Jun UAT) | Sesudah (18 Jun Test) | Status |
|---|---|---|---|
| NIE MT all-time | 95.736 (wrong) | Tidak bisa diukur (warehouse fail) | ⏳ Belum terverifikasi |
| Garam Beryodium 2023 | 189 | 198 (jenis_pangan='1204') | ✅ Kode benar, off-by-1 minor |
| Komitmen Dibatalkan MR | 254 | Belum benar (Case B masih salah) | ❌ Masih perlu perbaikan |
| Total NIE 2025 | Non-deterministic | Belum bisa diukur (warehouse fail) | ⏳ Belum terverifikasi |
| Code resolution sumber-aware | Tidak ada | Ada, berjalan | ✅ Implementasi berhasil |
| Forecast 7-block output | Belum ada | Ada tapi tidak konsisten | ⚠️ Parsial |

---

## Appendix A: Distribusi Tool Calls Per Skenario

| Range Tool Calls | Jumlah Skenario | Interpretasi |
|---|---|---|
| 0 (crash) | 8 | Infra crash sebelum agent berjalan |
| 0 (cached) | 45 | Tidak dieksekusi — ambil dari checkpoint |
| 1–30 | ~15 | Query langsung, koneksi bagus |
| 31–50 | ~35 | Moderate schema hunting |
| 51–70 | ~80 | Heavy schema hunting |
| 71–90 | ~15 | Sangat berat — koneksi sulit |
| 91+ | 2 (CB-25: 95) | Ekstrem — connection chaos + retry |

---

## Appendix B: Ground Truth Verification Checklist

Angka-angka berikut perlu diverifikasi ulang terhadap database `rpo_v2` sebelum dijadikan expected value di test suite berikutnya:

```sql
-- 1. BTP ERBA 2023 (expected: 950)
SELECT COUNT(DISTINCT nomor) FROM warehouse.public.t_btp_3_erba
WHERE tanggal::timestamp >= '2023-01-01' AND tanggal::timestamp < '2024-01-01'
  AND status IN ('0999','0906','9999')
  AND trader_id::bigint NOT IN (5, 17, 50, 85);

-- 2. Garam Beryodium 2023 (expected: 199)
SELECT COUNT(DISTINCT nomor) FROM warehouse.public.t_produk_3_erba
WHERE jenis_pangan = '1204'
  AND tanggal::timestamp >= '2023-01-01' AND tanggal::timestamp < '2024-01-01'
  AND status IN ('0999','0906','9999')
  AND NULLIF(TRIM(trader_id),'')::bigint NOT IN (5, 17, 50, 85);

-- 3. Komitmen Disetujui MR (expected: 2.717) — Case B
SELECT COUNT(DISTINCT produk_id) FROM warehouse.public.t_produk_3_erba
WHERE kategori_dokumen = '303'
  AND ROUND(status_komitmen::numeric)::int::text = '2';

-- 4. NIE Risiko Tinggi all-time (expected: ~103.698)
SELECT COUNT(DISTINCT nomor) FROM (
  SELECT nomor FROM warehouse.public.t_produk_3_erba
  WHERE kategori_dokumen IN ('301','304')
    AND status IN ('0999','0906','9999')
    AND jenis_permohonan IN ('301','305')
    AND tanggal >= '2000-01-01' AND tanggal < '2030-01-01'
    AND NULLIF(TRIM(trader_id),'')::bigint NOT IN (5, 17, 50, 85)
  UNION
  SELECT nomor FROM warehouse.public.t_produk_3_rilis_erla
  WHERE jenis_dokumen = '302'
    AND status IN ('0099','0999','0906','9999')
    AND tanggal >= '2000-01-01' AND tanggal < '2030-01-01'
    AND trader_id != 3384
) sub;
```

---

*Audit ini disusun berdasarkan analisis langsung terhadap file JSON hasil test `multiturn_results_20260618_043252.json`, dikaitkan dengan planning docs 17-18 Juni 2026 dan audit sebelumnya (15 Juni 2026).*  
*Tanggal audit: 18 Juni 2026.*
