# 00 — Connection Contract & Smoke Test (Mencegah Kegagalan Mode "Tidak Temukan Tabel")

> **Latar belakang**: Pada satu sesi IBA, agen ditanya *"Bagaimana hasil pengawasan iklan selama periode 2026?"* dan menjawab **"Data tidak ditemukan, Jumlah Kejadian: 0, hanya skema sistem terdeteksi"** setelah 25 langkah thrashing selama 54.6 detik. Jawaban yang benar seharusnya **27.620 event** (8.858 MK / 5.296 TMK / 13.466 belum dinilai). File ini mencegah kegagalan itu terulang.

## Akar masalah kegagalan tersebut

Bukan masalah "connection refused". Akar masalahnya **penulisan context/skill yang tidak memberi agen prosedur terstruktur** saat query pertama gagal, sehingga agen fallback ke schema discovery yang salah metode (`information_schema.tables` bersifat **privilege-aware** → menampilkan 0 tabel kalau role tak di-grant → agen salah menyimpulkan "tidak ada tabel operasional").

## Aturan koneksi (connection contract)

| Item | Spesifikasi |
|---|---|
| Database name | **`pengawasan`** (bukan `postgres`, bukan `template1`) |
| Schema bisnis | **`public`** (default `search_path`). JANGAN query dari `dimension` — itu reruntuhan star-schema (lihat `01_arsitektur_dan_grain.md`) |
| Tabel bisnis (hardcoded) | **7 tabel**, selalu di `public`: `mv_pengawasan`, `mv_pengawasan_log`, `mv_pengawasan_timeline`, `mv_pengawasan_agg`, `mv_pengawasan_ketidaksesuaian`, `coverage_balai`, `target_balai` |
| Role | Harus punya grant SELECT. Saat ini **hanya `postgres`** yang di-grant. Role `readonly_user` **TIDAK punya grant** → jangan dipakai |
| Connection string format | `postgresql://<role>:<password>@<host>:<port>/pengawasan` |

**Jangan pernah** menganggap koneksi "supplied by runtime" tanpa verifikasi. Verifikasi adalah langkah eksplisit.

## Smoke test WAJIB di awal turn (Gate 0.5)

Sebelum menjawab pertanyaan data apapun, jalankan SATU query ini:

```sql
SELECT COUNT(*) AS smoke_main FROM mv_pengawasan;
```

**Aturan baca hasil smoke test**:

| Hasil | Interpretasi | Aksi |
|---|---|---|
| Angka besar (≈183.000) | Koneksi OK, tabel benar, role benar | Lanjut ke Gate 1 |
| Error `relation "mv_pengawasan" does not exist` | Salah database / salah schema | **STOP**. Cek: apakah connect ke DB `pengawasan`? Apakah `search_path` include `public`? |
| Error `permission denied` | Role tak di-grant | **STOP**. Ganti role ke yang punya SELECT |
| Angka 0 | Tabel ada tapi kosong (sangat tidak normal) | **STOP**. Laporkan: "tabel ada tapi 0 baris, kemungkinan ETL gagal load" |
| Timeout / connection error | Masalah jaringan/tunnel | **STOP**. Laporkan masalah koneksi secara plain |

**Jangan lanjut ke pertanyaan user sebelum smoke test menghasilkan angka besar.** Kegagalan smoke test = akar masalah, BUKAN dilewati dengan brute-force query lain.

## Question → table router (jalan pintas)

Untuk pertanyaan umum, **langsung** query tabel berikut (tanpa schema discovery):

| Frasa pertanyaan user | Tabel utama | Kolom kunci |
|---|---|---|
| "hasil pengawasan", "keputusan", "MK/TMK", "lulus/gagal" | `mv_pengawasan` | `kesimpulan_penilaian_akhir` (tapi baca `09` — hanya 3 komoditi) |
| "jumlah pengawasan" | `mv_pengawasan` | `COUNT(*)` (baris) / `COUNT(DISTINCT id)` (event) — KLAIRFIKASI dulu |
| "berapa produk", "produk unik" | `mv_pengawasan` | `nama_produk`, `nie` |
| "alur", "status", "sudah selesai", "ditolak" | `mv_pengawasan_log` | `status_code`, `trx_steps` (999 = final) |
| "berapa lama", "durasi", "SLA", "kapan selesai" | `mv_pengawasan_timeline` | `mulai_kabalai`, `kabalai_direktur` — HINDARI `direktur_pusat` (flag, bukan durasi) |
| "target", "capaian", "realisasi vs target" | `target_balai` + `mv_pengawasan` | hanya tahun 2024 |
| "pelanggaran", "ketidaksesuaian", "klaim kesehatan" | `mv_pengawasan_ketidaksesuaian` | `id_klasifikasi` — hanya PRODUK PANGAN |
| "trend bulanan", "per bulan" | `mv_pengawasan_agg` (basis `tgl_end`) atau `mv_pengawasan` (basis `tgl_start`) |
| "wilayah balai", "kabupaten" | `coverage_balai` | join via `nama_balai` (UPPER kanan-kiri) |

## Router vocabulary user → kolom DB (dari 340 pertanyaan production)

User production TIDAK pakai nama kolom. Petakan frasa operasional ke kolom SEBELUM query (sumber lengkap: `14_pola_pertanyaan_user_dan_vocabulary.md`):

| Frasa user | Kolom DB | SQL |
|---|---|---|
| **UPT** | `nama_balai` | `GROUP BY nama_balai` |
| **obat keras** | `komoditi = 'OBAT'` | `WHERE komoditi='OBAT'` |
| **hasil verifikasi pusat** | `kesimpulan_penilaian_pusat` | `WHERE ... <> 'Null'` |
| **hasil verifikasi balai** | `kesimpulan_penilaian_balai` | `WHERE ... <> 'Null'` |
| **mk / tmk** | nilai verdict | `IN ('MK','TMK','TMK KRITIKAL','TMK MAYOR','TMK MINOR')` |
| **tanggal sampling / pemeriksaan** | `tgl_start` | `WHERE tgl_start BETWEEN ...` |
| **tanggal kepala balai** | `tanggal_kirim_kabalai` (timeline) | — |
| **tanggal direktur** | `tanggal_kirim_direktur` (timeline) | — |
| **klausul pelanggaran** | `mv_pengawasan_ketidaksesuaian` | JOIN main via `id` |
| **label / label pangan** | `komoditi = 'PRODUK PANGAN'` | `WHERE komoditi='PRODUK PANGAN'` |

**Frasa yang HARUS dijawab honest "tidak tersedia" (JANGAN query, JANGAN fabrikasi):**

| Frasa | Jawaban singkat |
|---|---|
| sarana produksi / produsen | `pendaftar` = registrant, BUKAN produsen. Data tidak ada di DB pengawasan |
| jenis pangan / kategori pangan | Ada di database `neo`, bukan pengawasan |
| provinsi | Hanya `kabupaten_kota` di coverage_balai |
| cek BPOM / cekb pom | Sistem eksternal |
| SIAPik | Sistem eksternal |
| BKO (bahan kimia obat) | Kolom tidak ada |

Detail honest response lengkap: `15_ekspektasi_informasi_dan_boundary.md`.

## Metode schema discovery yang andal (jika harus discover)

**DILARANG** memakai `information_schema.tables` untuk discovery — itu **privilege-aware**: hanya menampilkan tabel yang current user punya hak SELECT. Jika role tak di-grant → 0 baris → salah simpul.

**Pakai `pg_catalog`** (selalu visible ke semua role):

```sql
-- Discovery yang ANDAL: list semua tabel di schema public via pg_catalog
SELECT n.nspname AS schema, c.relname AS table_name, c.relkind
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY 1, 2;
-- Harusnya kembali 7 baris (mv_pengawasan, mv_pengawasan_log, ...)
```

```sql
-- Verifikasi kolom juga via pg_catalog (bukan information_schema.columns)
SELECT a.attname AS column_name, format_type(a.atttypid, a.atttypmod) AS data_type
FROM pg_catalog.pg_attribute a
JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'mv_pengawasan' AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY a.attnum;
```

## Peringatan: `mv_` adalah regular table, BUKAN materialized view

Semua 7 tabel di `public` punya `relkind = 'r'` (regular table), bukan `'m'` (materialized view). Verifikasi:

```sql
SELECT relname, relkind FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND relkind IN ('r','m','v');
-- Semua harus 'r'
```

**Konsekuensi**:
- Tidak ada `REFRESH MATERIALIZED VIEW`. Isi di-update oleh ETL eksternal via drop+load.
- Tidak ada index, FK, atau constraint yang dideklarasikan — semua join bersifat **logical**, harus diingat manual.
- `id` di `mv_pengawasan` BUKAN primary key (grain-nya per produk, bukan per event — lihat `01`).

## Anti-pattern yang menyebabkan kegagalan

| Anti-pattern | Akibat |
|---|---|
| Skip smoke test, langsung query kompleks | Kalau koneksi salah, 25 langkah thrashing tanpa diagnose |
| Discovery via `information_schema.tables` | 0 baris kalau role salah → salah simpul "tidak ada tabel" |
| Asumsi `mv_*` = materialized view | Cari di `pg_matviews`, tidak ketemu, bingung |
| Connect ke database `postgres` (default) | `public` schema kosong → "tidak ada tabel operasional" |
| Pakai role `readonly_user` | Tidak ada grant SELECT → semua query permission denied |
| Query `dimension.*` | Data rusak/parcial — lihat `01` |

## Checklist awal turn (salin ke setiap sesi baru)

1. [ ] Connect ke DB `pengawasan` dengan role yang punya grant
2. [ ] Smoke test: `SELECT COUNT(*) FROM mv_pengawasan` → harus ≈183.000
3. [ ] Klasifikasi pertanyaan → route ke tabel (lihat router di atas)
4. [ ] Baca `context/predikat.md` §1 untuk entity counting (baris/event/surat berbeda!)
5. [ ] Jika pertanyaan verdict → baca `09_verdict_rules_reversal.md` (aturan `akhir` per komoditi)
6. [ ] Query evidence (max 4 SQL/turn per skill contract)

## Bukti: jawaban yang BENAR untuk kasus kegagalan

Pertanyaan: *"Bagaimana hasil pengawasan iklan selama periode 2026?"*
Klarifikasi: Jumlah Event × Kesimpulan Penilaian Akhir.

```sql
SELECT kesimpulan_penilaian_akhir AS verdict,
       COUNT(DISTINCT id) AS jumlah_event,
       COUNT(*) AS jumlah_baris
FROM mv_pengawasan
WHERE EXTRACT(YEAR FROM tgl_start) = 2026
GROUP BY 1 ORDER BY 2 DESC;
```

Hasil (snapshot 2026-08-12):

| verdict | jumlah_event | jumlah_baris | % event |
|---|---|---|---|
| `Null` (belum difinalisasi) | 13.466 | 13.466 | 48.8% |
| `MK` (Memenuhi Ketentuan) | 8.858 | 10.027 | 32.1% |
| `TMK` (Tidak Memenuhi Ketentuan) | 5.296 | 5.432 | 19.2% |
| **Total** | **27.620** | **28.925** | 100% |

Periode 2026-01-01 → 2026-08-31 (8 bulan, tahun parsial). Catatan wajib: 48.8% verdict 'Null' karena 4 komoditi (PANGAN/OT/SUPLEMEN/KUASI) tidak pernah sinkron kolom `akhir` — bukan berarti "belum dinilai" dalam arti proses.
