# 06 — Tabel `mv_pengawasan_ketidaksesuaian` (Non-Conformity / Alasan TMK)

> **9.070 baris · 4 kolom · 1,3 MB · snapshot 2026-08-12 23:24:49**
> Grain: **1 baris = 1 klasifikasi pelanggaran per event**. Satu event bisa kena banyak klasifikasi.

## Profil 4 kolom

| Kolom | Tipe | Distinct | Catatan |
|---|---|---|---|
| `id_pengawasan` | bigint | 7.259 | 4,2% dari 172.180 event main punya ketidaksesuaian |
| `id_klasifikasi` | integer | 6 | kode klasifikasi |
| `keterangan_ketidaksesuaian` | text | 6 | label klasifikasi (1:1 dengan id_klasifikasi) |
| `sync` | timestamp | 1 | 2026-08-12 23:24:49 |

## Dictionary 6 klasifikasi (lengkap)

| `id_klasifikasi` | Klasifikasi | n | % |
|---|---|---|---|
| **2** | **Iklan dengan klaim kesehatan – Iklan yang tidak sesuai dengan ketentuan** | **3.346** | **36,9%** (terbesar) |
| 5 | Iklan dengan kalimat superlatif, komparatif, & mendiskreditkan | 2.068 | 22,8% |
| 3 | Iklan menyesatkan karena tidak sesuai dengan karakteristik/komposisi produk | 1.866 | 20,6% |
| 6 | Iklan dengan kata-kata, figure, logo, lambang yang tidak boleh diiklankan | 1.203 | 13,3% |
| 1 | Iklan produk yang tidak boleh diiklankan (alkohol, PKMK, formula bayi) | 499 | 5,5% |
| 4 | Iklan yang melanggar norma-norma yang berlaku (adegan berbahaya, SARA) | 88 | 1,0% |

**Aturan**: pemetaan `id_klasifikasi` → klasifikasi di atas **tetap** dan boleh dipakai sebagai kode
filter. Peringkatnya **tidak** — komposisi bergeser tiap ETL, jadi "pelanggaran terbanyak" harus
selalu dijawab dari query saat itu juga, bukan dari tabel ini. Angka di kolom `n`/`%` adalah
snapshot untuk memahami bentuk data, bukan jawaban siap pakai.

> ⚠️ **Status penyaluran ke context — belum.** Diverifikasi ulang 14 Agustus 2026: halaman
> `context/40-ketidaksesuaian.md` menyebut nama tabel dan kunci join `id_pengawasan`, tetapi
> **tidak pernah menyebut `id_klasifikasi` maupun `keterangan_ketidaksesuaian`**, dan tidak memuat
> keenam kodenya. Akibatnya pertanyaan seperti *"berapa iklan dengan klaim kesehatan"* tidak bisa
> diresolusi langsung — agent harus menebak atau memakai kuota probe untuk menemukan sesuatu yang
> sebenarnya tetap. Katalog di dokumen ini sudah benar sejak awal; yang kurang adalah salinannya
> di context. Lihat `17_cakupan_context_vs_database.md`.

## Multi-klasifikasi per event

| jumlah klasifikasi per event | event |
|---|---|
| 1 | 5.743 |
| 2 | 1.252 |
| 3 | 233 |
| 4 | 31 |

**1.516 event (21%) kena lebih dari 1 klasifikasi**. Sebagian kecil (31 event) kena 4 klasifikasi sekaligus — pelanggar berat.

## ⚠️ Temuan KRITIS: 100% PRODUK PANGAN

Semua 7.259 distinct id di ketidaksesuaian = PRODUK PANGAN. Verifikasi:

```sql
SELECT string_agg(DISTINCT p.komoditi, ',')
FROM mv_pengawasan_ketidaksesuaian k JOIN mv_pengawasan p ON p.id = k.id_pengawasan;
-- Hasil: 'PRODUK PANGAN'
```

**Mengapa hanya pangan?** Menghubungkan titik:
- PRODUK PANGAN adalah komoditi yang macet di pusat (status 4) dan verdict-nya hidup di `balai` (MK/TMK MAYOR/TMK MINOR).
- Tabel ketidaksesuaian = **rincian ALASAN TMK untuk pangan**.
- Komoditi lain tak punya tabel rincian ini karena alur & sistem penilaiannya berbeda (kemungkinan direktorat berbeda mencatat alasan di tempat lain / tidak ter-ETL).

**Jadi ketidaksesuaian ⟺ pangan BUKAN kebetulan**, melainkan konsekuensi arsitektur proses per-komoditi.

## Verdict balai vs ada ketidaksesuaian (PANGAN)

| `kesimpulan_penilaian_balai` | events | punya alasan ketidaksesuaian |
|---|---|---|
| MK | 26.518 | **0** |
| TMK MAYOR | 3.828 | **3.828 (100%)** |
| TMK MINOR | 3.431 | **3.431 (100%)** |

**Korelasi sempurna**: setiap event PANGAN berbalai TMK (MAYOR/MINOR) **pasti punya** baris ketidaksesuaian. MK tidak punya. Tabel ini = rincian alasan untuk verdict TMK pangan.

## Klasifikasi × `jenis_pembuat_iklan` (PANGAN)

| id_klasifikasi | PELAKU USAHA | PERORANGAN | total event |
|---|---|---|---|
| 1 (produk terlarang) | 355 | 144 | 499 |
| 2 (klaim kesehatan) | 2.686 | 660 | 3.346 |
| 3 (menyesatkan) | 1.551 | 315 | 1.866 |
| 4 (norma) | 68 | 20 | 88 |
| 5 (superlatif) | 1.801 | 267 | 2.068 |
| 6 (lambang terlarang) | 938 | 265 | 1.203 |

**Pola**: PELAKU USAHA mendominasi setiap klasifikasi (rasio ~4:1), tapi PERORANGAN proporsional lebih banyak di klasifikasi 1 (produk terlarang: 29% perorangan) dan 6 (lambang: 22%). Perorangan lebih sering pakai lambang terlarang / iklan produk terlarang.

## Sebaran per balai (top 8)

| nama_balai | total ketidaksesuaian | jenis klasifikasi |
|---|---|---|
| BALAI BESAR POM DI JAKARTA | 867 | 6 (semua) |
| BALAI BESAR POM DI PONTIANAK | 413 | 6 |
| BALAI BESAR POM DI PEKANBARU | 409 | 6 |
| BALAI BESAR POM DI BANDAR LAMPUNG | 394 | 6 |
| BALAI BESAR POM DI MANADO | 345 | 6 |
| BALAI BESAR POM DI SEMARANG | 340 | 6 |
| BALAI BESAR POM DI SAMARINDA | 324 | 6 |
| BALAI BESAR POM DI SERANG | 318 | 6 |

**BALAI BESAR** mendominasi (bukan BALAI POM / LOKA) — wajar karena BB punya wilayah lebih luas + jakarta tertinggi (pusat aktivitas).

## Pivot SQL

### Top pelanggaran by klasifikasi
```sql
SELECT k.id_klasifikasi, MIN(k.keterangan_ketidaksesuaian) AS klasifikasi,
       COUNT(*) AS cnt, COUNT(DISTINCT k.id_pengawasan) AS event_unik
FROM mv_pengawasan_ketidaksesuaian k
GROUP BY 1 ORDER BY cnt DESC;
```

### Event dengan multi-pelanggaran
```sql
SELECT cnt, COUNT(*) AS events FROM (
  SELECT id_pengawasan, COUNT(*) cnt FROM mv_pengawasan_ketidaksesuaian GROUP BY 1
) x GROUP BY 1 ORDER BY 1;
```

### Join ke main (WAJIB LEFT JOIN dari main)
```sql
SELECT p.kesimpulan_penilaian_balai,
       COUNT(DISTINCT p.id) AS events,
       COUNT(DISTINCT k.id_pengawasan) AS punya_alasan
FROM mv_pengawasan p
LEFT JOIN mv_pengawasan_ketidaksesuaian k ON k.id_pengawasan = p.id
WHERE p.komoditi = 'PRODUK PANGAN'
GROUP BY 1 ORDER BY 2 DESC;
```

## Jebakan

1. **`INNER JOIN` dari main akan drop 96% data** — hanya 7.259 id (4,2%) punya ketidaksesuaian. Selalu `LEFT JOIN` dari main.
2. **100% PRODUK PANGAN** — jangan generalisasi ke komoditi lain. Komoditi lain TIDAK punya data ketidaksesuaian di tabel ini.
3. **Satu event bisa banyak baris** — `COUNT(DISTINCT id_pengawasan)` untuk hitung event, `COUNT(*)` untuk hitung baris klasifikasi.
4. **`id_klasifikasi` = `keterangan_ketidaksesuaian` 1:1** — keduanya redundant, kode saja cukup.
5. **Klasifikasi 4 (norma) sangat jarang (88)** — jangan di-rank sama dengan klasifikasi 2.

## Bukti SQL
Lihat `13_sql_audit_trail.md` §06.
