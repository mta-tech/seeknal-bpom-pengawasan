# 14 — Pola Pertanyaan User Production & Vocabulary Mapping

> Sumber: **340 pertanyaan real user** dari KAI (KeyCenter AI, production text2sql BPOM), periode 2025-07-10 s/d 2026-04-22. Filter: `db_alias` mengandung "pengawasan", status VALID, question type real.
>
> **SQL generation KAI TIDAK dipakai** (AI-generated, belum valid). Hanya pola pertanyaan user yang dipelajari.

## Statistik 340 pertanyaan pengawasan

| Tema / Keyword | Frek | % |
|---|---|---|
| Tahun 2024/2025 explicit | 169 | 49,7% |
| Jumlah / total / berapa | 168 | 49,4% |
| UPT / balai | 154 | 45,3% |
| Obat (keras) | 90 | 26,5% |
| MK / TMK | 74 | 21,8% |
| Trend / rentang waktu | 72 | 21,2% |
| Verifikasi pusat | 38 | 11,2% |
| Kosmetik | 31 | 9,1% |
| Obat tradisional | 28 | 8,2% |
| Timeline / SLA | 27 | 7,9% |
| Pangan / label | 25 | 7,4% |
| Kepala balai / milestone | 25 | 7,4% |
| Obat kuasi | 22 | 6,5% |
| Suplemen | 21 | 6,2% |
| Verifikasi balai | 17 | 5,0% |
| Top N / terbanyak | 15 | 4,4% |
| Tidak melaporkan | 12 | 3,5% |
| Tanggal sampling | 12 | 3,5% |
| Grafik / visualisasi | 11 | 3,2% |
| Label | 11 | 3,2% |
| Rekapitulasi | 10 | 2,9% |
| Target / capaian | 6 | 1,8% |
| Perbedaan (reversal) | 6 | 1,8% |
| Cek BPOM / SIAPik | 6 | 1,8% |
| Media cetak | 5 | 1,5% |
| Media luar ruang | 4 | 1,2% |
| Media elektronik | 3 | 0,9% |
| Rokok | 1 | 0,3% |

**Insight**: pertanyaan user **didominasi** UPT (45,3%), jumlah (49,4%), dan periode (49,7%). User hampir tak pernah nanya ROKOK (0,3%) meski rokok = 22% data — konsisten dengan cliff Januari 2025.

## Vocabulary Mapping — Frasa User → Kolom DB

User production **TIDAK** memakai nama kolom database. Mereka berpikir dalam vocabulary operasional. Mapping ini WAJIB ada untuk agent bisa memahami pertanyaan.

### Tabel utama: konsep inti

| Frasa user (production) | Kolom DB | Tabel | Notes |
|---|---|---|---|
| **UPT** | `nama_balai` | `mv_pengawasan` | Unit Pelaksana Teknis = balai POM. 45% pertanyaan |
| **hasil verifikasi pusat** | `kesimpulan_penilaian_pusat` | `mv_pengawasan` | Bukan `akhir` |
| **hasil verifikasi balai** | `kesimpulan_penilaian_balai` | `mv_pengawasan` | |
| **mk / tmk** | nilai verdict | `mv_pengawasan` | 3 kolom punya MK/TMK + severity |
| **obat keras** | `komoditi = 'OBAT'` | `mv_pengawasan` | Istilah farmasi, bukan label DB |
| **obat tradisional; suplemen; kuasi** | 3 komoditi | `mv_pengawasan` | Sering digabung user — Cluster B+C |
| **label / label pangan** | `komoditi = 'PRODUK PANGAN'` | `mv_pengawasan` | User sebut "label pangan" |
| **kosmetik / kosmetika** | `komoditi = 'KOSMETIKA'` | `mv_pengawasan` | |
| **rokok** | `komoditi = 'ROKOK'` | `mv_pengawasan` | Jarang ditanya (0,3%) |
| **tanggal sampling / pemeriksaan** | `tgl_start` | `mv_pengawasan` | |
| **tanggal selesai** | `tgl_end` | `mv_pengawasan` | |
| **tanggal kepala balai menandatangani** | `tanggal_kirim_kabalai` | `mv_pengawasan_timeline` | |
| **tanggal direktur** | `tanggal_kirim_direktur` | `mv_pengawasan_timeline` | |
| **klausul pelanggaran** | `id_klasifikasi` | `mv_pengawasan_ketidaksesuaian` | Join ke main |
| **pemenuhan timeline** | SLA compliance | timeline | Butuh business rule deadline |
| **ketepatan waktu pelaporan** | timeliness vs deadline | timeline | Rule "9 bulan" belum di DB |
| **rekapitulasi** | GROUP BY + COUNT | mv_pengawasan | |
| **tren data** | GROUP BY tahun/bulan | mv_pengawasan | |
| **media iklan / cetak / luar ruang** | `media_iklan` | `mv_pengawasan` | |

### Tabel: konsep yang TIDAK ADA di DB pengawasan

| Frasa user | Frek | Status | Honest response |
|---|---|---|---|
| **sarana produksi** | 21x | ❌ Tidak ada | "Kolom `sarana_produksi` tidak tersedia di database pengawasan. `pendaftar` = registrant (pemohon izin), bukan produsen." |
| **produsen** | 13x | ❌ Tidak ada | Idem — `pendaftar` ≠ produsen |
| **jenis pangan** | 9x | ❌ Domain neo | "Jenis pangan tersedia di database registrasi (neo), bukan pengawasan." |
| **kategori pangan** | 9x | ❌ Domain neo | Idem |
| **provinsi** | 9x | ❌ Tidak ada | "Database hanya punya `kabupaten_kota` di `coverage_balai`, tidak ada kolom provinsi." |
| **cek BPOM / cekb pom** | 5x | ❌ Eksternal | "Cek BPOM adalah sistem eksternal, bukan bagian dari database pengawasan." |
| **SIAPik** | 1x | ❌ Eksternal | "SIAPik adalah sistem eksternal." |
| **BKO (bahan kimia obat)** | 3x | ❌ Tidak ada | "Kolom BKO tidak tersedia di database pengawasan." |

## 10 Template Pertanyaan Berulang

Template yang muncul ≥3 kali (21% pertanyaan = 71 baris). Untuk tiap template: routing ke tabel + jebakan.

### Template 1: Pemenuhan timeline (11x)

**Contoh pertanyaan**: *"tampilkan data pemenuhan timeline untuk masing-masing laporan pengawasan iklan yang dihitung dari tanggal sampling/pemeriksaan hingga tanggal direktur."*

**Routing**: `mv_pengawasan_timeline` join `mv_pengawasan`
**Tabel sumber**: `mv_pengawasan_timeline` (tanggal_kirim_kabalai, tanggal_kirim_direktur)
**Jebakan**:
- `direktur_pusat` = flag biner, BUKAN durasi (lihat `04`)
- Deadline "9 bulan berikutnya" = business rule eksternal, belum ada di DB
- Banyak timeline NULL (event belum sampai direktur) → filter `WHERE ... IS NOT NULL` wajib

### Template 2: Jumlah pengawasan [komoditi] per UPT (5x+4x)

**Contoh**: *"tampilkan data berapa jumlah iklan obat keras yang dilaporkan oleh UPT dengan hasil verifikasi pusat mk/tmk."*

**Routing**: `mv_pengawasan` GROUP BY `nama_balai`, `kesimpulan_penilaian_pusat`
**Jebakan**:
- "obat keras" = `komoditi = 'OBAT'`, BUKAN semua komoditi farmasi
- `kesimpulan_penilaian_pusat` punya banyak 'Null' → filter `<> 'Null'` dulu
- Entity = `COUNT(DISTINCT id)` (event), bukan `COUNT(*)` (baris)

### Template 3: Reversal pusat TMK vs balai MK (5x)

**Contoh**: *"tampilkan data hasil kesimpulan TMK berdasarkan hasil verifikasi pusat dengan hasil verifikasi balai MK pada rentang waktu antara tanggal mulai dan tanggal selesai"*

**Routing**: `mv_pengawasan` WHERE `kesimpulan_penilaian_balai='MK' AND kesimpulan_penilaian_pusat IN ('TMK','TMK KRITIKAL','TMK MAYOR','TMK MINOR')`
**Jebakan**:
- Pakai **TMK family** di pusat (4 severity), bukan cuma `='TMK'`
- 3 kolom verdict — pastikan mana yang dipakai

### Template 4: UPT yang tidak melaporkan (3x+)

**Contoh**: *"tampilkan data UPT yang tidak melaporkan hasil pengawasan iklan pada media cetak / media luar ruang"*

**Routing**: anti-join `coverage_balai` → `mv_pengawasan`
**Jebakan**:
- Definisi "tidak melaporkan" perlu klarifikasi (periode apa?)
- Default: balai di coverage yang tidak punya baris di main

### Template 5: Trend tahunan per komoditi (3x+)

**Contoh**: *"tampilkan tren data hasil pengawasan iklan obat pada rentang tahun 2024-2025 berdasarkan hasil verifikasi pusat mk/tmk"*

**Routing**: `GROUP BY EXTRACT(YEAR FROM tgl_start), komoditi`
**Jebakan**:
- 2026 partial year → label "(YTD Agustus)"
- `tgl_start` vs `tgl_end` — user biasanya mean `tgl_start` (mulai kegiatan)

### Template 6: Ketepatan waktu pelaporan vs 9 bulan (4x)

**Contoh**: *"tampilkan data ketepatan waktu pelaporan oleh UPT yang dihitung berdasarkan laporan yang dikirimkan tanggal kepala balai sebelum batas tanggal 9 bulan berikutnya"*

**Routing**: timeline `tanggal_kirim_kabalai`
**Jebakan**:
- Rule "9 bulan berikutnya" = **business rule eksternal**, belum terdokumentasi di DB
- Deadline dihitung dari tanggal apa? (tgl_start? tgl_end? tgl_sampling?) — **butuh klarifikasi**

### Template 7: Rekapitulasi laporan per UPT (3x)

**Contoh**: *"tampilkan rekapitulasi jumlah laporan pengawasan label pangan masing-masing UPT yang telah dikirim ke pusat"*

**Routing**: `GROUP BY nama_balai` + filter komoditi + filter verdict
**Jebakan**:
- "label pangan" = `komoditi = 'PRODUK PANGAN'`
- "dikirim ke pusat" = `tanggal_kirim_pusat IS NOT NULL` (timeline)

### Template 8: Lengkapi data dari cek BPOM (3x)

**Contoh**: *"lengkapi data berikut yang masih blank dengan informasi yang tersedia pada cek BPOM seperti NIE, nama sarana produksi, nama produk"*

**Honest response**: "Cek BPOM adalah sistem eksternal yang tidak terkoneksi ke database pengawasan. Data NIE dan nama_produk tersedia di tabel `mv_pengawasan`, tetapi sarana_produksi tidak ada."

### Template 9: Pelanggaran / klausul (3x)

**Contoh**: *"tampilkan data hasil pengawasan TMK berdasarkan klausul pelanggaran secara keseluruhan, masing-masing UPT, media iklan"*

**Routing**: `mv_pengawasan_ketidaksesuaian` JOIN `mv_pengawasan`
**Jebakan**:
- 100% PRODUK PANGAN — komoditi lain TIDAK punya ketidaksesuaian

### Template 10: Label MK/TMK per UPT multi-dimensi (3x)

**Contoh**: *"tampilkan data label yang dilaporkan mk/tmk dari masing-masing UPT yang dikategorikan berdasarkan nama produk, jenis pangan, kategori pangan, produsen, kabupaten/provinsi produsen"*

**Honest response**: "Jenis/kategori pangan dan produsen tidak ada di DB pengawasan. Nama_produk dan kabupaten_kota tersedia."

## Frasa Pembuka User

| Pembuka | Frek |
|---|---|
| "tampilkan data ..." | 93x |
| "pertanyaan: tampilkan data" | 21x |
| "tolong buatkan query untuk ..." | 18x |
| "berapa jumlah ..." | 11x |
| "tampilkan rekapitulasi ..." | 7x |
| "tampilkan tren data ..." | 5x |
| "tampilkan data hasil ..." | 12x |
| "tampilkan jumlah ..." | 13x |
| "tampilkan data UPT ..." | 9x |
| "tampilkan data berapa ..." | 10x |

## Bigram paling sering (frasa 2 kata)

| Bigram | Frek | Interpretasi |
|---|---|---|
| tampilkan data | 93 | Prefiks perintah paling umum |
| jumlah pengawasan | 64 | Aggregate count |
| tahun 2025 | 62 | Tahun paling sering ditanyakan |
| pengawasan iklan | 56 | Domain |
| hasil verifikasi | 50 | Verdict |
| berapa jumlah | 48 | Count question |
| iklan obat | 48 | Komoditi OBAT |
| UPT yang | 46 | Filter per balai |
| hasil pengawasan | 43 | Hasil / verdict |
| pada rentang | 40 | Time filter |
| verifikasi pusat | 38 | Kolom pusat |
| masing-masing UPT | 32 | Per-balai breakdown |
| rentang waktu | 32 | Time filter |
| yang dilaporkan | 30 | Reported/delivered |
| pada tahun | 30 | Time filter |
| verifikasi balai | 17 | Kolom balai |
| kepala balai | 20 | Timeline milestone |
| pemenuhan timeline | 20 | SLA compliance |
| ke pusat | 20 | Timeline milestone |

## Interpretasi: apa yang user benar-benar peduli

Dari 340 pertanyaan, 3 dominasi utama:

1. **"Bagaimana kinerja UPT?"** (45% mention UPT) — per-balai breakdown hampir selalu diminta
2. **"Berapa banyak dan bagaimana trennya?"** (49% jumlah + 21% trend) — aggregate + time-series
3. **"Apa verdictnya dan apa bedanya pusat vs balai?"** (21.8% MK/TMK + 11.2% pusat) — verdict analysis termasuk reversal

**Yang user TIDAK tanya tapi ada di data:**
- Self-approve governance (temuan analis, bukan user query)
- `lokasi_iklan` structure (tak pernah ditanya)
- `pendaftar` cleansing (tak pernah ditanya)
- `agg` kubus (tak pernah ditanya user — user langsung ke main)
- dimension schema (tak pernah ditanya — user bahkan tak tahu ada)

## Korelasi dengan 15 file dokumentasi yang sudah ada

| Temuan dokumentasi | Tervalidasi KAI? | Notes |
|---|---|---|
| 3 Cluster komoditi (`08`) | ✅ KUAT — user natural group "OT+suplemen+kuasi" | Persis Cluster B+C |
| PANGAN ↔ ketidaksesuaian (`06`) | ✅ KUAT — user tanya "klausul pelanggaran pangan" | |
| Reversal pusat↔balai (`09`) | ✅ SANGAT KUAT — 5x template recurring | Top-5 use case |
| Timeline/SLA (`04`) | ✅ SANGAT KUAT — 11x+ template #1 | Tapi user butuh rule "9 bulan" yang docs belum cover |
| ROKOK cliff (`08`) | ✅ KUAT — user berhenti nanya ROKOK (0,3%) | Double-validasi (data + behavior) |
| 'Null' string bug (`09`) | ✅ KRITIS — 74 pertanyaan verdict langsung kena | |
| agg basis tgl_end (`05`) | ✅ MODERAT — user peduli trend | |
| Self-approve 95,9% (`03`) | ⚠️ Tak ditanya user | Insight governance, bukan Q&A topic |
| lokasi_iklan 2-field (`02`) | ⚠️ Tak ditanya user | Parsing issue |
| pendaftar corrupt (`02`) | ⚠️ Tak ditanya user | Data quality issue |

---

## Batch pertanyaan tambahan — diuji ke DB live 2026-08-14

| Pertanyaan | Pemetaan | Catatan hasil |
|---|---|---|
| Jumlah **pemeriksaan** durasi >3 hari | `tgl_end - tgl_start` | jalan — tapi kata "pemeriksaan" milik domain lain; di sini artinya durasi pengawasan iklan |
| Total pengawasan KOSMETIKA **per media** | `komoditi` × `media_iklan` | jalan; ingat `media_iklan` punya nilai string kosong |
| Total pengawasan KOSMETIKA **di media elektronik** | `media_iklan='ELEKTRONIK'` | jalan |
| Total pengawasan KOSMETIKA (tanpa filter) | — | ⚠️ **tiga jawaban sah** — lihat di bawah |
| Perbandingan **makanan vs obat-obatan** Juli 2025 | istilah informal | ⚠️ **dua ambiguitas sekaligus** — lihat di bawah |
| **Tren hasil uji TMS 2023–2025** | — | ⛔ **salah domain** — lihat di bawah |
| Tren pengawasan iklan OBAT 2024–2025 per verifikasi **pusat** | `kesimpulan_penilaian_pusat` | jalan, tapi **didominasi `'Null'`** |

### ⚠️ "Berapa total jumlah pengawasan" punya tiga jawaban yang sama-sama benar

Untuk komoditi yang sama, tiga cara hitung memberi angka berbeda:

```sql
SELECT count(*)                                                        AS baris,   -- per produk
       count(DISTINCT id)                                              AS event,   -- per pengawasan
       count(DISTINCT nomor_surat) FILTER (WHERE nomor_surat NOT IN ('','-')) AS surat
FROM mv_pengawasan WHERE komoditi = 'KOSMETIKA';
```

Ketiganya berbeda karena satu event bisa memuat banyak produk (khusus OBAT & KOSMETIKA) dan satu
surat bisa memuat banyak event. **Wajib klarifikasi entity sebelum menjawab** — ini sudah tercatat
di `SEEKNAL_ASK.md` Gate 1 dan batch ini mengonfirmasinya dengan pertanyaan nyata.

### ⚠️ "Makanan vs obat-obatan" — dua ambiguitas dalam satu pertanyaan

1. **"obat-obatan"** — `OBAT` saja, atau termasuk `OBAT TRADISIONAL (OT)`, `OBAT KUASI`,
   `SUPLEMEN KESEHATAN`? Ketiga tafsir memberi angka berbeda.
2. **Entity** — `PRODUK PANGAN` selalu 1 baris = 1 event, sedangkan `OBAT` bisa banyak produk per
   event. Membandingkan `COUNT(*)` antar keduanya **memberi OBAT keunggulan semu**. Perbandingan
   antar komoditi **wajib** `COUNT(DISTINCT id)`.

### ⛔ "Tren hasil uji TMS" bukan pertanyaan domain ini

```sql
SELECT string_agg(column_name, ', ' ORDER BY ordinal_position) FROM information_schema.columns
WHERE table_schema='public' AND table_name='mv_pengawasan';
--  id, nomor_surat, komoditi, nama_balai, tgl_start, tgl_end, nama_produk, nie, pendaftar,
--  media_iklan, lokasi_iklan, jenis_pembuat_iklan, kesimpulan_penilaian_akhir,
--  kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, sync
```

**Nol kolom** yang memuat "hasil", "uji", atau "TMS". Domain ini memakai istilah **MK/TMK**
(Ketentuan) untuk iklan; **MS/TMS** (Syarat) adalah istilah hasil laboratorium milik domain
`pengujian`. Pertanyaan ini **salah rute** dan harus dijawab: *"pengujian laboratorium bukan
cakupan database pengawasan"* — bukan dijawab dengan `kesimpulan_penilaian_*` yang kebetulan mirip.

### ⚠️ Tren "berdasarkan verifikasi pusat" didominasi nilai belum terisi

Pada tren OBAT 2024–2025 per `kesimpulan_penilaian_pusat`, kelompok terbesar adalah **`'Null'`** —
jauh melampaui MK maupun TMK. Menggambar tren MK/TMK tanpa menyebut porsi `'Null'` membuat
pembaca mengira itu keseluruhan populasi.

**Aturan:** setiap tren berbasis kolom verdict wajib menyertakan `'Null'` sebagai kelompok
tersendiri, atau menyatakan berapa bagian populasi yang dikeluarkan.
