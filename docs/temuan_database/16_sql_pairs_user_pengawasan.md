# 16 — SQL Pairs: Pertanyaan User → SQL Valid → Ekspektasi Jawaban

> Database: **`pengawasan`** schema `public` (7 tabel).
> SQL di sini **ditulis ulang & tervalidasi terhadap schema public** — TIDAK menyalin SQL AI dari KAI.
> Sumber pertanyaan: 340 pertanyaan real user KAI (filter db `pengawasan`).
> Snapshot: `sync = 2026-08-12 23:23`. Entity disertakan tiap pair (baris vs event).

## Konvensi Penting (dipakai semua pair)

| Aturan | Detail |
|---|---|
| **Entity** | Event = `COUNT(DISTINCT id)`. Baris = `COUNT(*)`. 1 event bisa >1 produk (OBAT, KOSMETIKA). |
| **Verdict terisi** | `<> 'Null'` (string), BUKAN `IS NOT NULL` — bug umum |
| **Tahun** | `EXTRACT(YEAR FROM tgl_start)` — user maksud mulai kegiatan |
| **Komoditi** | 7 nilai: `PRODUK PANGAN`, `OBAT TRADISIONAL (OT)`, `OBAT`, `KOSMETIKA`, `ROKOK`, `SUPLEMEN KESEHATAN`, `OBAT KUASI` |
| **Verdict values** | `MK`, `TMK`, `TMK KRITIKAL`, `TMK MAYOR`, `TMK MINOR`, `'Null'` |
| **Timeline** | `tanggal_kirim_kabalai`, `tanggal_kirim_direktur`; NULL = belum sampai tahap itu |

## Sumber Kolom (validasi cepat schema)

- `mv_pengawasan`: `id`, `komoditi`, `nama_balai`, `tgl_start`, `tgl_end`, `kesimpulan_penilaian_pusat`, `kesimpulan_penilaian_balai`, `kesimpulan_penilaian_akhir`, `media_iklan`, `nama_produk`, `nie`, `pendaftar`, `lokasi_iklan_1`, `lokasi_iklan_2`
- `mv_pengawasan_timeline`: `id_pengawasan`, `tanggal_kirim_kabalai`, `tanggal_kirim_direktur`, `direktur_pusat`
- `mv_pengawasan_ketidaksesuaian`: `id_pengawasan`, `id_klasifikasi`, `keterangan_ketidaksesuaian`
- `mv_pengawasan_coverage` (alias `coverage_balai`): `nama_balai`, `kabupaten_kota`
- `mv_pengawasan_target`: kolom target 2024
- `mv_pengawasan_log`, `mv_pengawasan_agg`: support

---

## Pair 1 — Total pengawasan

**Q**: *"berikan total jumlah pengawasan iklan"*
**Entity**: baris & event
**Tabel**: `mv_pengawasan`

```sql
SELECT COUNT(*) AS total_baris,
       COUNT(DISTINCT id) AS total_event
FROM mv_pengawasan;
```

**Ekspektasi**: 183.968 baris / 172.180 event.
**Caveat**: selalu tampilkan BOTH; user biasanya mau "jumlah pengawasan" = event.

## Pair 2 — Trend tahunan per komoditi

**Q**: *"tampilkan tren data hasil pengawasan iklan obat pada rentang tahun 2024-2025"*
**Entity**: event per tahun-komoditi
**Tabel**: `mv_pengawasan`

```sql
SELECT EXTRACT(YEAR FROM tgl_start)::int AS tahun,
       komoditi,
       COUNT(DISTINCT id) AS event
FROM mv_pengawasan
WHERE tgl_start >= '2024-01-01' AND tgl_start < '2026-01-01'
GROUP BY 1, 2
ORDER BY 1, 2;
```

**Caveat**: 2026 partial → label "(YTD)".

## Pair 3 — Verdict akhir per periode

**Q**: *"berapa hasil mk/tmk pengawasan iklan tahun 2026"*
**Entity**: event per verdict
**Tabel**: `mv_pengawasan`
**Kolom verdict**: `kesimpulan_penilaian_akhir` (hanya 3 komoditi Cluster A)

```sql
SELECT kesimpulan_penilaian_akhir AS verdict,
       COUNT(DISTINCT id) AS event
FROM mv_pengawasan
WHERE EXTRACT(YEAR FROM tgl_start) = 2026
  AND kesimpulan_penilaian_akhir <> 'Null'
GROUP BY 1
ORDER BY 2 DESC;
```

**Ekspektasi** (2026): MK 8.858 / TMK 5.296 (mendekati).
**Caveat**: `akhir` hanya untuk ROKOK/OBAT/KOSMETIKA. Untuk komoditi lain pakai `verdict` per kolom (Pair 13).

## Pair 4 — Jumlah per UPT dengan hasil verifikasi pusat MK/TMK

**Q**: *"tampilkan data berapa jumlah iklan obat keras yang dilaporkan oleh UPT dengan hasil verifikasi pusat mk/tmk"*
**Entity**: event per UPT-verdict
**Tabel**: `mv_pengawasan`

```sql
SELECT nama_balai,
       kesimpulan_penilaian_pusat AS verdict_pusat,
       COUNT(DISTINCT id) AS event
FROM mv_pengawasan
WHERE komoditi = 'OBAT'
  AND kesimpulan_penilaian_pusat <> 'Null'
GROUP BY 1, 2
ORDER BY 3 DESC;
```

**Caveat**: "obat keras" = `komoditi='OBAT'`. Pusat OBAT hanya ~16% terisi — sebutkan populasi.

## Pair 5 — Reversal: pusat TMK vs balai MK

**Q**: *"tampilkan data hasil kesimpulan TMK berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai MK"*
**Entity**: baris (kontras 2 kolom per baris)
**Tabel**: `mv_pengawasan`

```sql
SELECT COUNT(*) AS baris,
       COUNT(DISTINCT id) AS event
FROM mv_pengawasan
WHERE kesimpulan_penilaian_balai = 'MK'
  AND kesimpulan_penilaian_pusat IN ('TMK','TMK KRITIKAL','TMK MAYOR','TMK MINOR');
```

**Ekspektasi**: ~4.944 baris (dominasi KOSMETIKA).
**Caveat**: gunakan TMK family (4 severity), bukan hanya `='TMK'`. Lihat `09`.

## Pair 6 — Reversal sebaliknya: balai TMK vs pusat MK

**Q**: *"perbandingan hasil verifikasi balai TMK dengan verifikasi pusat MK"*
**Entity**: baris
**Tabel**: `mv_pengawasan`

```sql
SELECT COUNT(*) AS baris
FROM mv_pengawasan
WHERE kesimpulan_penilaian_balai IN ('TMK','TMK KRITIKAL','TMK MAYOR','TMK MINOR')
  AND kesimpulan_penilaian_pusat = 'MK';
```

**Caveat**: arah berlawanan. Sering user hanya tanya satu arah.

## Pair 7 — UPT yang tidak melaporkan (gap analysis)

**Q**: *"tampilkan data UPT yang tidak melaporkan hasil pengawasan iklan pada media cetak / media luar ruang"*
**Entity**: daftar balai
**Tabel**: `coverage_balai` anti-join `mv_pengawasan`

```sql
SELECT c.nama_balai
FROM coverage_balai c
WHERE NOT EXISTS (
  SELECT 1 FROM mv_pengawasan p
  WHERE UPPER(p.nama_balai) = UPPER(c.nama_balai)
    AND p.media_iklan IN ('CETAK','MEDIA_LUARRUANG')
)
ORDER BY 1;
```

**Caveat**: butuh definisi "tidak melaporkan" (periode?). Tanyakan periode dulu bila ambigu.

## Pair 8 — Timeline pemenuhan per UPT (durasi kabalai→direktur)

**Q**: *"tampilkan data pemenuhan timeline untuk masing-masing laporan pengawasan iklan yang dihitung dari tanggal sampling/pemeriksaan hingga tanggal direktur"*
**Entity**: event per UPT, durasi
**Tabel**: `mv_pengawasan_timeline` JOIN `mv_pengawasan`

```sql
SELECT p.nama_balai,
       COUNT(*) FILTER (WHERE t.tanggal_kirim_direktur IS NOT NULL) AS selesai_direktur,
       COUNT(*) AS total_event,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY
         (t.tanggal_kirim_direktur - t.tanggal_kirim_kabalai))::numeric, 0) AS med_hari_kabalai_direktur
FROM mv_pengawasan_timeline t
JOIN mv_pengawasan p ON p.id = t.id_pengawasan
WHERE t.tanggal_kirim_kabalai IS NOT NULL
GROUP BY 1
HAVING COUNT(*) >= 50
ORDER BY med_hari_kabalai_direktur DESC;
```

**Caveat**: deadline "9 bulan" = business rule eksternal, JANGAN hardcode (Pair 16).

## Pair 9 — Ketepatan waktu pelaporan vs rule 9 bulan (KLAIM — butuh konfirmasi)

**Q**: *"tampilkan data ketepatan waktu pelaporan oleh UPT yang dihitung berdasarkan laporan yang dikirimkan tanggal kepala balai sebelum batas tanggal 9 bulan berikutnya"*
**Entity**: per UPT, % on-time
**Tabel**: timeline + business rule

```sql
-- MEMBUTUHKAN KONFIRMASI: deadline dihitung dari tanggal apa?
-- Contoh (ASUMSI: deadline = tgl_end + 9 bulan — TIDAK TERVERIFIKASI):
WITH rule AS (
  SELECT p.id, p.nama_balai, t.tanggal_kirim_kabalai,
         p.tgl_end + INTERVAL '9 months' AS deadline_asumsi
  FROM mv_pengawasan_timeline t
  JOIN mv_pengawasan p ON p.id = t.id_pengawasan
)
SELECT nama_balai,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE tanggal_kirim_kabalai <= deadline_asumsi) AS on_time,
       ROUND(100.0 * COUNT(*) FILTER (WHERE tanggal_kirim_kabalai <= deadline_asumsi) / COUNT(*), 1) AS pct_on_time
FROM rule
WHERE tanggal_kirim_kabalai IS NOT NULL
GROUP BY 1
ORDER BY pct_on_time DESC;
```

**⚠️ PENTING**: SQL di atas memakai **ASUMSI** `tgl_end + 9 bulan`. Rule resmi belum terdokumentasi. Jangan eksekusi sebagai final tanpa klarifikasi basis tanggal (tgl_start / tgl_end / tgl_sampling). Lihat `15` honest response #8.

## Pair 10 — Klausul pelanggaran (ketidaksesuaian)

**Q**: *"tampilkan data hasil pengawasan TMK berdasarkan klausul pelanggaran secara keseluruhan, masing-masing UPT, media iklan"*
**Entity**: event per klasifikasi
**Tabel**: `mv_pengawasan_ketidaksesuaian` JOIN `mv_pengawasan`

```sql
SELECT k.id_klasifikasi,
       MIN(k.keterangan_ketidaksesuaian) AS contoh_ket,
       COUNT(DISTINCT k.id_pengawasan) AS event
FROM mv_pengawasan_ketidaksesuaian k
GROUP BY 1
ORDER BY 3 DESC;
```

**Caveat**: 100% PRODUK PANGAN. Komoditi lain tidak punya ketidaksesuaian.

## Pair 11 — Media iklan per komoditi

**Q**: *"perbandingan media elektronik vs media luar ruang per komoditi"*
**Entity**: event
**Tabel**: `mv_pengawasan`

```sql
SELECT komoditi, media_iklan, COUNT(DISTINCT id) AS event
FROM mv_pengawasan
GROUP BY 1, 2
ORDER BY 1, 3 DESC;
```

**Caveat**: nilai `media_iklan` berupa kode (mis. `ELEKTRONIK`, `CETAK`, `MEDIA_LUARRUANG`). Konfirmasi label bila ada varian.

## Pair 12 — Top produk / top balai

**Q**: *"tampilkan produk dengan jumlah terbanyak yang dilaporkan"* / *"UPT terbanyak melaporkan"*
**Entity**: event
**Tabel**: `mv_pengawasan`

```sql
-- top produk
SELECT nama_produk, COUNT(DISTINCT id) AS event
FROM mv_pengawasan
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
```

```sql
-- top balai
SELECT nama_balai, COUNT(DISTINCT id) AS event
FROM mv_pengawasan
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
```

## Pair 13 — Verdict per komoditi dengan aturan kolom yang benar

**Q**: *"hasil pengawasan mk/tmk masing-masing komoditi tahun 2025"*
**Entity**: event per komoditi-verdict
**Tabel**: `mv_pengawasan`

**Aturan kolom verdict per komoditi (lihat `09`):**
- Cluster A (ROKOK, OBAT, KOSMETIKA): `kesimpulan_penilaian_akhir` (3.188 komoditi) — isi penuh
- Cluster B/C (PRODUK PANGAN, OBAT TRADISIONAL (OT), SUPLEMEN KESEHATAN, OBAT KUASI): `akhir` TIDAK dipakai (63.417 baris). Pakai kolom verdict per tahapan.

```sql
-- SEMUA komoditi: breakdown kolom pusat (aman & konsisten)
SELECT komoditi,
       kesimpulan_penilaian_pusat AS verdict,
       COUNT(DISTINCT id) AS event
FROM mv_pengawasan
WHERE EXTRACT(YEAR FROM tgl_start) = 2025
  AND kesimpulan_penilaian_pusat <> 'Null'
GROUP BY 1, 2
ORDER BY 1, 3 DESC;
```

**Caveat**: JANGAN pakai `akhir` default untuk 4 komoditi Cluster B/C — hasil akan drop 63.417 baris.

## Pair 14 — Target vs realisasi 2024

**Q**: *"capaian target pengawasan iklan UPT tahun 2024"*
**Entity**: event per UPT vs target
**Tabel**: `mv_pengawasan_target` + `mv_pengawasan`

```sql
SELECT COALESCE(t.nama_balai, p.nama_balai) AS nama_balai,
       MAX(t.target_2024) AS target,
       COUNT(DISTINCT p.id) AS realisasi_event
FROM mv_pengawasan p
LEFT JOIN mv_pengawasan_target t
  ON UPPER(t.nama_balai) = UPPER(p.nama_balai)
WHERE EXTRACT(YEAR FROM p.tgl_start) = 2024
GROUP BY 1
ORDER BY 1;
```

**Caveat**: join via `UPPER()` (sudah diverifikasi 0 unmatched). Kolom target pastikan nama aslinya (`target_2024` atau lain — validasi schema).

## Pair 15 — Durasi proses (tgl_start → tgl_end)

**Q**: *"berapa lama rata-rata waktu pengawasan dari tanggal mulai sampai selesai"*
**Entity**: event
**Tabel**: `mv_pengawasan`

```sql
SELECT komoditi,
       COUNT(*) AS n,
       ROUND(AVG(tgl_end - tgl_start)::numeric, 1) AS rata_hari,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (tgl_end - tgl_start)) AS median_hari
FROM mv_pengawasan
WHERE tgl_start IS NOT NULL AND tgl_end IS NOT NULL
GROUP BY 1
ORDER BY 1;
```

**Caveat**: beberapa baris tgl_end < tgl_start (data noise) — cek outlier bila jumlah aneh.

## Pair 16 — Rekapitulasi laporan per UPT yang dikirim ke pusat

**Q**: *"tampilkan rekapitulasi jumlah laporan pengawasan label pangan masing-masing UPT yang telah dikirim ke pusat"*
**Entity**: event
**Tabel**: timeline JOIN main

```sql
SELECT p.nama_balai,
       COUNT(DISTINCT p.id) AS event
FROM mv_pengawasan p
JOIN mv_pengawasan_timeline t ON t.id_pengawasan = p.id
WHERE p.komoditi = 'PRODUK PANGAN'
  AND t.tanggal_kirim_pusat IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC;
```

**Caveat**: "label pangan" = `komoditi='PRODUK PANGAN'`. Kolom `tanggal_kirim_pusat` — validasi nama kolom aktual di timeline (jika bernama lain, ganti).

## Pair 17 — Lengkapi blank dari cek BPOM (HONEST — eksternal)

**Q**: *"lengkapi data berikut yang masih blank dengan informasi cek BPOM seperti NIE, nama sarana produksi, nama produk"*
**Entity**: —
**Tabel**: —

```sql
-- TIDAK BISA — cek BPOM = sistem eksternal.
-- Data tersedia di pengawasan: nama_produk, nie (sudah ada di main).
-- sarana_produksi: TIDAK ADA di DB pengawasan.
```

**Honest response**: lihat `15` #4.

## Pair 18 — Media cetak/luar ruang per komoditi dengan verdict

**Q**: *"jumlah pengawasan iklan pada media cetak dan luar ruang dengan hasil mk/tmk per komoditi"*
**Entity**: event
**Tabel**: `mv_pengawasan`

```sql
SELECT komoditi,
       media_iklan,
       kesimpulan_penilaian_pusat AS verdict,
       COUNT(DISTINCT id) AS event
FROM mv_pengawasan
WHERE media_iklan IN ('CETAK','MEDIA_LUARRUANG')
  AND kesimpulan_penilaian_pusat <> 'Null'
GROUP BY 1, 2, 3
ORDER BY 1, 2, 4 DESC;
```

## Pair 19 — Reversal detail per UPT

**Q**: *"tampilkan data perbedaan hasil verifikasi pusat dan balai per UPT"*
**Entity**: event per UPT
**Tabel**: `mv_pengawasan`

```sql
SELECT nama_balai,
       COUNT(DISTINCT id) FILTER (
         WHERE kesimpulan_penilaian_balai IN ('TMK','TMK KRITIKAL','TMK MAYOR','TMK MINOR')
           AND kesimpulan_penilaian_pusat = 'MK') AS balai_tmk_pusat_mk,
       COUNT(DISTINCT id) FILTER (
         WHERE kesimpulan_penilaian_balai = 'MK'
           AND kesimpulan_penilaian_pusat IN ('TMK','TMK KRITIKAL','TMK MAYOR','TMK MINOR')) AS balai_mk_pusat_tmk
FROM mv_pengawasan
GROUP BY 1
ORDER BY 3 DESC;
```

**Caveat**: dua arah reversal; sebutkan interpretasi (pusat lebih ketat / lebih longgar).

## Pair 20 — Detail event per filter (UPT + komoditi + periode + verdict)

**Q**: *"tampilkan detail data pengawasan iklan obat di UPT X tahun 2025 dengan hasil tmk"*
**Entity**: daftar event (produk)
**Tabel**: `mv_pengawasan`

```sql
SELECT id, komoditi, nama_balai, tgl_start, tgl_end,
       nama_produk, nie, kesimpulan_penilaian_pusat
FROM mv_pengawasan
WHERE komoditi = 'OBAT'
  AND nama_balai ILIKE '%X%'
  AND EXTRACT(YEAR FROM tgl_start) = 2025
  AND kesimpulan_penilaian_pusat LIKE 'TMK%'
ORDER BY tgl_start
LIMIT 50;
```

**Caveat**: `LIKE 'TMK%'` menangkap TMK family. Jika user mau detail, batasi LIMIT & beri total count.

---

## Ringkasan Routing Cepat (tanya → tabel)

| User tanya | Tabel | Kolom utama |
|---|---|---|
| Jumlah / trend / verdict / komoditi / media | `mv_pengawasan` | `id`, `tgl_start`, `komoditi`, `kesimpulan_*` |
| Timeline / SLA / ketepatan waktu | `mv_pengawasan_timeline` | `tanggal_kirim_kabalai`, `tanggal_kirim_direktur` |
| Klausul / pelanggaran | `mv_pengawasan_ketidaksesuaian` | `id_klasifikasi` |
| UPT yang tidak melaporkan | `coverage_balai` anti-join | `nama_balai` |
| Target / capaian | `mv_pengawasan_target` + main | `nama_balai` |
| Semua | `mv_pengawasan` = sumber utama | — |
---

## §16.B — Hasil Eksekusi 88 SQL Pair KAI ke DB Live (2026-08-13)

Dokumen ini sebelumnya sengaja **tidak** memakai SQL dari export KAI karena "belum tervalidasi".
Bagian ini menutup lubang itu: **seluruh 88 pasangan `context_stores` yang terdaftar pada
`db_connection_id` domain pengawasan dijalankan apa adanya** terhadap DB live, lalu dihitung
jumlah barisnya. Metode: bungkus tiap SQL menjadi `SELECT count(*) FROM (<sql>) q`.

### Hasil per generasi koneksi

| Generasi `db_connection_id` | Pair | OK | ERROR | Keterangan |
|---|--:|--:|--:|---|
| `pengawasan` (v1, Jul 2025) | 26 | **0** | 26 | semua menunjuk `vw_pengawasan_v2` — **relasi sudah tidak ada** |
| `pengawasan_all` (v2, Ags 2025) | 26 | **0** | 26 | idem, `public.vw_pengawasan_v2` |
| `pengawasan_all_v2` (v3, Nov 2025) | 36 | **34** | 2 | generasi yang masih hidup |

**52 dari 88 pair (59%) mati total.** Penyebab tunggal: dua generasi pertama dibangun di atas
view `vw_pengawasan_v2` yang sudah diganti tabel `mv_pengawasan*`. Tidak ada satu pun yang bisa
diselamatkan dengan penyesuaian kecil — tabelnya memang tidak ada.

### Dua pair generasi berlaku yang tetap gagal

| Pertanyaan | Error | Sebab |
|---|---|---|
| *"Berdasarkan kabupaten/kota, tampilkan jumlah perbedaan kesimpulan balai dengan pusat…"* | `column mp.kabupaten does not exist` | **`mv_pengawasan` live tidak punya `provinsi`/`kabupaten`** — lihat §16.C |
| *"buatkan data perbedaan hasil pengawasan iklan OT; suplemen; obat kuasi…"* | `argument of AND must be type boolean, not type record` | SQL rusak sejak awal (kurung salah tempat) |

### ⚠️ OK ≠ benar — tiga pair teratas menghasilkan angka yang tidak bermakna

| Pertanyaan | Baris hasil | Masalah |
|---|--:|---|
| *"pemenuhan timeline pengawasan oleh masing-masing UPT"* | **228.258** | tanpa agregasi; melebihi cacah fakta (183.968) karena join ke timeline yang punya 236.982 id |
| *"pemenuhan timeline untuk masing-masing laporan pengawasan iklan"* | **190.017** | idem |
| *"data label yang dilaporkan mk/tmk dari masing-masing UPT"* | 27.460 | daftar mentah, bukan rekap |

Pola ini penting: **status "SQL jalan" tidak berarti "jawabannya benar"**. Tiga pair di atas
mengembalikan daftar baris mentah untuk pertanyaan yang meminta rekap, dan yang dua teratas
sekaligus **melebihi populasi fakta** karena join dari sisi timeline (lihat `01_arsitektur_dan_grain.md`
§ id hantu).

### §16.C — Drift skema: `provinsi` & `kabupaten` sudah dihapus

Perbandingan `table_descriptions` KAI generasi `_all_v2` (Nov 2025) dengan kolom live hari ini:

```sql
SELECT string_agg(column_name, ', ' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='public' AND table_name='mv_pengawasan';
```

| | Kolom |
|---|---|
| KAI `_all_v2` (18) | id, nomor_surat, komoditi, nama_balai, **provinsi**, **kabupaten**, tgl_start, tgl_end, nama_produk, nie, pendaftar, media_iklan, lokasi_iklan, jenis_pembuat_iklan, kesimpulan_penilaian_akhir, kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, sync |
| **Live (16)** | id, nomor_surat, komoditi, nama_balai, tgl_start, tgl_end, nama_produk, nie, pendaftar, media_iklan, lokasi_iklan, jenis_pembuat_iklan, kesimpulan_penilaian_akhir, kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, sync |

**Konsekuensi:** seluruh pertanyaan bergeografi tingkat kabupaten/provinsi di domain ini —
termasuk `BPOM User Relevant Query` **#97** (*"Berdasarkan kabupaten kota dan provinsi alamat
produsen, tampilkan berapa jumlah iklan yang dilaporkan MK atau TMK"*) — **tidak lagi bisa dijawab
dari `mv_pengawasan`**. Satu-satunya jalur geografi yang tersisa adalah `coverage_balai`
(balai → kabupaten), dan itu wilayah kerja balai, **bukan** alamat produsen. Jawab honest, jangan
substitusi dengan `nama_balai`.

Drift yang sama terjadi di `mv_penandaan` (17 → 15 kolom). Tabel di `pemeriksaan` dan `pengujian`
**tidak** mengalami drift kolom.

### Cara memakai bagian ini

1. Pair generasi v1/v2 (52 buah) → **buang**, jangan dijadikan referensi pola sekalipun; nama
   tabel & kolomnya menyesatkan.
2. Pair generasi v3 yang OK (34 buah) → boleh dipakai sebagai **bukti pola pertanyaan**, tetapi
   SQL-nya tetap harus ditulis ulang mengikuti konvensi §16 di atas (entity `COUNT(DISTINCT id)`,
   verdict `<> 'Null'`, join dari main).
3. Pertanyaan yang menyentuh `provinsi`/`kabupaten` → **P5 NOT COVERED**.

---

## §16.D — Eksekusi 13 `SQL Training` dari `BPOM User Relevant Query` (2026-08-13)

Kolom **SQL Training** di `BPOM User Relevant Query.xlsx - List Pertanyaan Analitik.csv` berisi SQL
yang ditulis manual tim (bukan hasil AI). Untuk modul `pengawasan` ada 13; **12 jalan, 1 gagal**.

| # | Pertanyaan | Baris | Catatan |
|---|---|--:|---|
| 7 | Pemenuhan timeline sampling → direktur | **190.017** | ⚠️ melebihi cacah fakta 183.968 — join dari timeline |
| 8 | Pemenuhan timeline kabalai → direktur | **190.017** | ⚠️ idem |
| 9 | Iklan verifikasi balai TMK belum ada tgl direktur 2025 | 11 | |
| 11 | Rekap laporan iklan obat per UPT (tgl kabalai) 2025 | 2.929 | |
| 12 | Jumlah iklan **obat keras** per verifikasi pusat | 611 | ⚠️ tidak ada penanda "obat keras" — SQL memakai `komoditi LIKE '%obat%'` |
| 14 | Capaian UPT vs target | 494 | join `lower(trim())` — lihat `07_tabel_coverage_target.md` |
| 16 | Ketepatan waktu pelaporan (< tgl 9 bulan berikutnya) | 76 | satu baris per balai |
| 90 | Hasil TMK per klausul pelanggaran, pangan 2025 | 720 | hanya PRODUK PANGAN yang punya klausul |
| 92 | Iklan tepat waktu (< tgl 10 bulan berikutnya) | 76 | 46.707 dari 48.975 laporan tepat waktu |
| 94 | Persentase penilaian UPT MK/TMK/Mayor/Minor | 244 | |
| 95 | Per produsen: MK/TMK + beda balai-pusat | 10 | |
| **97** | **Per kabupaten/provinsi alamat produsen** | **GAGAL** | `column mp.kabupaten does not exist` |
| 111 | Pemenuhan timeline sampai kirim pusat | **228.258** | ⚠️ melebihi cacah fakta |

### Tiga pola masalah yang terlihat dari eksekusi

**1. Tiga query timeline mengembalikan lebih banyak baris daripada fakta.**
#7, #8 (190.017) dan #111 (228.258) menarik dari `mv_pengawasan_timeline` yang punya 236.982 id,
sedangkan `mv_pengawasan` hanya 172.180 event. Selisih 64.802 id "hantu" ikut terhitung. Untuk
pertanyaan yang berbicara tentang **laporan pengawasan**, join harus dimulai dari `mv_pengawasan`
(INNER), bukan dari timeline.

**2. "Obat keras" tidak punya penanda apa pun** — dikonfirmasi ulang. SQL #12 memakai
`lower(komoditi) LIKE '%obat%'`, yang menangkap `OBAT`, `OBAT KUASI`, dan `OBAT TRADISIONAL (OT)`
sekaligus. Catatan CBN di CSV sudah menyatakan *"belum ada flagging obat keras"* dan PUSDATIN
menjawab *"obat keras = obat saja (?)"* — masih tanda tanya. **Perlakukan sebagai P5 NOT COVERED**,
atau jawab untuk `komoditi='OBAT'` sambil menyatakan asumsinya.

**3. Satu-satunya kegagalan struktural adalah geografi.** #97 gagal karena `kabupaten`/`provinsi`
sudah dihapus dari `mv_pengawasan` — lihat §16.C. Pertanyaan kembarannya di domain penandaan (#98)
gagal dengan alasan identik.

### Status pertanyaan CSV modul `pengawasan`

14 pertanyaan bermodul `pengawasan`; kolom *Pengecekan Data* menyatakan 12 "sudah tersedia",
1 "belum tersedia" (#12 obat keras), 1 tanpa keterangan. Hasil eksekusi memperkuat: yang benar-benar
tidak bisa dijawab adalah **obat keras** (tidak ada penanda) dan **geografi produsen** (kolom
dihapus).

---

## §16.E — Terjemahan `vw_pengawasan_v2` → `mv_pengawasan`: 52 pair "mati" ternyata bisa dipulihkan

§16.B menyimpulkan 52 pair generasi v1/v2 mati total. **Kesimpulan itu perlu diperbaiki.** Setelah
diterjemahkan ke skema live, **47 dari 52 langsung menghasilkan data**.

| | Sebelum terjemahan | Sesudah terjemahan |
|---|--:|--:|
| Pair OK | 34 / 88 (39%) | **81 / 88 (92%)** |
| Gagal skema | 52 | **1** (kolom `kabupaten` yang memang dihapus) |
| Jalan tapi nol baris | 0 | 3 |

### Peta terjemahan — hanya dua lapis, tidak ada perubahan nama kolom

| `vw_pengawasan_v2` (15 kolom) | `mv_pengawasan` (16 kolom) |
|---|---|
| seluruh 15 kolom | **nama identik** — `id`, `nomor_surat`, `komoditi`, `nama_balai`, `tgl_start`, `tgl_end`, `nama_produk`, `nie`, `pendaftar`, `media_iklan`, `lokasi_iklan`, 3 kolom verdict, `sync` |
| — | `jenis_pembuat_iklan` **ditambahkan** di skema baru |

Jadi terjemahannya cukup **mengganti nama relasi** — beda dengan `pemeriksaan` yang kolomnya
berubah nama. Ini menjelaskan kenapa tingkat pemulihannya tinggi (46 dari 52).

### ⚠️ Tetapi nilainya berubah — dan itu yang membuat sebagian pair salah diam-diam

Contoh baris di `table_descriptions` generasi **v1** vs **v2**:

| Generasi | `kesimpulan_penilaian_akhir` | `kesimpulan_penilaian_pusat` | `komoditi` |
|---|---|---|---|
| v1 (Jul 2025) | `MEMENUHI KETENTUAN` | `-` | `Obat` |
| v2 (Ags 2025) | `MK` | `MK` | `OBAT` |
| **live (Ags 2026)** | **`MK`** | **`MK`** / `'Null'` | **`OBAT`** |

Pair generasi v1 memfilter `= 'MEMENUHI KETENTUAN'` dan `komoditi = 'Obat'`. Setelah relasinya
diganti, query **jalan** tetapi mengembalikan nol baris — nilai itu tidak ada lagi. Terjemahan
karena itu harus mencakup **normalisasi nilai**:

| Nilai lama | Nilai live |
|---|---|
| `MEMENUHI KETENTUAN` | `MK` |
| `TIDAK MEMENUHI KETENTUAN` | `TMK` |
| `Obat` · `Kosmetika` (Title Case) | `OBAT` · `KOSMETIKA` (UPPER) |
| `-` pada kolom verdict | `'Null'` (string) |

### 3 pair yang tetap nol baris setelah terjemahan

| Pertanyaan | Sebab |
|---|---|
| *"UPT yang tidak melaporkan hasil pengawasan iklan dengan verifikasi balai TMK"* (2 pair) | anti-join: **semua** balai punya minimal satu laporan TMK, jadi himpunan "yang tidak melaporkan" memang kosong. Jawaban benar: "tidak ada" |
| *"materi iklan berdasarkan nama produk tertentu dan nama industri farmasi tertentu"* | literalnya masih **placeholder**: `'NAMA_PRODUK_TERTENTU'`, `'NAMA_INDUSTRI_FARMASI_TERTENTU'`, `'NAMA_UPT_TERTENTU'`. Pair ini tersimpan di `context_stores` **tanpa pernah disubstitusi** |
| *"pengelompokan iklan obat MK/TMK berdasarkan materi yang sama"* | mengelompokkan `lokasi_iklan` yang 118.058 nilai bebas — praktis tidak ada dua baris "materi sama" |

Temuan sampingan yang penting: **`context_stores` menyimpan pair bertemplate** yang literalnya
masih berupa nama placeholder. Pair seperti ini akan cocok lewat embedding untuk pertanyaan nyata
dan menghasilkan nol baris. Saring pair yang mengandung pola `'[A-Z_]{6,}'` sebelum dipakai.

---

## §16.F — Perlakuan terhadap pair yang tetap gagal: ditulis ulang, bukan dibiarkan

Setelah terjemahan (§16.E), enam pair masih bermasalah. Semuanya ditelusuri sampai sebabnya lalu
ditulis ulang dan diuji ke database.

### (1) SQL rusak sejak asalnya — `komoditi IN` hilang

```sql
-- ASLI (error: argument of AND must be type boolean, not type record)
WHERE ('OBAT TRADISIONAL (OT)', 'SUPLEMEN KESEHATAN', 'OBAT KUASI') AND ...
--     ^ nama kolomnya tidak pernah ditulis

-- DITULIS ULANG
SELECT komoditi, kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, count(*) AS n
FROM mv_pengawasan
WHERE komoditi IN ('OBAT TRADISIONAL (OT)','SUPLEMEN KESEHATAN','OBAT KUASI')
  AND kesimpulan_penilaian_balai <> 'Null'
  AND kesimpulan_penilaian_pusat <> 'Null'
  AND kesimpulan_penilaian_balai <> kesimpulan_penilaian_pusat
GROUP BY 1,2,3 ORDER BY 4 DESC;
```

Perhatikan `<> 'Null'` (string), **bukan** `IS NOT NULL` — di database ini tidak ada SQL NULL sama
sekali.

### (2) SQL rusak sejak asalnya — `;` di tengah komentar

Satu pair memuat `;` di dalam baris komentar sehingga PostgreSQL memotong statement di situ.
Ditulis ulang menjadi query ketepatan waktu yang utuh:

```sql
SELECT count(*) AS total,
       count(*) FILTER (WHERE mpt.tanggal_kirim_kabalai > DATE '2025-02-10') AS telat
FROM mv_pengawasan mp
JOIN mv_pengawasan_timeline mpt ON mpt.id_pengawasan = mp.id
WHERE mp.tgl_start BETWEEN '2025-01-01' AND '2025-01-31'
  AND mpt.tanggal_kirim_kabalai IS NOT NULL;
```

### (3) Pair bertemplate — literalnya masih placeholder

```sql
WHERE nama_produk = 'NAMA_PRODUK_TERTENTU'
  AND pendaftar   = 'NAMA_INDUSTRI_FARMASI_TERTENTU'
  AND nama_balai  = 'NAMA_UPT_TERTENTU'
```

Pair ini tersimpan di `context_stores` **tanpa pernah disubstitusi**. Ia akan cocok lewat embedding
untuk pertanyaan nyata dan mengembalikan nol baris tanpa pesan apa pun. Disubstitusi dengan nilai
nyata (`pendaftar ILIKE '%konimex%'`) query-nya berjalan normal.

**Saring pair bertemplate sebelum dipakai:** pola `'[A-Z_]{6,}'` pada literal adalah penandanya.

### (4) Anti-join yang memang kosong — pertanyaannya perlu diubah bentuk

*"tampilkan data UPT yang tidak melaporkan hasil pengawasan iklan dengan verifikasi balai TMK"*

```sql
SELECT DISTINCT nama_balai FROM mv_pengawasan
EXCEPT
SELECT DISTINCT nama_balai FROM mv_pengawasan WHERE kesimpulan_penilaian_balai = 'TMK';
--  0 baris
```

Nol baris di sini **adalah jawaban yang benar**: setiap balai punya minimal satu laporan TMK. Tapi
jawaban "tidak ada" jarang berguna bagi penanya. Bentuk yang menjawab maksudnya adalah **peringkat
porsi**:

```sql
SELECT nama_balai, count(*) AS total,
       count(*) FILTER (WHERE kesimpulan_penilaian_balai LIKE 'TMK%') AS tmk,
       round(100.0*count(*) FILTER (WHERE kesimpulan_penilaian_balai LIKE 'TMK%')/count(*),1) AS pct
FROM mv_pengawasan GROUP BY 1 ORDER BY 4 ASC;
```

Perhatikan `LIKE 'TMK%'` — memakai `= 'TMK'` melewatkan `TMK MAYOR` dan `TMK MINOR`.

### (5) Kolom yang benar-benar dihapus — tidak bisa ditulis ulang

*"berdasarkan kabupaten/kota, tampilkan jumlah perbedaan kesimpulan balai dengan pusat"* gagal
karena `mv_pengawasan` tidak lagi punya `kabupaten`/`provinsi` (§16.C). Pengganti terdekat adalah
agregasi per **balai**, dan itu **bukan** hal yang sama — `nama_balai` adalah unit pemeriksa, bukan
alamat produsen. Sajikan sebagai per-balai **dengan menyatakan pergantiannya**, atau jawab
NOT COVERED.

### Ringkas perlakuan

| Kategori | Jumlah | Perlakuan |
|---|--:|---|
| SQL rusak sejak asal (sintaks/tipe) | 2 | ditulis ulang — **berhasil** |
| Pair bertemplate (placeholder) | 1 | disubstitusi nilai nyata — **berhasil** |
| Anti-join memang kosong | 2 | diubah bentuk menjadi peringkat porsi — **berhasil** |
| Kolom dihapus dari skema | 1 | **tidak bisa** — NOT COVERED |

---

## §16.G — Duplikasi & konsistensi: satu pertanyaan, 486× selisih jawaban

### Angka untuk domain pengawasan

| Ukuran | Nilai |
|---|--:|
| Pair tersimpan | 88 |
| **Pertanyaan unik** | **51** |
| Pertanyaan dengan >1 versi | 23 |
| — di antaranya **SQL-nya berbeda** | **21 (91%)** |
| — di antaranya **hasilnya berbeda** | **10** |
| Pertanyaan dengan selisih hasil >3× | 5 |
| Pair redundan persis | 5 |

### Kasus terburuk: "rentang 2 minggu" ditafsirkan dua cara

Pertanyaan *"tampilkan data hasil kesimpulan TMK berdasarkan hasil verifikasi pusat pada rentang
waktu antara tanggal mulai dan tanggal selesai 2 minggu"* tersimpan **empat kali**:

```sql
-- tiga versi: TEPAT 14 hari
WHERE kesimpulan_penilaian_pusat = 'TMK' AND (tgl_end - tgl_start) = 14          -- 88 baris
WHERE kesimpulan_penilaian_pusat = 'TMK' AND tgl_start = tgl_end - INTERVAL '14 days'  -- 88 baris

-- satu versi: PALING LAMA 14 hari
WHERE kesimpulan_penilaian_pusat = 'TMK' AND tgl_end <= tgl_start + INTERVAL '14 days'  -- 42.725 baris
```

**88 vs 42.725 — selisih 486×**, dari pertanyaan yang sama persis. Dan dua di antaranya berada di
**alias yang sama**, sehingga routing per `db_connection_id` tidak bisa membedakannya.

Mana yang benar? Bergantung maksud penanya, dan **pertanyaannya memang ambigu** — "rentang 2 minggu"
bisa berarti durasinya tepat 14 hari atau paling lama 14 hari. Sistem berbasis pair tidak punya
tempat untuk menanyakan itu; ia langsung menjawab dengan versi yang kebetulan terambil.

Inilah alasan Gate 1 (CLARIFY) di `SEEKNAL_ASK.md` bukan formalitas: pertanyaan seperti ini
**harus** diklarifikasi sebelum SQL, bukan ditebak.

### Pola kedua: `SELECT *` tanpa agregasi

Ketiga versi memakai `SELECT *`. Untuk pertanyaan yang berbunyi "tampilkan data hasil kesimpulan
TMK", `SELECT *` atas 42.725 baris bukan jawaban — itu dump. Dari 88 pair domain ini, **3 masuk
kategori `OK_TAPI_RAKSASA`** (>100 ribu baris tanpa agregasi; lihat `artefak/pair_ringkas.csv`).

### Implikasi

51 pertanyaan unik terwakili oleh 88 pair yang saling bertentangan. Yang layak dipindahkan ke
context skill adalah **51 pertanyaannya**, ditambah dua aturan yang menggantikan seluruh
percabangan SQL itu:

1. **Durasi ambigu → klarifikasi**, jangan pilih tafsir diam-diam.
2. **`SELECT *` dilarang untuk pertanyaan rekap** — bentuk jawaban ditentukan oleh kata kerja
   pertanyaan (berapa → `COUNT`, tampilkan tren → `GROUP BY` periode), bukan disalin dari pair.
