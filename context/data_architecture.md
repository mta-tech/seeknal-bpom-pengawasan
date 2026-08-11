# DATABASE STRUCTURE MAP — TABLE INVENTORY, COUNTING GRAIN, JOIN RULES, WORKFLOW TOPOLOGY

Domain: **Pengawasan Iklan BPOM** (bukan registrasi pangan — domain itu ada di `seeknal-bpom-neo`).
Source: data disync dari sistem RPO (sumber asli), lalu dituangkan ke tabel-tabel di sini.
**Snapshot terakhir**: `sync = 2026-08-10 22:53:15` (semua tabel disync serempak kecuali `last_updated` di agg).
**Cakupan waktu data**: `tgl_start`/`tgl_end` 2023-01-01 → 2026-08-31.

## Naming lie: `mv_*` adalah tabel biasa, BUKAN materialized view

Semua 7 relasi di schema `public` memiliki `relkind='r'` (regular table) di `pg_catalog` — verifikasi:
```sql
SELECT relname, relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND relkind IN ('r','m','v');
```
Konsekuensi:
- Tidak ada `REFRESH MATERIALIZED VIEW` — isi di-update oleh ETL dari RPO lewat kolom `sync`.
- Tidak ada index, FK, atau constraint yang dideklarasikan — semua join bersifat **logical**, harus diingat, bukan diharapkan dari schema.
- Jangan pernah berasumsi `id` adalah PK hanya karena namanya — lihat § counting grain.

## Tables

| Table | Coverage | Rows (verified) | Notes |
|---|---|---|---|
| `mv_pengawasan` | Jan 2023 → Aug 2026 | **183.953 baris** | Tabel utama. **Grain = 1 baris per (pengawasan × produk)** — bukan per pengawasan, bukan per surat. |
| `mv_pengawasan_log` | Jan 2023 → Aug 2026 | **1.816.774 baris** | Log per status transition. Banyak baris per `id_pengawasan`. **Punya 236.856 distinct id > 172.165 distinct id di main** → ada id historis yang sudah hilang dari main. |
| `mv_pengawasan_timeline` | Jan 2023 → Aug 2026 | **236.856 baris** | Sama dengan log: lebih banyak dari main. Berisi tanggal pipeline + 3 kolom durasi hari. |
| `mv_pengawasan_agg` | Jan 2023 → Aug 2026 | **118.114 baris** | Pre-aggregated per `(periode_type, tanggal_periode, komoditi, nama_balai, media_iklan, jenis_pembuat_iklan, kesimpulan_*)`. Dua `periode_type`: `day` (70.736 rows), `month` (47.378 rows). |
| `mv_pengawasan_ketidaksesuaian` | Jan 2023 → Aug 2026 | **9.068 baris** | Non-conformity per `id_pengawasan`. 7.257 distinct id. 6 klasifikasi tetap (lihat `filter_code_reference.md` §3). |
| `coverage_balai` | master | **668 baris** | Balai → kabupaten/kota (many-to-many). 84 balai, banyak kabupaten per balai. |
| `target_balai` | tahun 2024 saja | **532 baris** | Target tahunan per `(nama_balai, komoditi, tahun)`. 76 balai × 7 komoditi × 1 tahun. **Hanya 2024 — tidak ada target 2025/2026.** |

## Identities & grain hierarchy (WAJIB tahu sebelum ngomong "jumlah")

```
nomor_surat (≈9.738 unik non-empty)
    └── id pengawasan event (172.165 distinct id di main; baris bisa dup untuk id sama)
            └── nama_produk + nie (183.953 baris = grain sebenarnya dari mv_pengawasan)
```

**Satu surat pengawasan bisa mengecek banyak produk.** Contoh nyata: `id=195924` punya **40 baris** dengan 40 NIE berbeda. Avg 16.58 produk per surat (ter-skew: top surat punya 1.304 produk).

## Counting entities — semua berbeda, semua legitimate, semua harus disebut

| Pertanyaan | Hitung di | Query |
|---|---|---|
| Berapa baris produk pengawasan | `mv_pengawasan` | `COUNT(*)` |
| Berapa event pengawasan | `mv_pengawasan` | `COUNT(DISTINCT id)` |
| Berapa surat pengawasan | `mv_pengawasan` | `COUNT(DISTINCT nomor_surat)` **dengan filter sentinel** |
| Berapa produk unik | `mv_pengawasan` | `COUNT(DISTINCT nama_produk)` |
| Berapa NIE unik | `mv_pengawasan` | `COUNT(DISTINCT nie) FILTER (WHERE nie <> '--')` |
| Berapa pendaftar unik | `mv_pengawasan` | `COUNT(DISTINCT pendaftar)` (perlu cleansing, lihat § di bawah) |
| Berapa balai | `mv_pengawasan` | `COUNT(DISTINCT nama_balai)` = **84** |

Untuk angka yang verified per snapshot 2026-08-10, lihat `predikat.md` §1.

## Joins (semua logical — tidak ada FK di schema)

- **`mv_pengawasan.id` ↔ `mv_pengawasan_log.id_pengawasan`** — banyak log per pengawasan (timeline status). **INNER JOIN akan drop 0 baris** karena log punya superset id (236.856 > 172.165). LEFT JOIN dari main aman; RIGHT/INNER dari log akan menampilkan id historis yang tidak ada di main.
- **`mv_pengawasan.id` ↔ `mv_pengawasan_timeline.id_pengawasan`** — sama dengan log. Satu baris timeline per id (236.856 = jumlah id timeline, ini grain 1:1 dengan log distinct id).
- **`mv_pengawasan.id` ↔ `mv_pengawasan_ketidaksesuaian.id_pengawasan`** — hanya 7.257 id yang punya ketidaksesuaian (3.6% dari total). **LEFT JOIN dari main**; INNER JOIN akan drop 96% data.
- **`mv_pengawasan_agg`** — TIDAK ada id. Join via `(periode_type, tanggal_periode, komoditi, nama_balai, ...)`. Gunakan langsung tanpa join kalau bisa — angka di agg sudah pre-computed untuk Q "berapa pengawasan per bulan per komoditi".
- **`coverage_balai.nama_balai`** ↔ `mv_pengawasan.nama_balai` — many-to-many (satu balai → banyak kabupaten). Jangan join kalau hanya butuh daftar balai (langsung `SELECT DISTINCT nama_balai FROM mv_pengawasan`).
- **`target_balai.nama_balai`** ↔ `mv_pengawasan.nama_balai` — perlu cleansing nama balai (case-insensitive match direkomendasikan).

## Workflow topology — pipeline kabalai → direktur → pusat

Status transisi ada di `mv_pengawasan_log` (kronologis per `tanggal_proses`) dan dirangkum di `mv_pengawasan_timeline` (tanggal milestone + durasi).

```
[0] Operator - Draft Sampling
[1] Supervisor - Verifikasi
[2] Supervisor 2 - Verifikasi
[3] TPS - Penerimaan SPU
[4] MT - Pembuatan SPK
[5] Deputi MT - Pembuatan SPK
[6] Penyelia - Pembuatan SPP
[7] Penguji - Entri Hasil Pengujian
...990-997 (transitional/special — label kosong, count kecil)
[999] Sampel Rujukan Selesai  ← final state
```

Mapping `status_code` → `status_label` lengkap ada di `filter_code_reference.md` §2.

**Tiga kolom durasi di timeline (semua dalam HARI):**
- `mulai_kabalai` — dari mulai sampai kirim ke kabalai (median **8 hari**, max 740)
- `kabalai_direktur` — kabalai ke direktur (median **18 hari**, max 1.551 — ada outlier 4 tahun)
- `direktur_pusat` — direktur ke pusat (median **0**, max 1 — kemungkinan jarang terisi atau auto-fill saat selesai)

**Trap durasi:** `direktur_pusat` yang 0 di mayoritas baris TIDAK berarti prosesnya cepat — bisa berarti **tanggal_kirim_pusat belum terisi**. Selalu cek `WHERE tanggal_kirim_pusat IS NOT NULL` sebelum hitung avg/median durasi pusat.

## Sentinels & data quality (HARUS diexclude dari ranking, dilaporkan terpisah)

Sama seperti `0`/`9999`/`''` di neo — di sini:

| Kolom | Sentinel | Count | Arti |
|---|---|---|---|
| `nomor_surat` | `NULL`, `''`, `'-'` | **49.050 baris** | Tidak ada nomor surat (kemungkinan pengawasan langsung tanpa surat formal) |
| `nie` | `NULL`, `'--'` | **45.429 baris** | Produk diiklankan tanpa NIE (bukan kesalahan — ini sengaja, jadi angka penting) |
| `pendaftar` | `NULL`, `''` | **44.775 baris** | Pendaftar tidak tercatat |
| `nama_produk` | `NULL`, `''` | **25 baris** | Sangat jarang — bisa diabaikan |
| `jenis_pembuat_iklan` | `NULL`, `''` | **150.188 baris** | Kolom ini 82% kosong — hampir tidak usable untuk filter |

**`pendaftar` corrupt data:** beberapa baris punya string diduplikasi tanpa delimiter, contoh:
- `PT PHAROS INDONESIAPT PHAROS I` (string sama diconcat ke dirinya sendiri)
- `PJ  GUNA SEHAT  CILACAPPJ  GUN`

 Ini artifact ETL dari RPO. **Jangan gunakan `COUNT(DISTINCT pendaftar)` langsung tanpa cleansing** — angka akan undercount akibat string corrupt. Lihat `predikat.md` §6 untuk cleansing rule.

## Finding a dimension this file does not list

Tidak ada `data_dictionary` di database ini (beda dengan neo). Semua kode sudah dilabeli (ada `status_label`, `keterangan_ketidaksesuaian`, dst). Aturan:

1. **Kode di sini sudah punya label** — tidak perlu lookup tabel. Tapi tetap sebutkan label + kode di jawaban: "`MK` (Memenuhi Keputusan)", bukan cuma "`MK`".
2. **Dimensi yang tidak ada di file ini = tidak ada di tabel.** Jangan fabriase kolom `provinsi`, `klaim`, atau `risk_grade` — kolom itu tidak ada. Cek `pg_catalog.pg_attribute` dulu kalau ragu.
3. **Free text (`nama_produk`, `pendaftar`):** ILIKE untuk discover, lalu filter exact. Tapi ingat corrupt-string trap di `pendaftar`.

## Refresh lag

Kolom `sync` seragam = 2026-08-10 22:53:15 di semua tabel utama. `last_updated` di `mv_pengawasan_agg` juga. **Data kemarin (hari ini = 2026-08-11) belum ada** — jawab dengan range terverifikasi, jangan ekstrapolasi.

## Tools

File ini = planning map. `pg_catalog.pg_attribute` selalu readable walau user restricted — gunakan untuk verify nama kolom sebelum query kompleks.
