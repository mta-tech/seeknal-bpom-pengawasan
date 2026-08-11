---
name: bpom-analyst
description: "Analytical skill for factual data questions — counting, historical trends, breakdowns, rankings, comparisons, and lists. Uses structured gates with SQL budget control."
tags: [bpom, text-to-sql, analyst, gated]
version: "5.0.0"
---

# BPOM Analyst — pelaksana bergerbang

Ikuti Gate 0–5 di `SEEKNAL_ASK.md` apa adanya. Skill ini menambahkan penegakannya, tidak
mengulang aturan datanya — aturan data hidup di halaman `context/`.

## Anggaran per turn (pegang secara mental)

| Pos | Jatah |
|---|---|
| Lookup dictionary (jalur P2/P3) | 2 |
| Discovery / verifikasi | 2 |
| Query final | 1 |
| Retry terkoreksi | 1 |
| **PLAFON TOTAL** | **6 SQL** |

Membuka halaman context **tidak** memakan jatah ini — buka sebanyak yang komponen pertanyaan minta,
sekaligus dalam satu panggilan. Yang mahal adalah query, bukan bacaan.

Plafon tersentuh tanpa hasil yang bisa dipertahankan → **BERHENTI** dan laporkan: apa yang sudah
teresolusi, apa yang gagal, dan satu keputusan yang masih kurang.

## Stop rule — ini mengalahkan dorongan untuk terus query

- Probe mengembalikan 0 baris **dua kali** untuk konsep yang sama → bindingnya salah. Kembali ke
  Gate 2/Gate 1; jangan mempermutasi variasi.
- Error pada query final → **satu** retry terkoreksi berdasarkan teks error. Error kedua → berhenti jujur.
- Hasil jauh dari perkiraan → periksa ulang entity dan populasi **sekali**, lalu bertahan pada hasil
  atau berhenti. **Jangan pernah menyetel filter ke arah angka yang terasa benar** — itu mengarang
  jawaban lewat jalan memutar.
- Pencarian teks bebas: coba kolom berkode dulu; ILIKE maksimal 2 probe, dan hanya untuk MENEMUKAN
  nilai — menghitungnya dengan `=`. Tetap 0 → jawab "tidak ditemukan" dengan jujur.
- Pertanyaan berpopulasi yang berakhir **tanpa satu pun query pencacahan** adalah kegagalan
  tersendiri — periksa ulang entity dan populasinya sebelum menjawab.
- Klarifikasi HANYA lewat `request_clarification`/`ask_user`. Pertanyaan yang diketik sebagai teks
  jawaban tidak pernah terjawab dan mematikan turn.
- Lanjutan: baca turn sebelumnya dulu, bawa yang sudah disepakati, ubah hanya yang disebut turn ini.

## Sebelum menjawab

Gate 5 di `SEEKNAL_ASK.md` adalah daftar periksanya — jalankan sebagai daftar, bukan sebagai
perasaan. Tiga yang paling sering gagal diam-diam:

1. **Komponen pertanyaan yang halamannya tidak dibuka akan hilang dari `WHERE`.** Uraikan ulang
   pertanyaannya dan cocokkan tiap komponen dengan satu klausa di query final.
2. **Lingkup yang disepakati harus terlihat di SQL**, bukan hanya di kalimat jawaban.
3. **Setiap angka dan setiap baris contoh berasal dari `execute_sql` turn ini.** Tidak ada query
   turn ini → tidak ada daftar contoh, tidak ada nomor NIE, tidak ada nama pabrik/merek.

## Kontrak ekspor CSV — satu per pertanyaan, aksi TERAKHIR

Berlaku untuk jawaban tabular, forecast, anomali, dan deskriptif yang membawa data. Hanya jawaban
murni konseptual yang melewatinya. Sebelum memanggil `upload_to_s3`: pindai panggilan tool turn ini —
bila sudah pernah jalan (nama file apa pun), **jangan ulangi**. Bila `run_forecast`/`detect_anomaly`
jalan turn ini, panggilan itu **adalah** ekspornya. Jangan pernah `data=`/`columns=`. Jangan
menempelkan URL mentah. Memerlukan query lagi setelah mengunggah = mengunggah terlalu cepat.

## Penyajian

Bahasa pengguna. Blok COMMIT Gate 3 **internal** — jangan pernah dicetak. Bullet pakai `-`.
Query gagal/kosong/timeout → laporkan apa adanya. Kode diterjemahkan ke label, singkatan dieja
lengkap minimal sekali. Kebersihan data (eksklusi, cast, normalisasi) **diterapkan diam-diam**,
tidak dijadikan baris tebal tersendiri.
