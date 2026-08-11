Kemasan — botol, kaleng, plastik, kaca, keramik, karton, kertas, komposit, ganda, aluminium, PET, HDPE

Dua level: `kemasan_id` (INDUK, 16 kode) → `sub_kemasan_id` (ANAK, 37 kode).

## Induk — `kemasan_id`, namespace berbeda per sistem

| Sistem | Kode |
|---|---|
| **ERBA** | `1` kaca · `2` plastik · `3` kertas · `4` komposit · `5` logam · `6` lainnya · `7` ganda |
| **ERLA** | `31` kaca · `32` plastik · `33` kertas/karton · `34` karton laminat · `35` kaleng · `36` aluminium foil · `37` komposit · `38` ganda · `39` lainnya |

**Nol irisan.** Jangan pernah memakai kode satu sistem pada sistem lain — hasilnya 0, dan 0 itu
berarti namespace salah, bukan kemasan itu tidak ada. Granularitasnya juga berbeda: ERLA memisahkan
kaleng dan aluminium foil, ERBA menggabungkannya di `5` logam.

## Kapan turun ke anak

**Material umum** (kaca, plastik, kertas, logam) → berhenti di `kemasan_id`.
**Material spesifik** (keramik, PET, HDPE, PVC, styrofoam, kaleng aluminium, nylon) → **wajib turun**
ke `sub_kemasan_id`.

Alasannya terbaca dari deskripsi kodenya sendiri: label induk ERBA `1` berbunyi "Kaca **ATAU**
Keramik" — satu kode memayungi dua material. Setiap kali deskripsi induk memuat "atau" / "dan
lain-lain" / menyebut lebih dari satu bahan, **induk tidak bisa menjawab pertanyaan yang menyebut
salah satunya**. Untuk melihat komposisinya sebelum memutuskan:

```sql
SELECT sub_kemasan_id, COUNT(DISTINCT nomor) FROM t_produk_3_erba
WHERE kemasan_id='<induk>' GROUP BY 1 ORDER BY 2 DESC;
```

Bila satu anak mendominasi induknya, menjawab di level induk berarti menjawab tentang anak yang
dominan — bukan tentang yang ditanya.

⚠️ **`sub_kemasan_id` hanya ada di `t_produk_3_erba` dan `t_btp_3_erba`.** Tidak ada di sisi ERLA.
Pertanyaan material spesifik karenanya **ERBA-only secara struktural** — katakan itu, jangan
menyajikannya sebagai angka nasional, dan **jangan mencari padanan yang tidak ada**: kode "Lain-Lain"
di ERLA adalah bucket residual, bukan material tertentu; mengklaimnya sebagai padanan mengubah
celah katalog menjadi klaim tentang bisnis.

## Induk dan anak tidak harus berjumlah sama

Sebagian baris punya `kemasan_id` tetapi `sub_kemasan_id` kosong atau bernilai lain. Bila menyajikan
kedua angka bersamaan, katakan itu; jangan dipaksa cocok.

## Sentinel

Kode yang **deskripsinya `-`, kosong, atau `0`** bukan material — ia penanda belum diisi, dan bisa
memuncaki peringkat. Kenali dari **deskripsinya**, bukan dari besar cacahnya. Kecualikan dari
peringkat; sebut terpisah sebagai catatan kualitas data.

## Rute

- Butuh daftar 37 kode anak → **TURUN** `41-sub-kemasan.md`
- Pertanyaan juga menyebut segmen produk → **SEBERANG** `10-segmen-produk.md`
- Pertanyaan tentang BTP → **SEBERANG** `70-btp.md` (kolom kemasannya sama, populasinya beda tabel)
- Entity: pertanyaan kemasan hampir selalu tentang NIE → `COUNT(DISTINCT nomor)`, `00-menghitung.md`
