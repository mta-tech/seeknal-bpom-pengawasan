# 01 — Arsitektur Database & Grain Hierarchy

## Apa sebenarnya database ini?

**Database `pengawasan` BUKAN database operasional.** Ini adalah **cermin ETL harian** dari sistem RPO (sumber asli). Lima bukti yang saling mengunci:

1. **Kolom `sync` seragam** — semua tabel utama punya satu timestamp yang sama (snapshot 2026-08-12 23:23:43). Tidak ada transaksi real-time.
2. **`last_updated` di `mv_pengawasan_agg`** = 2026-08-12 23:23:50, beda beberapa detik dari sync main → di-refresh dalam batch yang sama.
3. **0 index, 0 FK, 0 constraint, 0 sequence, 0 trigger, 0 function, 0 view** — tak ada satupun karakteristik database operasional.
4. **Prefix `mv_` menyesatkan** — semua 7 relasi di `public` punya `relkind = 'r'` (regular table), BUKAN `'m'` (materialized view). Jadi di-refresh oleh pipeline ETL eksternal (drop+load), bukan `REFRESH MATERIALIZED VIEW`.
5. **Kolom `id` di `mv_pengawasan` bukan PK** — grain-nya per produk, bukan per event (lihat §grain).

**Konsekuensi berpikir (lensa interpretasi)**: setiap anomali data bukan bug transaksi, melainkan **artefak transformasi ETL** atau **cerminan proses bisnis di hulu (RPO)**. Ini lensa untuk menafsirkan semua temuan di dokumen lain.

## Instance & schema

| Level | Fakta |
|---|---|
| Instance | PostgreSQL 17.5 |
| Database yang ada di instance | `pengawasan`, `pemeriksaan`, `penandaan`, `pengujian`, `rpo`, `rpo_v2`, `postgres`, `template0`, `template1` (9 database) |
| Database `pengawasan` | 472 MB |
| Schema di `pengawasan` | `public` (reliable) + `dimension` (BROKEN — reruntuhan) |
| Role | `postgres` (superuser, punya semua grant) + `readonly_user` (login-only, **tanpa grant SELECT** — jangan dipakai) |
| `search_path` default | `"$user", public` — query tak berkualifikasi aman ke `public` |

## Dua schema, dua dunia

```
pengawasan (DB, 472 MB)
├── public/     ← DUNIA NYATA (7 tabel, terisi, reliable)
└── dimension/  ← DUNIA GAGAL (5 tabel, reruntuhan star-schema)
```

### `dimension/` adalah JEBAKAN — 4 dari 5 tabel rusak

| Tabel dimension | Kondisi | Bukti |
|---|---|---|
| `dimension.mv_pengawasan_timeline` | **0 baris** | Tabel dibuat, tak pernah diisi |
| `dimension.mv_pengawasan_log` | 25.905 baris, hanya 16 terisi | 16 baris itu **off-by-2 shift**: `draft` dapat label `Supervisor 2 - Verifikasi` (seharusnya milik `spv_2`) |
| `dimension.mv_pengawasan` | 91.147 baris | 91.140 (99,99%) `komoditi` kosong; 7 baris terisi (1 per komoditi) seperti header |
| `dimension.coverage_balai` | 513 baris | 432 (84%) `nama_balai` kosong; 81 terisi masing-masing 1 kabupaten |
| `dimension.target_balai` | 76 baris | **Satu-satunya yang bersih** — distinct `(nama_balai, komoditi)` |

**Inferensi arsitektural**: seseorang mencoba membangun star-schema (memisahkan dimensi dari fakta). Pola off-by-2 pada log = jejak query pembangun yang salah (kemungkinan `ROW_NUMBER()`/`generate_series` yang menyandingkan kolom berdasarkan posisi baris, bukan berdasarkan kunci). Upaya ini **ditinggalkan setengah jalan**.

**Aturan turunan**: **semua analisis WAJIB dari `public`. `dimension` adalah jebakan.** Search path default ke `public` jadi query tak berkualifikasi aman.

## ERD — tulang punggung `id`

```
                    mv_pengawasan  (183.968 baris / 172.180 id)
                    "1 baris = 1 PRODUK dalam 1 EVENT"
                            │ id
        ┌───────────────────┼───────────────────┬──────────────┐
        │ 1:N               │ 1:1               │ 1:N          │  dimensi
        ▼                   ▼                   ▼              ▼
   log (1.8jt)         timeline (237k)    ketidak- (9k)   agg (118k)
   transisi status     milestone+durasi   sesuaian        kubus pre-agg
   id_pengawasan       id_pengawasan      id_pengawasan   (NO id!)
```

## Grain hierarchy — WAJIB tahu sebelum bilang "jumlah"

```
nomor_surat  (9.742 unik non-sentinel)
    └── id pengawasan event  (172.180 distinct id di main)
            └── nama_produk + nie  (183.968 baris = grain sebenarnya mv_pengawasan)
```

**Satu surat pengawasan bisa mengecek banyak produk.** Tapi pola multi-produk sangat tidak merata per komoditi:

| Komoditi | 1 produk | 2-5 | 6-20 | >20 | max |
|---|---|---|---|---|---|
| ROKOK | 100% | 0 | 0 | 0 | 1 |
| PRODUK PANGAN | 100% | 0 | 0 | 0 | 1 |
| OBAT TRADISIONAL | 100% | 0 | 0 | 0 | 1 |
| SUPLEMEN KESEHATAN | 100% | 0 | 0 | 0 | 1 |
| OBAT KUASI | 100% | 0 | 0 | 0 | 1 |
| KOSMETIKA | 39.922 | 2.457 | 183 | 0 | 18 |
| OBAT | 22.527 | 3.526 | 100 | 2 | 40 |

**Temuan**: multi-product HANYA fenomena OBAT & KOSMETIKA (sweep monitoring, mis. apotek display 1 surat cek 40 obat). Lima komoditi lain 100% 1 event = 1 produk. **Grain pengawasan tidak setara antar komoditi** — analisis "event" untuk OBAT/KOSMETIKA berbeda dari komoditi lain.

### Konsistensi kolom dalam satu `id`

Diuji: apakah satu `id` bisa punya komoditi/balai/tanggal/surat berbeda antar baris? **0 kasus**. Di dalam satu event, yang bervariasi HANYA: `nama_produk`, `nie`, `pendaftar`, `lokasi_iklan` (dan verdict per produk). Selebihnya konstan.

## Entity counting — semua berbeda, semua legitimate, semua harus dilabeli

| Entity | Angka | Query |
|---|---|---|
| Baris (produk × pengawasan) | **183.968** | `SELECT COUNT(*) FROM mv_pengawasan` |
| Event pengawasan unik | **172.180** | `COUNT(DISTINCT id)` |
| Surat unik (non-sentinel) | **9.742** | `COUNT(DISTINCT nomor_surat) FILTER (WHERE nomor_surat IS NOT NULL AND nomor_surat NOT IN ('','-'))` |
| Produk unik | **42.855** | `COUNT(DISTINCT nama_produk)` |
| NIE unik (valid) | **41.210** | `COUNT(DISTINCT nie) FILTER (WHERE nie NOT IN ('','--','-'))` |
| Pendaftar unik (RAW — perlu cleansing) | **6.584** | `COUNT(DISTINCT pendaftar)` — over-count, lihat `10_data_quality_catalog.md` |
| Balai unik | **84** | `COUNT(DISTINCT nama_balai)` |

**Tidak ada default tersembunyi untuk kata "pengawasan".** Kalau user bilang "jumlah pengawasan" tanpa grain, **klarifikasi dulu**: baris / event / surat. Setiap jawaban wajib dilabel: "172.180 event" atau "183.968 baris produk", tidak boleh "jumlah pengawasan" mentah.

## Produk ↔ NIE = many-to-many

| Cek | Hasil |
|---|---|
| produk distinct | 42.855 |
| NIE valid distinct | 41.210 |
| produk dengan banyak NIE | **4.136** (produk yg punya >1 NIE — varian formulasi) |
| NIE dengan banyak nama produk | **1.400** (NIE yg punya >1 nama — variance penamaan) |

Jadi `nama_produk` dan `nie` **bukan kandidat key** — keduanya many-to-many. Hitung entity harus sadar ini.

## Jebakan kardinalitas: 64.982 id hantu

`mv_pengawasan_log` dan `mv_pengawasan_timeline` punya **236.982 distinct id**, sedangkan `mv_pengawasan` hanya **172.180**. Selisih **64.982 id** ada di log/timeline tapi TIDAK di main.

### Profil tahun id hantu

| Tahun | Jumlah id hantu |
|---|---|
| 2019 | 7 |
| 2020 | 6.550 |
| 2021 | 24.912 |
| 2022 | 25.929 |
| **2023** | **997** |
| **2024** | **2.036** |
| **2025** | **2.059** |
| **2026** | **2.251** |

**Dua klaster**:
- 57.398 id hantu di **pra-2023** (2019-2022) → ETL main dibatasi ≥2023 (batas retensi/scope).
- **7.343 id hantu di 2023+** → TIDAK murni historis. Status mereka: draft (4.879), ditolak_spv_1 (1.187), ditolak_pusat (773), dll.

**Catatan log ghost 2023+**: catatan-nya NORMAL (bukan marker deletion): *"Telah masuk di rekapitulasi laporan peng..."*, *"Mohon dilanjutkan"*, *"Entri Data oleh..."*. Hipotesis terkuat: **main = event aktif**, **log/timeline = audit lengkap termasuk event draft-only/ditolak yang sudah diarsipkan setelah dilaporkan**. Bukan ETL bug, tapi mekanisme retensi aktif-vs-audit.

### Implikasi join

- **main → log/timeline**: aman `LEFT JOIN` (semua 172.180 id main ada di log/timeline, 0 main tanpa log).
- **log/timeline → main**: `INNER JOIN` akan drop 64.982 baris yatim. Untuk populasi main, selalu filter `WHERE id_pengawasan IN (SELECT id FROM mv_pengawasan)` atau join dari main sebagai sisi kiri.

## Jembatan tanpa id: `mv_pengawasan_agg`

`agg` tak punya `id`. `SUM(jumlah_pengawasan)` per `periode_type`:
- `day`: 70.746 baris, total 183.968
- `month`: 47.387 baris, total 183.968

**Total global = main total (cocok 100%)**. Tapi basis tanggal `agg` = `tgl_end` (tanggal selesai), BUKAN `tgl_start` (lihat `05_tabel_agg_kubus.md` untuk bukti). Join ke main hanya via kombinasi dimensi `(periode_type, tanggal_periode, komoditi, nama_balai, media_iklan, jenis_pembuat_iklan, kesimpulan_*)`, bukan id.

## Lensa interpretasi anomaly data

Setiap anomali yang ditemukan harus ditafsirkan melalui pertanyaan: **"ETL artifact atau proses bisnis?"**

| Jenis anomali | Contoh | Interpretasi |
|---|---|---|
| String sentinel | `'Null'` di verdict, `'--'` di nie | Artefak ETL — cara transformasi menandai kosong |
| Casing beda antar tabel | main UPPERCASE vs log Title Case | Artefak ETL — transformasi beda untuk beda tujuan |
| Self-concat pendaftar | `KONIMEX   INDONESIA` jadi 2× | Artefak ETL — `STRING_AGG`/join salah di hulu |
| `direktur_pusat` biner | Flag {0,1} bukan durasi | Proses bisnis — kolom dipakai sbg flag di sumber |
| PANGAN stop status 4 | Workflow tak pernah final | Proses bisnis — flow pangan terminal di pusat |
| ROKOK cliff Jan 2025 | 1.665→18/bln | Proses bisnis — peristiwa kebijakan |

Membedakan dua ini krusial: artefak ETL perlu cleansing/query-workaround, proses bisnis perlu dipahami apa adanya.

---

## Batas Domain: istilah yang TIDAK boleh dibawa dari/ke domain lain

Diverifikasi live 2026-08-13 terhadap keempat database BPOM.

| Konsep | Di `pengawasan` | Di domain lain | Risiko kalau disamakan |
|---|---|---|---|
| **Vonis** | tiga kolom: `_akhir` (3 nilai) · `_balai` (5) · `_pusat` (6, termasuk `TMK KRITIKAL`) | pemeriksaan satu kolom `kesimpulan` (MK/TMK/TDP/TTP/TMBB); pengujian `kesimpulan_akhir` (MS/TMS/HPST) | `TMK KRITIKAL` **hanya ada di `_pusat` domain ini**. `TDP`/`TTP` tidak ada di sini. MS/TMS milik pengujian |
| **Status** | `bigint` 0–9 · 990–996 · 999 | pemeriksaan `text` `VERIFY*`; pengujian `bigint` 0–21; penandaan `bigint` 0–14/991–999 | ruang kode berbeda. `999` = "Sampel Rujukan Selesai" di sini; di pengujian tidak ada 999 |
| **Komoditi** | 7 nilai (tanpa `KEMASAN PANGAN`) | penandaan 8 (dengan `KEMASAN PANGAN`); pemeriksaan 13 dengan ejaan lain | jangan salin daftar. Pemeriksaan menulis `KOSMETIK`, di sini `KOSMETIKA` |
| **Tanggal bisnis** | `tgl_start`/`tgl_end` (2023-01-01 → 2026-08-31) | pemeriksaan sejak 2019/2020; pengujian sejak 2019 | pertanyaan "tren 5 tahun" **tidak setara lintas domain**. `tgl_start` di sini bahkan mencapai 2026-08-31 (masa depan relatif tanggal tarik data) |
| **Sentinel** | string `'Null'` di 3 kolom verdict; `''` di `media_iklan`/`jenis_pembuat_iklan`; `'-'` & `'--'` di `nomor_surat`/`nie`. **Tidak ada satu pun SQL NULL** | pemeriksaan `'NULL'` huruf besar; penandaan `''`; pengujian `'Null'` + SQL NULL asli di beberapa kolom | `IS NULL` **selalu 0 baris** di `mv_pengawasan`. Aturan sentinel domain lain tidak berlaku |
| **Grain** | 1 baris = (pengawasan × produk); `id` berulang untuk OBAT (1,23×) & KOSMETIKA (1,14×) | pemeriksaan & penandaan: `id` unik penuh; pengujian: `id_sampling` unik | `COUNT(*)` di sini **bukan** cacah event. Di pemeriksaan/penandaan `COUNT(*)` sah |
| **Geografi** | **tidak ada** `provinsi`/`kabupaten` | pemeriksaan punya keduanya (34 provinsi, 514 kab/kota); pengujian punya keduanya | pertanyaan geografi produsen = NOT COVERED di sini; jangan pakai `nama_balai` sebagai gantinya |

**Aturan praktis:** pertanyaan tentang *sarana*, *temuan produk*, *nilai sitaan*, *grading*,
*CPOB* adalah domain **pemeriksaan**. Pertanyaan tentang *sampel*, *parameter uji*, *LHU*, *MS/TMS*
adalah domain **pengujian**. Pertanyaan tentang *label/penandaan produk* adalah domain
**penandaan**. Di `pengawasan` yang tersedia hanya **iklan**: media, lokasi, pembuat iklan,
klausul ketidaksesuaian, dan tiga lapis verdict.
