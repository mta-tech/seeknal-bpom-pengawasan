# 09 — Aturan Verdict, Hukum COALESCE, Reversal

> Tiga kolom verdict (`akhir`, `balai`, `pusat`) adalah sumber **kesalahpahaman terbanyak** di database ini. File ini mendokumentasikan aturan yang 100% terverifikasi.

## Tiga kolom verdict — populasi berbeda

| Kolom | Distinct | Values + count |
|---|---|---|
| `kesimpulan_penilaian_akhir` | 3 | MK 67.920 / 'Null' 64.391 / TMK 51.657 |
| `kesimpulan_penilaian_balai` | 5 | MK 111.175 / TMK 62.702 / TMK MAYOR 3.828 / TMK MINOR 3.431 / 'Null' 2.832 |
| `kesimpulan_penilaian_pusat` | 6 | MK 63.723 / 'Null' 55.889 / TMK 50.934 / TMK KRITIKAL 8.684 / TMK MINOR 2.420 / TMK MAYOR 2.318 |

## ⚠️ Aturan #1 (paling kritis): String 'Null' ≠ SQL NULL

Semua kolom verdict memakai **string 4-karakter `'Null'`** untuk menandai kosong, BUKAN SQL NULL.

```sql
-- BENAR
WHERE kesimpulan_penilaian_akhir = 'Null'    -- 64.391 baris
WHERE kesimpulan_penilaian_akhir <> 'Null'   -- 119.577 baris (MK + TMK)

-- SALAH (error umum)
WHERE kesimpulan_penilaian_akhir IS NULL     -- 0 baris (!)
WHERE kesimpulan_penilaian_akhir IS NOT NULL -- 183.968 baris (semua!)
```

**Verifikasi karakter**:
```sql
SELECT kesimpulan_penilaian_akhir, LENGTH(kesimpulan_penilaian_akhir) AS panjang
FROM mv_pengawasan GROUP BY 1;
-- 'Null' → panjang 4, MK → 2, TMK → 3
```

**Dampak anti-pattern**: Banyak query/SKILL lama memakai `IS NULL` untuk "belum dinilai" → mengembalikan 0 → agen salah lapor "100% sudah dinilai".

## ⚠️ Aturan #2 (hukum derivasi 100% valid): `akhir = COALESCE(pusat, balai)` untuk 3 komoditi

Hukum matematika terverifikasi untuk **ROKOK, OBAT, KOSMETIKA** (Cluster A):

```
IF komoditi IN (ROKOK, OBAT, KOSMETIKA) AND akhir <> 'Null':
    akhir = pusat                    (saat pusat <> 'Null')
    akhir = balai                    (saat pusat = 'Null')
```

**Bukti 3 lapis dari 183.968 baris**:

| Kondisi | Baris |
|---|---|
| `akhir <> 'Null' AND pusat <> 'Null' AND akhir = pusat` | **91.819** |
| `akhir <> 'Null' AND pusat = 'Null' AND akhir = balai` | **27.773** |
| Anomali (akhir tidak ikut pusat/balai) | **0** |

**0 anomali dari 119.592 baris ber-akhir-non-Null** → hukum **100% valid**.

### Verifikasi SQL
```sql
-- Cek anomali (harusnya 0)
SELECT komoditi, kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, kesimpulan_penilaian_akhir, COUNT(*)
FROM mv_pengawasan
WHERE kesimpulan_penilaian_akhir <> 'Null'
  AND NOT (
    kesimpulan_penilaian_akhir = kesimpulan_penilaian_pusat
    OR (kesimpulan_penilaian_pusat = 'Null' AND kesimpulan_penilaian_akhir = kesimpulan_penilaian_balai)
  )
GROUP BY 1,2,3,4;
-- Hasil: 0 baris
```

## Aturan #3: `akhir` hanya diisi untuk 3 komoditi

Dari 4 komoditi lain (PANGAN, OT, SUPLEMEN, KUASI), `akhir` **100% 'Null'**:

| Komoditi | total | akhir terisi | % |
|---|---|---|---|
| ROKOK | 40.031 | 40.031 | 100% |
| OBAT | 32.180 | 32.180 | 100% |
| KOSMETIKA | 48.325 | 47.366 | 98% (959 'Null' = event belum sampai pusat) |
| PRODUK PANGAN | 33.777 | **0** | **0%** |
| OBAT TRADISIONAL | 19.003 | 0 | 0% |
| SUPLEMEN | 7.821 | 0 | 0% |
| OBAT KUASI | 2.831 | 0 | 0% |

**Aturan ETL hulu**: hanya 3 komoditi (yang dikelola direktorat tertentu) yang mensinkron `akhir` ke database ini. 4 komoditi lain dicatat di `balai`/`pusat` saja.

**Konsekuensi**: tingkat kepatuhan (compliance rate) TIDAK boleh dihitung dari `akhir` tanpa memisahkan komoditi. Untuk 4 komoditi non-Cluster-A, gunakan:
- PRODUK PANGAN → `balai` (verdict sah di balai)
- OBAT TRADISIONAL, SUPLEMEN → `pusat` (terisi 99%)
- OBAT KUASI → `pusat` (HANYA ini yang terisi, `balai` 100% 'Null')

## Aturan #4: hierarki severity beda per level kolom

```
MK = Memenuhi Keputusan (lulus pengawasan)
TMK = Tidak Memenuhi Keputusan (gagal)

Severity grade (hanya di TMK):
  MINOR < MAYOR < KRITIKAL
```

| Level | Severity tersedia |
|---|---|
| `balai` | MK, TMK, **TMK MAYOR, TMK MINOR** (tidak ada KRITIKAL) |
| `pusat` | MK, TMK, **TMK KRITIKAL, TMK MAYOR, TMK MINOR** (lengkap) |
| `akhir` | MK, TMK saja (TANPA severity grade — paling ringkas) |

**Jebakan**:
- `WHERE kesimpulan_penilaian_balai = 'TMK KRITIKAL'` → **0 baris** (tidak ada di balai).
- `WHERE kesimpulan_penilaian_akhir = 'TMK MAYOR'` → **0 baris** (tidak ada di akhir).

### Closure sets (TIDAK boleh dijahit manual)

```sql
-- "Semua TMK family" di kolom balai:
WHERE kesimpulan_penilaian_balai IN ('TMK', 'TMK MAYOR', 'TMK MINOR')

-- "Semua TMK family" di kolom pusat:
WHERE kesimpulan_penilaian_pusat IN ('TMK', 'TMK KRITIKAL', 'TMK MAYOR', 'TMK MINOR')

-- "Sudah dinilai" (any non-Null):
WHERE kesimpulan_penilaian_akhir <> 'Null'
WHERE kesimpulan_penilaian_balai <> 'Null'
WHERE kesimpulan_penilaian_pusat <> 'Null'
```

**Exact `TMK` dan `TMK family` jawaban berbeda — harus dilabel berbeda.**

## Reversal asimetris — pusat membalik putusan balai

Reversal = baris dimana balai dan pusat KEDUanya terisi (`<> 'Null'`) TAPI berbeda.

### Global
- balai MK, pusat TMK: 4.944
- balai TMK, pusat MK: ~5.179
- Total reversal: ~10.123 (6,3% dari baris dua-duanya terisi)

**`akhir` selalu ikut `pusat` pada reversal** → pusat = otoritas final.

### Per komoditi (membongkar bias direktorat)

| Komoditi | MK→TMK | TMK→MK | total | arah dominan |
|---|---|---|---|---|
| KOSMETIKA | 3.203 | 2.319 | 5.522 | pusat lebih ketat |
| ROKOK | 1.522 | 643 | 2.165 | pusat lebih ketat |
| OBAT | 219 | 1.835 | 2.054 | pusat lebih lunak |
| OT | 0 | 279 | 279 | pusat lebih lunak |
| SUPLEMEN | 0 | 103 | 103 | pusat lebih lunak |
| PANGAN | 0 | 0 | 0 | (tidak ada pusat-final) |
| KUASI | 0 | 0 | 0 | (tidak ada balai) |

**Insight budaya**: direktorat KOSMETIKA lebih ketat dari bawahannya (balai); direktorat OBAT lebih lunak. Dua direktorat beda "strictness bias".

## Kasus khusus: 959 KOSMETIKA `akhir`='Null'

Satu-satunya Cluster A yang belum 100% `akhir` terisi. Profilmu:

| balai | pusat | n |
|---|---|---|
| TMK | 'Null' | 485 |
| MK | 'Null' | 474 |

Semua 959 kasus = `pusat`='Null' → event belum sampai dinilai pusat. **Sesuai hukum COALESCE** (akhir='Null' karena pusat='Null' dan ini event Cluster A yang `akhir` menunggu pusat). Bukan anomali — event yang masih dalam pipeline pusat.

## Template pertanyaan reversal dari user production

Dari 340 pertanyaan KAI, **reversal = use case top-5** — user eksplisit bertanya (5x template berulang):

> *"tampilkan data hasil kesimpulan TMK berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai MK pada rentang waktu ..."*

Dua arah yang harus bisa dijawab:

| Pertanyaan user | Kondisi SQL | Interpretasi |
|---|---|---|
| "TMK (pusat) ... balai MK" | `balai='MK' AND pusat IN (TMK family)` | pusat **mengoreksi naik** (lebih ketat) |
| "MK (pusat) ... balai TMK" | `balai IN (TMK family) AND pusat='MK'` | pusat **melonggarkan** (lebih lunak) |

```sql
-- Arah 1: pusat TMK, balai MK (pusat lebih ketat)
SELECT COUNT(*) AS baris,
       COUNT(DISTINCT id) AS event
FROM mv_pengawasan
WHERE kesimpulan_penilaian_balai = 'MK'
  AND kesimpulan_penilaian_pusat IN ('TMK','TMK KRITIKAL','TMK MAYOR','TMK MINOR');

-- Arah 2: balai TMK, pusat MK (pusat lebih lunak)
SELECT COUNT(*) AS baris
FROM mv_pengawasan
WHERE kesimpulan_penilaian_balai IN ('TMK','TMK KRITIKAL','TMK MAYOR','TMK MINOR')
  AND kesimpulan_penilaian_pusat = 'MK';
```

**Jebakan reversal**:
- **WAJIB pakai TMK family** (4 severity), bukan `= 'TMK'` saja — `TMK KRITIKAL` di pusat akan terlewat.
- Kedua kolom harus `<> 'Null'` (implisit dari kondisi IN/equal di atas).
- Untuk breakdown per komoditi, tambahkan `GROUP BY komoditi` — bias direktorat terlihat (KOSMETIKA lebih ketat, OBAT lebih lunak).
- "Rentang waktu antara tanggal mulai dan selesai" = filter `tgl_start` (dan/atau `tgl_end`) — tanyakan ke user mana basisnya bila ambigu.

## Bukti SQL
Lihat `13_sql_audit_trail.md` §09.
