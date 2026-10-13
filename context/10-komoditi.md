komoditi · obat · kosmetika · pangan · obat tradisional · suplemen · rokok · obat kuasi

# Komoditi

## Apa yang halaman ini putuskan

Istilah komoditi user dipetakan ke kolom mana, dan mengapa ada **dua** kolom komoditi dengan grain
berbeda.

## Dua kolom komoditi — jangan dicampur

| Kolom | Grain | Isi |
|---|---|---|
| `kategori` (teks) | **kasar — 6 nilai** | `rokok` · `obat` · `pangan` · `kosmetik` · `otsk` · `obat_kuasi` |
| `komoditi_id` (tanpa kamus nama di akun ini) | **halus** | memecah lebih halus dari `kategori` (mis. OT vs Suplemen di dalam `otsk`); sebut kodenya, jangan menebak nama |

## Tabel keputusan — istilah user → kolom

| Istilah user | Kolom yang dipakai |
|---|---|
| "obat" (keluarga) | `kategori = 'obat'` |
| "obat tradisional" · "OT" | `kategori = 'otsk'` (gabungan) atau `komoditi_id = 131` (OT saja) |
| "suplemen kesehatan" | `komoditi_id = 150` |
| "OT & suplemen" · "otsk" | `kategori = 'otsk'` |
| "obat kuasi" | `kategori = 'obat_kuasi'` / `komoditi_id = 1233` |
| "kosmetik(a)" | `kategori = 'kosmetik'` / `komoditi_id = 167` |
| "pangan" · "pangan olahan" | `kategori = 'pangan'` / `komoditi_id = 177` |
| "rokok" | `kategori = 'rokok'` / `komoditi_id = 873` |

## Matriks operasi

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `kategori` | langsung (6 nilai) | langsung | — | bisa |
| `komoditi_id` | kode langsung | langsung | — (tanpa kamus nama di akun ini) | bisa |

## Cara mencari

```sql
-- nilai kategori yang benar-benar ada di akun ini
SELECT kategori, count(*) FROM public.fact_pengawasan GROUP BY 1 ORDER BY 2 DESC;

-- daftar kode komoditi yang benar-benar terpakai (jangan hafal)
SELECT komoditi_id, count(*) FROM public.fact_pengawasan GROUP BY 1 ORDER BY 2 DESC;
```

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| angka "obat" tidak cocok | satu sisi `kategori`, sisi lain `komoditi_id` | putuskan satu grain, sebutkan di jawaban |
| suplemen hilang dari "OT" | `otsk` di `kategori`, tapi `komoditi_id` memecahnya | pilih `kategori='otsk'` bila maksudnya gabungan |
| komoditi dari domain lain muncul | memakai kamus tanpa filter `type` | filter `type='KOMODITI'` |

## Batas

- Komoditi yang tidak pernah diawasi tidak akan muncul — bukan berarti tidak ada.
- Nama untuk kode `komoditi_id` tidak ada kamusnya di akun ini: sebut kode + `kategori`,
  jangan menebak nama.

## Rute

- Vonis/kesimpulan → **lihat** `30-vonis.md`
- Produk & NIE → **lihat** `50-produk-dan-pendaftar.md`
- Media iklan → **lihat** `20-media-dan-iklan.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `fact_pengawasan` | `kategori`, `komoditi_id` | `kategori ∈ {rokok,obat,pangan,kosmetik,otsk,obat_kuasi}` |
