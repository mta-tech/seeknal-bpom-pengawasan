MK · TMK · mayor · minor · kritikal · memenuhi ketentuan · kesimpulan · balai · pusat · akhir

# Vonis (kesimpulan penilaian)

## Apa yang halaman ini putuskan

Kolom vonis mana yang dipakai, bagaimana join ke kamusnya, dan mengapa tiga kolom vonis **tidak
bisa dipertukarkan**.

## Tiga kolom vonis, satu kamus

`kesimpulan_balai_id`, `kesimpulan_pusat_id`, `kesimpulan_akhir_id` **semuanya** merujuk
`dim_kesimpulan_penilaian.id` — join **tiga kali** dengan alias berbeda.

Kode kamus: `MK` · `TMK` · `TMK_MINOR` · `TMK_KRITIKAL` · `TMK_MAYOR`.

## Tabel keputusan

| Istilah user | Kolom |
|---|---|
| "menurut balai" · "hasil verifikasi balai" | `kesimpulan_balai_id` |
| "menurut pusat" · "hasil evaluasi pusat" | `kesimpulan_pusat_id` |
| "kesimpulan akhir" · "final" | `kesimpulan_akhir_id` — **terisi hanya sebagian** (lihat Batas) |
| "TMK mayor/minor/kritikal" | `dim_kesimpulan_penilaian.kode` (`TMK_MAYOR` / `TMK_MINOR` / `TMK_KRITIKAL`) |
| "yang lulus" · "memenuhi" | `kode='MK'` pada kolom vonis yang dimaksud |
| "ditolak" · "tidak lolos" | dua jalur: keluarga `TMK*` pada kolom vonis (balai/pusat/akhir), atau `trx_steps LIKE 'ditolak_%'` di `fact_pengawasan_approval` (`45-status-dan-alur.md`) |

## Matriks operasi

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `kesimpulan_balai_id` | butuh kamus | butuh kamus | `dim_kesimpulan_penilaian.id` (alias) | bisa |
| `kesimpulan_pusat_id` | butuh kamus | butuh kamus | idem (alias berbeda) | bisa |
| `kesimpulan_akhir_id` | butuh kamus + **sadar cakupan** | idem | idem | sebutkan keterisian |
| `ketidaksesuaianhasil_kode` | `dim_pengawasan_ketidaksesuaian_hasil` | idem | `.kode` | — |

## Cara mencari

```sql
-- nilai kamus vonis (jangan hafal)
SELECT id, kode, keterangan FROM public.dim_kesimpulan_penilaian ORDER BY id;

-- keterisian tiap kolom vonis (wajib dicek sebelum menjawab "kesimpulan")
SELECT count(*) FILTER (WHERE kesimpulan_balai_id IS NOT NULL) balai,
       count(*) FILTER (WHERE kesimpulan_pusat_id IS NOT NULL) pusat,
       count(*) FILTER (WHERE kesimpulan_akhir_id IS NOT NULL) akhir
FROM public.fact_pengawasan;
```

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| "yang lulus" angka berbeda 2× | kolom vonis tertukar (balai vs pusat) | tanyakan/ikat kolom yang dimaksud di Gate 1 |
| TMK terlihat lebih sedikit | hanya menghitung `TMK`, melewatkan `TMK_*` bergradasi | pakai keluarga (prefix) atau set kode lengkap |
| kesimpulan akhir kosong banyak | kolom sparsial | sebutkan cakupan sebelum persentase |
| rekap vonis dari bridge iklan-produk | teks mentah, bukan kode | pakai kolom ID di fakta |

## Batas

- `kesimpulan_akhir_id` hanya terisi untuk sebagian kategori (rokok/obat) → jangan menggunakannya
  sebagai vonis universal.
- `kesimpulan_pusat_id` terisi parsial; kosong **bukan** berarti "belum diproses" kecuali dijelaskan.

## Rute

- Komoditi → **lihat** `10-komoditi.md`
- Klausul/ketidaksesuaian → **lihat** `40-ketidaksesuaian.md`
- Status & alur → **lihat** `45-status-dan-alur.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `fact_pengawasan` | `kesimpulan_balai_id`, `kesimpulan_pusat_id`, `kesimpulan_akhir_id`, `ketidaksesuaianhasil_kode` | — |
| `dim_kesimpulan_penilaian` | `id`, `kode` | `MK`, `TMK`, `TMK_MINOR`, `TMK_KRITIKAL`, `TMK_MAYOR` |
| `dim_pengawasan_ketidaksesuaian_hasil` | `kode`, `keterangan` | — |
