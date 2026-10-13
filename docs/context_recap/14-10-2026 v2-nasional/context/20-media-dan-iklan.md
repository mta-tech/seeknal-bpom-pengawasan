media · iklan · elektronik · cetak · luar ruang · televisi · ecommerce · medsos · pembuat iklan · lokasi iklan

# Media dan iklan

## Apa yang halaman ini putuskan

Media iklan ada di **dua lapis**: satu kolom kasar di fakta, dan detail per kategori di tabel bridge.
Halaman ini memutuskan lapis mana yang dibaca, dan bagaimana routing-nya.

## Tabel keputusan — istilah user → sumber

| Istilah user | Sumber |
|---|---|
| "jenis media" (kasar) | `jenis_iklan_id` → `dim_pengawasan_jenis_iklan` |
| "e-commerce" · "media sosial" · "TV" · "cetak" · "luar ruang" · "website" · "pangan" · "kosmetik online/elektronik/cetak" | lihat **tabel routing** di bawah — bridge berbeda per `kategori` × `media_iklan_kode` |
| lokasi iklan ditemukan | `provinsi_iklan_id` / `kabupaten_iklan_id` |
| pembuat iklan | `bridge_pengawasan_media_pangan.pembuat_iklan` (khusus pangan) |
| "kelompok iklan" · indikasi · promosi (rokok/obat) | `kelompok_iklan_id` → `dim_pengawasan_kelompok_iklan` |

## Matriks operasi

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `jenis_iklan_id` | butuh `dim_pengawasan_jenis_iklan` | butuh kamus | `dim_pengawasan_jenis_iklan.id` | bisa |
| `kategori_media` | teks (visual/audio/…) — **banyak kosong** | langsung | — | sebutkan keterisiannya |
| `provinsi_iklan_id` / `kabupaten_iklan_id` | **ID kanonik** (`00` P11) | ID kanonik | `dim_provinsi` / `dim_kabupaten` | bisa |
| `media_iklan_kode` (bridge) | **setelah** cek `kategori` | langsung | bridge media per routing | bisa |
| `kelompok_iklan_id` | butuh kamus | butuh kamus | `dim_pengawasan_kelompok_iklan.id` | bisa |

## Cara mencari — routing media (cek `kategori` DULU, baru `media_iklan_kode`)

```sql
-- 1. kode media apa yang ada, per kategori (jangan hafal)
SELECT kategori, media_iklan_kode, count(*)
FROM public.bridge_pengawasan_media_detail d
JOIN public.fact_pengawasan f ON f.id = d.pengawasan_id
GROUP BY 1,2 ORDER BY 1,3 DESC;

-- 2. setelah tahu kode, baca tabel turunan yang tepat (bridge_*_media_*)
```

| `kategori` | `media_iklan_kode` | Bridge tujuan |
|---|---|---|
| `pangan` | semua nilai | `bridge_pengawasan_media_pangan` |
| `kosmetik` | `online` | `bridge_pengawasan_media_kosmetik_online` |
| `kosmetik` | `elektronik` | `bridge_pengawasan_media_kosmetik_elektronik` |
| `kosmetik` | `mediacetak` · `luarruang` | `bridge_pengawasan_media_kosmetik_cetak_luarruang` |
| `otsk` / `obat_kuasi` | `mediasosial` | `bridge_pengawasan_media_sosial` |
| `otsk` / `obat_kuasi` | `ecommerce` | `bridge_pengawasan_media_ecommerce` |
| `otsk` / `obat_kuasi` | `tvnasional` · `penyiaranlokal` | `bridge_pengawasan_media_tv_radio` |
| `otsk` / `obat_kuasi` | `cetak` · `luarruang` | `bridge_pengawasan_media_cetak_luarruang` |
| `otsk` / `obat_kuasi` | `website` · `internetlain` · `medialain` | `bridge_pengawasan_media_website_lain` |
| `rokok` / `obat` | tidak ada detail media terstruktur | — (mentah: `bridge_pengawasan_media_detail.detail_json`) |


Kode media yang sama bisa punya struktur berbeda antar kategori — **selalu cek `kategori` dulu**.

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| hasil kosong | media dibaca dari bridge kategori yang salah | cek `kategori` sebelum memilih bridge |
| lokasi iklan hilang | dikira sama dengan lokasi kantor balai | lokasi iklan = `provinsi_iklan_id`/`kabupaten_iklan_id`; lokasi balai = `dim_balai` |
| nama produk tampak aneh (`&amp;`, `&#039;`) | entity HTML belum dibersihkan | `90-kualitas-data.md` |
| "kategori media" banyak kosong padahal ada iklan | kolom ini sparsial | sebutkan keterisiannya di jawaban |

## Batas

- `kategori_media` (Visual/Audio/Audio Visual) sering kosong — jangan dipakai sebagai filter tunggal.
- Media "rokok"/"obat" tidak punya detail media terstruktur; data mentah ada di
  `bridge_pengawasan_media_detail.detail_json`.

## Rute

- Komoditi → **lihat** `10-komoditi.md`
- Wilayah ganda → **lihat** `95-batas-domain.md`
- Kekosongan kolom → **lihat** `90-kualitas-data.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `fact_pengawasan` | `jenis_iklan_id`, `kategori_media`, `provinsi_iklan_id`, `kabupaten_iklan_id`, `tgl_pengambilan_iklan` | — |
| `dim_pengawasan_jenis_iklan` | `id`, `kode`, `keterangan` | `LUAR_RUANG`, `ELEKTRONIK`, `CETAK`, `LAIN` |
| `bridge_pengawasan_media_detail` | `pengawasan_id`, `kategori`, `media_iklan_kode`, `detail_json` | — |
