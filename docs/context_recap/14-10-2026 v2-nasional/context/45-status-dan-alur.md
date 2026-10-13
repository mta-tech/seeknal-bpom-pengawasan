status · alur · draft · verifikasi · selesai · ditolak · pipeline · bottleneck

# Status dan alur

## Apa yang halaman ini putuskan

Bagaimana status dibaca, bagaimana riwayat tahapan (approval) dibaca, dan dua jalur untuk kata
"ditolak".

## Status — satu kolom, satu kamus, filter domain

Kode status ada di kolom `status_id` fakta → `dim_status_code.id`. Kolom kamus dipakai **dua
domain**; join **wajib** memakai filter domain:

```sql
JOIN dim_status_code s ON s.id = f.status_id AND s.domain = 'pengawasan'
```

`status_code` berupa **angka-dalam-teks** (`0`–`9` dan blok `990`–`999`).

## Alur tahapan — `fact_pengawasan_approval`

Satu baris per langkah proses: `trx_steps` (nama langkah), `status_code`, `urutan_step`,
`user_id`, `catatan`, `created_at`. Langkah penolakan berawalan **`ditolak_`** — penamaannya jelas,
berbeda dari langkah normal (`draft`, `spv_1`, `kepala_balai`, `pusat`, `direktur`, `selesai`).

⚠️ **Tabel ini memuat `pengawasan_id` yang tidak ada di fakta** (populasinya lebih besar). Bila
jawabannya berbicara tentang populasi pengawasan, **INNER JOIN dari `fact_pengawasan`**. Sifat id
tambahan itu belum dipastikan — perlakukan sebagai populasi berbeda, jangan menyimpulkan sebabnya.

## Tabel keputusan

| Istilah user | Cara mengikat |
|---|---|
| "draft" · "belum selesai" · "selesai" | kode `status_code` — **tanpa label** (lihat Batas); tahap akhir = `trx_steps='selesai'` di approval |
| "ditolak" · "tidak lolos" | **dua jalur** — vonis (keluarga TMK pada kolom yang ditanyakan, `30-vonis.md`) atau tahapan (`trx_steps LIKE 'ditolak_%'`); tanya bila ambigu |
| "bottleneck" · "menumpuk" | distribusi `status_id` saat ini, atau tahap yang paling lama menahan (durasi antar `created_at` approval) |
| "riwayat alur" · "pernah ditolak" | langkah di `fact_pengawasan_approval` |
| "siapa yang menyetujui" · "self-approval" | **NOT COVERED** (lihat Batas) |

## Matriks operasi

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `status_id` (fakta) | butuh `dim_status_code` + `domain` | butuh kamus + `domain` | `dim_status_code.id AND domain='pengawasan'` | bisa |
| `trx_steps` (approval) | `LIKE 'ditolak_%'` untuk penolakan | langsung | `pengawasan_id` → fakta | bisa |
| `urutan_step` (approval) | — | urutan tahap per kasus | — | bisa |

## Cara mencari

```sql
-- distribusi status saat ini (jangan hafal artinya)
SELECT s.status_code, count(*)
FROM public.fact_pengawasan f
JOIN public.dim_status_code s ON s.id = f.status_id AND s.domain = 'pengawasan'
GROUP BY 1 ORDER BY 2 DESC;

-- tahapan penolakan per kasus (INNER JOIN dari fakta)
SELECT a.trx_steps, count(DISTINCT a.pengawasan_id)
FROM public.fact_pengawasan_approval a
JOIN public.fact_pengawasan f ON f.id = a.pengawasan_id
WHERE a.trx_steps LIKE 'ditolak_%'
GROUP BY 1 ORDER BY 2 DESC;
```

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| join menggandakan | `dim_status_code` dipakai tanpa filter `domain` | tambahkan `AND s.domain='pengawasan'` |
| arti kode dikarang | `status_label` kosong → mencoba menebak | jawab kode apa adanya |
| "ditolak" dijawab dari status saja | status bukan bukti penolakan | ikat ke dua jalur: vonis atau `ditolak_*` |
| angka approval melebihi populasi kasus | menghitung approval tanpa join fakta | INNER JOIN dari `fact_pengawasan` |

## Batas

- **`status_label` kosong untuk semua kode** dan arti kode belum dikonfirmasi — sebutkan ini saat
  menyajikan kode.
- `user_id` di approval terisi penuh, tetapi maknanya tidak dapat dipastikan dari database ini
  sendirian — pelaku tahap itu, atau pengirim ke tahap itu. Pertanyaan *"siapa yang menyetujui"*,
  *"pemisahan tugas"*, *"self-approval"* → **NOT COVERED** (kesimpulannya bersifat tuduhan).
- Yang **boleh** dijawab dari alur: kapan berkas berpindah tahap, berapa lama tersangkut, tahap
  mana yang paling menahan — tentang **waktu dan volume**, bukan tentang **siapa**.

## Rute

- Waktu & durasi → **lihat** `60-waktu-dan-durasi.md`
- Vonis → **lihat** `30-vonis.md`
- Petugas/penginput → **lihat** `70-atribusi-kasus.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `fact_pengawasan` | `status_id` | — |
| `dim_status_code` | `id`, `status_code`, `status_label`, `domain` | `domain='pengawasan'` |
| `fact_pengawasan_approval` | `pengawasan_id`, `trx_steps`, `status_code`, `urutan_step`, `user_id`, `catatan`, `created_at` | penolakan: `trx_steps LIKE 'ditolak_%'` |
