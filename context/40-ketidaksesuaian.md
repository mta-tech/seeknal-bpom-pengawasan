klausul · pelanggaran · ketidaksesuaian · klaim kesehatan · superlatif · menyesatkan · pangan · kosmetik

# Ketidaksesuaian / klausul pelanggaran

## Apa yang halaman ini putuskan

Tabel mana yang memuat klasifikasi pelanggaran, dan bagaimana join-nya — berbeda per kategori.

## Sumber per kategori

| Kategori | Sumber klasifikasi | Kunci join |
|---|---|---|
| `pangan` | `bridge_pengawasan_ketidaksesuaian` (Balai) · `bridge_pengawasan_ketidaksesuaian_pusat` (Pusat, jarang) | `pengawasan_id` = `id` fakta |
| `kosmetik` | `uraian_pelanggaran_id` → `dim_pengawasan_uraian_pelanggaran_kosmetik` | `.id` |
| `otsk` / `obat_kuasi` | `klasifikasiklaim_id` + `ketidaksesuaianhasil_kode` → `dim_pengawasan_klasifikasi_klaim` + `dim_pengawasan_ketidaksesuaian_hasil` | klaim: **dua kolom** `kode` + `komoditi_id` |
| `rokok` / `obat` | belum ada klasifikasi terstruktur | — |

## Matriks operasi

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `uraian_pelanggaran_id` | butuh kamus | butuh kamus | `dim_pengawasan_uraian_pelanggaran_kosmetik.id` | bisa |
| `klasifikasiklaim_id` | butuh kamus (dengan `komoditi_id`) | butuh kamus | `dim_pengawasan_klasifikasi_klaim ON kode=... AND komoditi_id=...` | bisa |
| `ketidaksesuaianhasil_kode` | butuh kamus | idem | `dim_pengawasan_ketidaksesuaian_hasil.kode` | bisa |
| bridge `ketidaksesuaian.id_klasifikasi` | butuh kamus | idem | `dim_pengawasan_klasifikasi_ketidaksesuaian_iklan.id_klasifikasi` | bisa |

## Cara mencari

```sql
-- klaim: join WAJIB memakai dua kolom (kode + komoditi_id)
SELECT f.klasifikasiklaim_id, f.komoditi_id, k.keterangan, count(*)
FROM public.fact_pengawasan f
JOIN public.dim_pengawasan_klasifikasi_klaim k
  ON k.kode = f.klasifikasiklaim_id AND k.komoditi_id = f.komoditi_id
GROUP BY 1,2,3 ORDER BY 4 DESC;
```

## Grain — jangan salah hitung

- Satu event bisa punya **beberapa** baris ketidaksesuaian (bridge).
- Cacah **baris** ≠ cacah **event yang punya** ketidaksesuaian → event: `COUNT(DISTINCT f.id)`.
- Hanya sebagian event punya baris di bridge ini → `LEFT JOIN` **dari fakta** (jangan mulai dari bridge).
- Setiap bridge berisi data nasional → wajib join ke fakta (`00`).

## Narasi kasus — `fact_pengawasan_narasi`

Satu tabel narasi mentah: `pengawasan_id`, `kategori`, `jenis_narasi`, `teks` — ikat lewat
`pengawasan_id` = `fact_pengawasan.id`.

- Narasi tidak terisi untuk semua kasus — **cek keterisian per `kategori` dulu** sebelum
  menjanjikan ringkasan; bila tipis untuk suatu kategori, sebutkan.
- "Ringkas klaim pada kasus X" = baca `teks` kasus tersebut — bukan agregat.
- `jenis_narasi` membedakan jenis teks — lihat nilainya lewat `SELECT DISTINCT`, jangan hafal.

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| angka baris ≠ jumlah kasus | membaca bridge tanpa join fakta | `INNER JOIN` ke fakta |
| klaim dobel / ketuker | join klaim hanya dengan `kode` | tambahkan `komoditi_id` |
| "klausul pelanggaran obat" dijawab | kategori itu tidak merekam klausul | jawab batasnya (`95-batas-domain.md`) |
| vonis dikira klausul | kolom vonis dipakai sebagai klausul | vonis ≠ klausul — `30-vonis.md` |

## Batas

- `bridge_pengawasan_ketidaksesuaian_pusat` hanya untuk kasus yang direview ulang Pusat — tidak ada
  baris ≠ "belum review".
- Klasifikasi terstruktur hanya ada untuk kategori yang tercantum di tabel sumber; kategori lain
  tidak merekam klausul.

## Rute

- Vonis → **lihat** `30-vonis.md`
- Komoditi → **lihat** `10-komoditi.md`
- Kualitas teks → **lihat** `90-kualitas-data.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `bridge_pengawasan_ketidaksesuaian` | `pengawasan_id`, `id_klasifikasi` | — |
| `fact_pengawasan_narasi` | `pengawasan_id`, `kategori`, `jenis_narasi`, `teks` | join `pengawasan_id` = `fact.id` |
| `bridge_pengawasan_ketidaksesuaian_pusat` | `pengawasan_id`, `id_klasifikasi` | — |
| `dim_pengawasan_klasifikasi_ketidaksesuaian_iklan` | `id_klasifikasi`, `keterangan` | — |
| `dim_pengawasan_klasifikasi_klaim` | `id`, `komoditi_id`, `kode`, `keterangan` | — |
| `dim_pengawasan_uraian_pelanggaran_kosmetik` | `id`, `kode`, `keterangan` | — |
| `dim_pengawasan_ketidaksesuaian_hasil` | `kode`, `keterangan` | — |
