# Pipeline Status Code Mapping — Audit Log (KHUSUS MANUSIA)

> File ini **tidak pernah dirujuk** oleh context/skill mana pun dan tidak dibaca agent.
> Isinya metodologi + bukti verifikasi di balik `context/pipeline_stage_map.md` (draft, lihat file
> terpisah). Kalau angka live menyimpang jauh dari sini → verifikasi ulang sebelum revisi mapping.

Tanggal: 2026-07-15 · DB: `rpo_v2` via tunnel `localhost:5533` (`readonly_user`)

## Metodologi — TIDAK reverse-fit ke angka GT

Percobaan sebelumnya (lihat riwayat) membangun grup kode dengan cara mencoba kombinasi sampai
jumlahnya mendekati angka GT test suite — ini secara efektif menyembunyikan jawaban di dalam
pilihan kode, melanggar prinsip "jangan kasih ikannya". Metodologi di file ini terbalik:

1. Tarik **seluruh** baris kategori `STATUS` dari `data_dictionary` (98 baris, ERBA + ERLA).
2. Kelompokkan kode **murni dari pola teks `deskripsi`** (token peran: "Evaluator -",
   "Verifikator 1 -" / "Kepala Seksi -", "Verifikator 2 -" / "Kepala Sub Direktorat -",
   "Direktur -", "Pendaftar -", dst). Tidak melihat angka GT sama sekali di langkah ini.
3. **Cek silang ke data live** (`GROUP BY status` di tabel produk) — dictionary text tidak cukup;
   dictionary bisa median-basi (ada kode yang didefinisikan tapi datanya kosong, dan ada kode yang
   dipakai di data tapi tidak terdaftar di dictionary).
4. Angka hasil query dibandingkan ke GT **sebagai pemeriksaan akhir**, bukan sebagai metode
   penyusunan. Ketidakcocokan dicatat apa adanya (lihat `UAT_AUDIT_2026-07-15.md` — sudah
   melakukan ini lebih dulu dan independen; angka saya di bawah dipakai untuk **cross-check**,
   dan ternyata cocok persis dengan hasil UAT_AUDIT meski dijalankan di waktu yang berbeda).

## Temuan 1 — ERLA benar-benar tidak punya data pipeline (terverifikasi, bukan asumsi)

```sql
SELECT status, COUNT(*) FROM t_produk_3_rilis_erla GROUP BY status ORDER BY status;
```
Hasil: **hanya 7 nilai status yang pernah muncul** di `t_produk_3_rilis_erla`:
`0000(14), 0009(2064), 0099(2849), 0501(1 — noise), 0906(18353), 0999(183861), 9999(205497)`.

Semua kode pipeline ERLA yang terdaftar di dictionary (300-399 evaluator, 401-417 kepala seksi,
500-504 kepala subdit, 600-800 direktur/deputi/kepala badan, 900-952 pendaftar-kecuali-final)
menghasilkan **nol baris** di tabel aktual. Satu baris nyasar di `0501` (1 baris) diabaikan sebagai
noise/data-entry error, bukan populasi nyata.

**KOREKSI (setelah dicek lebih lanjut ke `t_btp_3_erla`):** klaim "ERLA nol data pipeline" di atas
HANYA berlaku untuk tabel produk (`t_produk_3_rilis_erla`), BUKAN seluruh sistem ERLA. Tabel BTP
sisi ERLA (`t_btp_3_erla`) justru masih aktif secara pipeline: Draft=297, Bayar=144,
DitolakSystem=727, dst (lihat Temuan 7). Kesimpulan yang benar: **produk registrasi ERLA sudah
beku, tapi BTP ERLA belum** — kemungkinan karena alur approval BTP terpisah dari alur produk dan
migrasinya belum/tidak menyertakan BTP. Ini fakta struktural yang tetap aman ditulis ke context,
tapi granularitasnya per-tabel, bukan per-sistem.

Catatan format: kode ERBA di tabel disimpan 4-digit zero-padded (`'0999'`), kode ERLA di
`data_dictionary` tidak (`'999'`) — konsisten dengan bug zero-padding ERLA yang sudah didokumentasi
di `code_resolution.md`. Tabel ERLA sendiri (`t_produk_3_rilis_erla.status`) TERNYATA memakai
4-digit zero-padded juga (`'0999'`, `'0906'`) — jadi mismatch-nya ada di **dictionary vs tabel**,
bukan di antar-tabel.

## Temuan 2 — Dictionary ERBA untuk Verifikator 2 sudah tidak sinkron dengan kode yang benar-benar dipakai

```sql
SELECT status, COUNT(*) FROM t_produk_3_erba GROUP BY status ORDER BY status;
```
Dictionary ERBA mendefinisikan Verifikator 2 sebagai `0501, 0502, 0503`. Data live:

| kode | di dictionary? | baris di data |
|---|---|---|
| 0500 | **tidak** | 149 |
| 0501 | ya | **0** |
| 0502 | ya | 70 |
| 0503 | ya | **0** |
| 0504 | **tidak** | 18 |

Kode yang benar-benar dipakai sistem sekarang adalah `0500, 0502, 0504` (total 237), bukan
`0501, 0502, 0503` (total 70) seperti tertulis di dictionary. Dictionary-nya sendiri basi untuk
kategori ini. Ini kemungkinan penyebab ketidakstabilan pilihan kode agent di `UAT-PIPE-VERIF2-1`
(agent menemukan 76 atau 243 tergantung mana yang di-probe — sekarang jelas: yang benar adalah
`0500,0502,0504`, bukan gabungan keduanya, bukan pula hanya kode yang "resmi" di dictionary).

Kode lain yang terdaftar di dictionary tapi **nol baris di data ERBA saat ini**: `0402, 0406, 0501,
0503, 0601, 0666, 0700, 0905`. Ini bukan berarti kode tersebut salah — beban antrian per tahap
memang berubah dari waktu ke waktu (lihat Temuan 4).

## Temuan 3 — "Data Tambahan" memang cross-cutting dua peran (terverifikasi, bukan tebakan)

Deskripsi `%Data Tambahan%` muncul di dua kelompok kode yang berbeda peran:
- Evaluator/Verifikator 1 (kode diminta tambahan data oleh pemeriksa): `0308, 0402, 0407`
- Pendaftar (giliran pendaftar melengkapi): `0901, 0914, 0915, 0917, 0951`

```sql
SELECT COUNT(*) FROM t_produk_3_erba WHERE status IN ('0308','0402','0407','0901','0914','0915','0917','0951');
-- 7136
```
Cocok dengan hasil independen `UAT_AUDIT_2026-07-15.md` (7.136, exact). GT fixture-nya sendiri
(7.371) memang sudah basi (data terus bertambah) — bukan salah kode.

## Temuan 4 — metrik "sedang di tahap X" adalah ukuran antrian sesaat, bukan kumulatif

Beda dengan metrik terminal (total terbit, total dicabut) yang hanya naik seiring waktu, jumlah
"sedang menunggu di tahap X" bisa naik ATAU turun tergantung throughput — item masuk lewat draft,
keluar lewat terbit/tolak. Ini terlihat di perbandingan independen (`UAT_AUDIT_2026-07-15.md`):
Evaluator dan Verifikator1 hasil live LEBIH RENDAH dari GT (backlog berkurang / diproses lebih
cepat dari saat fixture ditulis), sementara Draft/DitolakSystem/Direktur LEBIH TINGGI (backlog
menumpuk). Arahnya tidak konsisten satu arah — konfirmasi bahwa GT snapshot lama untuk kelas
pertanyaan ini **secara struktural tidak bisa dijadikan patokan toleransi ketat**, terlepas dari
seberapa benar kode yang dipakai. Rekomendasi: regenerasi GT untuk 9 skenario pipeline/ops secara
berkala (sama seperti rekomendasi existing untuk ERBA scope-agnostic total).

## Temuan 5 — dua "decoy" kolom/kode yang terbukti berbahaya kalau dipakai (data, bukan dugaan)

### `klaim` vs `klasifikasi_id='305'` (Pangan Berklaim)
```sql
SELECT klaim, (klasifikasi_id='305') AS is_305, COUNT(*) FROM t_produk_3_erba GROUP BY 1,2;
```
| klaim | is klasifikasi_id=305 | jumlah |
|---|---|---|
| '1' | false | 18.486 |
| '1' | true | 2.151 |
| '0'/blank | true | 133 |

`klaim='1'` (20.637 baris) dan `klasifikasi_id='305'` (2.284 baris) adalah **populasi yang jauh
berbeda** — overlap cuma 2.151/20.637 = 10%. `klaim` bertipe multi-value (`klaim_label` berisi
daftar kode dipisah `|`, mis. `'0001|0002|0009'`) — itu flag "produk punya klaim gizi/kesehatan
APAPUN", bukan kategori registrasi resmi "Pangan Berklaim". Dictionary sendiri mengonfirmasi
`klasifikasi_id='305'` berlabel persis **"Pangan Berklaim"** (kategori `KLASIFIKASI_ID`,
`sumber='ERBA dan ERLA'`). `klaim` adalah jebakan leksikal murni.

### `klasifikasi_id='309'` vs `pemrosesan='301'` (Organik)
Dictionary `KLASIFIKASI_ID` kode `309` JUGA berlabel "Organik" — kandidat yang tampak sah.
```sql
SELECT (pemrosesan='301') AS is_pemrosesan_301, (klasifikasi_id='309') AS is_klasid_309, COUNT(*)
FROM t_produk_3_erba GROUP BY 1,2;
```
`klasifikasi_id='309'`: cuma 38 baris total di seluruh ERBA (nyaris tidak dipakai secara
operasional). `pemrosesan='301'`: 612 baris — inilah yang benar-benar dipakai sistem BPOM untuk
menandai proses organik. Overlap cuma 33 baris. Binding yang sudah ada (`pemrosesan='301'`) **sudah
benar** dan terbukti menghindari jebakan ini — dicatat di sini supaya tetap begitu ke depannya
(kalau ada yang mau "memperbaiki" jadi `klasifikasi_id='309'` karena namanya lebih cocok, itu salah).

## Temuan 6 — pengecualian akun test tidak seragam dampaknya per tahap

| tahap | raw | exclude test-acct (5,17,50,85) |
|---|---|---|
| Evaluator | 5.246 | 5.246 (0%) |
| Verifikator 1 | 1.503 | 1.503 (0%) |
| Verifikator 2 (kode live) | 237 | 237 (0%) |
| Direktur | 467 | 467 (0%) |
| Data Tambahan | 7.136 | 7.136 (0%) |
| Draft | 27.800 | 26.260 (**-5,5%**) |
| Bayar | 7.007 | 6.930 (-1,1%) |
| Ditolak System | 12.820 | 12.735 (-0,7%) |

Akun test terkonsentrasi di Draft/Bayar/DitolakSystem — pengecualian tetap wajib diterapkan
seragam (aturan `predikat.md` yang sudah ada), tapi jangan heran kalau efeknya nol di beberapa
tahap; itu bukan bukti filter salah.

## Temuan 7 — BTP bukan detail sepele: memasukkannya mengubah jawaban secara material

Pemeriksaan pertama (Temuan 1-6) cuma memakai `t_produk_3_erba` / `t_produk_3_rilis_erla`. Setelah
ditegur untuk mengecek lebih menyeluruh, saya jalankan grup yang sama ke `t_btp_3_erba` dan
`t_btp_3_erla`:

```sql
-- pola: SELECT COUNT(*) FROM t_btp_3_erba WHERE status = ANY(<kode grup>)
```

| tahap | produk ERBA saja | + BTP ERBA | + BTP ERLA | dampak relatif |
|---|---:|---:|---:|---:|
| Evaluator | 5.246 | +132 | +0 | +2,5% |
| Verifikator 1 | 1.503 | +1 | +0 | ~0% |
| Verifikator 2 | 237 | +1 | +1 | ~0% |
| Direktur | 467 | +8 | +0 | +1,7% |
| Draft | 27.800 | +693 | +297 | +3,6% |
| Bayar | 7.007 | +108 | +144 | +3,6% |
| Ditolak Sistem | 12.820 | +742 | +727 | **+11,4%** |

Untuk Draft/Bayar/Ditolak Sistem, mengikutsertakan BTP mengubah jawaban di luar toleransi 5% biasa
— terutama Ditolak Sistem (+11,4%). Ini menjelaskan salah satu ketidakstabilan lama: varian
`forecast-anomaly` (baseline, tidak pernah diubah) sempat menghasilkan **5.378** untuk pertanyaan
Evaluator — itu persis `5.246 (produk) + 132 (BTP ERBA)`. Bukan salah pilih kode status, tapi
BTP diam-diam ikut terhitung tanpa itu jadi keputusan sadar.

**Kesimpulan: "produk vs BTP" adalah dimensi scope yang sama pentingnya dengan "ERBA vs ERLA",
dan sampai saat ini tidak ada aturan eksplisit di `predikat.md` atau manapun yang mengatur kapan
BTP ikut dihitung untuk pertanyaan "permohonan"/"produk" pipeline.** Perlu keputusan bisnis
(bukan yang bisa saya tentukan sendiri dari DB) — apakah kata "produk"/"permohonan" di pertanyaan
pipeline dimaksudkan generik (termasuk BTP) atau spesifik pangan-olahan (t_produk saja).

## Temuan 8 — kode "dirty" bukan noise, itu permohonan asli dengan kode tak terdokumentasi

Klaim awal saya (kode `000X`, `0201`, `0900`, `0909`, `0916` di `t_produk_3_erba` = "noise") salah
tanpa saya cek isinya. Setelah di-sample:

```sql
SELECT status, jenis_permohonan, trader_id, tanggal_bayar, nomor FROM t_produk_3_erba
WHERE status IN ('000X','0201','0900','0909','0916') ORDER BY status LIMIT 20;
```

Semua baris punya nomor registrasi asli (`MD 2431...`, `ERBA3...`), trader_id asli, tanggal aju
nyata rentang 2023–2026 (termasuk Mei 2026, sangat baru) — ini permohonan sungguhan, bukan
data-entry junk. Volumenya kecil (23 dari ~253rb baris ERBA, <0,01%), tapi:
- `000X` (11 baris): kode non-numerik, tidak ada di dictionary ERBA maupun ERLA sama sekali.
- `0900, 0909, 0916` (1+3+4 baris): tidak ada di dictionary ERBA, tapi **ADA** di dictionary ERLA
  (0900=Pendaftar-Draft, 0909=Pendaftar-Proses Verifikasi Ditolak, 0916=sama) — indikasi kebocoran
  skema/kode gaya-ERLA ke tabel ERBA, kemungkinan sisa migrasi.
- `0201` (4 baris): tidak ada di dictionary STATUS manapun; kebetulan sama dengan kode PERUNTUKAN
  `'0201'` tapi muncul di kolom `status`, bukan `peruntukan` — kemungkinan silang-kolom saat input.

**Rekomendasi**: jangan diam-diam dibuang dari total (`status NOT IN (...)` yang tidak
menyebutkannya secara eksplisit akan otomatis memasukkannya ke bucket "in-progress" yang salah).
Tandai eksplisit sebagai "kode tak terdokumentasi — volume kecil, perlu klarifikasi ke pemilik
data" di context, bukan diasumsikan noise.

## Status akhir tiap kelompok — untuk ditulis ke `context/pipeline_stage_map.md`

Semua kode di bawah lolos langkah 1-3 metodologi (pola teks + cek silang data live), DIPERBARUI
dengan Temuan 7 (BTP) dan Temuan 8 (kode tak terdokumentasi). TIDAK ada angka jawaban di sini
secara sengaja — lihat file mapping terpisah untuk versi yang aman dibaca agent.
