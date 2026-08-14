# 02 — Tabel `mv_pengawasan` (Jantung Sistem)

> **183.968 baris · 16 kolom · 49 MB · snapshot 2026-08-12 23:23:43**
> Grain: **1 baris = 1 produk dalam 1 event pengawasan**. Bukan per event, bukan per surat.

## Profil semua 16 kolom

Semua kolom **NOT NULL** (0 SQL NULL di tabel ini), tapi banyak yang berisi **empty string** atau **string sentinel**. Inilah jebakan utama.

| Kolom | Tipe | Distinct | Empty | Min–Max / Catatan |
|---|---|---|---|---|
| `id` | bigint | 172.180 | 0 | 56.894 → 238.127; **bukan PK** (grain per produk) |
| `nomor_surat` | text | 9.742 | 22.490 | 7 pola (lihat §nomor_surat) |
| `komoditi` | text | **7** | 0 | UPPERCASE, exact-match (lihat §komoditi) |
| `nama_balai` | text | 84 | 0 | UPPERCASE |
| `tgl_start` | date | 1.313 | 0 | 2023-01-01 → 2026-08-31 |
| `tgl_end` | date | 1.314 | 0 | 2023-01-01 → 2026-08-31; 78% = tgl_start (same-day) |
| `nama_produk` | text | 42.855 | 25 | top: SURYA 2.936; ada unicode Greek (Α, Ν) |
| `nie` | text | 41.213 | 40.053 | prefix multi-komoditi (lihat §nie) |
| `pendaftar` | text | 6.584 | 44.775 | **CORRUPT** (lihat §pendaftar & `10_data_quality_catalog.md`) |
| `media_iklan` | text | 5 | 972 | ELEKTRONIK, MEDIA_LUARRUANG, CETAK, MEDIA_LAIN |
| `lokasi_iklan` | text | 118.058 | 5.648 | **2-FIELD `"A""B"`** (lihat §lokasi_iklan) |
| `jenis_pembuat_iklan` | text | 3 | 150.191 | **EKSKLUSIF PANGAN** (lihat §jenis_pembuat) |
| `kesimpulan_penilaian_akhir` | text | 3 | 0 (str 'Null') | MK/TMK/'Null' — hanya 3 komoditi terisi |
| `kesimpulan_penilaian_balai` | text | 5 | 0 | MK/TMK/TMK MAYOR/TMK MINOR/'Null' |
| `kesimpulan_penilaian_pusat` | text | 6 | 0 | MK/TMK/TMK KRITIKAL/MAYOR/MINOR/'Null' |
| `sync` | timestamp | 1 | 0 | 2026-08-12 23:23:43 (snapshot) |

## `komoditi` — sumbu paling menentukan segalanya

7 nilai UPPERCASE (exact-match):

```sql
WHERE komoditi = 'KOSMETIKA'            -- 48.325
WHERE komoditi = 'ROKOK'                -- 40.031
WHERE komoditi = 'PRODUK PANGAN'        -- 33.777
WHERE komoditi = 'OBAT'                 -- 32.180
WHERE komoditi = 'OBAT TRADISIONAL (OT)'-- 19.003
WHERE komoditi = 'SUPLEMEN KESEHATAN'   --  7.821
WHERE komoditi = 'OBAT KUASI'           --  2.831
```

**Temuan besar**: komoditi bukan sekadar kategori — ia **menentukan perilaku HAMPIR SEMUA kolom lain**. Setiap kolom berperilaku beda per komoditi (lihat capstone `08_komoditi_master_axis.md`). **Analisis apa pun yang tak dipisah per komoditi akan menyesatkan.**

### Istilah informal yang perlu klarifikasi

- "obat" → `OBAT` saja, atau gabungan farmasi (`OBAT` ∪ `OT` ∪ `OBAT KUASI` ∪ `SUPLEMEN KESEHATAN`)? → klarifikasi.
- "pangan" → `PRODUK PANGAN` saja (tidak ambigu).
- "rokok" → `ROKOK` (tidak ambigu).
- "yang lulus/gagal" → verdict di `akhir`, `pusat`, atau `balai`? → klarifikasi.

## `nie` — kolom berkode yang menyimpan taksonomi (TAPI bukan 1:1)

Prefix 2 huruf pertama **indikatif** ke komoditi, tapi **TIDAK deterministik** — koreksi terhadap asumsi umum:

| Prefix | Komoditi yang muncul |
|---|---|
| `NA`, `NB`, `NC`, `ND`, `NE`, `NI`, `NK` | KOSMETIKA (dominan) |
| `DT`, `DB`, `DK`, `DN`, `DP`, `GB`, `GK`, `GP`, `GT`, `IK`, `LK`, `MA`, `OB`, `pa`, `Ph` | OBAT |
| `MD`, `ML` | PRODUK PANGAN (dominan) |
| `TR`, `HT`, `TI`, `PO` | OBAT TRADISIONAL |
| `SD`, `SI`, `SL` | SUPLEMEN KESEHATAN |
| `QD`, `QI`, `QL` | OBAT KUASI |

**Prefix yang muncul di banyak komoditi (bukan 1:1)**:
- `BP` → KOSMETIKA + OBAT + PANGAN (3 komoditi)
- `NA` → 3 komoditi
- `MD` → 3 komoditi
- `SD` → **5 komoditi** (paling ambigu)
- `PO` → 4 komoditi
- `QL` → 4 komoditi
- `QD`, `DT` → 3 komoditi

**Trap case**: ada prefix lowercase (`na`, `br`, `Ad`, `Am`, `Ke`, `Lu`, `Mi`) bercampur dengan uppercase. Wajib `UPPER(LEFT(nie,2))` sebelum group.

### ROKOK = 100% tanpa NIE

ROKOK: 40.053 baris NIE kosong (empty + `'--'` + `'-'`). Ini **bukan data hilang** — rokok memang tak punya Nomor Izin Edar BPOM (diatur cukai/Kemenkes), tetapi iklannya tetap diawasi. **`nie` kosong pada ROKOK = by design**, sedangkan pada komoditi lain = data quality issue.

| Komoditi | total | sentinel NIE (`''`/`'--'`/`'-'`) | % |
|---|---|---|---|
| ROKOK | 40.031 | 40.031 | **100%** (by design) |
| OBAT TRADISIONAL | 19.003 | 3.970 | 20.9% |
| SUPLEMEN | 7.821 | 1.406 | 18.0% |
| OBAT KUASI | 2.831 | 430 | 15.2% |
| KOSMETIKA | 48.325 | 2.135 | 4.4% |
| PRODUK PANGAN | 33.777 | 667 | 2.0% |
| OBAT | 32.180 | 40 | 0.1% |

## `media_iklan` × `komoditi` — profil kanal yang bercerita

```
ELEKTRONIK        98.079   MEDIA_LUARRUANG  56.064   CETAK 25.028   MEDIA_LAIN 3.825   (empty 972)
```

Profil per komoditi (prediksi silang, lihat `11_sinapsis_prediksi.md`):
- **ROKOK**: 91% MEDIA_LUARRUANG, 0% ELEKTRONIK, 0% CETAK → iklan rokok hidup di baliho/jalanan (regulasi)
- **KOSMETIKA**: 82% ELEKTRONIK → perang kosmetik di media sosial/e-commerce
- **OBAT**: 48% ELEKTRONIK + 37% CETAK
- **OT/SUPLEMEN/KUASI**: >74% ELEKTRONIK
- **PRODUK PANGAN**: 60% ELEKTRONIK + 25% LUARRUANG

## `lokasi_iklan` — struktur 2-field tersembunyi `"A""B"`

**Bukan satu field, tapi DUA field dalam satu string** dengan pembatas `""`:

```
"RCTI"
"Indomaret""Kembang Seri"
"medicastore.com""medicastore.com"
"Tijong Wiyono""https://www.tiktok.com/@tjiongwiyono/video/..."
```

- **Bagian 1 (A)** = nama platform/kanal/tempat (RCTI, Indomaret, halodoc, medicastore.com, Tijong Wiyono)
- **Bagian 2 (B)** = URL atau alamat detail

### Kuantifikasi struktur

| Pola | Baris |
|---|---|
| Dua bagian `"A""B"` | **49.101** |
| Satu bagian `"A"` saja | 14.318 |
| URL murni (ELEKTRONIK tanpa wrap) | 44.588 |
| Empty / dash | 8.988 |

### Isi bagian 2 (Y)

| Jenis | Baris |
|---|---|
| URL (`https?://...`) | 22.397 |
| Alamat (`Jl.`/`jalan`/`Desa`/`Kec.`/`Kab`) | 13.484 |
| Domain murni (`xxx.id`) | 1.254 |

### Domain paling banyak dimonitor BPOM (top 15)

| Domain | Baris |
|---|---|
| www.instagram.com | 6.932 |
| shopee.co.id | 2.727 |
| www.tokopedia.com | 1.699 |
| www.facebook.com | 1.386 |
| id.shp.ee | 828 |
| drive.google.com | 785 |
| www.youtube.com | 736 |
| vt.tiktok.com | 592 |
| www.halodoc.com | 505 |
| www.tiktok.com | 503 |
| vt.tokopedia.com | 503 |
| www.lazada.co.id | 390 |
| www.blibli.com | 343 |
| www.vidio.com | 315 |
| youtu.be | 282 |

### Kasus khusus

- **TV_CONCAT** `"SCTV""SCTV"`: nama stasiun disimpan dua kali (pola entri form TV sistematis) — 49.101 baris punya tanda kutip.
- **Embedded record**: 998 baris >1.000 karakter berisi rekaman multi-kolom terkombinasi (nomor urut, tanggal, media, produk, NIE, klaim, pendaftar, verdict) — perlu parse terpisah.
- **3.239 baris dengan newline** (`\n`) di dalam string.

### Cross media → struktur lokasi

| `media_iklan` | total | dua_bagian | url_murni |
|---|---|---|---|
| ELEKTRONIK | 98.079 | 30.670 | 44.479 |
| MEDIA_LUARRUANG | 56.064 | 8.445 | 24 |
| CETAK | 25.028 | 9.076 | 4 |
| MEDIA_LAIN | 3.825 | 979 | 1 |
| (empty) | 972 | 0 | 80 |

**Bentuk `lokasi_iklan` adalah fungsi `media_iklan`**. ELEKTRONIK → URL/platform; LUARRUANG → alamat jalan; TV → concat stasiun.

## `pendaftar` — kolom paling rusak

6.584 distinct mentah, 44.775 empty. Tiga pola kerusakan **sistematis** (bukan acak):

1. **DUPLICATED_CONCAT** — string digandakan tanpa delimiter: `PT KONIMEX` → `PT KONIMEXPT KONIMEX` (panjang persis 2×). **23.455 baris** terbukti self-concat (separuh depan = separuh belakang).
2. **DOUBLE/TRIPLE SPACE** — `KONIMEX   INDONESIA`, `PT  PT  PT  PT  PT`.
3. **ADDRESS LEAKAGE** — nama + alamat lengkap tumpah jadi satu string 107 karakter. **5.773 baris** mengandung unsur alamat (JL/JALAN/BLOK/NO/KAB/RT/RW).

**Dampak**: satu perusahaan muncul dalam puluhan varian. Inflasi distinct: 6.584 mentah → 6.001 setelah normalisasi kasar (`regexp_replace(upper(pendaftar), '[^A-Z0-9]', '', 'g')`). **8.8% over-count**.

**Top pendaftar mentah**:
| pendaftar (mentah) | n |
|---|---|
| KONIMEX   INDONESIA | 6.023 |
| UNILEVER INDONESIA TBK   PT | 3.350 |
| TEMPO SCAN PACIFIC TBK   INDONESIA | 2.870 |
| KALBE FARMA   INDONESIA | 2.285 |
| PT INDUSTRI JAMU...SIDO MUNCUL TBK... (self-concat) | 2.017 |

**Aturan**: `COUNT(DISTINCT pendaftar)` RAW hanya diagnostik. Jangan pernah presentasikan sebagai "jumlah perusahaan" tanpa normalisasi yang approved.

**Inferensi ETL**: pola self-concat tanpa delimiter = jejak `STRING_AGG`/join yang menggandakan baris di hulu. Kerusakan lahir di transformasi, bukan di sumber asli.

## `jenis_pembuat_iklan` — kolom EKSKLUSIF PRODUK PANGAN

| Komoditi | terisi | kosong |
|---|---|---|
| PRODUK PANGAN | **33.777 (100%)** | 0 |
| 6 komoditi lain | 0 | 100% |

Isi: `PELAKU USAHA` (29.290), `PERORANGAN` (4.487).

**Koreksi penting**: anggapan "kolom ini 82% kosong, hampir tidak usable" (yang muncul di beberapa context lama) **menyesatkan**. Kolom ini **100% usable untuk analisis PRODUK PANGAN**. Hanya tidak usable untuk 6 komoditi lain.

### TMK rate per media × jenis_pembuat (PANGAN)

| media × jenis | MK% | TMK% |
|---|---|---|
| ELEKTRONIK × PELAKU USAHA | 75.3% | 24.7% |
| ELEKTRONIK × PERORANGAN | 65.8% | 34.2% |
| LUARRUANG × PELAKU USAHA | 87.1% | 12.9% |

Perorangan lebih sering TMK; ELEKTRONIK insiden pelanggaran paling tinggi.

## `nomor_surat` — 7 pola, banyak sentinel

| Kategori | Baris | Contoh |
|---|---|---|
| LETTER_START (normal) | 127.349 | `AGUSTUS 15`, surat resmi |
| SINGLE_DASH `-` | 26.560 | sentinel |
| EMPTY | 22.490 | sentinel |
| DASH_PW `-PW.*` | 2.625 | **format nomor surat tersusun** (PW = Pengawasan Wilayah): `-PW.02.03.11A.05.24.1185` |
| DIGIT_START | 2.419 | `00` s/d `9-PW...` |
| OTHER | 1.389 | `'`, ` T-PW...` |
| ZERO `0` | 449 | sentinel |
| HAS_COMMA | 21 | `Apotek Adapotek Jl. ...` (address leak) |

**Koreksi penting**: `-PW.*` (2.625 baris) **bukan sentinel** — itu format nomor surat resmi tersusun dengan dash prepend. Dipakai terutama untuk multi-product event (1 surat dipakai 40-63 produk OBAT). Jangan di-exclude sebagai sentinel.

### Distribusi kategori × komoditi

| Komoditi | empty | single_dash | zero | dash_pw | normal |
|---|---|---|---|---|---|
| KOSMETIKA | 11.434 | 4.370 | 47 | 0 | 32.470 |
| OBAT | 0 | 7.899 | 4 | 973 | 22.949 |
| PRODUK PANGAN | 5.743 | 3.247 | 104 | 0 | 24.682 |
| ROKOK | 0 | 8.016 | 2 | **1.649** | 30.058 |
| OBAT TRADISIONAL | 3.435 | 1.899 | 195 | 3 | 13.471 |
| SUPLEMEN | 1.322 | 822 | 78 | 0 | 5.599 |
| OBAT KUASI | 556 | 307 | 19 | 0 | 1.949 |

**Temuan**: ROKOK dominan memakai format `-PW.*` (1.649 baris) — sistem nomor surat terstruktur per wilayah pengawasan.

## Tiga kolom verdict — inti dari SEMUA kesalahpahaman

Lihat detail lengkap di `09_verdict_rules_reversal.md`. Ringkasan:

| Kolom | Distinct values | Count |
|---|---|---|
| `kesimpulan_penilaian_akhir` | MK / TMK / **'Null'** | 67.920 / 51.657 / 64.391 |
| `kesimpulan_penilaian_balai` | MK / TMK / TMK MAYOR / TMK MINOR / **'Null'** | 111.175 / 62.702 / 3.828 / 3.431 / 2.832 |
| `kesimpulan_penilaian_pusat` | MK / TMK / TMK KRITIKAL / TMK MAYOR / TMK MINOR / **'Null'** | 63.723 / 50.934 / 8.684 / 2.318 / 2.420 / 55.889 |

**Tiga hal wajib**:
1. **'Null' = string 4-karakter**, BUKAN SQL NULL. `WHERE ... IS NULL` → 0 baris. Harus `= 'Null'` / `<> 'Null'`.
2. **Hierarki severity beda per level**: balai kenal MINOR/MAYOR (tidak KRITIKAL); pusat menambah KRITIKAL.
3. **Hukum derivasi 100%**: `IF komoditi IN (ROKOK,OBAT,KOSMETIKA) THEN akhir = COALESCE(pusat, balai)`. Untuk 4 komoditi lain, `akhir` selalu 'Null'.

## Bukti SQL (audit trail)

Lihat `13_sql_audit_trail.md` §02 untuk semua query yang menghasilkan angka di file ini.

---

## Katalog Nilai Penuh & Asimetri Taksonomi (live 2026-08-13, 183.968 baris)

`GROUP BY` penuh atas seluruh baris — bukan sampel `categories` KAI.

### Tiga kolom verdict punya **taksonomi yang tidak sama**

| Nilai | `_akhir` | `_balai` | `_pusat` |
|---|--:|--:|--:|
| `MK` | 67.920 (36,9%) | 111.175 (60,4%) | 63.723 (34,6%) |
| `TMK` | 51.657 (28,1%) | 62.702 (34,1%) | 50.934 (27,7%) |
| `'Null'` | 64.391 (35,0%) | 2.832 (1,5%) | 55.889 (30,4%) |
| `TMK MAYOR` | — | 3.828 (2,1%) | 2.318 (1,3%) |
| `TMK MINOR` | — | 3.431 (1,9%) | 2.420 (1,3%) |
| **`TMK KRITIKAL`** | — | **—** | **8.684 (4,7%)** |
| **Jumlah nilai** | **3** | **5** | **6** |

Tiga hal yang harus diketahui sebelum menulis filter:

1. **`TMK KRITIKAL` hanya ada di `_pusat`.** Balai tidak pernah memberi vonis kritikal. Jadi
   "TMK family" bukan himpunan yang sama di kedua kolom:
   `balai ∈ {TMK, TMK MAYOR, TMK MINOR}` · `pusat ∈ {TMK, TMK KRITIKAL, TMK MAYOR, TMK MINOR}`.
   Filter `kesimpulan_penilaian_pusat = 'TMK'` **melewatkan 13.422 baris** TMK bergradasi.
2. **`_akhir` hanya biner** (MK/TMK) — gradasi hilang saat diturunkan ke kolom akhir.
3. **`'Null'` adalah string empat huruf**, bukan SQL NULL. Tidak ada satu pun kolom di
   `mv_pengawasan` yang bernilai SQL NULL (`null=0` pada seluruh 16 kolom). `WHERE x IS NULL`
   selalu mengembalikan 0 baris di tabel ini.

### `media_iklan` — 5 nilai, satu di antaranya string kosong

| Nilai | Baris | % |
|---|--:|--:|
| `ELEKTRONIK` | 98.079 | 53,3 |
| `MEDIA_LUARRUANG` | 56.064 | 30,5 |
| `CETAK` | 25.028 | 13,6 |
| `MEDIA_LAIN` | 3.825 | 2,1 |
| `''` (kosong) | 972 | 0,5 |

Perhatikan bentuk penulisannya: **`MEDIA_LUARRUANG` dan `MEDIA_LAIN` memakai garis bawah**,
sementara `ELEKTRONIK` dan `CETAK` tidak. Pertanyaan user memakai frasa "media luar ruang"
(dengan spasi) — jangan `ILIKE '%luar ruang%'` karena nilainya `LUARRUANG` tanpa spasi.

### `jenis_pembuat_iklan` — 3 nilai, 81,6% kosong dan kosongnya bermakna

| Nilai | Baris | % |
|---|--:|--:|
| `''` (kosong) | 150.191 | 81,6 |
| `PELAKU USAHA` | 29.290 | 15,9 |
| `PERORANGAN` | 4.487 | 2,4 |

Terisi = 33.777 baris = **persis jumlah baris komoditi PRODUK PANGAN**. Kolom ini hanya diisi
untuk pangan. `WHERE jenis_pembuat_iklan <> ''` karena itu **identik dengan "komoditi pangan
saja"** — sebuah filter tersembunyi. `BPOM User Relevant Query` #88/#89 yang memintanya hanya
bisa dijawab untuk pangan, dan catatan CBN di CSV sudah menyatakan hal yang sama.

### `komoditi` — 7 nilai (tanpa `KEMASAN PANGAN`)

`KOSMETIKA` 48.325 · `ROKOK` 40.031 · `PRODUK PANGAN` 33.777 · `OBAT` 32.180 ·
`OBAT TRADISIONAL (OT)` 19.003 · `SUPLEMEN KESEHATAN` 7.821 · `OBAT KUASI` 2.831.

Domain `penandaan` punya 8 nilai (dengan `KEMASAN PANGAN`); domain `pemeriksaan` punya 13 dan
memakai ejaan berbeda (`KOSMETIK` tanpa A, `OBAT TRADISIONAL` tanpa `(OT)`). **Jangan salin
daftar komoditi antar domain.**

### `mv_pengawasan_ketidaksesuaian.id_klasifikasi` — 6 klausul tetap, 100% pangan

| Kode | Keterangan (ringkas) | Baris |
|---|---|--:|
| 2 | Iklan dengan klaim kesehatan yang tidak sesuai ketentuan | 3.346 |
| 5 | Kalimat superlatif/komparatif/mendiskreditkan | 2.068 |
| 3 | Menyesatkan — tidak sesuai karakteristik/komposisi | 1.866 |
| 6 | Kata/figur/logo/lambang yang tidak boleh diiklankan | 1.203 |
| 1 | Produk yang tidak boleh diiklankan (alkohol, PKMK, formula bayi) | 499 |
| 4 | Melanggar norma (adegan berbahaya, SARA) | 88 |

```sql
SELECT mp.komoditi, count(DISTINCT mp.id), count(*)
FROM mv_pengawasan mp JOIN mv_pengawasan_ketidaksesuaian k ON k.id_pengawasan = mp.id
GROUP BY 1;
--  PRODUK PANGAN | 7259 | 9070      ← satu-satunya komoditi
```

**Seluruh 9.070 baris ketidaksesuaian milik PRODUK PANGAN**, mencakup 7.259 dari 33.777 event
pangan (21,5%). Untuk enam komoditi lain, klausul pelanggaran **tidak direkam** — pertanyaan
"klausul pelanggaran" untuk iklan obat/kosmetik adalah **NOT COVERED**.

### Filter yang tersedia per tabel

| Tabel | Dimensi filter | Ukuran |
|---|---|---|
| `mv_pengawasan` | `komoditi` (7) · `nama_balai` (84) · `media_iklan` (5) · `jenis_pembuat_iklan` (3) · 3 kolom verdict (3/5/6) · `tgl_start`/`tgl_end` | 183.968 baris · 172.180 event |
| `mv_pengawasan_log` | `trx_steps` (16) · `status_code` (17) · `status_label` (9 + NULL) · `fullname` (1.536) | 1.817.233 baris · 236.982 id |
| `mv_pengawasan_timeline` | `status` (18) · 3 tanggal milestone · 3 kolom durasi | 236.982 baris |
| `mv_pengawasan_ketidaksesuaian` | `id_klasifikasi` (6) | 9.070 baris · 7.259 event |
| `mv_pengawasan_agg` | 8 dimensi + `periode_type` (2) | 118.133 baris |
| `coverage_balai` | `nama_balai` (88) · `kabupaten_kota` (514) | 668 baris |
| `target_balai` | `nama_balai` (76) · `komoditi` (7) · `tahun` (**2024 saja**) | 532 baris |

⚠️ **`provinsi` dan `kabupaten` TIDAK ADA** di `mv_pengawasan` (16 kolom). Geografi hanya lewat
`nama_balai` → `coverage_balai`, dan itu wilayah kerja balai — bukan alamat produsen.
