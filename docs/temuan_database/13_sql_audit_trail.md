# 13 — SQL Audit Trail (Semua Query Reproducible)

> File ini berisi **semua query** yang menghasilkan angka di dokumentasi `temuan_database/`. Setiap klaim bisa diverifikasi ulang dengan menjalankan query di sini. Snapshot: **2026-08-12 23:23** (refresh harian, angka dapat geser ±sedikit).

## Konvensi

- Semua query asumsikan koneksi ke database `pengawasan`, schema `public`.
- Ganti `<DB>` dengan connection string Anda: `postgresql://<role>:<pass>@<host>:<port>/pengawasan`.
- Jalankan via `psql "<DB>" -c "..."` atau client SQL pilihan.

## §00 — Smoke test & verifikasi koneksi

```sql
-- Smoke test utama (harus kembali angka besar ≈183.000)
SELECT COUNT(*) AS smoke_main FROM mv_pengawasan;

-- Verifikasi snapshot
SELECT MAX(sync) AS main_sync, COUNT(*) AS rows FROM mv_pengawasan;

-- Verifikasi role punya grant
SELECT grantee, table_name, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema='public' AND privilege_type='SELECT';
-- Harusnya muncul 7 baris untuk role Anda

-- Discovery andal via pg_catalog (privilege-AGNOSTIC)
SELECT n.nspname AS schema, c.relname AS table_name, c.relkind
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname='public' AND c.relkind='r'
ORDER BY 1,2;
-- Harusnya 7 baris: mv_pengawasan, mv_pengawasan_log, mv_pengawasan_timeline,
-- mv_pengawasan_agg, mv_pengawasan_ketidaksesuaian, coverage_balai, target_balai
```

## §01 — Arsitektur & grain

```sql
-- Inventory kolom semua tabel public
SELECT table_name, ordinal_position, column_name, data_type
FROM information_schema.columns
WHERE table_schema='public' ORDER BY table_name, ordinal_position;

-- Entity counting (5 entitas berbeda)
SELECT
  COUNT(*) AS baris,
  COUNT(DISTINCT id) AS event_unik,
  COUNT(DISTINCT NULLIF(NULLIF(NULLIF(nomor_surat,'-'),''),'')) AS surat_unik,
  COUNT(DISTINCT nama_produk) AS produk_unik,
  COUNT(DISTINCT nie) FILTER (WHERE nie NOT IN ('','--','-')) AS nie_unik,
  COUNT(DISTINCT pendaftar) AS pendaftar_raw
FROM mv_pengawasan;

-- Produk ↔ NIE many-to-many
SELECT
  (SELECT COUNT(*) FROM (SELECT nama_produk FROM mv_pengawasan WHERE nama_produk<>'' AND nie NOT IN ('','--','-') GROUP BY 1 HAVING COUNT(DISTINCT nie)>1) x) AS produk_mult_nie,
  (SELECT COUNT(*) FROM (SELECT nie FROM mv_pengawasan WHERE nie NOT IN ('','--','-') GROUP BY 1 HAVING COUNT(DISTINCT nama_produk)>1) y) AS nie_mult_produk;

-- Multi-product per komoditi
WITH x AS (SELECT id, komoditi, COUNT(*) AS rows FROM mv_pengawasan GROUP BY 1,2)
SELECT komoditi,
  COUNT(*) FILTER (WHERE rows=1) AS satu_produk,
  COUNT(*) FILTER (WHERE rows BETWEEN 2 AND 5) AS "2-5",
  COUNT(*) FILTER (WHERE rows BETWEEN 6 AND 20) AS "6-20",
  COUNT(*) FILTER (WHERE rows>20) AS lebih20,
  MAX(rows) AS max_produk
FROM x GROUP BY 1 ORDER BY 2 DESC;

-- Id ghost per tahun (di timeline tak di main)
SELECT EXTRACT(YEAR FROM t.tgl_start)::int AS tahun, COUNT(*) AS n
FROM mv_pengawasan_timeline t
WHERE NOT EXISTS (SELECT 1 FROM mv_pengawasan p WHERE p.id=t.id_pengawasan)
GROUP BY 1 ORDER BY 1;

-- Dimension schema rusak (buktinya)
SELECT n.nspname, c.relname, pg_stat_get_live_tuples(c.oid) AS live_rows
FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid
WHERE n.nspname='dimension' AND c.relkind='r' ORDER BY 1,2;
```

## §02 — mv_pengawasan detail

```sql
-- Profil kolom (null/empty/distinct)
SELECT 'id' col, COUNT(*)::text rows, COUNT(id)::text notnull,
       (COUNT(*) FILTER (WHERE id IS NULL))::text null_cnt,
       COUNT(DISTINCT id)::text distinct_v, MIN(id)::text, MAX(id)::text
FROM mv_pengawasan;
-- Ulangi per kolom lain (nomor_surat, komoditi, nama_balai, dst.)

-- Komoditi (7 nilai)
SELECT komoditi, COUNT(*) FROM mv_pengawasan GROUP BY 1 ORDER BY 2 DESC;

-- NIE prefix × komoditi (taksonomi multi)
SELECT LEFT(UPPER(nie),2) AS prefix, COUNT(DISTINCT komoditi) AS n_kom,
       array_agg(DISTINCT komoditi) AS komo
FROM mv_pengawasan WHERE nie ~ '^[A-Za-z]{2}'
GROUP BY 1 ORDER BY 1;

-- Sentinel NIE per komoditi
SELECT komoditi, COUNT(*) total,
       COUNT(*) FILTER (WHERE nie IN ('','--','-')) sentinel,
       ROUND(100.0*COUNT(*) FILTER (WHERE nie IN ('','--','-'))/COUNT(*),1) pct
FROM mv_pengawasan GROUP BY 1 ORDER BY 2 DESC;

-- media_iklan × komoditi
SELECT komoditi,
  COUNT(*) FILTER (WHERE media_iklan='ELEKTRONIK') AS elektronik,
  COUNT(*) FILTER (WHERE media_iklan='MEDIA_LUARRUANG') AS luar_ruang,
  COUNT(*) FILTER (WHERE media_iklan='CETAK') AS cetak
FROM mv_pengawasan GROUP BY 1 ORDER BY 1;

-- lokasi_iklan struktur 2-field
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE lokasi_iklan ~ E'^"[^"]+""[^"]+"$') AS dua_bagian,
  COUNT(*) FILTER (WHERE lokasi_iklan ~ E'^"[^"]+"$') AS satu_bagian_quote,
  COUNT(*) FILTER (WHERE lokasi_iklan ~ '^https?://') AS url_murni,
  COUNT(*) FILTER (WHERE lokasi_iklan='' OR lokasi_iklan='-') AS empty_dash
FROM mv_pengawasan;

-- Top domain di lokasi_iklan (bagian 2)
WITH x AS (
  SELECT (regexp_match(lokasi_iklan, E'^"[^"]+""(.*)"$'))[1] AS detail
  FROM mv_pengawasan WHERE lokasi_iklan ~ E'^"[^"]+""'
)
SELECT substring(detail from '://([^/"]+)') AS host, COUNT(*) n
FROM x WHERE detail LIKE '%://%' GROUP BY 1 ORDER BY 2 DESC LIMIT 15;

-- jenis_pembuat_iklan (EKSKLUSIF PANGAN)
SELECT komoditi,
  COUNT(*) FILTER (WHERE jenis_pembuat_iklan<>'') AS terisi,
  COUNT(*) total
FROM mv_pengawasan GROUP BY 1 ORDER BY 1;

-- pendaftar self-concat (inflasi)
SELECT COUNT(DISTINCT pendaftar) AS mentah,
       COUNT(DISTINCT regexp_replace(upper(pendaftar),'[^A-Z0-9]','','g')) AS normal_kasar
FROM mv_pengawasan WHERE pendaftar IS NOT NULL AND pendaftar<>'';

SELECT COUNT(*) AS gandaan FROM mv_pengawasan
WHERE LENGTH(pendaftar)%2=0 AND LENGTH(pendaftar)>6
  AND LEFT(pendaftar,LENGTH(pendaftar)/2)=RIGHT(pendaftar,LENGTH(pendaftar)/2);

-- nomor_surat 7 pola
SELECT CASE
  WHEN nomor_surat='' THEN 'EMPTY'
  WHEN nomor_surat='-' THEN 'SINGLE_DASH'
  WHEN nomor_surat='0' THEN 'ZERO'
  WHEN nomor_surat LIKE '-PW.%' THEN 'DASH_PW'
  WHEN nomor_surat LIKE '-%' THEN 'DASH_LAIN'
  WHEN nomor_surat ~ ', ' THEN 'HAS_COMMA'
  WHEN nomor_surat ~ '^[A-Za-z]' THEN 'LETTER_START'
  WHEN nomor_surat ~ '^[0-9]' THEN 'DIGIT_START'
  ELSE 'OTHER' END AS kategori,
  COUNT(*) n
FROM mv_pengawasan GROUP BY 1 ORDER BY 2 DESC;

-- Verdict (3 kolom)
SELECT kesimpulan_penilaian_akhir, COUNT(*) FROM mv_pengawasan GROUP BY 1 ORDER BY 2 DESC;
SELECT kesimpulan_penilaian_balai, COUNT(*) FROM mv_pengawasan GROUP BY 1 ORDER BY 2 DESC;
SELECT kesimpulan_penilaian_pusat, COUNT(*) FROM mv_pengawasan GROUP BY 1 ORDER BY 2 DESC;
```

## §03 — log workflow

```sql
-- Dictionary status_code × label × trx_steps (lengkap)
SELECT status_code, status_label, trx_steps, COUNT(*) AS n
FROM mv_pengawasan_log
GROUP BY 1,2,3 ORDER BY 1,4 DESC;

-- Beban penolakan per tahap
SELECT status_code, COUNT(*) transisi, COUNT(DISTINCT id_pengawasan) events
FROM mv_pengawasan_log WHERE status_code BETWEEN 990 AND 997
GROUP BY 1 ORDER BY 1;

-- Event yang pernah ditolak
SELECT COUNT(*) FILTER (WHERE ada_tolak) AS pernah_ditolak, COUNT(*) total
FROM (SELECT id_pengawasan, BOOL_OR(status_code BETWEEN 990 AND 997) ada_tolak
      FROM mv_pengawasan_log GROUP BY 1) x;

-- PANGAN workflow (terminal di status 4)
SELECT l.trx_steps, l.status_code, COUNT(*) n
FROM mv_pengawasan_log l JOIN mv_pengawasan p ON p.id=l.id_pengawasan
WHERE p.komoditi='PRODUK PANGAN'
GROUP BY 1,2 ORDER BY 3 DESC;

-- Path mining (HATI-HATI: tanggal_proses NULL distorsi)
WITH seq AS (
  SELECT id_pengawasan,
         STRING_AGG(status_code::text,'>' ORDER BY tanggal_proses NULLS FIRST, status_code) AS path,
         COUNT(*) n
  FROM mv_pengawasan_log GROUP BY 1)
SELECT path, COUNT(*) events, ROUND(AVG(n)::numeric,1) AS avg_langkah
FROM seq GROUP BY 1 ORDER BY 2 DESC LIMIT 20;

-- Self-approve (draft=spv_1 orang sama)
WITH m AS (
  SELECT DISTINCT id_pengawasan, p.komoditi,
    MAX(fullname) FILTER (WHERE trx_steps='draft') AS d,
    MAX(fullname) FILTER (WHERE trx_steps='spv_1') AS s
  FROM mv_pengawasan_log l JOIN mv_pengawasan p ON p.id=l.id_pengawasan
  GROUP BY 1,2)
SELECT komoditi, COUNT(*) event_dgn_kedua,
       COUNT(*) FILTER (WHERE d=s) org_sama,
       ROUND(100.0*COUNT(*) FILTER (WHERE d=s)/COUNT(*),1) pct
FROM m WHERE d IS NOT NULL AND s IS NOT NULL GROUP BY 1 ORDER BY 4 DESC;

-- Pemutus final per komoditi
WITH x AS (
  SELECT p.komoditi, l.fullname, COUNT(*) n,
    ROW_NUMBER() OVER (PARTITION BY p.komoditi ORDER BY COUNT(*) DESC) rn
  FROM mv_pengawasan_log l JOIN mv_pengawasan p ON p.id=l.id_pengawasan
  WHERE l.trx_steps='direktur' AND l.fullname<>''
  GROUP BY 1,2)
SELECT komoditi, fullname, n FROM x WHERE rn<=2 ORDER BY komoditi;
```

## §04 — timeline

```sql
-- Konfirmasi direktur_pusat = flag
SELECT direktur_pusat, COUNT(*),
       COUNT(*) FILTER (WHERE tanggal_kirim_pusat IS NOT NULL) AS ada_tgl_pusat,
       COUNT(*) FILTER (WHERE tanggal_kirim_direktur IS NOT NULL) AS ada_tgl_direktur
FROM mv_pengawasan_timeline GROUP BY 1 ORDER BY 1;

-- Null sinkron (3 kolom direktur)
SELECT
  COUNT(*) FILTER (WHERE tanggal_kirim_direktur IS NULL) AS tgl_dir_null,
  COUNT(*) FILTER (WHERE kabalai_direktur IS NULL) AS kb_dir_null,
  COUNT(*) FILTER (WHERE direktur_pusat IS NULL) AS dir_pus_null
FROM mv_pengawasan_timeline;

-- Status distribusi timeline (status 8 & 9 aneh)
SELECT status, COUNT(*) n FROM mv_pengawasan_timeline GROUP BY 1 ORDER BY 2 DESC;

-- Durasi per komoditi
SELECT p.komoditi,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (t.tgl_end - t.tgl_start)) AS med_hari,
  PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY (t.tgl_end - t.tgl_start)) AS p90,
  COUNT(*) FILTER (WHERE t.kabalai_direktur IS NULL) AS belum_ke_direktur
FROM mv_pengawasan_timeline t JOIN mv_pengawasan p ON p.id=t.id_pengawasan
GROUP BY 1 ORDER BY 2 NULLS LAST;

-- Konsistensi tgl_start vs main
SELECT COUNT(*) FILTER (WHERE p.tgl_start<>t.tgl_start) AS tgl_start_beda,
       COUNT(*) FILTER (WHERE p.tgl_end<>t.tgl_end) AS tgl_end_beda
FROM mv_pengawasan p JOIN mv_pengawasan_timeline t ON t.id_pengawasan=p.id;
```

## §05 — agg kubus

```sql
-- Verifikasi basis agg = tgl_end (bukan tgl_start)
WITH m AS (SELECT date_trunc('month',tgl_end)::date b, COUNT(*) c FROM mv_pengawasan GROUP BY 1)
SELECT a.tanggal_periode, a.s AS agg_sum, m.c AS main_count
FROM (SELECT tanggal_periode, SUM(jumlah_pengawasan) s FROM mv_pengawasan_agg
      WHERE periode_type='month' GROUP BY 1) a
JOIN m ON m.b=a.tanggal_periode WHERE a.s <> m.c;
-- Hasil: 0 baris (cocok 100% dengan tgl_end)

-- Bandingkan dengan tgl_start (akan banyak beda)
WITH m AS (SELECT date_trunc('month',tgl_start)::date b, COUNT(*) c FROM mv_pengawasan GROUP BY 1)
SELECT COUNT(*) AS bulan_beda_dari_tgl_start
FROM (SELECT tanggal_periode, SUM(jumlah_pengawasan) s FROM mv_pengawasan_agg
      WHERE periode_type='month' GROUP BY 1) a
JOIN m ON m.b=a.tanggal_periode WHERE a.s <> m.c;

-- Total per periode_type (paralel, masing-masing 183.968)
SELECT periode_type, SUM(jumlah_pengawasan) total, COUNT(*) rows
FROM mv_pengawasan_agg GROUP BY 1;

-- Verdict rollup match main
SELECT 'akhir' k, kesimpulan_penilaian_akhir v, SUM(jumlah_pengawasan) n
FROM mv_pengawasan_agg WHERE periode_type='month' GROUP BY 2
ORDER BY 3 DESC;
```

## §06 — ketidaksesuaian

```sql
-- Dictionary 6 klasifikasi
SELECT id_klasifikasi, keterangan_ketidaksesuaian, COUNT(*) n
FROM mv_pengawasan_ketidaksesuaian GROUP BY 1,2 ORDER BY 1;

-- Multi-klasifikasi per event
SELECT cnt, COUNT(*) events FROM (
  SELECT id_pengawasan, COUNT(*) cnt FROM mv_pengawasan_ketidaksesuaian GROUP BY 1
) x GROUP BY 1 ORDER BY 1;

-- 100% PRODUK PANGAN?
SELECT string_agg(DISTINCT p.komoditi, ',')
FROM mv_pengawasan_ketidaksesuaian k JOIN mv_pengawasan p ON p.id=k.id_pengawasan;

-- Verdict balai vs ada alasan (PANGAN)
SELECT p.kesimpulan_penilaian_balai,
       COUNT(DISTINCT p.id) events,
       COUNT(DISTINCT k.id_pengawasan) punya_alasan
FROM mv_pengawasan p
LEFT JOIN mv_pengawasan_ketidaksesuaian k ON k.id_pengawasan=p.id
WHERE p.komoditi='PRODUK PANGAN' GROUP BY 1 ORDER BY 2 DESC;
```

## §07 — coverage & target

```sql
-- Coverage: blind spot balai main
SELECT DISTINCT p.nama_balai FROM mv_pengawasan p
WHERE NOT EXISTS (
  SELECT 1 FROM coverage_balai c WHERE UPPER(c.nama_balai)=UPPER(p.nama_balai))
ORDER BY 1;

-- Target: 22 unmatched (KOREKSI: sebenarnya 0)
SELECT nama_balai FROM target_balai t
WHERE NOT EXISTS (
  SELECT 1 FROM mv_pengawasan p WHERE UPPER(p.nama_balai)=UPPER(t.nama_balai))
GROUP BY 1;
-- Hasil: 0 baris

-- Target struktur regulasi
SELECT komoditi, SUM(target_penandaan) penandaan,
       SUM(target_pengawasan) pengawasan, SUM(target_pengujian) pengujian
FROM target_balai GROUP BY 1 ORDER BY 1;
```

## §08 — komoditi master axis

```sql
-- Matriks master (capstone)
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

-- Completion rate per komoditi (basis: ada baris 999)
SELECT p.komoditi,
  COUNT(DISTINCT p.id) AS events_main,
  COUNT(DISTINCT p.id) FILTER (WHERE EXISTS (
    SELECT 1 FROM mv_pengawasan_log l
    WHERE l.id_pengawasan=p.id AND l.status_code=999)) AS punya_999,
  ROUND(100.0*COUNT(DISTINCT p.id) FILTER (WHERE EXISTS (
    SELECT 1 FROM mv_pengawasan_log l
    WHERE l.id_pengawasan=p.id AND l.status_code=999))/COUNT(DISTINCT p.id),1) AS pct_selesai
FROM mv_pengawasan p GROUP BY 1 ORDER BY 2 DESC;

-- Trend tahunan per komoditi
SELECT komoditi, EXTRACT(YEAR FROM tgl_start)::int AS tahun, COUNT(DISTINCT id) event
FROM mv_pengawasan WHERE tgl_start IS NOT NULL
GROUP BY 1,2 ORDER BY 1,2;

-- TMK rate ELEKTRONIK vs LUARRUANG per komoditi
SELECT komoditi,
  ROUND(100.0*COUNT(*) FILTER (WHERE media_iklan='ELEKTRONIK' AND kesimpulan_penilaian_balai IN ('TMK','TMK MAYOR','TMK MINOR','TMK KRITIKAL'))/NULLIF(COUNT(*) FILTER (WHERE media_iklan='ELEKTRONIK'),0),1) AS tmk_rate_elek,
  ROUND(100.0*COUNT(*) FILTER (WHERE media_iklan='MEDIA_LUARRUANG' AND kesimpulan_penilaian_balai IN ('TMK','TMK MAYOR','TMK MINOR','TMK KRITIKAL'))/NULLIF(COUNT(*) FILTER (WHERE media_iklan='MEDIA_LUARRUANG'),0),1) AS tmk_rate_luar
FROM mv_pengawasan GROUP BY 1 ORDER BY 1;
```

## §09 — verdict rules & reversal

```sql
-- Aturan #1: String 'Null' (bukan SQL NULL)
SELECT kesimpulan_penilaian_akhir, LENGTH(kesimpulan_penilaian_akhir) AS panjang
FROM mv_pengawasan GROUP BY 1;
-- Hasil: 'Null' → 4, MK → 2, TMK → 3

-- Aturan #2: hukum COALESCE
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE kesimpulan_penilaian_akhir = kesimpulan_penilaian_pusat
                   AND kesimpulan_penilaian_pusat<>'Null') AS akhir_ikut_pusat,
  COUNT(*) FILTER (WHERE kesimpulan_penilaian_pusat='Null'
                   AND kesimpulan_penilaian_akhir=kesimpulan_penilaian_balai) AS akhir_ikut_balai_saat_pusat_null,
  COUNT(*) FILTER (WHERE kesimpulan_penilaian_akhir<>'Null'
                   AND NOT (kesimpulan_penilaian_akhir=kesimpulan_penilaian_pusat
                            OR (kesimpulan_penilaian_pusat='Null'
                                AND kesimpulan_penilaian_akhir=kesimpulan_penilaian_balai))) AS anomali
FROM mv_pengawasan;
-- Hasil: anomali = 0 (hukum 100% valid)

-- Aturan #3: akhir hanya 3 komoditi
SELECT komoditi,
  COUNT(*) total,
  COUNT(*) FILTER (WHERE kesimpulan_penilaian_akhir<>'Null') AS akhir_isi
FROM mv_pengawasan GROUP BY 1 ORDER BY 1;

-- Reversal per komoditi
SELECT komoditi,
  COUNT(*) FILTER (WHERE kesimpulan_penilaian_balai='MK' AND kesimpulan_penilaian_pusat='TMK') AS mk_ke_tmk,
  COUNT(*) FILTER (WHERE kesimpulan_penilaian_balai='TMK' AND kesimpulan_penilaian_pusat='MK') AS tmk_ke_mk
FROM mv_pengawasan GROUP BY 1 ORDER BY 2+3 DESC;
```

## §10 — data quality + bug context/skill

```sql
-- Bug B1 bukti: IS NULL di verdict = 0 baris
SELECT COUNT(*) FROM mv_pengawasan WHERE kesimpulan_penilaian_akhir IS NULL;
-- Hasil: 0 (padahal 'Null' ada 64.391)

SELECT COUNT(*) FROM mv_pengawasan WHERE kesimpulan_penilaian_akhir = 'Null';
-- Hasil: 64.391

-- Bug B2 bukti: 22 unmatched sebenarnya 0
SELECT COUNT(*) FROM target_balai t
WHERE NOT EXISTS (
  SELECT 1 FROM mv_pengawasan p WHERE UPPER(p.nama_balai)=UPPER(t.nama_balai));
-- Hasil: 0

-- Bug B3 bukti: direktur_pusat hanya {0,1,NULL}
SELECT direktur_pusat, COUNT(*) FROM mv_pengawasan_timeline
GROUP BY 1 ORDER BY 1;
-- Hasil: hanya 0, 1, NULL

-- Bug B5 bukti: jenis_pembuat_iklan 100% terisi untuk PANGAN
SELECT komoditi,
  COUNT(*) FILTER (WHERE jenis_pembuat_iklan<>'') AS terisi,
  COUNT(*) total
FROM mv_pengawasan GROUP BY 1 ORDER BY 1;
-- Hasil: hanya PRODUK PANGAN yang 100% terisi
```

## §12 — honest gaps

```sql
-- Gap 1: ROKOK cliff Jan 2025
SELECT date_trunc('month',tgl_start)::date AS bln, COUNT(*) AS rokok
FROM mv_pengawasan WHERE komoditi='ROKOK' AND tgl_start>='2024-10-01'
GROUP BY 1 ORDER BY 1;

-- Gap 3: id ghost 2023+ catatan (bukan deletion)
SELECT LEFT(COALESCE(catatan,'NULL'),40) AS catatan_prefix, COUNT(*) n
FROM mv_pengawasan_log l
WHERE l.id_pengawasan IN (
  SELECT t.id_pengawasan FROM mv_pengawasan_timeline t
  LEFT JOIN mv_pengawasan p ON p.id=t.id_pengawasan
  WHERE p.id IS NULL AND t.tgl_start>='2023-01-01')
GROUP BY 1 ORDER BY 2 DESC LIMIT 12;

-- Gap 6: status 8 & 9 di timeline
SELECT id_pengawasan, tgl_start, status, mulai_kabalai, kabalai_direktur
FROM mv_pengawasan_timeline WHERE status IN (8,9);

-- Gap 5: embedded record lokasi_iklan >1000 char
SELECT COUNT(*) FROM mv_pengawasan WHERE LENGTH(lokasi_iklan) > 1000;
```

## §16 — SQL pairs: pertanyaan user production → SQL valid

Dari 340 pertanyaan real user KAI, 20 pasangan pertanyaan → SQL → ekspektasi jawaban disimpan di **`16_sql_pairs_user_pengawasan.md`**. Query-query di sana ditulis ulang & diverifikasi terhadap schema `public` (BUKAN menyalin SQL AI KAI). Prinsip yang dipakai:

- **Entity eksplisit** per query: `COUNT(DISTINCT id)` = event, `COUNT(*)` = baris produk.
- **Verdict terisi**: `<> 'Null'` (string), bukan `IS NULL`.
- **Komoditi**: label DB persis 7 nilai; user "obat keras" = `OBAT`.
- **Timeline**: `tanggal_kirim_kabalai`, `tanggal_kirim_direktur`; NULL = belum sampai.
- **Rule "9 bulan"**: TIDAK di-hardcode — di SQL diberi label "ASUMSI, butuh konfirmasi basis tanggal".

Query kunci yang direplikasi dari file 16 (validasi silang dengan dokumentasi):

```sql
-- Pair 3: verdict akhir per periode (2026)
SELECT kesimpulan_penilaian_akhir AS verdict, COUNT(DISTINCT id) AS event
FROM mv_pengawasan
WHERE EXTRACT(YEAR FROM tgl_start)=2026
  AND kesimpulan_penilaian_akhir <> 'Null'
GROUP BY 1 ORDER BY 2 DESC;
-- Ekspektasi: MK 8.858 / TMK 5.296 (snapshot 2026-08-12)

-- Pair 5: reversal pusat TMK vs balai MK
SELECT COUNT(*) AS baris, COUNT(DISTINCT id) AS event
FROM mv_pengawasan
WHERE kesimpulan_penilaian_balai='MK'
  AND kesimpulan_penilaian_pusat IN ('TMK','TMK KRITIKAL','TMK MAYOR','TMK MINOR');
-- Ekspektasi: ~4.944 baris

-- Pair 7: UPT tidak melaporkan (anti-join)
SELECT c.nama_balai FROM coverage_balai c
WHERE NOT EXISTS (
  SELECT 1 FROM mv_pengawasan p
  WHERE UPPER(p.nama_balai)=UPPER(c.nama_balai)
    AND p.media_iklan IN ('CETAK','MEDIA_LUARRUANG'))
ORDER BY 1;

-- Pair 13: verdict per komoditi dari kolom pusat (aman semua komoditi)
SELECT komoditi, kesimpulan_penilaian_pusat AS verdict, COUNT(DISTINCT id) AS event
FROM mv_pengawasan
WHERE EXTRACT(YEAR FROM tgl_start)=2025
  AND kesimpulan_penilaian_pusat <> 'Null'
GROUP BY 1,2 ORDER BY 1,3 DESC;
```

**Catatan**: Pair 9 (ketepatan waktu vs "9 bulan") memakai ASUMSI `tgl_end + 9 months` — JANGAN eksekusi sebagai final sebelum business rule dikonfirmasi (lihat `15` honest response #8).

## Cara reproduksi penuh

Untuk mereproduksi seluruh dokumentasi ini dari awal:

1. Connect ke database `pengawasan` (lihat `00` untuk connection contract).
2. Jalankan smoke test §00.
3. Jalankan query per section §01-§12 secara berurutan.
4. Bandingkan angka hasil dengan dokumentasi — kalau beda >5%, ETL telah refresh, perbarui dokumentasi dengan angka baru + sebutkan tanggal refresh.

**Refresh policy**: ETL `pengawasan` berjalan harian (~23:23 UTC). Angka di dokumentasi valid untuk snapshot 2026-08-12. Setiap sesi baru, jalankan smoke test + verifikasi angka kunci sebelum mempercayai dokumentasi.
