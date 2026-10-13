target · capaian · realisasi · pencapaian · persentase capaian · target sampling · target sarana

# Target & capaian

## Apa yang halaman ini putuskan

Target ada di **`dim_balai`** (per balai), bukan di tabel fakta. Halaman ini memutuskan kolom target
mana yang dipakai dan bagaimana menyajikannya dibanding realisasi.

## Tabel keputusan

| Kata dalam pertanyaan | Sumber |
|---|---|
| "target" (tanpa keterangan) | `dim_balai.target_sampling` **atau** `target_sarana` — dua kolom berbeda; tanyakan maksudnya |
| "target sampling" | `dim_balai.target_sampling` |
| "target sarana" | `dim_balai.target_sarana` |
| "realisasi" · "capaian" | hitungan kasus dari fakta |
| "persentase capaian" | realisasi ÷ target — **sebutkan pembilang, penyebut, dan periode** |

## Matriks operasi

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `target_sampling` | baris balai akun ini saja | langsung | dari `dim_balai` | sebutkan satuan |
| `target_sarana` | idem | langsung | dari `dim_balai` | sebutkan satuan |
| realisasi (kasus) | periode + eksklusi | — | dari fakta | biasa |

## Cara mencari

```sql
-- target balai akun ini (baris balai sendiri — jangan menampilkan balai lain)
SELECT balai_id, nama_balai, target_sampling, target_sarana
FROM public.dim_balai WHERE balai_id = 10;

-- target vs realisasi (contoh; periode sesuai pertanyaan)
SELECT count(DISTINCT f.id) AS realisasi
FROM public.fact_pengawasan f
WHERE f.tgl_start >= DATE '2025-01-01' AND f.tgl_start < DATE '2026-01-01';
```

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| persentase menyesatkan | pembilang (realisasi kasus iklan) dan penyebut (target sarana/sampling) beda satuan | sebutkan keduanya apa adanya, jangan diamkan |
| "target nasional" diminta | akun hanya balai ini | jelaskan cakupan; jangan menampilkan balai lain |
| periode tidak sama | realisasi lintas periode vs target tahunan | samakan periode, sebutkan keduanya |

## Batas

- Kolom target yang tersedia (`target_sampling`, `target_sarana`) bersatuan **sarana/sampling**; tidak
  ada kolom target khusus pengawasan iklan.
- Target hanya per balai — akun ini hanya memuat baris balai sendiri; perbandingan antar-balai bukan
  cakupan akun (`95-batas-domain.md`).

## Rute

- Periode → **lihat** `60-waktu-dan-durasi.md`
- Wilayah & batas cakupan → **lihat** `95-batas-domain.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `dim_balai` | `balai_id`, `nama_balai`, `target_sampling`, `target_sarana` | — |
| `fact_pengawasan` | `id`, `tgl_start` | — |
