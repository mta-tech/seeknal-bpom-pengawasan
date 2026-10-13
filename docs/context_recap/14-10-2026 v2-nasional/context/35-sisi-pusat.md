pusat · verifikasi pusat · evaluasi pusat · tindak lanjut · klaim berlebihan · kosmetik · obat · otsk

# Sisi Pusat (verifikasi & tindak lanjut)

## Apa yang halaman ini putuskan

Kolom dan bridge **sisi Pusat** mana yang dipakai, untuk kategori apa, dan bagaimana memperlakukan
kekosongannya.

## Tabel keputusan — kata pertanyaan → kolom

| Istilah user | Sumber | Kategori yang mengisi |
|---|---|---|
| "verifikasi pusat" · "sesuai pusat" | `verifikasi_pusat_sesuai` (boolean) | kosmetik |
| "diunggah akun resmi" | `pengunggah_resmi` (boolean) | kosmetik |
| "kesesuaian data (kode)" | `verifikasi_data_sesuai_kode` (1/2 — arti kode belum dikonfirmasi) | kosmetik |
| "tindak lanjut" · "TL pusat" | `tindak_lanjut_pusat_id` → `dim_pengawasan_tindak_lanjut_pusat` | kosmetik |
| "evaluasi pusat" · "tanggal evaluasi" | `tgl_evaluasi_pusat` | otsk · obat_kuasi |
| "klaim berlebihan" | `klaim_berlebihan` (boolean) | obat |
| produk hasil review Pusat | `bridge_pengawasan_produk_pusat` (join `pengawasan_id`) | kosmetik |
| ketidaksesuaian versi Pusat | `bridge_pengawasan_ketidaksesuaian_pusat` (join `pengawasan_id`) | pangan |

## Matriks operasi

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `verifikasi_pusat_sesuai` | boolean — **hanya bermakna untuk kosmetik** | idem | — | — |
| `pengunggah_resmi` | boolean | idem | — | — |
| `verifikasi_data_sesuai_kode` | kode 1/2 — arti belum dikonfirmasi | idem | — | — |
| `tindak_lanjut_pusat_id` | butuh kamus | butuh kamus | `dim_pengawasan_tindak_lanjut_pusat.id` | bisa |
| `tgl_evaluasi_pusat` | rentang berbatas | boleh | — | — |
| `klaim_berlebihan` | boolean | idem | — | — |
| `bridge_pengawasan_produk_pusat.asal_produk` | teks (lokal/impor) | langsung | dari fakta | bisa |

## Cara mencari

```sql
-- keterisian kolom sisi pusat per kategori (jangan diasumsikan)
SELECT f.kategori,
       count(*) FILTER (WHERE f.verifikasi_pusat_sesuai IS NOT NULL) AS kosmetik_verif,
       count(*) FILTER (WHERE f.tgl_evaluasi_pusat IS NOT NULL)     AS otsk_kuasi_eval,
       count(*) FILTER (WHERE f.klaim_berlebihan)                   AS obat_klaim
FROM public.fact_pengawasan f
GROUP BY 1 ORDER BY 1;
```

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| "belum direview pusat" dihitung besar | menganggap semua NULL = belum direview | kosong **bukan** berarti belum diproses; sebutkan cakupan kolomnya |
| klaim berlebihan dijawab semua kategori | kolom hanya untuk obat | sebutkan cakupan |
| TL pusat kosong dianggap tidak ada TL | kolom/bridge Pusat hanya untuk kategori tertentu | cek kategori dulu (tabel di atas) |
| kode 1/2 diartikan | arti kode belum dikonfirmasi BPOM | tampilkan kode apa adanya |

## Batas

- Kolom sisi Pusat dan bridge Pusat **parsial** — hanya untuk kasus yang direview ulang Pusat; tidak
  ada baris ≠ "belum review".
- Arti `verifikasi_data_sesuai_kode` belum dikonfirmasi.
- Tindak lanjut TMK **Balai** (`tltmk`) tidak terekam di staging — TL yang tersedia hanya sisi
  Pusat (kosmetik).

## Rute

- Vonis (MK/TMK 3 tingkat) → **lihat** `30-vonis.md`
- Ketidaksesuaian → **lihat** `40-ketidaksesuaian.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `fact_pengawasan` | `verifikasi_pusat_sesuai`, `pengunggah_resmi`, `verifikasi_data_sesuai_kode`, `tindak_lanjut_pusat_id`, `tgl_evaluasi_pusat`, `klaim_berlebihan` | boolean / kode 1–2 |
| `bridge_pengawasan_produk_pusat` | `pengawasan_id`, `produk_id`, `asal_produk`, `kemasan`, `merk` | — |
| `bridge_pengawasan_ketidaksesuaian_pusat` | `pengawasan_id`, `id_klasifikasi` | — |
| `dim_pengawasan_tindak_lanjut_pusat` | `id`, `kode`, `keterangan` | `surat_tindak_lanjut`, `sp`, `penelusuran`, `lain_lain` |
