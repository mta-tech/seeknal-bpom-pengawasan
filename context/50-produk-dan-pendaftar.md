produk · nama produk · NIE · pendaftar · produsen · perusahaan · importir

# Produk dan pendaftar

## Apa yang halaman ini putuskan

Daftar produk per kasus berasal dari mana, bagaimana membaca NIE/pendaftar, dan kolom mana yang
**tidak boleh** dipakai.

## Tabel keputusan

| Istilah user | Sumber |
|---|---|
| daftar produk dalam kasus | `bridge_pengawasan_produk` (join `pengawasan_id` = `id` fakta) |
| jumlah produk dalam kasus | `jumlah_produk` (fakta) — cacah yang tercatat; daftar lengkap dari bridge |
| nama produk | `bridge_pengawasan_produk.nama_produk` — **bukan** `f.produk_id` |
| NIE | `bridge_pengawasan_produk.nie` · kamus `dim_produk.nomor_registrasi` |
| pendaftar | `bridge_pengawasan_produk.pendaftar` · kamus `dim_produk.pendaftar` |
| produsen | `dim_produk.produsen` (via `produk_id`) |
| status NIE | `dim_produk.status_registrasi` — mayoritas NULL; sebutkan cakupan |
| asal produk lokal/impor | `bridge_pengawasan_produk_pusat.asal_produk` (khusus kosmetik yang direview Pusat) |

> **`f.produk_id` hanya "1 produk wakil" per kasus** — sering NULL dan tidak lengkap. Daftar lengkap
> selalu dari bridge. Jangan join `dim_produk` lewat `f.produk_id` dan bridge sekaligus (tertukar).

## Matriks operasi

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `jumlah_produk` (fakta) | biasa | langsung | — | bisa (produk per kasus) |
| `nama_produk` | `ILIKE` **sekali** (P3) lalu nilai persis | hati-hati ejaan/entity | — | bisa |
| `nie` | sentinel dibuang dulu | langsung | `dim_produk.nomor_registrasi` | bisa |
| `produk_id` (bridge) | butuh angka | langsung | `dim_produk.produk_id` | bisa |
| `pendaftar` | `ILIKE` sekali lalu nilai persis | **string tergandakan** — lihat Jebakan | `dim_produk.pendaftar` | bisa |
| `dim_produk.is_imported` | **jangan dipakai** (selalu false) | — | — | — |
| `dim_produk.status_registrasi` | butuh nilai persis | bisa — status NIE | — | bisa |

## Cara mencari

```sql
-- 1 produk yang paling sering diawasi (hitung KASUS, bukan baris bridge)
SELECT b.nama_produk, count(DISTINCT f.id) AS kasus
FROM public.bridge_pengawasan_produk b
JOIN public.fact_pengawasan f ON f.id = b.pengawasan_id
GROUP BY 1 ORDER BY 2 DESC LIMIT 10;
```

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| daftar produk tidak lengkap | membaca `f.produk_id` saja | baca bridge produk |
| hasil pencarian teks nol padahal ada | entity HTML (`&amp;`, `&#039;`) | cari potongan kata tanpa tanda baca |
| jumlah perusahaan membengkak | `pendaftar` memuat string tergandakan | normalisasi/`DISTINCT` — sebutkan bila ragu |
| "impor" selalu false | `dim_produk.is_imported` tidak reliabel | pakai `bridge_pengawasan_produk_pusat.asal_produk` |

## Batas

- `bridge_pengawasan_produk_pusat` hanya untuk kasus yang direview ulang Pusat — tidak ada baris ≠
  "belum review".
- Rokok sering tanpa `produk_id` → `dim_produk` tidak bisa di-join; nama tetap ada di bridge.

## Rute

- Vonis → **lihat** `30-vonis.md`
- Komoditi → **lihat** `10-komoditi.md`
- Kualitas teks → **lihat** `90-kualitas-data.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `fact_pengawasan` | `produk_id`, `jumlah_produk` | — |
| `bridge_pengawasan_produk` | `pengawasan_id`, `produk_id`, `nama_produk`, `nie`, `pendaftar` | — |
| `bridge_pengawasan_produk_pusat` | `pengawasan_id`, `produk_id`, `asal_produk` | — |
| `dim_produk` | `produk_id`, `nomor_registrasi`, `nama_produk`, `pendaftar`, `produsen`, `status_registrasi` | — |
