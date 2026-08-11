# seeknal-bpom-neo: Mapping Fidelity & Coverage Closure — Perbaikan `after-forecast-chart-enhance`

**Document type:** Audit Findings + Implementation Plan
**Project:** seeknal-bpom-neo (BPOM RPO Analytics Agent)
**Status:** Implemented 2026-08-04 — lihat §11 untuk catatan pelaksanaan dan satu koreksi arah
**Date:** 2026-08-04
**Target varian:** `docs/context_recap/after-chart-030826/after-forecast-chart-enhance`
**Pembanding (baseline):** `after-forecast-anomaly-refactor` (v1) · `after-forecast-anomaly-refactor-v2` (v2)
**Scope berkas:** `SEEKNAL_ASK.md` · `context/predikat.md` · `context/filter_code_reference.md` · `context/data_architecture.md` · `skills/bpom-analyst/SKILL.md` · `skills/visualize-chart/SKILL.md` · `skills/bpom-forecaster/SKILL.md`
**Melanjutkan:** `docs/audit_context/2026-07-29-*` · `2026-07-30-*` · `2026-08-03-uat-compact-IV-*`

---

## 1. Ringkasan Eksekutif

Audit ini memverifikasi isi context/skill terhadap **kondisi database yang sebenarnya**, bukan
terhadap dokumen lain. Tiga sumber bukti dipakai bersama: 105 berkas test UAT-v2-compact I–VII
sebagai spesifikasi pemetaan, 4.997 SQL agent yang nyata dari jejak run, dan ±90 query verifikasi
langsung ke `rpo_v2`.

**Temuan pokok:**

1. **Prinsip yang bekerja sudah teridentifikasi dan terbukti.** Di keluarga yang context-nya
   menyerahkan **daftar kode lengkap** (`filter_code_reference.md` §2), kepatuhan agent 90–100%.
   Di keluarga yang context-nya hanya memberi **aturan naratif** (§4 compound/OR), agent berhenti
   di satu kode pada 4 dari 5 run. Ini adalah prinsip desain yang harus dipakai untuk semua
   perbaikan berikutnya: **serahkan jawabannya, jangan perintahkan penurunannya.**

2. **Tiga cacat fakta membuat SQL gagal atau nol-baris**, bukan salah hitung: alamat kolom
   `kode_kbli`, tipe kolom `t_btp_3_erba`, dan format kode STATUS ERLA.

3. **Kerugian karena cakupan tidak tertutup terukur 20–99%**, terkonsentrasi di lima keluarga
   (`status`, `kemasan_id` ERLA, `status_komitmen`, `jenis_permohonan`, pemilihan sistem) —
   bukan merata di semua keluarga kode.

4. **Kelas pertanyaan segmen-bebas tidak tercakup regression suite sama sekali** dan itulah
   sumber keluhan UAT terbaru (kopi/sirup). Semua 105 test memakai segmen yang punya anchor
   kode; tidak satu pun menguji segmen tanpa anchor.

5. **Seluruh perbaikan yang direncanakan bersifat deklaratif — nol SQL tambahan, nol langkah
   runtime tambahan.** Satu-satunya tambahan prosedural adalah dua butir cek-baca di Gate 5
   terhadap SQL yang sudah ada di context turn itu.

---

## 2. Kondisi Sekarang — Tiga Varian

| Varian | `SEEKNAL_ASK` | `predikat` | `filter_code_ref` | `data_arch` | `visualize-chart` |
|---|--:|--:|--:|--:|:--:|
| `after-forecast-anomaly-refactor` (v1) | 120 | 297 | 247 | 67 | ✗ |
| `after-forecast-anomaly-refactor-v2` (v2) | 123 | 281 | 204 | 67 | ✓ |
| **`after-forecast-chart-enhance`** | **144** | **309** | **259** | **67** | ✓ |

`after-forecast-chart-enhance` = gabungan kedalaman v1 + orkestrasi chart v2, ditambah lima
penambahan yang sudah ada di dalamnya:

| Area | Sudah ada di chart-enhance | Tidak ada di v1/v2 |
|---|---|:--:|
| §1 aturan entity digeneralkan lintas keluarga kode | ✓ | ✓ |
| §7 tren tahunan bukan pelarian saat filter gagal di-resolve | ✓ | ✓ |
| §11 preferensi filter yang pushdown | ✓ | ✓ |
| §12-C headline vs breakdown dipisah per jenis kolom | ✓ | ✓ |
| §12-D lampiran contoh `nomor` sebagai bukti | ✓ | ✓ |
| §12-D2 sinonim · §12-D3 nol adalah jawaban | ✓ | ✓ |
| §4 fixed-binding diperluas + aturan compound/OR | ✓ | ✓ |
| §4d dictionary ≠ data | ✓ | v1 sebagian |
| §5 segmen bebas: coba kolom berkode dulu, jangan jatuh ke tren, dua-bagian di-AND | ✓ | ✓ |
| Gate 3 urutan pemetaan bernomor (intent→entity→kolom→kode→sistem) | ✓ | ✓ |
| Gate 5 butir 6 & 7 (headline global; angka dari SQL turn ini) | ✓ | ✓ |
| Gate 5 kesadaran chart/forecast gagal render | ✓ | ✓ |
| Follow-up carry-over eksplisit | ✓ | ✓ |

**Kesimpulan status:** chart-enhance sudah lebih baik dari kedua baseline pada 13 aspek di atas.
Dokumen ini menangani sisa cacat yang **masih ada di ketiga varian**, termasuk chart-enhance.

### 2.1 Hasil terakhir yang sah

Run `20260804_070140` (3 varian × UAT-MEI26-1) **tidak menghasilkan bukti apa pun** — ketiganya
`status: fatal`, `total_turns: 0`, 0 SQL, 0,0 s. Mati di infra sebelum satu turn pun jalan.
Bukti terakhir yang sah tetap audit compact-IV 3 Agustus: v1 87,5% · v2 56,3%.

---

## 3. Basis Bukti

### 3.1 Database — verifikasi langsung 2026-08-04

`rpo_v2` via tunnel `localhost:5533`, PostgreSQL 17.5, 652 MB, user read-only (terverifikasi:
`CREATE TABLE` ditolak). Schema `public` saja, 8 tabel, **tanpa view/matview sama sekali**.

| Tabel | Baris | Rentang | Catatan tipe |
|---|--:|---|---|
| `t_produk_3_rilis_erla` | 412.643 | 2012-03 → 2026-05 | native; **hanya 7 nilai status** (final states) |
| `t_produk_3_erba` | 259.318 | 2022-09 → hari ini | **seluruh kolom TEXT** |
| `t_btp_3_erla` | 9.784 | 2017-12 → 2026-06 | native; **punya pipeline penuh** |
| `t_btp_3_erba` | 6.928 | 2022-06 → hari ini | **campuran** — tanggal `timestamp`, `trader_id` `bigint` |
| `m_trader_rba` | 15.064 | — | satu-satunya dengan `is_status_industri_*` |
| `m_trader_rla` | 10.302 | — | **tanpa** `is_status_industri_*` |
| `data_dictionary` | 1.141 | — | 21 kategori |
| `forecast_permohonan` | 111 | ds 2022-02 → 2031-04 | `predicted_at` terakhir 2026-05-18 = **basi 78 hari** |

### 3.2 Jejak agent — 4.997 SQL dari 127 skenario, lintas 5 varian context

Diambil dari field `sqls` pada `_data.json` seluruh run di `tests/outputs/2026-07-*` dan `2026-08-*`.

### 3.3 Spesifikasi — 105 berkas UAT-v2-compact I–VII

| Batch | n | Tema |
|---|--:|---|
| compact-I | 16 | AMDK · KOMITMEN · MR/MT · OFF |
| compact-II | 17 | PIPELINE · RISIKO · SKALA · TREN · TOP · TOTAL · SUSU |
| compact-III | 16 | BAYI · BTP · CHAR (kemasan) |
| compact-IV | 16 | MEI26 · NIE25 · OPS · PANGAN · NEGARA · ORGANIK · PERUNTUKAN |
| compact-V | 16 | JP · KEMASAN · KLASIFIKASI · KOMITMEN · LC · MAKLOON · MD |
| compact-VI | 16 | COM · DAERAH · DICABUT · DQ · DRAFT · ERLA · EXPIRY · PIPE |
| compact-VII | 8 | GARAM · IMPOR · IMPORTIR · INVESTIGASI · JP-BARU |

Tiap `note` memuat SQL kanonik literal per sistem + ground truth + alasan pemilihan kolom/kode.
**Ke-105 berkas ini de facto adalah spesifikasi pemetaan paling lengkap yang dimiliki proyek —
lebih rinci dari `filter_code_reference.md` sendiri.** Agent tidak pernah membacanya; ia hanya
membaca context. Setiap fakta pemetaan yang hanya hidup di `note` adalah pengetahuan yang tidak
pernah sampai ke agent.

---

## 4. Yang Sudah Terbukti Bekerja — Jangan Diubah

Empat pilar berikut terverifikasi ke DB dan menjelaskan pass-rate v1 83–87%.

| Aturan | Bukti DB 2026-08-04 |
|---|---|
| §1 entity `nomor` vs `produk_id` | ERBA `COUNT(*)` vs `DISTINCT nomor` = **+25,9%**; ERLA = **+133,3%** |
| §3 dua tier status | Seluruh kode ada di data; terdaftar ERBA 142.405 · ERLA 175.678 |
| §6 format ganda `status_komitmen` | Kode terdampak **0,1,4,5,7,8,9** persis seperti tertulis |
| §12-C anti sum-partisi | 24.710 dari 142.405 `nomor` ERBA punya >1 status → +19,3% over-count |

**Decoy yang benar-benar berbahaya sudah tertangkap:** organik `pemrosesan='301'` = 822 NIE vs
decoy `klasifikasi_id='309'` = 497 NIE (**−40%**).

**Namespace kemasan tepat:** ERBA `1–7` / ERLA `31–39`, **nol irisan**, termasuk beda granularitas.

**`TRIM` pada skala industri load-bearing:** 833 baris `m_trader_rba.skala_industri_id` menyimpan
spasi, bukan string kosong.

**Drift bukan penyebab kegagalan:**

| Kelas | Drift 8–12 hari |
|---|---|
| Seluruh ERLA | **0,00%** (beku sejak 2023) |
| ERBA tahun tertutup | **0,00%** |
| ERBA all-time terbuka | +0,34% … +2,04% |

Toleransi harness 5–10%. Seluruh drift jauh di bawahnya.

---

## 5. Prinsip Desain yang Diturunkan dari Bukti

**Serahkan jawabannya, jangan perintahkan penurunannya.**

| Bentuk aturan | Contoh di context | Kepatuhan agent (jejak nyata) |
|---|---|---|
| **Deklaratif** — daftar kode diserahkan jadi | §2 bucket pipeline | Draft `0910`+`0912`: **79/88 = 90%** lengkap · Data Tambahan (8 kode): seluruh sampel lengkap · Ditolak Sistem (3 kode): seluruh sampel lengkap |
| **Prosedural** — agent disuruh menurunkan sendiri | §4 compound/OR untuk kemasan | `UAT-CHAR-LOGAM-1`: **4 dari 5 run** berhenti di `kemasan_id='35'` saja |

**Koreksi terhadap hipotesa awal.** Sempat diduga penyebabnya adalah deskripsi dictionary yang
kembar (9 dari 36 kode STATUS ERBA dan 15 dari 62 ERLA tidak punya deskripsi unik) sehingga agent
menyimpulkan duplikat lalu mengambil satu. **Jejak membantah itu** — 90% SQL Draft memakai kedua
kode. Jebakan deskripsi kembar tidak pernah aktif justru karena §2 sudah menyerahkan bucket-nya.
Deskripsi kembar tetap dicatat sebagai risiko laten: ia akan aktif untuk keluarga apa pun yang
daftarnya **tidak** diserahkan.

**Konsekuensi biaya.** Perbaikan deklaratif = penambahan isi tabel rujukan yang sudah dibaca agent
di gate yang sama → **nol SQL tambahan, nol round-trip tambahan**. Ini penting karena:

- Anggaran keras `bpom-analyst` = **6 SQL/turn** (2 lookup + 2 discovery + 1 final + 1 retry).
  Aturan prosedural memakan jatah yang sama dipakai P2/P3.
- Audit compact-IV mencatat 3 timeout di rentang **349–387 s** dengan batas 400 s. Satu langkah
  tambahan bisa mendorong query berat melewati batas.
- Varian v2 menambah orkestrasi chart → durasi **+14%** (162 vs 142 s) dengan SQL lebih sedikit
  (3,6 vs 4,4) dan akurasi **turun** (56,3% vs 87,5%). Menambah langkah tidak membuat jawaban
  lebih benar.
- Jejak: rata-rata SQL penghitung run PASS 2,8 vs FAIL 2,6 — nyaris identik. **Yang membedakan
  bukan berapa banyak query, tapi query yang mana.**

---

## 6. Temuan & Rencana Perbaikan

Format tiap butir: kondisi sekarang → bukti → alasan → perubahan → ekspektasi.

---

### F-1 · `kode_kbli` salah alamat kolom
**Prioritas: P0 — hard error** · Berkas: `filter_code_reference.md` §4b

**Kondisi sekarang.** §4b baris "Bidang usaha": `KODE_KBLI` → *"KBLI columns on trader tables"*.

**Bukti.**
```
ERROR:  column "kode_kbli" does not exist    -- m_trader_rba
```
Kolomnya ada di `t_produk_3_erba` (terisi 259.317 dari 259.318) dan `t_btp_3_erba`.
Dictionary memuat 95 kode `KODE_KBLI` — konsepnya hidup, hanya alamatnya salah tulis.

**Alasan.** Setiap pertanyaan bidang usaha yang mengikuti context menghasilkan error, bukan angka.
Error memakan jatah *corrected retry* di Gate 4.

**Perubahan.** Perbaiki alamat kolom: `kode_kbli` berada di tabel produk/BTP ERBA, bukan tabel
trader. Tambahkan bahwa entitas yang dihitung karenanya adalah produk, bukan perusahaan.

**Ekspektasi.** Pertanyaan bidang usaha menghasilkan angka. Satu slot retry kembali tersedia.

---

### F-2 · `t_btp_3_erba` bukan all-TEXT
**Prioritas: P0 — hard error** · Berkas: `predikat.md` §9, §2 · `data_architecture.md`

**Kondisi sekarang.** `predikat.md` §9: *"ERBA stores **all** columns as TEXT… Always cast on the
ERBA side"*. §2: *"A BTP table is structurally a product table for counting purposes"*.
`data_architecture.md` tabel: `t_btp_3_erba / t_btp_3_erla | TEXT / native`.

**Bukti.**

| Kolom | `t_produk_3_erba` | `t_btp_3_erba` |
|---|---|---|
| `tanggal`, `tanggal_aju`, `tanggal_bayar`, `tanggal_exp` | text | **timestamp** |
| `trader_id` | text | **bigint** |
| `produk_id`, `status` | text | text |

```
ERROR:  invalid input syntax for type timestamp: ""
LINE 1: ... from t_btp_3_erba where nullif(tanggal,'')::timestamp ...
```

**Alasan.** Dua berkas sepakat pada fakta yang salah. Pola cast wajib §9 diterapkan ke tabel BTP
menghasilkan error keras. **12 berkas test bertema BTP** bergantung pada kolom ini.

**Perubahan.** Batasi §9 ke `t_produk_3_erba`; beri baris tipe tersendiri untuk tabel BTP di
`data_architecture.md`. Nyatakan bahwa "BTP structurally a product table" berlaku untuk **entity
dan aturan hitung**, bukan untuk tipe kolom.

**Ekspektasi.** Pertanyaan BTP bertanggal menghasilkan angka. Tidak ada lagi cast yang salah arah.

---

### F-3 · Format kode STATUS ERLA — dictionary tanpa zero-pad
**Prioritas: P0 — nol baris senyap** · Berkas: `filter_code_reference.md` §4b, §4d

**Kondisi sekarang.** Anchor §3 sudah benar (`'0099','0999','0906','9999'`). Gate 2 menyahkan
jalur **P2** (listing kategori dictionary) sebagai jalan resmi, tanpa memberi tahu bahwa untuk
`status` ERLA jalur itu menghasilkan kode yang tidak cocok dengan data.

**Bukti.**

| | dictionary `sumber='ERLA'` | data `t_produk_3_rilis_erla.status` |
|---|---|---|
| NIE terbit | `999` | `0999` (183.865) |
| Perubahan | `906` | `0906` (18.353) |
| Tidak berlaku | `99` | `0099` (2.849) |
| Dicabut | `9` | `0009` (2.064) |
| Dihapus | `0` | `0000` (14) |
| Sudah diubah | `9999` | `9999` (205.497) ← satu-satunya cocok literal |

Aturan `LPAD(kode,4,'0')` pada baris `sumber='ERLA'` **juga menyelesaikan kode yang §4d(2)
sebut "tidak ada di dictionary"**:

| Data | Ada di dict ERBA | Setelah zero-pad pada dict ERLA |
|---|:--:|---|
| `0500` (107, ERBA) | ✗ | ✓ Kepala Sub Direktorat - Proses Verifikasi |
| `0916` (5, ERBA) | ✗ | ✓ Pendaftar - Proses Verifikasi Ditolak |
| `0909` (3, ERBA) | ✗ | ✓ Pendaftar - Proses Verifikasi Ditolak |
| `0417` (1, ERBA) | ✗ | ✓ Kepala Seksi - Proses Verifikasi Data Tambahan |
| `0504` (1, ERBA) | ✗ | ✓ Kepala Sub Direktorat - Proses Verifikasi Tambahan Data |
| `0900` (1, ERBA) | ✗ | ✓ Pendaftar - Draft |
| `0299` (2, `t_btp_3_erla`) | ✗ | ✓ Admin Loket - SPP Siap Diambil |

Yang benar-benar tak terpetakan tinggal dua: `000X` (14 baris) dan status berisi **4 spasi**.

**Alasan.** Dari 6 kode status ERLA yang dipakai sehari-hari, hanya satu yang cocok literal.
Agent yang menempuh P2 mendapat filter yang mengembalikan 0 baris lalu menyimpulkan "tidak ada
data". Efek keduanya: kolom `status` ERBA ternyata **memuat campuran** kode ERBA-native dan kode
ber-namespace ERLA yang di-zero-pad — premis "kolom status ERBA hanya berisi kode ERBA" salah.

**Perubahan.**
1. §4b: satu baris aturan format — kode `STATUS` `sumber='ERLA'` disimpan tanpa zero-pad di
   dictionary sementara data menyimpan 4 karakter; pakai `LPAD(kode,4,'0')`.
2. §4d(2): perbaiki daftar. Pindahkan `0500/0504/0909/0916/0900/0201` dari "hilang dari dictionary"
   ke "terdaftar di namespace ERLA, butuh zero-pad". Sisakan `000X` dan status-4-spasi sebagai
   satu-satunya yang benar-benar tak terpetakan.
3. Generalisasi: **format kode di dictionary belum tentu sama dengan format di data** — berlaku
   juga untuk `DAERAH` (lihat F-4).

**Ekspektasi.** Lookup status ERLA menghasilkan kode yang cocok dengan data. Kode "asing" di ERBA
bisa diberi label, bukan dilaporkan sebagai anomali tanpa nama. Jawaban "tidak ada data" hanya
muncul ketika memang tidak ada barisnya.

---

### F-4 · Format kode wilayah & `provinsi_id` tanpa dictionary
**Prioritas: P1** · Berkas: `filter_code_reference.md` §4b

**Kondisi sekarang.** §4b: *"probe one sample row for the code format before filtering"*.

**Bukti.**
- Dictionary: 514 baris, **semuanya 5 karakter bertitik** (`11.01`, `31.75`).
- Data `daerah_trader`: **4 karakter tanpa titik** (`3175`).
- Jembatan `REPLACE(kode,'.','')` terverifikasi cocok.
- Hit-rate join ke `m_trader_rba.kotakab_id` = **9.755/15.064 = 64,8%**; seri `3700`/`3800`
  (mis. `3878`, `3701`) tidak punya baris dictionary.
- `provinsi_id` (`3100`, `3700`, `3800`) **tidak punya entri dictionary sama sekali** — kategorinya
  berisi kabupaten/kota saja.

**Alasan.** "Probe dulu" adalah insting yang benar tapi membakar satu query dan bisa salah baca.
Formatnya tetap, jadi bisa dipin. Dan klaim §4b bahwa `PROVINSI_ID` bisa di-resolve lewat kategori
itu tidak benar.

**Perubahan.** Pin jembatan formatnya; nyatakan hit-rate 65% sebagai keterbatasan yang harus
disebut saat menyajikan agregasi wilayah; hapus `PROVINSI_ID` dari daftar yang bisa di-resolve
lewat kategori DAERAH.

**Ekspektasi.** Nol query probe untuk wilayah. Jawaban agregasi wilayah menyebut porsi yang tidak
terpetakan alih-alih menyajikannya sebagai total lengkap.

---

### F-5 · `status` kosong berisi 4 spasi
**Prioritas: P1** · Berkas: `predikat.md` §8 · `filter_code_reference.md` §2

**Kondisi sekarang.** §8 menyediakan guard `WHERE tanggal IS NOT NULL AND tanggal != ''`.
Tidak ada guard untuk `status`.

**Bukti.**
```
t_produk_3_erba.status  →  WHITESPACE len=4 : 1.071 baris
                           NULL             : 0
                           EMPTY ''         : 0
```
`status <> ''` **tidak menangkapnya**; hanya `TRIM(status) = ''` yang menangkap. Nilai ini lebih
besar dari Verifikator 2 (193) + Direktur (829) digabung, dan selalu masuk ke setiap bucket
`NOT IN`. Kolom lain bersih: `kemasan_id` dan `peruntukan` tidak punya kasus ini.

**Alasan.** Bucket `NOT IN` seperti "belum selesai / dalam proses" menyerapnya diam-diam.
`filter_code_reference.md` §2 sudah punya rambu untuk kode langka tapi tidak menyebut bucket
whitespace yang justru terbesar.

**Perubahan.** Tambahkan ke §2 sebagai anggota daftar kode tak terpetakan, dengan catatan bahwa
guardnya `TRIM(...)`, bukan `<> ''`. Perbaiki juga isi daftar itu: buang `0201` (tidak eksis
sebagai status ERBA), tambahkan `0417`.

**Ekspektasi.** Bucket `NOT IN` menyebutkan porsi tak terpetakan dengan angka, bukan diam.

---

### F-6 · Daftar kode terpenggal — `klasifikasi_id`
**Prioritas: P1** · Berkas: `filter_code_reference.md` §4

**Kondisi sekarang.** §4 baris "Klasifikasi pangan" memuat 6 kode: `301` makanan · `302` minuman ·
`305` berklaim · `310` diet · `311` bayi & anak · `312` ibu hamil/menyusui.

**Bukti.** Dictionary memuat **13 kode**. Yang hilang dari §4:

| Kode | Deskripsi | Volume |
|---|---|--:|
| **`3`** | **Deputi 3 (Pangan)** — bucket induk | **42.834 NIE ERBA = 30% populasi** |
| `303` | Bahan Tambahan Pangan | 2 ERLA |
| `304` | **Minuman Beralkohol** | **17.009 baris ERLA** |
| `306` | Pangan Dengan Herbal | 390 ERLA |
| `307` | Pangan Iradiasi | 2 ERLA |
| `308` | Pangan Rekayasa Genetika | 13 ERLA |
| `309` | Organik (decoy — sudah tercatat) | 694 ERLA |

Jejak agent: **47 SQL memfilter `klasifikasi_id`, nol menyertakan kode `3`.**
Kode `3` aktif sampai hari ini (`tanggal_aju` max = 2026-08-04), bukan sisa legacy.

Perbandingan satuan NIE ERBA: `301` = 60.753 · `3` = 42.834 · `302` = 38.935 · total terdaftar
142.405. Jadi Makanan + Minuman = 70% populasi; bucket induk `3` = 30%.

**Alasan.** Daftar tampil sebagai daftar lengkap padahal memuat 6 dari 13. Dari sudut agent, kode
yang tidak terdaftar **tidak ada di dunia** — ia tidak punya alasan membuka dictionary untuk
konsep yang rujukannya sudah menjawab. 0 dari 47 adalah bukti langsung.

**Perubahan.** Lengkapi ke 13 kode. Tandai `3` sebagai **bucket induk/catch-all** dengan porsinya,
dan tetapkan aturan umum: kode yang menampung >25% populasi dan deskripsinya bukan kelas bisnis
adalah bucket sisa — jangan diperlakukan sebagai kelas, dan sebutkan porsinya saat menyajikan
breakdown.

**Ekspektasi.** "Berapa produk makanan" menjawab `301` = 60.753 **dan** menyebut 42.834 NIE (30%)
berada di bucket induk yang belum terklasifikasi ke subtipe. "Minuman beralkohol" bisa dijawab.

---

### F-7 · Konsep majemuk hanya diatur lewat prosa
**Prioritas: P1** · Berkas: `filter_code_reference.md` §4

**Kondisi sekarang.** §4 punya paragraf compound/OR yang menyuruh membaca kategori penuh dan
menyertakan setiap kode yang anggota konsep. Cakupannya disebut eksplisit: *"kemasan, BTP,
klasifikasi, pemrosesan, status produk"* — **`status` tidak termasuk**.

**Bukti — kerugian terukur bila berhenti di satu kode.**

*Pipeline ERBA (entity `produk_id`):*

| Konsep | ambil satu | LENGKAP | hilang |
|---|--:|--:|--:|
| Ditolak Sistem — `0908` saja | 3.059 | 13.085 | **−76,6%** |
| Verifikator 2 — `0502` saja | 85 | 193 | −56,0% |
| Data Tambahan — sisi petugas saja | 3.164 | 6.993 | −54,8% |
| Data Tambahan — `0901` saja | 13 | 6.993 | **−99,8%** |
| Draft — `0912` saja | 22.767 | 28.271 | −19,5% |
| Verifikator 1 — `0405` saja | 1.283 | 1.563 | −17,9% |
| Bayar — `0903` saja | 6.867 | 7.230 | −5,0% |

*Kemasan ERLA (entity `nomor`):*

| Konsep | ambil satu | LENGKAP | hilang |
|---|--:|--:|--:|
| Komposit/laminat — `37` saja | 741 | 3.361 | **−78,0%** |
| Logam — `35` saja | 6.968 | 21.118 | −67,0% |
| Logam — `36` saja | 14.150 | 21.118 | −33,0% |

*Lainnya:*

| Konsep | ambil satu | LENGKAP | hilang |
|---|--:|--:|--:|
| Komitmen "disetujui" — `4` saja | 2.947 | 15.482 | **−81,0%** |
| "Perubahan/revisi" — mayor saja | 8.184 | 17.442 | −53,1% |
| JP "baru" — `301` saja | 45.493 | 57.085 | −20,3% |
| `status_komitmen` kode 8 — bentuk polos saja | 108 | 136 | −20,6% |
| Risiko Tinggi — `301` saja (tanpa `304`) | 84.372 | 87.464 | −3,5% |

*Yang justru aman — supaya aturan tidak berlebihan:*

| Konsep | ambil satu | LENGKAP | hilang |
|---|--:|--:|--:|
| AMDK ERBA — `1401` saja | 6.709 | 6.874 | −2,4% |
| AMDK ERLA — `652` saja | 9.038 | 9.132 | −1,0% |
| Formula bayi ERBA — `1301` saja | 61 | 61 | **0%** |
| Single MD — `306` saja | 5.955 | 5.959 | −0,1% |
| Pipeline produk saja vs produk+BTP | 28.271 | 29.237 | −3,3% |

Jejak agent pada keluarga prosedural: `UAT-CHAR-LOGAM-1` — 4 dari 5 run memakai `kemasan_id='35'`
saja, satu memakai `35`+`36`.

**Alasan.** Daftar kode ada, tapi **pemetaan konsep→himpunan tidak ada**. Agent harus
menurunkannya sendiri dari deskripsi, dan "Aluminium Foil" tidak mengandung kata "logam" maupun
"kaleng". Aturan compound/OR memberi *perintah* tanpa memberi *jawaban*. Bandingkan §2 yang
memberi jawaban: kepatuhan 90–100%.

**Perubahan.** Tambahkan **tabel penutupan konsep** di §4 — satu baris per konsep majemuk, berisi
himpunan kode per sistem, sejajar bentuk §2:

| Konsep | ERBA | ERLA |
|---|---|---|
| logam (kaku) | `5` | `35` |
| logam (termasuk foil) | `5` | `35`,`36` |
| komposit/laminat | `4` | `34`,`37` |
| disetujui (komitmen) | `4`,`7` | — |
| perubahan/revisi | `302`,`303` | `302`,`303` |
| dicabut atau dihapus | `0009`,`0000` | `0009`,`0000` |
| risiko Tinggi | `301`,`304` | — |

Perluas cakupan paragraf compound/OR agar menyertakan `status`. Tambahkan **aturan penutupan
umum** di §0: resolusi kode belum selesai saat satu kode ditemukan; ia selesai saat pertanyaan
*"adakah kode lain dalam kategori ini yang juga anggota konsep yang diminta?"* sudah dijawab.
Tiga pemicu yang bisa dikenali dari data tanpa hafalan:
- deskripsi kode terpilih **tidak unik** dalam kategorinya → ambil semua yang berbagi deskripsi
  (9 dari 36 kode STATUS ERBA dan 15 dari 62 ERLA masuk kategori ini);
- konsep yang diminta lebih lebar dari bunyi satu deskripsi → baca kategori penuh;
- pertanyaan menyentuh dua sistem → penerjemahan kode boleh **1:banyak**, bukan hanya 1:1.

**Batas atas yang wajib disebut.** Penutupan dibatasi oleh konsep yang ditanya, bukan oleh
kemiripan string. "Ditolak Sistem" (`0908`,`0911`,`0918`) **tidak boleh** dilebur dengan "Ditolak
petugas" (`0902`,`0905`,`0913`). Daftar bucket §2 yang menentukan batasnya.

**Ekspektasi.** Konsep majemuk dijawab dari tabel, bukan dari penurunan mandiri. Kerugian 20–99%
di lima keluarga di atas hilang. Nol query tambahan.

---

### F-8 · Prioritas sumber: rujukan vs dictionary belum dinyatakan
**Prioritas: P1** · Berkas: `SEEKNAL_ASK.md` Gate 2 · `filter_code_reference.md` §0

**Kondisi sekarang.** Gate 2 menyahkan lima jalur: P1 anchor, P2 category listing, P3 scoped
label, P4 segment discovery, P5 ask. Tidak ada yang menyatakan siapa menang ketika P2/P3
menghasilkan sesuatu yang berbeda dari daftar §2.

**Bukti.** §2 memuat bucket lengkap dan hand-curated. Dictionary memuat 16 grup deskripsi kembar
(`Pendaftar - Draft` untuk `0910`+`0912`, `Pendaftar - Perlu Data Tambahan` untuk lima kode, dst)
dan format ERLA tanpa zero-pad. Dua sumber ini bisa berbeda hasilnya untuk pertanyaan yang sama.

**Alasan.** Selama prioritasnya tidak dinyatakan, jalur P2/P3 bisa membatalkan §2 tanpa agent sadar.

**Perubahan.** Satu kalimat di §0 dan Gate 2: untuk keluarga yang rujukan ini sudah menyerahkan
bucket lengkapnya (`status`, dan tabel penutupan F-7), daftar di rujukan **mengalahkan** hasil
listing dictionary. Dictionary di situ berperan sebagai pemberi label, bukan penentu cakupan.

**Ekspektasi.** Verifikasi ke dictionary tidak lagi bisa mempersempit cakupan yang sudah benar.

---

### F-9 · Scope hasil klarifikasi tidak diverifikasi terpakai
**Prioritas: P1** · Berkas: `SEEKNAL_ASK.md` Gate 5

**Kondisi sekarang.** Gate 1 mewajibkan klarifikasi sistem dan itu berjalan. Gate 5 butir 5
mengecek scope **dinyatakan**, bukan scope **terpakai**.

**Bukti — kerugian menjawab satu sistem untuk pertanyaan dua sistem:**

| Konsep | ERBA saja | GABUNGAN | hilang |
|---|--:|--:|--:|
| pangan berklaim | 260 | 8.954 | **−97,1%** |
| pangan diet | 35 | 854 | **−95,9%** |
| makloon | 2.261 | 7.307 | −69,1% |
| impor | 45.747 | 110.787 | −58,7% |

Jejak agent pada skenario yang deskripsinya sendiri menyatakan *scope-agnostic*:

| Cakupan tabel di SQL agent | FAIL | PASS | rasio gagal |
|---|--:|--:|--:|
| satu tabel | 29 | 31 | **48%** |
| dua tabel | 61 | 124 | 33% |

Kasus terverifikasi di audit compact-IV: `UAT-NEGARA-1` v2 menjawab **4.081** setelah scope
gabungan disepakati; ground truth 16.813.

**Alasan.** Tidak ada butir mana pun yang membandingkan scope hasil klarifikasi dengan tabel yang
benar-benar muncul di SQL final.

**Perubahan.** Satu butir di Gate 5: tabel yang muncul di SQL final harus sama dengan scope yang
disepakati; bila satu sisi sengaja ditinggalkan, alasannya disebut di jawaban (mis. `jenis_btp`
ERLA yang tidak punya label — lihat F-12).

**Ekspektasi.** Scope "Gabungan" berarti SQL final menyentuh kedua tabel, atau jawaban menyatakan
keterbatasannya. **Nol query tambahan** — ini cek terhadap SQL yang sudah tertulis di context turn.

---

### F-10 · Aturan permohonan tanpa cabang kata kerja
**Prioritas: P1** · Berkas: `predikat.md` §4

**Kondisi sekarang.** §4 baris permohonan: *"all types `IN ('301','302','303','304','305')`,
**no status filter**"* — mutlak.

**Bukti.** Permohonan ERBA 2023, `tanggal_bayar`, entity `produk_id`:

| | hasil |
|---|--:|
| tanpa filter status | **42.328** |
| dengan filter status sah | **37.757** |

Selisih **10,8%** — dua kali toleransi 5%.

Spesifikasi membedakannya lewat kata kerja: *"tren permohonan"* / *"berapa yang masuk"* → tanpa
filter; *"permohonan … yang **disetujui** / **diterima**"* → dengan filter.

**Alasan.** Aturan tanpa syarat, spesifikasi bersyarat. Apa pun yang dipilih agent, separuh
keluarga pertanyaan permohonan pasti meleset.

**Perubahan.** Pecah baris permohonan menjadi dua dengan pemicu kata kerja eksplisit — pola yang
sudah terbukti bekerja di §3 untuk tier status ("aktif" vs "terdaftar").

**Ekspektasi.** Kedua bentuk pertanyaan permohonan dijawab dengan populasi yang tepat.

---

### F-11 · Segmen bebas — kelas yang tidak tercakup regression suite
**Prioritas: P0 untuk UAT berjalan** · Berkas: `filter_code_reference.md` §5 · `data_architecture.md`

**Kondisi sekarang.** chart-enhance §5 sudah punya perbaikan yang tidak ada di baseline: coba
kolom berkode dulu, jangan jatuh ke tren tahunan, dan pertanyaan dua-bagian ("kopi dari
Indonesia", "sirup impor") di-AND dalam satu WHERE dengan *"Never drop one part"*.
`predikat.md` §7 chart-enhance juga sudah punya pengaman anti-tren.

**Cacat yang tersisa — ada di ketiga varian.** `data_architecture.md` (byte-identik di v1, v2,
dan chart-enhance):

> `nama_kategori is ERBA-only ~40% filled (search only, never group)`

**Bukti.**

| | terisi | % | nilai distinct |
|---|--:|--:|--:|
| ERBA | 104.749 | 40,4% | 1.106 |
| **ERLA** | **396.949** | **96,2%** | **1.697** |

ERLA justru yang paling penuh, dan katalog kopi/sirup terkaya ada di sana:

| Nilai `nama_kategori` | ERBA | ERLA |
|---|--:|--:|
| `Kopi Instan` | 160 | 435 |
| `Kopi Bubuk` | 2.100 | 4.008 |
| `Sirup Berperisa` | 754 | **2.440** |
| `Sirup Encer Berperisa` | 409 | 906 |

Jawaban yang seharusnya keluar: kopi instan asal Indonesia = ERBA **116** + ERLA **199**;
sirup asal Malaysia = ERBA **92** + ERLA **264**.

Enam berkas test (`UAT-GARAM-1`, `GARAM-2`, `BAYI-1`, `BAYI-2`, `BAYI-3`, `BAYI-DICABUT-1`)
memakai `nama_kategori` **di sisi ERLA** sebagai jalur kanonik. Context melarang agent memakai
kolom yang justru dibutuhkan spesifikasi.

**Cacat kedua — penutupan di ranah teks bebas.** "kopi" menyebar ke **12+ nilai**
`nama_kategori`. `%kopi%instan%` → 315 NIE gabungan; `%kopi%` → 7.776 NIE. Belum ada aturan
untuk kasus ini di varian mana pun.

**Cacat ketiga — ejaan bervariasi di dalam kolom yang sama.** `Garam Konsumsi Beriodium` (1.476)
vs `Garam Konsumsi Ber**y**odium` (480) vs `Garam Beriodium` (359). Dan ILIKE bocor:
`Bumbu Penguat Rasa dan Garam` (10) ikut terjaring oleh `%garam%`.

**Cacat keempat — namespace segmen terpisah total.**
```
jenis_pangan:  ERBA 209 kode · ERLA 304 kode · IRISAN = 0
panjang kode:  ERBA 2–5 char · ERLA tepat 3 char
kategori_pangan panjang: ERBA 12–13 char · ERLA 2–10 char
```
Nol irisan — bukan "sebagian berbeda". §5 hanya memberi 3 baris contoh (AMDK, garam, formula
bayi) tanpa menyatakan aturan umumnya.

**Cacat kelima — kode induk vs anak, dan §5 mengikat ke yang salah.** §5 saat ini:
*"Garam beryodium | ERBA `kategori_pangan = '120101000001'` (never `jenis_pangan='1204'`)"*.

| Filter ERBA | baris | DISTINCT `nomor` |
|---|--:|--:|
| `jenis_pangan LIKE '1204%'` (induk, 8 sub-kode) | 1.864 | **1.782** |
| `kategori_pangan='120101000001'` (satu anak) | 1.736 | 1.672 |

Sub-kode 100% berada di dalam induknya. Mengikat ke anak membuang 110 NIE (−6,2%), dan §5
justru **melarang** induk yang benar. Di sisi ERLA `jenis_pangan LIKE '1204%'` = **0 baris**
(namespace tidak ada), sementara `kategori_pangan='12010103'` = 1.453 NIE berfungsi.

**Bukti cakupan uji.** Dari 105 berkas test, **tidak satu pun** menguji segmen bebas tanpa
anchor kode. Semua yang ada (AMDK, garam, formula bayi, susu) punya kode kanonik. **Kelas
kegagalan ini tidak tercakup regression suite** — itu sebabnya bisa lolos tanpa terdeteksi.

**Hipotesa regresi "Juni jalan, sekarang tidak"** — belum terbukti, tidak ada trace percobaan:

| | protein (berhasil) | kopi instan asal Indonesia (gagal) |
|---|---|---|
| bagian pertanyaan | satu (segmen saja) | **dua** (segmen + negara) |
| bentuk `nama_kategori` | panjang & deskriptif (`Pangan Tambahan Untuk Olahragawan Tinggi Energi Protein`) | pendek (`Kopi Instan`) |
| satu ILIKE cukup? | ya | tidak — butuh dua kolom di-AND |

Dugaan yang lebih sederhana daripada "ada poin terlewat saat training ulang": bukan kemampuan
yang hilang, melainkan **kelas pertanyaan dua-bagian yang memang belum pernah tertangani**.
Dapat diuji dengan menambahkan skenario test (lihat §8).

**Perubahan.**
1. `data_architecture.md`: perbaiki keterisian `nama_kategori` per sistem; hapus label "ERBA-only".
2. §5: ganti binding garam ke kode induk `jenis_pangan='1204'` untuk ERBA; pertahankan
   `kategori_pangan='12010103'` untuk ERLA.
3. §5: nyatakan aturan umum **kode induk vs anak** — bila kolom bertingkat, mulai dari induk;
   turun ke anak hanya bila pertanyaan menyebut varian spesifik.
4. §5: nyatakan aturan umum **namespace segmen terpisah total** antara ERBA dan ERLA
   (irisan nol) — bukan tiga contoh, tapi sifat kolomnya.
5. §5: aturan **penutupan teks bebas** — segmen yang cocok ke >1 nilai `nama_kategori`
   menampilkan daftar nilai yang terjaring, atau menanyakan lingkupnya; ejaan bisa bervariasi
   dalam kolom yang sama; ILIKE bisa bocor, jadi sebutkan pola yang dipakai.

**Ekspektasi.** "Kopi instan asal Indonesia" dijawab **116 (ERBA) + 199 (ERLA)** dengan pola
pencarian disebutkan, bukan tren tahunan 2020–2026. "Sirup berperisa asal Malaysia" dijawab
**92 + 264**. Kedua bagian pertanyaan selalu bertahan ke WHERE.

---

### F-12 · Keluarga kode tanpa label — jangan laporkan sebagai nol
**Prioritas: P2** · Berkas: `filter_code_reference.md` §4d

**Kondisi sekarang.** §4d(1) sudah benar menyatakan rentang `jenis_btp` ERBA dan ERLA terpisah.

**Bukti.** ERBA 21–48, ERLA **777–805**, **nol irisan** — terverifikasi. Rentang ERLA
**tidak punya label di kategori dictionary mana pun**. Sebelas kode dictionary nol baris di ERBA,
termasuk **`46` Pengawet** — contoh yang dipakai §0 sendiri ("BTP pengawet"). Mengikuti resep §0
pada contohnya sendiri menghasilkan 0 baris di ERBA dan rentang tak terpetakan di ERLA.

**Perubahan.** Nyatakan konsekuensinya: pertanyaan "BTP jenis X" hanya bisa dijawab untuk ERBA;
untuk ERLA tidak ada pemetaan kode→label. Ganti contoh §0 dari "BTP pengawet" ke keluarga yang
datanya ada. Tandai kode terdaftar-tapi-nol-baris: `status` ERBA `0402·0406·0601·0666·0700·0905`,
`status_komitmen` `2`, `jenis_btp` ERBA 11 kode.

**Ekspektasi.** Nol dilaporkan sebagai keterbatasan pemetaan, bukan sebagai fakta bisnis.
Tahap yang tidak eksis tidak dilaporkan seolah menyumbang.

---

### F-13 · Kalibrasi — aturan yang benar tapi bobotnya salah
**Prioritas: P2** · Berkas: `predikat.md` §1, §8, §9 · `filter_code_reference.md` §4

**(a) `COUNT(*)` divonis terlalu luas.** §1: *"`COUNT(*)` on these tables is a **BLOCK** — the
answer is wrong by 25–57%"*. Bukti: `produk_id` **unik** di kedua tabel produk (259.318 distinct =
259.318 baris; 412.643 = 412.643) — jadi `COUNT(DISTINCT produk_id)` ≡ `COUNT(*)`. Vonis itu benar
**hanya untuk NIE**. Perubahan: pisahkan tegas per entity.

**(b) Angka over-count ERLA salah.** §1 menulis "+57% ERLA". Aktual **+133,3%** (412.643 baris /
176.900 distinct `nomor` = 2,33×). ERBA "+25%" benar (+25,9%). Meremehkan justru di tempat
dampaknya terbesar.

**(c) Eksklusi akun uji seragam padahal dampaknya tidak.**

| Populasi | tanpa eksklusi | dengan eksklusi | selisih |
|---|--:|--:|--:|
| Draft (`0910`,`0912`) | 28.271 | 26.711 | **−1.560 = −5,5%** |
| NIE terdaftar ERBA | 142.405 | 142.387 | −18 = −0,013% |

§8 mewajibkannya *"on every count query"* dengan bobot sama. Di pipeline selisihnya melampaui
toleransi 5% dan bisa menentukan PASS/FAIL sendirian; di NIE tidak pernah berpengaruh.
Perubahan: nyatakan bahwa keputusan eksklusi material untuk pipeline, nyaris tidak untuk NIE.

**(d) Kekhawatiran cast berlebihan.** ERBA `trader_id` 100% numerik (0 null, 0 kosong, 0
non-numerik); `tanggal`/`tanggal_bayar` 100% well-formed-atau-kosong; `status_komitmen` 100%
numerik-atau-kosong. Yang benar-benar perlu hanya `NULLIF(tanggal,'')::timestamp` — **57.931
baris ERBA (22,3%) `tanggal`-nya kosong**. Perubahan: sisakan yang berdasar.

**(e) Binding impor tidak berisiko.** `status_produk='302'` vs `status_usaha='33'` menghasilkan
populasi sama: ERBA 45.747 vs 45.745 (selisih 2); ERLA 65.040 vs 65.040 (identik). §4 membingkainya
sebagai jebakan yang *"returns a plausible-but-wrong number"* — tidak. Perubahan: turunkan dari
daftar fixed-binding supaya tidak mengencerkan decoy yang asli (organik −40%).

**Ekspektasi.** Perhatian agent terpakai di tempat yang benar-benar berisiko.

---

### F-14 · Cacat fakta lain-lain
**Prioritas: P2** · Berkas: `data_architecture.md` · `filter_code_reference.md`

| Klaim sekarang | Fakta DB 2026-08-04 |
|---|---|
| `t_btp_3_erla` "2018→2024" | **2017-12 → 2026-06** — meleset 2 tahun; agent akan menjawab "tidak ada data 2025/2026" |
| §2 kode langka: `000X, 0201, 0900, 0909, 0916` | `0201` **tidak eksis** sebagai status ERBA; `0417` (1 baris) tidak terdaftar; bucket 4-spasi (1.071) tidak disebut |
| §4b "berapa produsen/importir" | `m_trader_rla` **tidak punya** `is_status_industri_*` → strukturalnya ERBA-only, belum dinyatakan |
| §4c `kategori_dokumen` "NULL/empty" | ERBA 1.134 **NULL**, tidak pernah `''`; ERLA 163.454 NULL |
| §4 peruntukan khusus = `0201` mati | `0201` = 2.215 NIE; seluruh non-`0000` = 2.568 (**+16%**). §4 dan §4d saling tabrak tanpa pemutus |
| §4 `pemrosesan` 301/302/304 | Tidak menyebut `300` "Tanpa Proses Tertentu" = **99,6% seluruh baris** — breakdown pemrosesan hampir seluruhnya satu bucket |
| §4 `status_produk` set ERBA | ERLA punya `303` (1.432) dan `305` (198) yang tidak terdaftar |
| §5 `LEFT(kategori_pangan,2)` | Benar, tapi tidak dinyatakan bahwa **hanya prefiks 2-digit** yang sebanding lintas sistem |

**Ekspektasi.** Tidak ada lagi jawaban "tidak ada data" yang disebabkan cakupan tabel yang salah
dicatat, dan tidak ada aturan yang saling tabrak tanpa pemutus.

---

### F-15 · Follow-up: carry-over sudah ada, verifikasinya belum
**Prioritas: P1** · Berkas: `SEEKNAL_ASK.md` · `skills/bpom-analyst/SKILL.md`

**Kondisi sekarang.** chart-enhance sudah memperbaiki ini dibanding baseline. Baseline hanya
punya empat baris: *"Reuse validated ANSWERS; re-derive METHOD… Change only what the user
changed"* — menyuruh membawa tapi tidak pernah menyebut **apa** yang dibawa. chart-enhance
menambahkan paragraf carry-over eksplisit (subjek, sistem/scope, rentang waktu, entity, kode
yang sudah di-resolve) di `SEEKNAL_ASK.md`, plus stop-rule senada di `bpom-analyst`.

**Cacat yang tersisa.** Tidak ada cek bahwa hal-hal yang dibawa itu **benar-benar muncul** di SQL
final. Bentuknya sama persis dengan F-9: aturannya menyuruh, tidak ada yang memverifikasi. Ketika
agent menyusun SQL baru untuk turn lanjutan, tidak ada yang mengikat SQL itu ke scope turn
sebelumnya.

**Perubahan.** Gabungkan dengan butir Gate 5 dari F-9 menjadi satu cek: **scope efektif turn ini**
— hasil klarifikasi untuk turn baru, hasil carry-over untuk follow-up — harus terlihat di SQL
final. Satu cek, dua kegunaan.

**Ekspektasi.** Follow-up pendek ("kalau 2024?", "yang ERLA saja", "pisah per bulan") mengganti
hanya bagian yang disebut dan mewarisi sisanya, dan itu terverifikasi di SQL, bukan hanya di niat.
**Nol query tambahan.**

---

### F-16 · Lampiran nomor sebagai bukti
**Prioritas: P2** · Berkas: `predikat.md` §12-D

**Kondisi sekarang.** chart-enhance §12-D sudah punya, tidak ada di baseline:
*"For a specific product or narrow segment … add a few example `nomor` with their nama/merk as
evidence beside the count. Keep it short (about 5–10 rows), and keep it out of the chart …"*

**Cacat yang tersisa — ambiguitas istilah.** "Nomor pengajuan" bisa berarti dua hal:

| Istilah | Kolom | Isi |
|---|---|---|
| NIE / izin edar | `nomor` | `MD …` dalam negeri (ERBA 143.383) · `ML …` impor (58.005) |
| **nomor pengajuan** (NIE belum terbit) | `nomor` berawalan `ER…` (ERBA 57.920, hanya 9 di status sah) atau `produk_id` | berkas permohonan |

Data pendukungnya siap: `nomor`, `nama`, `merk`, `nama_kategori`, `tanggal` tersedia dalam satu
query. Format `nomor`: `MD ` + digit dengan **satu spasi**; baris menyimpang hanya 1 per tabel;
pola `BPOM RI MD` **0 baris** (itu format cetak label, bukan isi DB).

**Perubahan.** Tambahkan satu kalimat: kolom identitas pada lampiran bukti mengikuti `entity`
yang sudah dipilih di Gate 3 — `nomor` untuk pertanyaan NIE, `produk_id` (atau `nomor` berawalan
`ER`) untuk pertanyaan permohonan. Pin format `MD `/`ML ` supaya tidak perlu di-probe.

**Ekspektasi.** Lampiran bukti konsisten dengan entity yang dihitung, tidak menampilkan NIE untuk
pertanyaan permohonan.

---

### F-17 · Kesadaran chart/forecast gagal render
**Prioritas: P2 — sudah ada, dipertahankan** · Berkas: `SEEKNAL_ASK.md` Gate 5 · `skills/bpom-forecaster/SKILL.md`

**Kondisi sekarang.** chart-enhance sudah punya di dua tempat, baseline tidak:

> *If the tool ran but the chart did not render on screen (the same holds for `run_forecast`), the
> words still stand: give the full answer, mention the chart could not be shown, and never re-run
> the tool to force it.*

`skills/bpom-forecaster/SKILL.md:127` punya padanannya untuk proyeksi.

**Perubahan.** Tidak ada perubahan isi. Pastikan aturan yang sama juga tercermin di
`skills/visualize-chart/SKILL.md` supaya tidak bergantung pada Gate 5 saja ketika skill dimuat
tanpa membaca ulang `SEEKNAL_ASK.md`.

**Ekspektasi.** Chart atau forecast yang gagal tampil tidak pernah membatalkan jawaban, dan tidak
memicu pemanggilan ulang tool yang membakar anggaran.

---

## 7. Yang Berada di Luar Cakupan Context

**Giliran tanpa SQL penghitung.** Dari jejak: 174 dari 537 run FAIL (**32,4%**) tidak menjalankan
satu pun query `COUNT`, sementara pada run PASS 100 dari 574 (17,4%). Hanya 16 dari 174 itu
giliran AUTO-clarif — jadi cakupannya **lebih luas** dari hipotesa H6 audit compact-IV yang hanya
menyalahkan auto-clarif.

⚠️ **Angka ini belum bisa dipakai sebagai dasar keputusan.** Filter yang dipakai menuntut kata
`COUNT(` sehingga skenario forecast, anomaly, offline, dan konseptual — yang memang sah tanpa SQL
hitung — ikut terhitung nol. Perlu dipotong per jenis skenario dulu.

Tidak ada isi context yang bisa memaksa sebuah turn menjalankan query. Ini ranah harness:
guard giliran 0-SQL, sesuai rekomendasi §8-A audit compact-IV.

---

## 8. Cara Verifikasi Setelah Perubahan

**8.1 Regresi terhadap 105 test yang ada.** Jalankan `scripts/test_variant_compare.py` mode
`variant-compare` untuk chart-enhance vs kedua baseline. Yang harus naik: keluarga yang tersentuh
F-6, F-7, F-9, F-10. Yang tidak boleh turun: seluruh keluarga yang sudah PASS di §4.

**8.2 Skenario baru yang harus ditambahkan.** Kelas segmen-bebas belum tercakup sama sekali:

| Usulan skenario | Menguji |
|---|---|
| `UAT-SEGMEN-KOPI-1` — "berapa NIE kopi instan asal Indonesia?" | F-11 dua-bagian + `nama_kategori` ERLA |
| `UAT-SEGMEN-SIRUP-1` — "sirup berperisa asal Malaysia" | F-11 nilai literal + negara |
| `UAT-SEGMEN-LEBAR-1` — "berapa produk kopi di BPOM?" | F-11 penutupan teks bebas (12+ nilai) |
| `UAT-KLASIFIKASI-INDUK-1` — "berapa produk makanan?" | F-6 bucket induk `3` |
| `UAT-KBLI-1` — pertanyaan bidang usaha | F-1 alamat kolom |
| `UAT-BTP-TANGGAL-1` — BTP dengan filter tahun | F-2 tipe kolom |

**8.3 Verifikasi fakta DB.** Seluruh angka di dokumen ini berasal dari skrip verifikasi yang
dapat dijalankan ulang. Sumber kebenaran tetap `rpo_v2` via tunnel, bukan dokumen.

**8.4 Yang tidak boleh dipakai sebagai sinyal.** Drift data — ERLA 0%, tahun tertutup 0%, ERBA
all-time +0,3–2,0% per 8–12 hari, seluruhnya jauh di bawah toleransi 5–10%. Perbedaan hasil antar
run bukan karena data bergerak.

---

## 9. Ringkasan Prioritas

| Prio | Temuan | Sifat perbaikan | SQL tambahan |
|---|---|---|:--:|
| **P0** | F-1 `kode_kbli` salah alamat | koreksi fakta | **−1** (hilangkan retry error) |
| **P0** | F-2 `t_btp_3_erba` bukan TEXT | koreksi fakta | **−1** |
| **P0** | F-3 format kode STATUS ERLA | 1 aturan format | 0 |
| **P0** | F-11 segmen bebas (`nama_kategori` ERLA, induk/anak, penutupan teks) | koreksi fakta + aturan | 0 |
| **P1** | F-6 daftar `klasifikasi_id` terpenggal | data | 0 |
| **P1** | F-7 tabel penutupan konsep majemuk | data | 0 |
| **P1** | F-8 prioritas rujukan vs dictionary | 1 kalimat | 0 |
| **P1** | F-9 + F-15 cek scope efektif di Gate 5 | 1 butir cek-baca | 0 |
| **P1** | F-10 cabang permohonan | data | 0 |
| **P1** | F-4 format kode wilayah | data | **−1** (hilangkan probe) |
| **P1** | F-5 `status` 4 spasi | data | 0 |
| **P2** | F-12 keluarga tanpa label | data | 0 |
| **P2** | F-13 kalibrasi bobot aturan | data | 0 |
| **P2** | F-14 cacat fakta lain-lain | koreksi fakta | 0 |
| **P2** | F-16 lampiran nomor mengikuti entity | 1 kalimat | 0 |
| **P2** | F-17 kesadaran render (sudah ada) | konsistensi antar berkas | 0 |
| — | turn 0-SQL | **harness, di luar context** | — |

**Enam belas dari tujuh belas butir adalah penambahan atau koreksi data pada berkas yang sudah
dibaca agent di gate yang sama.** Satu-satunya tambahan prosedural (F-9 + F-15) memeriksa SQL yang
sudah ada di context turn itu. Tiga butir justru **mengurangi** query per turn.

---

## 10. Catatan Metodologi & Batasan

- Seluruh angka database diverifikasi **2026-08-04** melalui koneksi read-only ke `rpo_v2`.
  Angka bergerak; yang tidak bergerak adalah sifat strukturalnya (tipe kolom, namespace kode,
  format dictionary, kolom yang ada/tidak ada).
- Analisis jejak memakai 4.997 SQL dari `_data.json` seluruh run `2026-07-*` dan `2026-08-*`,
  lintas 5 varian context. Beberapa varian di dalamnya bukan bagian dari perbandingan tiga-varian
  ini (`v5-predikat-trim`, `forecast anomaly`, `seeknal-project`) tetapi dipakai karena memperluas
  sampel perilaku.
- **Hipotesa yang belum terbukti dan ditandai demikian:** penyebab regresi segmen bebas (§F-11),
  dan proporsi sebenarnya dari turn 0-SQL (§7). Keduanya butuh data tambahan sebelum dijadikan
  dasar keputusan.
- **Hipotesa yang sudah dibantah dan dicabut:** dugaan bahwa deskripsi dictionary yang kembar
  menyebabkan agent mengambil satu kode. Jejak menunjukkan kepatuhan 90% pada bucket Draft.
  Dicatat di §5 sebagai risiko laten, bukan sebagai penyebab aktif.

---

## 11. Catatan Pelaksanaan (2026-08-04)

Ketujuh berkas `after-forecast-chart-enhance` sudah diubah. Ukuran akhir:

| Berkas | v1 | v2 | sesudah |
|---|--:|--:|--:|
| `SEEKNAL_ASK.md` | 120 | 123 | 158 |
| `context/predikat.md` | 297 | 281 | 335 |
| `context/filter_code_reference.md` | 247 | 204 | 340 |
| `context/data_architecture.md` | 67 | 67 | 78 |
| `skills/bpom-analyst/SKILL.md` | 73 | 68 | 75 |
| `skills/visualize-chart/SKILL.md` | — | 157 | 164 |

### 11.1 Satu koreksi arah terhadap F-10

Rencana §F-10 menetapkan default permohonan = **tanpa** filter status, dengan cabang
"approved-only" saat ada kata *disetujui/diterima*. Pemeriksaan ke SQL kanonik 10 berkas test
permohonan membalik arahnya: **8 dari 10 justru memakai filter status** (`UAT-JP-MAYOR-2025-1`,
`JP-MINOR-1`, `JP-MINOR-VS-MAYOR-1`, `JP-PERMOHONAN-BARU-NOTIF-1`, `JP-TREN-1`, `JP-BARU-1`,
`JP-BARU-VS-REVISI-1`, `AMDK-3`); hanya `UAT-TREN-ERBA-1` dan `UAT-ERLA-1` yang tidak.

Aturan yang ditulis karena itu **dibalik**: default = **dengan** set status sah; filter dilepas
hanya ketika pertanyaan meminta volume terlepas dari hasilnya ("berapa yang masuk/mengajukan",
"seluruh periode data", tren volume polos tanpa kata izin edar). Menerapkan arah rencana semula
akan menjatuhkan 8 kasus yang hari ini lulus.

### 11.2 Perubahan lain di luar daftar F

- **Binding garam ERBA diganti** dari `kategori_pangan='120101000001'` ke kode induk
  `jenis_pangan='1204'` (F-11). Terverifikasi identik dengan `LIKE '1204%'` pada data, dan
  sejalan dengan GT `UAT-GARAM-1`. Sisi ERLA mempertahankan `kategori_pangan='12010103'` dengan
  `nama_kategori ILIKE '%garam%'` sebagai fallback yang lebih lebar.
- **Baris `JENIS_PENOLAKAN_KOMITMEN` di §4b diperbaiki**: memuat `|` mentah sehingga tabel
  markdown-nya pecah dan sel terbaca salah. Cacat ini juga ada di kedua baseline. Sekarang
  di-escape `\|`.
- **Angka presisi tidak dimasukkan ke context.** Magnitudo kerugian dipakai sebagai urutan
  prioritas ("most of the population is lost", "roughly half"), bukan sebagai persen. Alasannya:
  angka di context akan basi seiring data bergerak, dan berisiko dikutip agent sebagai hasil
  hitungan padahal tidak dihitung turn itu — melanggar `predikat.md` §12-B dan Gate 5 butir 9.
  Satu peringatan eksplisit ditambahkan di §4 bahwa kata-kata severity itu kalibrasi internal,
  bukan angka jawaban. Seluruh angka terukur tetap tersimpan di dokumen ini (§6).

### 11.3 Verifikasi regresi yang dijalankan

21 binding kanonik yang dipakai GT diperiksa masih utuh sesudah edit: decoy organik, berklaim,
peruntukan `0201`, makloon, impor, bucket Draft / Data Tambahan / Ditolak Sistem, namespace
kemasan, AMDK kedua sistem, formula bayi, risiko Tinggi `301`+`304`, set status kedua sistem,
entity NIE, Case A/B, normalisasi `status_komitmen`, JP "baru", eksklusi akun uji, dan template
UNION. Semua **OK**. Seluruh tabel markdown di ketujuh berkas terverifikasi konsisten kolomnya.

Uji regresi penuh terhadap 105 skenario belum dijalankan — itu langkah berikutnya (§8.1).
