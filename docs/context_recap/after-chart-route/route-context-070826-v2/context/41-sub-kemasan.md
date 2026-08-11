Sub-kemasan — 37 kode material spesifik: PET, HDPE, PVC, keramik, styrofoam, kaleng, nylon, akrilik

Kolom `sub_kemasan_id`, **hanya di `t_produk_3_erba` dan `t_btp_3_erba`** — tidak ada di sisi ERLA.

## Peta kode (kode → label; cacahnya diambil dari query, bukan dari halaman ini)

| Keluarga | Kode |
|---|---|
| **Kaca/Keramik (1xx)** | `101` Kaca · `102` Keramik |
| **Plastik (2xx)** | `201` PET · `202` HDPE · `203` PVC · `204` LDPE/LLDPE/HDPE/PE · `205` PP/OPP/BOPP/CPP · `206` PS/EPS/Styrofoam · `207` PC · `208` Nylon/PA · `209` PLA · `210` Melamin · `211` PVDC · `212` EVOH · `213` PMMA/Akrilik · `214` Lain-lain |
| **Kertas (3xx)** | `301` Kertas · `302` Karton · `303` Kardus |
| **Komposit (4xx)** | `401` Plastik/Aluminium Foil · `402` Plastik/Aluminium Metalized · `403` Kertas/Plastik · `404` Plastik/Aluminium/Kertas (Karton Laminat) · `405` Kertas/Aluminium (Can Komposit) · `406` Plastik/Plastik (Multilayer/Laminat) · `407` Campuran ≥2 jenis lain |
| **Logam (5xx)** | `501` Kaleng Fe/Baja · `502` Kaleng Aluminium · `503` Aluminium Tunggal · `504` Logam Lainnya |
| **Alami (6xx)** | `601` Kayu · `602` Bambu · `603` Kain · `604` Karet · `605` Lilin/Wax · `606` Lainnya |
| **7xx** | `701` deskripsinya **`-`** — bukan material; lihat "sentinel" di bawah |

Daftar ini contekan, bukan semesta kode. Kode yang tidak ada di sini:
`SELECT kode, deskripsi FROM data_dictionary WHERE kategori='SUB_KEMASAN_ID'`.

## Aturan pakai

- **Kode `4xx` bertabrakan lintas kategori.** Nilai `401`–`407` juga hidup di kategori `STATUS`
  (sumber ERLA) dan di kolom `pengolahan`. Cocokkan kode selalu dengan **kategori DAN kolomnya**;
  kode telanjang tidak berarti apa-apa.
- **Sentinel.** Kode yang deskripsinya `-`, `''`, atau `0` bukan material — ia penanda belum diisi,
  dan sering **memuncaki peringkat**. Kenali dari deskripsinya, bukan dari besarnya. Kecualikan dari
  peringkat; sebut terpisah sebagai catatan kualitas data.
- **Kode berbaris nol tetap boleh di filter** — biayanya nol dan tahan bila nanti terisi — tetapi
  jangan disajikan sebagai anggota penyumbang. `GROUP BY` sekali memperlihatkan yang mana.
- **Konsep majemuk ambil seluruh anggotanya**: "plastik" spesifik = seluruh `2xx` · "kaleng" =
  `501`+`502` · "komposit/laminat" = `4xx`. Satu kode dari sebuah keluarga adalah kurang hitung.
- **Induk dan anak tidak harus berjumlah sama.** Sebagian baris punya `kemasan_id` tetapi
  `sub_kemasan_id` kosong atau bernilai lain. Bila menyajikan kedua angka, katakan itu; jangan
  dipaksa cocok.

## Rute

- **KEMBALI** ke `40-kemasan.md` bila pertanyaannya material umum atau butuh sisi ERLA.
- Sisi ERLA tidak punya kolom ini → pertanyaan material spesifik **ERBA-only secara struktural**;
  nyatakan batas itu, jangan mencari padanan yang tidak ada.
