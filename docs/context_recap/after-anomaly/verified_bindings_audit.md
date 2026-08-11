# Verified Bindings — Log Audit (KHUSUS MANUSIA)

> File ini **tidak pernah dirujuk** oleh context/skill mana pun dan tidak dibaca agent.
> Isinya bukti verifikasi tiap entri `context/verified_bindings.md` + kandidat yang GAGAL.
> Kalau angka live menyimpang jauh dari angka di sini → binding basi, verifikasi ulang.

## Entri SAH

### pangan bayi · ERLA · `klasifikasi_id = '311'`
- Tanggal: 2026-07-15 · DB: `rpo_v2` via tunnel `localhost:5533`
- SQL bukti:
  ```sql
  SELECT COUNT(DISTINCT nomor) FROM t_produk_3_rilis_erla
  WHERE klasifikasi_id::text = '311' AND nomor IS NOT NULL AND nomor <> '';
  -- hasil: 81  (GT UAT-CHAR-PANGAN-BAYI-ERLA-1 = 81 — persis)
  -- dengan status valid ERLA ('0099','0999','0906','9999'): tetap 81
  ```
- Konteks kegagalan yang ditutup: agent menjawab 401 karena memakai `jenis_pangan`.

## Batch 2 — 8 entri SAH (2026-07-15, tolerance 5%)

Pola verifikasi AWAL: `COUNT(DISTINCT produk_id) WHERE <binding> AND <status valid per sistem>`.
**Sisi ERLA lolos SEMUA** (sistem beku — angka stabil). Sisi ERBA tampak melenceng seragam ke
atas — awalnya divonis "staleness", tapi lihat KOREKSI di bawah.

| concept | binding | ERLA live | ERLA GT | ERBA live (pid) | ERBA GT |
|---|---|---:|---:|---:|---:|
| organik | `pemrosesan='301'` | 795 | 781 ✓ | 255 | 202 |
| pangan berklaim | `klasifikasi_id='305'` | 30.102 | 30.071 ✓ | 451 | 256 |
| pangan diet | `klasifikasi_id='310'` | 1.480 | 1.480 ✓ | 50 | 35 |
| peruntukan khusus | `peruntukan='0201'` | 3.526 | 3.525 ✓ | 598 | 429 |
| Single MD Induk | `status_produk='306'` | 24.087 | 23.949 ✓ | 9.716 | 5.658 |
| makloon | `status_produk='304'` | 13.839 | 13.801 ✓ | 3.459 | 2.133 |
| makanan | `klasifikasi_id='301'` | 268.883 | 266.742 ✓ | 89.968 | 89.888 ✓ |
| minuman | `klasifikasi_id='302'` | 91.756 | ~91.111 ✓ | 50.583 | 50.542 ✓ |

Binding SAH karena: (a) ERLA reproduksi dalam toleransi, dan (b) SQL di note GT sendiri memakai
kolom+kode yang sama — pilihan kolamnya terkonfirmasi dua arah.

## ✅ KOREKSI (2026-07-15, sesi lanjutan): "ERBA GT basi" adalah SALAH DIAGNOSIS

Selisih 26–76% di kolom "ERBA live (pid)" bukan karena data bergeser, tapi karena verifikasi awal
memakai entity `produk_id` sedangkan fixture GT dihitung dengan **`COUNT(DISTINCT nomor)`**.
Diverifikasi ulang dengan `COUNT(DISTINCT nomor) + status 3-valid + exclude test account
(trader_id NOT IN (5,17,50,85)) + nomor != ''`:

| concept | ERBA GT | nomor+3status live | selisih |
|---|---:|---:|---:|
| pangan berklaim | 256 | **256** | **EXACT** |
| pangan diet | 35 | **35** | **EXACT** |
| organik | 202 | 211 | +4,5% ✓ |
| peruntukan khusus | 429 | 435 | +1,4% ✓ |
| Single MD Induk | 5.658 | 5.830 | +3,0% ✓ |
| makloon | 2.133 | 2.208 | +3,5% ✓ |

Semua 6 konsep rekonsiliasi dalam toleransi 5%, dua di antaranya persis. Konsekuensi:
1. GT ERBA di test suite **masih valid** untuk konsep-konsep ini — yang salah adalah metode
   verifikasi kami sebelumnya, dan (kemungkinan besar) metode agent saat menjawab.
2. Entity hitung (`nomor` vs `produk_id`) adalah keputusan sekelas pemilihan kolom — salah pilih
   bisa menggeser jawaban hingga ~2x (Single MD: 9.716 vs 5.830). Aturan dituangkan di
   `context/filter_code_reference.md` §1 dan `predikat.md` (3 varian).
3. Rekomendasi lama ("regenerasi angka kanonik ERBA secara berkala") tetap berlaku untuk metrik
   antrian pipeline (queue-depth, memang bergerak dua arah), tapi TIDAK lagi jadi alasan utama
   kegagalan soal scope-agnostic klasifikasi.

## Kandidat "GAGAL" lama — DIREKLASIFIKASI (2026-07-15 sesi lanjutan)

Vonis GAGAL awal memakai standar exact-match; standar batch 2 adalah toleransi 5%. Dicek ulang
dengan entity `nomor` + 3-status + exclude test account:

### BTP antioksidan · ERBA · `jenis_btp = '48'` → DALAM TOLERANSI
- nomor+3status+no-test = **972**; GT = **942** → +3,2%, LOLOS standar 5%.
  (pid+3status = 1.128 — sekali lagi konfirmasi entity `nomor` yang benar.)
- Tidak perlu masuk `verified_bindings.md` — `jenis_btp` 1:1 di dictionary (Bucket A, tidak ada
  ambiguitas kolom). Cukup dicatat di `filter_code_reference.md` §4.

### kemasan komposit · ERBA · `kemasan_id = '4'` → DALAM TOLERANSI
- nomor+3status+no-test = **42.087**; GT audit Juni = **~40.683** → +3,5%, LOLOS standar 5%.
  (pid = 64.207 — selisih +58% kalau salah entity; ini contoh paling ekstrem betapa fatalnya
  pemilihan entity.)
- Sama: `kemasan_id` 1:1 di dictionary, tidak butuh entri binding.

## Prosedur verifikasi entri baru
1. Jalankan SQL binding dengan `COUNT(DISTINCT …)` sesuai entitas.
2. Cocokkan dengan angka GT soal terkait (kalau ada) atau validasi sampel manual.
3. Persis / dalam toleransi soal → tulis entri di `context/verified_bindings.md` (tanpa angka)
   + catat bukti di file ini. Tidak tereproduksi → catat di daftar GAGAL, jangan masuk bindings.
