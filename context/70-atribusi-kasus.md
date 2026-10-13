kasus · created_by · atribusi · akun · dim_user · pencatat

# Atribusi kasus (`created_by`)

## Data yang ada

Satu-satunya atribusi pelaku yang tersimpan di domain ini adalah kolom **`created_by`** pada fakta —
user_id akun yang mencatat kasus, di-join ke `dim_user.user_id`.

- `created_by` **tidak pernah kosong**.
- `dim_user` adalah **katalog akun nasional** (semua balai) — bukan daftar petugas lapangan.
- Domain ini **tidak menyimpan** tabel petugas lapangan, verifikator, atau pemutus; riwayat tahapan
  **tersedia** di `fact_pengawasan_approval` (`45-status-dan-alur.md`).

## Tabel keputusan

| Pertanyaan | Sumber |
|---|---|
| "siapa yang mencatat kasus" | `created_by` → `dim_user` |
| "berapa kasus per akun" | `count(*)` per `created_by` |
| "petugas lapangan" · "verifikator" · "penyetuju" | **tidak tersedia** — jelaskan batas data |
| "jumlah pegawai" | hitung `DISTINCT created_by` **pada kasus**, bukan dari `dim_user` |

## Matriks operasi

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `created_by` | butuh nilai persis | langsung | `dim_user.user_id` | bisa (jumlah kasus per akun) |
| `dim_user.balai_id` | **jangan** dipakai untuk menghitung pegawai balai | — | — | — |

## Cara mencari

```sql
-- kasus per akun pencatat (nilai tidak dihafal)
SELECT u.username, u.fullname, count(*) AS kasus
FROM public.fact_pengawasan f
JOIN public.dim_user u ON u.user_id = f.created_by
GROUP BY 1,2 ORDER BY 3 DESC;
```

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| "jumlah pegawai" membengkak | `dim_user` = katalog akun nasional | hitung `DISTINCT created_by` pada kasus |
| kolom `balai_id` dim dijadikan filter pegawai | akun terdaftar ≠ pelaksana kasus | hitung lewat kasus |
| menyimpulkan penilaian mutu | data hanya atribusi pencatatan | sebutkan hanya atribusi input |

## Batas

- Yang tersedia: atribusi pencatatan (`created_by`) — volume kasus per akun.
- Yang tidak tersedia: petugas lapangan, pemutus, verifikator (peran). Riwayat tahapan tersedia via `fact_pengawasan_approval`.

## Rute

- Status & alur → **lihat** `45-status-dan-alur.md`
- Produk & pendaftar → **lihat** `50-produk-dan-pendaftar.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `fact_pengawasan` | `created_by` | tidak pernah NULL |
| `dim_user` | `user_id`, `username`, `fullname`, `balai_id`, `active` | katalog akun nasional |
