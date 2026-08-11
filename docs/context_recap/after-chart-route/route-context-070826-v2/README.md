# Varian `route-context-070826-v2`

**Dibuat:** 7 Agustus 2026 · **Status:** lolos verifikasi statis + verifikasi aturan ke database,
**belum dijalankan** terhadap suite.
**Induk:** `route-context-070826` (arsitektur halaman berutas — tidak diubah, tidak ditimpa)
**Basis:** audit `seeknal_audit/docs/audit_context/2026-08-07-route-context-execution/`

Arsitekturnya tetap: halaman kecil, dipanggil sesuai kebutuhan, dirutekan dari `SEEKNAL_ASK.md`.
**Yang berubah hanya isi halaman.** Rasional desain di
`docs/planning/2026-08-07-routed-context-pages-architecture.md`.

---

## 1. Baseline yang sebenarnya

Diukur ulang dari `seeknal/tests/outputs`, **33 skenario yang beririsan persis** (compact-I + II,
qwen-plus):

| Varian | PASS | SQL | tool | LLM | menit |
|---|---|--:|--:|--:|--:|
| `after-forecast-chart-enhance-diffuse` — **baseline 80 %** | **27/33 (82 %)** | 190 | 497 | 343 | 41 |
| `after-forecast-chart-enhance` | 22/33 (67 %) | 129 | 368 | 263 | 48 |
| **`route-context-070826` (v1)** | **21/33 (64 %)** | 204 | 431 | 263 | 32 |

Pada 116 skenario penuh, v1 route = 77/116 (66 %).

**Koreksi atas laporan saya sebelumnya:** saya menyatakan SQL route "204 vs 206 — identik".
Angka pembandingnya salah; yang benar **190**, jadi v1 route memakai **7 % lebih banyak SQL**,
bukan sama. Route memang lebih murah pada tool (−13 %), LLM (−23 %), dan waktu (−22 %) —
tetapi tidak pada SQL.

---

## 2. Sebab kegagalan pada batch pembanding

Dari 12 kegagalan v1 di batch itu, **8 menyentuh kolom risiko** dan 3 memakai filter wilayah yang
tidak diminta. Dua di antaranya (`MT-JP-MEI26-1`, `OFF-2`) **juga gagal di baseline 82 %** — itu
kasus sulit, bukan regresi route.

| Sebab | Kasus |
|---|--:|
| Kolom risiko lintas sistem | 8 |
| Filter wilayah tak diminta | 3 |
| Entity/tanggal, bucket, peran ganda | 3 |

Pada 116 skenario penuh urutannya terbalik (wilayah 13 · risiko 12) — kedua akar tetap yang terbesar.

---

## 3. Dua akar, dan mekanismenya

### Akar A · `daerah_pabrik IS NOT NULL` adalah filter "produk lokal saja" yang menyamar

v1 menaruh penjaga wilayah di tabel berjudul *"Eksklusi — wajib di setiap query pencacahan"*.
Agent membaca judul sebagai perintah dan menerapkannya ke pertanyaan organik, kemasan, peruntukan.

Diverifikasi ke `rpo_v2`: **`daerah_pabrik` kosong tepat ketika pabriknya di luar negeri** — 100 %
kosong pada produk impor, 0 % pada produk lokal, di kedua sistem. Menyaring "yang terisi" membuang
seluruh produk impor tanpa error. Ketiga kolom wilayah bahkan tidak seragam.

v2 menulis ujinya, bukan tambalan satu kolom:

> Apakah baris yang dibuang klausa ini bisa menjadi jawaban yang benar?
> Bisa → **penyempitan**, hanya boleh ada bila pertanyaan memintanya.

Daftar eksklusi wajib kini **tiga baris dan tertutup**.

### Akar B · Risiko hidup di kolom berbeda per sistem

v1 menulis *"Keduanya ERBA-only secara struktural — kolomnya tidak ada di `t_produk_3_rilis_erla`"*.
Benar untuk komitmen, **salah untuk risiko**: `kategori_dokumen` ada di keempat tabel dan terisi di
ERLA. Tanpa aturan untuk keadaan sebenarnya, agent meng-UNION dua skema.

| | Kolom | `sumber` dictionary | Skema |
|---|---|---|---|
| ERBA | `kategori_dokumen` | ERBA saja | 4 kelas BPOM |
| ERLA | `jenis_dokumen` | ERLA dan ERBA | 3 kelas |

Padanannya **bertukar** (kelas terendah ERBA → `301` ERLA, kelas tertinggi → `302`), dan bisa
diturunkan sendiri karena kedua kolom hidup berdampingan di `t_produk_3_erba`.

---

## 4. Tiga koreksi terhadap v2 saya sendiri

Diuji ulang ke GT dan database sebelum dikunci. Ketiganya salah, dan sudah diperbaiki:

| Saya sempat menulis | Bukti | Yang benar sekarang |
|---|---|---|
| Risiko tanpa sebut sistem → **wajib Gate 1 tanya** | **8 dari 8** skenario risiko GT-nya ERBA-only. Bertanya membakar satu turn dan tidak menambah ketepatan | **Default ERBA, nyatakan batasnya.** Jangan bertanya — sama seperti baseline 82 % |
| "baru" = `jenis_permohonan IN ('301','305')` | `JP-BARU-VS-REVISI-1` GT Baru=43.142 ≈ `301` saja (DB kini 45.628); `301`+`305` = 47.972. Dan `OFF-2` meleset −8,4 % dengan `301,305` | **"baru" = `301` saja**; `305` hanya bila pertanyaan menyebut notifikasi |
| `SEEKNAL_ASK` naratif + plafon keras "maks 6 SQL" | Orkestrator harus ringkas; plafon keras salah karena pemecahan ERBA/ERLA menggandakan cacah | Ditulis ulang **ringkas, gaya baseline, bahasa Inggris**; anggaran dihitung **langkah logis**, bukan plafon |

---

## 5. Verifikasi aturan v2 ke database

SQL yang **dihasilkan aturan v2** dijalankan ke `rpo_v2` lalu dibandingkan ke GT (toleransi 5 %):

| Skenario | Aturan v2 | GT | Selisih |
|---|--:|--:|---|
| `TREN-MT-1` | 3.082 · 4.195 · 3.854 | idem | **persis** ✓ |
| `TREN-RISK-1` | 9.689 · 10.963 · 15.644 | idem | **persis** ✓ |
| `RISIKO-TINGGI-NOTIF-TREN-1` | 519 · 1.891 | idem | **persis** ✓ |
| `OFF-4` | 5.667 | 5.667 | **persis** ✓ |
| `MR-1` (ERBA) | 43.046 | 42.263 | +1,9 % ✓ |
| `RISIKO-4-KATEGORI-1` | 84.587 · 12.261 · 43.046 · 3.823 | 83.403 · 12.090 · 42.001 · 3.689 | ≤ 3,6 % ✓ |
| `KOMITMEN-DISETUJUI-1` | 15.508 | 15.346 | +1,1 % ✓ |
| `PRODUSEN-1` (flag independen) | 1.326 | 1.312 | +1,1 % ✓ |

Pembanding: `PRODUSEN-1` dengan rantai `CASE` v1 → 1.238, meleset **−5,6 %**, tepat di luar toleransi.

**Delapan dari dua belas kegagalan batch pembanding kini menghasilkan angka GT.** Sisanya:
`TOTAL-1` (wilayah + spiral 16 SQL — tertutup akar A), `PIPELINE-VERIF-1` (bucket verifikasi),
dan dua yang **juga gagal di baseline 82 %**.

> Ini membuktikan **aturannya menghasilkan angka yang benar**. Ini belum membuktikan agent akan
> mematuhinya — v1 menunjukkan aturan bisa ada dan tetap dilanggar (`DICABUT-1` melanggar larangan
> yang terbaca). Proyeksi 29/33 = 88 % adalah batas atas dengan syarat kepatuhan.

---

## 6. Perubahan per berkas

| Berkas | v1 → v2 | Perubahan |
|---|--:|---|
| `SEEKNAL_ASK.md` | 145 → 150 | ditulis ulang sebagai orkestrator: bahasa Inggris, ringkas, tabel skill + peta halaman + gate. Tanpa plafon keras. Gate 1 mengembalikan pengecualian risiko/komitmen. Gate 5 butir 5: tiap `WHERE` harus bisa ditunjuk ke satu kata |
| `context/00-menghitung.md` | 134 → 157 | eksklusi wajib **tinggal tiga** · uji eksklusi-vs-penyempitan · kaidah kekosongan-berkorelasi-makna · entity+tanggal satu keputusan · empat cara sistem berbeda |
| `context/30-risiko-komitmen.md` | 66 → 101 | dua kolom, dua skema, tabel padanan, larangan UNION, **default ERBA dinyatakan** |
| `context/50-pihak-wilayah.md` | 96 → 132 | tiga kolom wilayah + arti kosongnya · penjaga wilayah **bersyarat** · flag peran non-eksklusif |
| `context/20-status-pipeline.md` | 66 → 106 | istilah pengguna → bucket · "verifikasi" ambigu · terminasi vs masa-berlaku vs versi · lingkup produk-vs-BTP |
| `context/15-permohonan.md` | 48 → 61 | satu skema kedua sistem · **"baru" = `301`** · `304`/`305` berdiri sendiri · entity+tanggal dipasangkan |
| `context/35-klasifikasi-sifat.md` | 83 → 99 | "kategori makanan/minuman" punya dua arti |
| `context/60-asal-produksi.md` | 80 → 91 | pembeda skema-sama vs skema-beda lewat kolom penyilang |
| `context/70-btp.md` · `90-kualitas-data.md` | 51→56 · 63→68 | entity kanonik · kapan menyaring kekosongan justru benar |
| `skills/bpom-analyst/SKILL.md` | 69 → 76 | bahasa Inggris, gaya baseline · ledger **langkah logis** · aturan anti-ulang · cek `WHERE`-ke-kata |
| `skills/visualize-chart/SKILL.md` | 181 → 122 | diringkas — bagian rencana v1 yang tertinggal. Semua aturan dipertahankan |
| `seeknal_agent.yml` | — | `prompt.custom` tak lagi menyuruh membaca `predikat.md` + `filter_code_reference.md` yang **tidak ada di varian ini** |

Sisanya disalin apa adanya. **Tanpa symlink.**

---

## 7. Biaya

Jalur panas — dimuat pada setiap pertanyaan data:

| Varian | Baris |
|---|--:|
| `after-forecast-chart-enhance-diffuse` (baseline 82 %) | **1.308** |
| `route-context-070826` (v1) | 529 |
| **`route-context-070826-v2`** | **505** |

v2 **lebih murah dari v1** meski aturannya bertambah — peringkasan `visualize-chart` dan
`SEEKNAL_ASK` membayarnya. Terhadap baseline, jalur panas **62 % lebih kecil**.

---

## 8. Disiplin isi

Halaman mengajarkan **cara menemukan data**, tidak pernah **jawabannya**.

| WAJIB ada | DILARANG masuk |
|---|---|
| kolom mana untuk konsep apa | cacah baris / populasi |
| kode filternya apa | persentase hasil |
| filter wajib pendamping | perbandingan besaran |
| tabel mana yang boleh & dilarang, beserta sebabnya | angka jawaban dalam bentuk apa pun |
| kolom mana yang mudah tertukar, dan cara membedakannya | |

Semua perbaikan diturunkan dari query ke `rpo_v2`, tetapi **angka hasilnya tidak ikut masuk**.
Dipindai otomatis: nol cacah, nol persentase, nol perbandingan besaran.

---

## 9. Verifikasi statis

| Gerbang | Hasil |
|---|---|
| Tautan mati · halaman yatim · symlink · direktori kosong | **0 · 0 · 0 · 0** |
| Keterjangkauan atas 116 prompt UAT compact I–VIII | **115/116 = 99 %** |
| Halaman topik menyala per pertanyaan | rata-rata **1,6** · maks 3 |
| Angka hasil bocor ke context/skill | **0** |
| Klaim "hanya ada di / tidak ada di" vs `information_schema` | semua **benar** |

Satu prompt yang tak menyalakan halaman topik (`TOTAL-1`) memang tidak membutuhkannya — dijawab
`00-menghitung.md` yang selalu dimuat.

---

## 10. Pilot

```bash
cd seeknal-bpom-neo
uv run python scripts/test_variant_compare.py \
  --variants-path docs/context_recap/after-chart-route \
  --variants route-context-070826-v2 \
  --test-path seeknal/tests/v1/singleturn/UAT-v2-compact \
  --test-path seeknal/tests/v1/singleturn/UAT-v2-compact-II \
  --workers 1 --timeout 400
```

| Metrik | v1 | baseline | Gerbang v2 |
|---|--:|--:|---|
| **PASS** | 21/33 (64 %) | 27/33 (82 %) | **≥ 28/33 (85 %)** |
| Skenario risiko | 0/8 | — | **≥ 7/8** |
| Skenario terdampak wilayah | 0/3 | — | **3/3** |
| SQL | 204 | 190 | **≤ 190** |
| tool · LLM | 431 · 263 | 497 · 343 | **tidak naik** |
| `bpom-analyst` termuat | 0× | — | **> 0×** |

Gagal melewati gerbang PASS → penyebabnya bukan isi halaman melainkan arsitektur paging-nya.

> **Prasyarat 1 — symlink.** Varian ini berisi berkas saja. Harness memerlukan `.env`, `.seeknal/`,
> dan `seeknal/skills/` → `../skills`. Tanpa itu `load_skill` gagal senyap.
>
> **Prasyarat 2 — jangan percaya kolom PASS/FAIL.** `_token_in_answer` memindai seluruh teks
> jawaban; kode status dan fragmen tanggal bisa meluluskan jawaban salah. Bandingkan headline
> dengan `note`.
>
> **Prasyarat 3 — assert kosakata masih cacat.** Lima kegagalan v1 murni soal pilihan kata,
> **empat di antaranya angkanya benar**. Ini cacat harness, bukan urusan context — perbaiki di
> `test_variant_compare.py` atau keluarkan dari hitungan regresi.

---

## 11. Sengaja tidak dikerjakan

`bpom-forecaster` · `detect-anomaly` · engine Seeknal — nol perubahan.
`upload_to_s3: enabled: false` diwarisi dari v1 agar perbandingan setara.
Cacat assert kosakata di harness — di luar cakupan varian.
