# Forecast Guide (BPOM Forecaster) — kontrak SQL untuk `run_forecast`

> Engine: **ETS seasonal (Holt-Winters)** via IBA forecast engine — deterministik; LLM tidak
> menghitung apa pun. **Konsistensi kritikal:** SQL yang berbeda antar-giliran menghasilkan
> jawaban yang tampak berbeda, bukan sekadar level berbeda. Ikuti template §2 untuk pertanyaan
> baru, dan pakai ulang SQL giliran sebelumnya untuk pertanyaan lanjutan.

## §1 Kontrak SQL — dua kolom, tepat

`run_forecast(sql, periods)` menuntut hasil **tepat dua kolom**:

1. **X** — grain waktu (timestamp): `date_trunc('month', tgl_start)`.
2. **Y** — angka (numerik): `COUNT(DISTINCT id)`.

Kolom ketiga, baris dengan X kosong, atau grain ganda → engine menolak.

## §2 Template

```sql
SELECT date_trunc('month', f.tgl_start) AS x,
       COUNT(DISTINCT f.id)             AS y
FROM   public.fact_pengawasan f
WHERE  f.tgl_start IS NOT NULL
GROUP  BY 1 ORDER BY 1;
```

- Seri tidak disebut user = **Total pengawasan (event)** — grain `fact`, bukan baris produk
  (`00-menghitung.md`).
- Filter seri (komoditi / media / wilayah) = `WHERE` tambahan mengikuti halaman terkait
  (`10` / `20` / `95`) — jangan mengubah grain.
- Bila user menanyakan balai tertentu, tambahkan `AND f.balai_id = <balai_id dari dim_balai>`.
- **Periode berjalan parsial** — bulan ini belum lengkap; pertimbangkan memotongnya:
  `AND f.tgl_start < date_trunc('month', now())`.

## §3 Kualitas & interpretasi

- Cek panjang seri dulu: riwayat terlalu pendek atau bolong → label kualitas turun; sebutkan
  label yang dikembalikan tool, jangan menjanjikan akurasi.
- Patahan volume antar periode bisa berarti komposisi berubah (`10-komoditi.md`) — sebutkan
  kemungkinan itu pada jawaban; forecast tidak menjelaskan **kenapa**.
- `periods` = jumlah langkah pada grain SQL (bulanan: 6 bulan → 6, 1 tahun → 12) — terjemahan
  horizon ada di skill `bpom-pengawasan-forecaster`.
