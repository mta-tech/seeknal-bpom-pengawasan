# 03 — Tabel `mv_pengawasan_log` (Anatomi Alur Kerja)

> **1.817.233 baris · 9 kolom · 356 MB · snapshot 2026-08-12 23:23:59**
> Grain: **1 baris = 1 transisi status** oleh 1 petugas. Banyak baris per `id_pengawasan`.

## Profil 9 kolom

| Kolom | Sifat | Catatan |
|---|---|---|
| `id_pengawasan` | 236.982 distinct | 64.982 id hantu tak di main (lihat `01`) |
| `trx_steps` | **16 distinct** text | label peran (draft, spv_1, dst.) |
| `status_code` | **17 distinct** bigint | 0-7, 990-997, 999 |
| `status_label` | 9 distinct text | **9.159 baris SQL NULL** (kode 990-997 label kosong) |
| `fullname` | 1.536 distinct | 0 empty string; 0 NULL |
| `nama_balai` | ~90 distinct | **Title Case** (beda dari main yang UPPERCASE) |
| `catatan` | ~5.946 distinct | 15.6% SQL NULL; bebas text audit trail |
| `tanggal_proses` | timestamp dinamis | **16.8% SQL NULL** (pekat di status 0 & 4) |
| `sync` | timestamp seragam | 2026-08-12 23:23:59 |

## Dictionary lengkap: `status_code` × `status_label` × `trx_steps`

Ini dictionary VERIFIED langsung dari data. Catat **anomali edge** — mapping TIDAK bijektif sempurna:

| status_code | status_label | trx_steps | n |
|---|---|---|---|
| 0 | Operator - Draft Sampling | draft | 267.404 |
| 1 | Supervisor - Verifikasi | spv_1 | 238.262 |
| 2 | Supervisor 2 - Verifikasi | spv_2 | 16.622 |
| **2** | Supervisor 2 - Verifikasi | **spv_1** | **1** ⚠️ anomali |
| 3 | TPS - Penerimaan SPU | kepala_balai | 228.937 |
| 4 | MT - Pembuatan SPK | pusat | 317.862 |
| 5 | Deputi MT - Pembuatan SPK | spv_1_pusat | 245.915 |
| **5** | Deputi MT - Pembuatan SPK | **spv_2_pusat** | **16** ⚠️ anomali |
| 6 | Penyelia - Pembuatan SPP | spv_2_pusat | 118.654 |
| 7 | Penguji - Entri Hasil Pengujian | direktur | 190.104 |
| 990 | (label kosong) | draft | 4 |
| **991** | (label kosong) | **ditolak_spv_1** | 5.743 |
| **991** | (label kosong) | **ditolak_kepala_balai** | **30** ⚠️ |
| **991** | (label kosong) | **draft** | **1** ⚠️ |
| 992 | (label kosong) | ditolak_spv_2 | 148 |
| 993 | (label kosong) | ditolak_kepala_balai | 381 |
| 994 | (label kosong) | ditolak_pusat | 1.705 |
| 995 | (label kosong) | ditolak_spv_1_pusat | 932 |
| 996 | (label kosong) | ditolak_spv_2_pusat | 92 |
| 997 | (label kosong) | ditolak_direktur | 123 |
| **999** | **Sampel Rujukan Selesai** | selesai | 183.962 |

**Anomali edge yang harus diingat**:
- `status_code=2` mayoritas `spv_2` TAPI ada 1 baris `spv_1`
- `status_code=5` mayoritas `spv_1_pusat` TAPI 16 baris `spv_2_pusat`
- `status_code=991` mayoritas `ditolak_spv_1` TAPI 30 baris `ditolak_kepala_balai` dan 1 baris `draft`

**Jangan asumsikan `trx_steps` ↔ `status_code` 1:1.** Ada kebocoran tepi.

## Topologi workflow

```
[0] Operator - Draft Sampling
   └→ [1] Supervisor - Verifikasi
        └→ [2] Supervisor 2 - Verifikasi  (jarang, hanya 16.622)
             └→ [3] TPS - Penerimaan SPU  (kabalai)
                  └→ [4] MT - Pembuatan SPK  (pusat)
                       └→ [5] Deputi MT - Pembuatan SPK  (spv_1_pusat)
                            └→ [6] Penyelia - Pembuatan SPP  (spv_2_pusat)
                                 └→ [7] Penguji - Entri Hasil Pengujian  (direktur)
                                      └→ [999] Sampel Rujukan Selesai

Cabang penolakan (label kosong di data):
  [990-997] = ditolak_spv_1 / ditolak_spv_2 / ditolak_kepala_balai / ditolak_pusat /
              ditolak_spv_1_pusat / ditolak_spv_2_pusat / ditolak_direktur
```

## Beban penolakan per tahap (kode 990-997)

| status_code | trx_steps | transisi | events |
|---|---|---|---|
| 991 | ditolak_spv_1 | 5.743 | 5.428 |
| 994 | ditolak_pusat | 1.705 | 1.533 |
| 995 | ditolak_spv_1_pusat | 932 | 881 |
| 993 | ditolak_kepala_balai | 381 | 379 |
| 997 | ditolak_direktur | 123 | 120 |
| 996 | ditolak_spv_2_pusat | 92 | 49 |
| 992 | ditolak_spv_2 | 148 | 143 |
| 990 | draft | 4 | 4 |

**Bottleneck rework paling awal**: `ditolak_spv_1` (5.428 event) — beban supervisor paling besar di tahap awal.

## Event yang pernah ditolak lalu lanjut (rework)

```
pernah_ditolak: 8.370 event (3.5% dari 236.921 total event di log)
```

3.5% event mengalami rework — ditolak lalu diproses ulang. Ini indikator inefisiensi proses.

## PRODUK PANGAN workflow terpotong di pusat

Distribusi `trx_steps` khusus PRODUK PANGAN (join ke main):

| trx_steps | status_code | n |
|---|---|---|
| spv_1 | 1 | 34.745 |
| kepala_balai | 3 | 33.828 |
| pusat | 4 | 33.788 |
| draft | 0 | 33.777 |
| ditolak_spv_1 | 991 | 956 |
| ditolak_kepala_balai | 993 | 37 |

**NOL baris** untuk spv_1_pusat, spv_2_pusat, direktur, selesai. PANGAN berhenti total di `pusat` (status 4). **Terminal flow pangan** — verdict sah di `balai` (lihat `09`).

## Path mining — jalur transisi paling umum

**PERINGATAN**: `tanggal_proses` 16.8% NULL (pekat di status 0 = 58% null, status 4 = 28% null). Path mining via `ORDER BY tanggal_proses` **terdistorsi**. Hasil di bawah memakai `NULLS FIRST` + tiebreak `status_code` — masih ada noise tapi pola dominan terlihat.

| Path | events | avg langkah |
|---|---|---|
| `0>1>3>4>5>7>999` | 47.397 | 7.0 |
| `0>1>3>4>5>6>7>999` | 35.291 | 8.0 |
| `0>4>5>1>3>4>5>6>7>999` | 32.453 | 10.0 |
| `0>1>3>4` | 31.289 | 4.0 (PANGAN stuck) |
| `0>4>1>3>4>5>6>7>999` | 15.979 | 9.0 |
| `0` saja | 6.038 | 1.0 (draft doang) |
| `0>1>3>4>5>7` | 5.000 | 6.0 |
| `0>1>991` | 1.096 | 3.0 (ditolak spv_1) |

Total **1.086 path unik** dari 236.921 event — sangat bervariasi. Jalur "mulus" `0>1>3>4>5>7>999` mendominasi (47.397 event).

**Catatan**: path seperti `0>4>5>1>3>4...` tak masuk akal sebagai workflow linier — ini artefak tanggal NULL/sama yang di-sort. **Untuk analisis urutan andal, pakai timeline** (lihat `04`), bukan log.

## `fullname` — spesialisasi peran tersembunyi

1.536 petugas. Top petugas per `trx_steps` (mengungkap struktur organisasi BPOM tanpa tabel pegawai):

| trx_steps | Top petugas | n |
|---|---|---|
| draft | Tito Veriyanto | 21.094 |
| spv_1 | Tito Veriyanto | 20.008 |
| spv_1_pusat | A. Elviera Altin, S.Si., Apt | 7.302 |
| spv_2_pusat | apt. Melyana Carolina, S.Farm. | 8.025 |
| kepala_balai | Ade Cahyana, S.Si, Apt | 2.542 |
| pusat | Agus Yudi P., S.Farm, Apt, M.M | 3.547 |
| direktur | **Franciska Yunita Wahyuni Febrianti** | **123.090** (64.7% dari 190.104 direktur!) |
| selesai | Nova Emelda, S.Si, MS, Apt | 18.502 |

**Konsentrasi pemutus final per komoditi**:
| komoditi | pemutus utama | n |
|---|---|---|
| ROKOK | Daryani, S.Si, M.Sc | 37.967 (~95%) |
| KOSMETIKA | Sulistyowati + Tita Nursjafrida | 25.603 + 19.909 |
| OBAT | Rina Apriani + Franciska | 13.432 + 9.670 |
| OT + KUASI + SUPLEMEN | **Lia Amalia** (1 org untuk 3 komoditi!) | 19.048 + 2.836 + 7.855 |

**Key-person risk**: Lia Amalia memutuskan 3 komoditi (29.739 event). Franciska memutuskan 64.7% seluruh keputusan direktur (123.090 dari 190.104).

### Petugas lintas-balai

Hanya **1 petugas** bekerja di >1 balai: Anis Kurniawati (2 balai, 2.356 log). Artinya petugas sangat terikat ke 1 balai/direktorat.

## Self-approve — TEMUAN GOVERNANCE BESAR

**Pemisahan tugas di tahap balai praktis tidak eksis.**

| Komoditi | event dgn draft+spv_1 | orang SAMA | % |
|---|---|---|---|
| OBAT KUASI | 2.831 | 2.831 | **100%** |
| OBAT TRADISIONAL | 19.003 | 19.003 | **100%** |
| SUPLEMEN KESEHATAN | 7.821 | 7.821 | **100%** |
| ROKOK | 40.031 | 39.336 | 98.3% |
| OBAT | 26.155 | 25.681 | 98.2% |
| KOSMETIKA | 42.562 | 39.669 | 93.2% |
| PRODUK PANGAN | 33.777 | 30.843 | 91.3% |
| **TOTAL** | **172.180** | **165.184** | **95.9%** |

**95.9% event di-supervisi oleh orang yang sama yang membuat draft-nya.** Kontrol dua-orang (segregation of duties) di tahap balai tidak berjalan. Ini institusional, bukan kasus terisolasi.

### Self-approve per balai (sample, >500 event)

| nama_balai | event | orang_sama | % |
|---|---|---|---|
| BALAI BESAR POM DI SERANG | 4.448 | 2.886 | 64.9% (paling "sehat") |
| BALAI BESAR POM DI SEMARANG | 5.568 | 5.021 | 90.2% |
| BALAI BESAR POM DI PADANG | 4.033 | 3.594 | 89.1% |
| BALAI BESAR POM DI SAMARINDA | 3.220 | 2.790 | 86.6% |
| BALAI BESAR POM DI KUPANG | 2.704 | 2.299 | 85.0% |

## `nama_balai` di log ≠ di main

- **main**: UPPERCASE (`LOKA POM DI KABUPATEN BONE`)
- **log**: Title Case (`Loka POM di Kabupaten Bone`) + lebih banyak (90 vs 84) karena ada DIREKTORAT sebagai pemroses pusat
- **target**: Title Case + singkatan (`Loka POM di Kab. Bone`)

Top `nama_balai` di log (mengungkap siapa memproses tahap pusat):
| nama_balai (log) | baris |
|---|---|
| Direktorat KMEI ONPPZA | **571.910** (dominasi direktorat pusat!) |
| Direktorat Kosmetik | 94.079 |
| Direktorat OTSK | 84.634 |
| BB PADANG | 53.868 |

**Inferensi**: tahap pusat diproses oleh direktorat → direktorat mendominasi log. Di main, direktorat hanya 4 baris (event pemilik direktorat).

**Wajib `UPPER()` di kedua sisi** saat join nama_balai. Verifikasi: 84/84 balai main cocok log saat keduanya di-UPPER.

## `catatan` — jejak audit bebas

15.6% SQL NULL. Pola konten:

| Kategori | n |
|---|---|
| `oleh: <nama>` (stamp auditor) | mayoritas |
| `ok`, `oke` (approval singkat) | 131.558 |
| `ACC` / `Memenuhi Ketentuan` | 66.478 |
| `Mohon koreksi` / `Mohon dilanjutkan` | review |
| `Laporkan ke Badan POM` | escalation |
| `MK` / `TMK` verdict stamp | 37.222 / 127 |
| `Entri Data oleh` | data entry trail |

Catatan = audit trail bebas, bukan field terstruktur. Berguna untuk forensik tapi tak bisa dipakai sebagai filter aggregate.

## `tanggal_proses` — 16.8% NULL, pekat di status 0 & 4

| Status | % NULL |
|---|---|
| 0 (draft) | **58%** |
| 4 (pusat) | **28%** |
| lainnya | rendah |

**Konsekuensi**: tahap draft & penerimaan pusat sering tak mencatat waktu. Ini **merusak perhitungan durasi** jika mengandalkan log. Makanya ada tabel `timeline` terpisah yang menyimpan milestone & durasi siap pakai.

Range `tanggal_proses`: 2020-03-17 06:22:22 → 2026-08-11 21:14:43.

## Status counting contract (TIGA grain berbeda — jangan tertukar)

| User tanya | Sumber & metode |
|---|---|
| Log records (transisi) | `COUNT(*) FROM mv_pengawasan_log` — 1 event bisa banyak baris |
| Latest status event main | `DISTINCT ON (id_pengawasan) ... ORDER BY tanggal_proses DESC NULLS LAST`, restrict ke main id |
| Distribusi timeline status | `COUNT(*) FROM mv_pengawasan_timeline.status` — beda populasi dari log |

**999 di log** (183.962 baris) **≈ baris main** (183.968) — beda 6 = lag sync, bukan bug.

## Bukti SQL
Lihat `13_sql_audit_trail.md` §03.

---

## ❌ KOREKSI: temuan "Self-approve 95,9%" TERBANTAH (uji ulang 2026-08-13)

Bagian *"Self-approve — TEMUAN GOVERNANCE BESAR"* di atas menyimpulkan kontrol pemisahan tugas
praktis tidak ada, berdasarkan kesamaan `fullname` pada `trx_steps='draft'` dan `'spv_1'`.
**Kesimpulan itu salah.** Sebabnya: `fullname` tidak menandai pelaku tahap yang dinamai
`trx_steps`, melainkan **pelaku aksi yang membawa berkas ke tahap itu**.

### Bukti

```sql
SELECT trx_steps, count(*) AS n, count(DISTINCT fullname) AS org,
       left(mode() WITHIN GROUP (ORDER BY catatan),46) AS catatan_tersering
FROM mv_pengawasan_log GROUP BY 1 ORDER BY 3 DESC;
```

| `trx_steps` | Baris | Orang unik | Catatan tersering |
|---|--:|--:|---|
| `draft` | 267.601 | **1.278** | *"Entri Data oleh - Yessy Yunita Saragih"* |
| `spv_1` | 238.358 | **1.253** | *" - oleh: Yessy Yunita Saragih"* |
| `kepala_balai` | 229.003 | 465 | *" - oleh: Reny Mailia, SKM., M.Sc"* |
| `pusat` | 317.882 | 221 | *" - oleh: Drs I Made Bagus Gerametta, Apt"* |
| `spv_1_pusat` | 245.972 | 49 | *" - oleh: Jamilah Nasution, SKM, M.Epid"* |
| `spv_2_pusat` | 118.670 | 19 | *"MK - oleh: Franciska…"* |
| `direktur` | 190.321 | 18 | *"ok - oleh: Daryani, S.Si, M.Sc"* |
| `selesai` | 183.962 | **17** | *" - oleh: Nova Emelda, S.Si, MS, Apt"* |

Jumlah orang unik menurun tajam sesuai senioritas: 1.278 → 1.253 → 465 → 221 → 49 → 19 → 18 → 17.
Kalau `spv_1` benar-benar tahap supervisor, mustahil dilakukan **1.253 orang berbeda** — angka itu
justru setara jumlah operator pembuat draft (1.278). Baris `spv_1` merekam **operator yang
mengirim**, bukan supervisor yang menyetujui.

### Pemisahan tugas yang sebenarnya

```sql
WITH d AS (SELECT id_pengawasan,
    min(fullname) FILTER (WHERE trx_steps='draft')        AS drafter,
    min(fullname) FILTER (WHERE trx_steps='spv_1')        AS s1,
    min(fullname) FILTER (WHERE trx_steps='kepala_balai') AS kb
  FROM mv_pengawasan_log GROUP BY 1)
SELECT round(100.0*count(*) FILTER (WHERE drafter=s1)/
             nullif(count(*) FILTER (WHERE drafter IS NOT NULL AND s1 IS NOT NULL),0),2) AS pct_draft_eq_spv1,
       round(100.0*count(*) FILTER (WHERE s1=kb)/
             nullif(count(*) FILTER (WHERE s1 IS NOT NULL AND kb IS NOT NULL),0),2) AS pct_spv1_eq_kabalai
FROM d;
```

| Pasangan | Berkas diuji | Orang sama |
|---|--:|--:|
| `draft` → `spv_1` (pengirim → dirinya sendiri) | 230.424 | 96,78% ← **artefak, bukan temuan** |
| `spv_1` → `kepala_balai` (pengirim → penyetuju) | 228.579 | **8,20%** |

**Pemisahan tugas utuh pada ~92% berkas.** Kesimpulan yang benar berkebalikan dari temuan awal.

### Yang harus diperbaiki di dokumen lain

Angka 95,9% sudah terlanjur dikutip sebagai fakta di empat tempat. Semuanya perlu dicoret:

| Berkas | Letak |
|---|---|
| `README.md` | §Ringkasan Eksekutif butir 7 |
| `10_data_quality_catalog.md` | baris "Self-approve 95,9% institusional" |
| `11_sinapsis_prediksi.md` | baris `trx_steps ∈ {draft, spv_1}` |
| `14_pola_pertanyaan_user_dan_vocabulary.md` | dua rujukan |
| `08_komoditi_master_axis.md` | §Self-approve per komoditi |

Pengganti yang benar: **"pemisahan tugas utuh pada ~92% berkas (`spv_1` vs `kepala_balai` beda
orang); kesamaan 96,8% pada `draft` vs `spv_1` adalah artefak semantik log, bukan temuan."**

> Pelajaran metodologis: angka yang benar secara aritmetika bisa menopang dua kesimpulan yang
> berlawanan. Sebelum sebuah angka dijadikan tuduhan governance, semantik kolomnya wajib
> dipastikan. Uji yang memutuskannya murah: sebaran `count(DISTINCT fullname)` per tahap — kalau
> jumlah pelaku suatu tahap setara jumlah operator, tahap itu merekam pengirim, bukan penyetuju.

---

## ⚠️ Status penyaluran ke `context/` — kode tahap log: BELUM

Diverifikasi 14 Agustus 2026 terhadap warehouse dan terhadap `context/45-status-dan-alur.md`.

Dokumen ini memuat dictionary lengkap `status_code` × `status_label` × `trx_steps`. Halaman context tidak menyebut `status_code` sama sekali, padahal pemisahan blok kode tahap dari blok kode penolakan itulah yang membuat pertanyaan "berapa yang ditolak dan di tahap mana" bisa dijawab.

Pengukuran cakupan lengkapnya di dokumen `cakupan_context_vs_database` di direktori ini.
