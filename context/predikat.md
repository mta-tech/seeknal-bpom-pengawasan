# COUNTING RULES, STATUS SETS, EXCLUSIONS — verifikasi langsung dari database

File ini = cheat-sheet untuk Gate 2 (RESOLVE). Semua angka verified terhadap snapshot `sync = 2026-08-10 22:53:15`.
Gunakan angka di sini sebagai anchor; jangan dijahit dengan asumsi.

## §1 — Counting entities (verified 2026-08-10)

| Entity | Angka | Query | Kapan dipakai |
|---|---|---|---|
| Baris (produk × pengawasan) | **183.953** | `SELECT COUNT(*) FROM mv_pengawasan` | Only when user explicitly asks for rows, records, or product-lines |
| Event pengawasan unik | **172.165** | `COUNT(DISTINCT id)` | Only when user explicitly means distinct pengawasan events |
| Surat unik (non-empty) | **9.738** | `COUNT(DISTINCT nomor_surat) FILTER (WHERE nomor_surat IS NOT NULL AND nomor_surat NOT IN ('','-'))` | Ketika user nanya "berapa surat pengawasan" |
| Produk unik | **42.854** | `COUNT(DISTINCT nama_produk)` | Ketika user nanya "berapa produk berbeda yang diawasi" |
| NIE unik | **41.208** | `COUNT(DISTINCT nie) FILTER (WHERE nie <> '--')` | Ketika user nanya "berapa NIE terkait" |
| Pendaftar unik | **6.584 (RAW — perlu cleanse)** | `COUNT(DISTINCT pendaftar)` | Lihat §6 sebelum pakai |
| Balai unik | **84** | `COUNT(DISTINCT nama_balai)` | Master dimensi |

**§1-RULE**: There is no hidden default for the bare word "pengawasan". Clarify whether the user means product rows, distinct events, or letters. Every answer must label the entity: "172.165 event pengawasan" or "183.953 baris produk", never an unlabeled "jumlah pengawasan".

**§1-CARRY**: Follow-up question mewariskan entity yang sudah disepakati. Kalau user sebelumnya jelas bicara "surat", follow-up tetap di surat kecuali user eksplisit ganti entity.

## §1A — Status counting contract

Status data has three different grains. Never substitute one for another:

| User asks for | Source and method |
|---|---|
| Log/transition records | `COUNT(*)` from `mv_pengawasan_log`; one event can contribute many rows |
| Current/latest status of main events | `DISTINCT ON (id_pengawasan) ... ORDER BY tanggal_proses DESC`, then count the deduplicated latest rows, restricted to main ids when the question is main-population scoped |
| Timeline status distribution | `COUNT(*)` from `mv_pengawasan_timeline`, using its actual `status` column; it includes historical ids absent from main |

The phrase "yang sudah selesai" must be clarified between latest log status `999` and timeline `status=999`; do not compare their raw row totals as if they were the same population.

If two log rows for one event share the same maximum `tanggal_proses`, the database has no declared sequence key. Do not invent a winner; report the event as latest-status ambiguous or use an approved `trx_steps` ordering rule.

## §2 — Status sets (verified, dari `mv_pengawasan_log`)

Workflow status dengan kode & label resmi:

| `status_code` | `status_label` | Count di log |
|---|---|---|
| 0 | Operator - Draft Sampling | 267.333 |
| 1 | Supervisor - Verifikasi | 238.235 |
| 2 | Supervisor 2 - Verifikasi | 16.623 |
| 3 | TPS - Penerimaan SPU | 228.937 |
| 4 | MT - Pembuatan SPK | 317.847 |
| 5 | Deputi MT - Pembuatan SPK | 245.920 |
| 6 | Penyelia - Pembuatan SPP | 118.654 |
| 7 | Penguji - Entri Hasil Pengujian | 190.104 |
| 990–997 | (label kosong di data) | 574–5.774 per kode |
| **999** | **Sampel Rujukan Selesai** | **183.962** ← final state |

**§2-FINAL**: Status final di log = `999` (Sampel Rujukan Selesai). Untuk Q "yang sudah selesai", filter `status_code = 999`. **Count `999` (183.962) ≈ baris di main (183.953)** — beda 9 baris = lag sync, bukan bug.

**§2-990-997**: Kode 990–997 adalah transitional/special — label kosong, jumlah kecil. **Jangan dipakai sebagai filter populer.** Kalau user tanya, jawab jujur "label tidak tercatat di data".

## §3 — Kesimpulan penilaian (verdict)

Tiga kolom berbeda dengan populasi berbeda — pilih sesuai pertanyaan:

| Kolom | Distinct values | Kapan dipakai |
|---|---|---|
| `kesimpulan_penilaian_balai` | `MK` (111.164), `TMK` (62.700), `TMK MAYOR` (3.827), `TMK MINOR` (3.430), NULL (2.832) | Penilaian awal di balai |
| `kesimpulan_penilaian_pusat` | `MK` (63.722), `TMK` (50.931), `TMK KRITIKAL` (8.683), `TMK MINOR` (2.419), `TMK MAYOR` (2.318), NULL (55.880) | Penilaian final di pusat — **lebih granular (KRITIKAL)**, tapi 30% NULL |
| `kesimpulan_penilaian_akhir` | `MK` (67.920), `TMK` (51.654), NULL (64.379) | Verdict gabungan final — **paling ringkas**, tanpa severity grade |

**§3-MK-TMK**: 
- `MK` = **Memenuhi Keputusan** (iklan sesuai, lulus pengawasan)
- `TMK` = **Tidak Memenuhi Keputusan** (iklan melanggar, gagal pengawasan)
- Severity grade: `MINOR` < `MAYOR` < `KRITIKAL` (hanya di TMK)

**§3-DEFAULT**: Kalau user nanya "yang lulus vs gagal" tanpa specify tingkat → pakai `kesimpulan_penilaian_akhir`, filter `IS NOT NULL` (64.379 baris tidak punya verdict akhir).

**§3-CLOSURE**: "TMK" sebagai keluarga di kolom pusat/balai = gabungan `TMK`, `TMK MINOR`, `TMK MAYOR`, `TMK KRITIKAL`. **Jangan hitung cuma `TMK` mentah** kecuali user explicit minta exact value. Closure set:
- balai TMK family = `{'TMK', 'TMK MAYOR', 'TMK MINOR'}`
- pusat TMK family = `{'TMK', 'TMK KRITIKAL', 'TMK MAYOR', 'TMK MINOR'}`

## §4 — Komoditi (verified, 7 kategori)

| `komoditi` | Count | % dari total |
|---|---|---|
| KOSMETIKA | 48.325 | 26.3% |
| ROKOK | 40.031 | 21.8% |
| PRODUK PANGAN | 33.765 | 18.4% |
| OBAT | 32.180 | 17.5% |
| OBAT TRADISIONAL (OT) | 19.001 | 10.3% |
| SUPLEMEN KESEHATAN | 7.820 | 4.3% |
| OBAT KUASI | 2.831 | 1.5% |

**§4-EXACT**: Komoditi text exact-match. Case-sensitif di query — gunakan `WHERE komoditi = 'KOSMETIKA'` (uppercase). Tidak ada kode, hanya label.

**§4-CLOSURE**: "Produk farmasi" (informal) = `OBAT` ∪ `OBAT TRADISIONAL (OT)` ∪ `SUPLEMEN KESEHATAN` ∪ `OBAT KUASI`. **KLARIFIKASI** kalau user pakai istilah informal — jangan asumsi.

## §5 — Media iklan & jenis pembuat (verified)

`media_iklan`:
- `ELEKTRONIK` (98.067)
- `MEDIA_LUARRUANG` (56.062)
- `CETAK` (25.027)
- `MEDIA_LAIN` (3.825)
- empty/NULL (972)

`jenis_pembuat_iklan`:
- empty/NULL (150.188) ← **82% kosong, HAMPIR TIDAK USABLE**
- `PELAKU USAHA` (29.281)
- `PERORANGAN` (4.484)

**§5-WARNING**: Kolom `jenis_pembuat_iklan` jangan dipakai sebagai filter utama — kebanyakan kosong. Kalau user nanya "berdasarkan pembuat iklan", katakan jujur hanya 18% data yang punya info ini.

## §6 — Pendaftar cleansing (anti-corrupt-string)

Beberapa baris `pendaftar` berisi string diduplikasi tanpa delimiter (ETL artifact dari RPO). Contoh:
- `PT PHAROS INDONESIAPT PHAROS I` → seharusnya `PT PHAROS INDONESIA`
- `PJ  GUNA SEHAT  CILACAPPJ  GUN` → seharusnya `PJ GUNA SEHAT CILACAP`

**§6-RULE**: `COUNT(DISTINCT pendaftar)` is raw diagnostic only. Corrupt duplicated strings can split one company into multiple values and make the result unsuitable as a company count. Before presenting a company metric, require an approved normalization mapping; otherwise label the result raw and do not call it a cleansed count.
```sql
-- Heuristik sederhana: kalau string >40 char dan dua bagian menyerupai, potong setengah
-- Untuk auditable result, lebih baik tampilkan TOP pendaftar dengan manual review
SELECT pendaftar, COUNT(*) FROM mv_pengawasan
WHERE pendaftar IS NOT NULL AND pendaftar <> ''
GROUP BY 1 ORDER BY 2 DESC LIMIT 50;
```
If no mapping exists, say "pendaftar unik raw" and disclose the ETL quality limitation.

## §7 — Date columns (4 jenis, beda konteks)

| Kolom | Tipe | Range verified | Untuk apa |
|---|---|---|---|
| `tgl_start` | date | 2023-01-01 → 2026-08-31 | Tanggal mulai pengawasan |
| `tgl_end` | date | 2023-01-01 → 2026-08-31 | Tanggal selesai pengawasan |
| `sync` | timestamp | seragam 2026-08-10 22:53:15 | Snapshot ETL — JANGAN dipakai sebagai tanggal bisnis |
| `tanggal_proses` (log) | timestamp | dinamis per status | Waktu transisi status di log |
| `tanggal_kirim_kabalai/direktur/pusat` (timeline) | date | bervariasi | Milestone pipeline |

**§7-DEFAULT**: Untuk trend tahunan/bulanan → pakai `tgl_start` dengan an explicit null guard. In the audited snapshot both start and end were non-null, but do not turn that observation into a permanent schema rule.

**§7-RANGE**: Range data 2023-01-01 → 2026-08-31. **Tahun 2026 baru sampai Agustus** — jangan tampilkan angka 2026 sebagai "tahun penuh" tanpa konteks partial-year.

## §8 — Ketidaksesuaian klasifikasi (6 kategori tetap, dari `keterangan_ketidaksesuaian`)

| `id_klasifikasi` | Klasifikasi | Count |
|---|---|---|
| 1 | Iklan produk yang tidak boleh diiklankan (minuman beralkohol dll) | 499 |
| 2 | Iklan dengan klaim kesehatan yang tidak sesuai | **3.345** ← terbesar |
| 3 | Iklan menyesatkan (tidak sesuai karakteristik/komposisi) | 1.865 |
| 4 | Iklan melanggar norma (adegan berbahaya dll) | 88 |
| 5 | Iklan superlatif/komparatif/mendiskreditkan | 2.068 |
| 6 | Iklan dengan kata/figure/logo/lambang yang tidak boleh | 1.203 |

Total: 9.068 baris ketidaksesuaian, dari 7.257 distinct id pengawasan (3.6% dari 172.165 event).

**§8-RULE**: Klaim_kesehatan (klasifikasi 2) selalu dominates. Kalau user nanya "pelanggaran terbanyak", jawab klasifikasi 2 dengan angka spesifik.

## §9 — Pivot (verified)

- **84 balai** di `mv_pengawasan.nama_balai`. Distinct nama balai case-sensitif.
- **76 distinct balai names** di `target_balai` versus 84 di main. This difference is not a reliable unmatched count: exact name matching currently identifies 22 target names (154 target rows) without a main match.
- **668 rows** di `coverage_balai` = 84 balai × rata-rata ~8 kabupaten per balai.

## §10 — NULL date guard untuk GROUP BY tanpa range

Saat GROUP BY tanpa WHERE tanggal, beberapa baris mungkin NULL:
```sql
SELECT komoditi, COUNT(*) FROM mv_pengawasan
WHERE tgl_start IS NOT NULL  -- guard
GROUP BY 1 ORDER BY 2 DESC;
```
`tgl_start` hampir selalu terisi (verifikasi: `SELECT COUNT(*) FROM mv_pengawasan WHERE tgl_start IS NULL` ≈ 0).

## §11 — Test data (apakah ada?)

**Belum teridentifikasi sentinel akun test** seperti neo's `test_*` di trader_id. Sebelum asumsi bersih, jalankan satu kali per session:
```sql
SELECT nama_balai, COUNT(*) FROM mv_pengawasan
GROUP BY 1 HAVING COUNT(*) < 5 ORDER BY 1;  -- balai dengan count sangat kecil = kandidat test
```
Laporkan hasilnya di jawaban kalau ada yang suspicious.

## §12 — Answer contract

- Bahasa user.
- Setiap angka dilabeli dengan **kode + deskripsi**: "`MK` (Memenuhi Keputusan)".
- Split per kategori (komoditi/verdict/balai) bukan satu angka glob.
- Period × kategori table dari **SATU closing GROUP BY** — bukan dijahit dari multiple query.
- Headline total dari **DISTINCT query sendiri** (mis. `COUNT(DISTINCT id)`), bukan dijumlah dari breakdown (breakdown by-komoditi akan over-count karena 1 id bisa muncul di 2 komoditi — jarang, tapi mungkin).
- Jika angka estafet di follow-up, sebutkan apa yang dipegang (entity, range, scope).
