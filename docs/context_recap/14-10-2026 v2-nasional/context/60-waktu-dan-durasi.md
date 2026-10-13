tahun · bulan · periode · tren · durasi · lama · berapa hari · tepat waktu · timeline · SLA

# Waktu dan durasi

## Apa yang halaman ini putuskan

Kolom tanggal mana yang kanonik untuk periode, mana untuk penyelesaian, dan durasi apa yang benar-
benar bisa dihitung di akun ini.

## Tabel keputusan

| Kata dalam pertanyaan | Kolom |
|---|---|
| periode · tren · "bulan X" · "tahun X" | `tgl_start` (kanonik) |
| penyelesaian · "selesai dalam" | `tgl_end` |
| tanggal surat tugas | `tgl_surat` |
| kapan iklan ditemukan | `tgl_pengambilan_iklan` |
| evaluasi Pusat | `tgl_evaluasi_pusat` (hanya untuk kategori tertentu — lihat Batas) |

## Matriks operasi

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `tgl_start` | **rentang berbatas**, bukan `EXTRACT` | `date_trunc` boleh untuk melabeli | — | bisa |
| `tgl_end` | rentang berbatas | `date_trunc` | — | bisa |
| `tgl_pengambilan_iklan` | rentang berbatas | `date_trunc` | — | sebutkan keterisiannya |
| `tgl_evaluasi_pusat` | rentang berbatas | — | — | hanya kategori tertentu |

## Cara mencari

```sql
-- 1. rentang yang benar-benar terisi
SELECT min(tgl_start), max(tgl_start), count(*) FILTER (WHERE tgl_start IS NULL)
FROM public.fact_pengawasan;

-- 2. keterisian tanggal yang sparsial sebelum dipakai
SELECT count(tgl_pengambilan_iklan) terisi FROM public.fact_pengawasan;
```

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| filter periode membuang banyak baris | `EXTRACT(YEAR …)` di `WHERE` | rentang berbatas; tidak ada indeks |
| data terlihat "segar" padahal tidak | memakai `max(tgl_start)` sebagai kesegaran | `tgl_start` bisa berisi jadwal masa depan; kesegaran pakai `created_at` |
| durasi aneh | memakai kolom tanggal yang belum tercapai | saring dulu baris yang tanggalnya terisi, sebutkan cakupannya |

## Batas

- **Durasi antar-tahap** dihitung dari `created_at` berturutan per kasus (`lag`) di
  `fact_pengawasan_approval`; durasi kasus = `tgl_end - tgl_start`.
- `tgl_evaluasi_pusat`, `tgl_pengambilan_iklan` sparsial dan hanya untuk sebagian kategori — sebutkan
  keterisian sebelum menyajikan tren berbasisnya.
- Periode berjalan selalu parsial → sebutkan.

## Rute

- Status & alur → **lihat** `45-status-dan-alur.md`
- Target & capaian → **lihat** `85-target-capaian.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `fact_pengawasan` | `tgl_start`, `tgl_end`, `tgl_surat`, `tgl_pengambilan_iklan`, `tgl_evaluasi_pusat`, `created_at` | — |
