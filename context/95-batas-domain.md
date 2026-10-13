batas · domain · wilayah · balai · provinsi · nasional · riau · dumai

# Batas domain dan batas wilayah

## Apa yang halaman ini putuskan

Apa yang **bukan** domain ini (domain lain), dan apa yang **bukan cakupan akun ini** (wilayah) —
sebelum menjawab "tidak tersedia".

## Empat domain BPOM yang terpisah

| Domain | Isi | Database |
|---|---|---|
| **pengawasan** (di sini) | pengawasan **iklan** | akun ini |
| pemeriksaan | inspeksi ke sarana/fasilitas | akun lain |
| pengujian | sampling dan hasil uji laboratorium | akun lain |
| penandaan | pengawasan **label/penandaan produk** | akun lain |

Keempatnya tidak tersambung. Istilah penanda salah rute: **MS/TMS** (pengujian) · **sarana ·
temuan produk · nilai sitaan** (pemeriksaan) · **label/kemasan produk** (penandaan) · **izin edar
sebagai objek** (sistem registrasi — di sini NIE hanya teks).

## Lingkup akun ini

- Akun memuat **semua balai**. Pertanyaan per balai = filter `balai_id` (nama via `dim_balai`).
- Perbandingan antar balai, peringkat, dan angka gabungan **boleh** — sebutkan lingkup yang dipakai.
- **Balai ≠ Provinsi.** Satu provinsi bisa memiliki beberapa kantor BPOM; "data provinsi X" ≠
  "data balai di X". Ikat lewat `dim_balai` (`provinsi_id`, `kabupaten_id`), bukan asumsi nama.
- Kolom `regional_name` di `dim_balai` adalah pengelompokan regional (bukan wilayah balai) —
  **jangan** dipakai sebagai filter.

## Wilayah ganda Sumatera

Wilayah 9 provinsi Sumatera tercatat **dua kali** di `dim_provinsi`/`dim_kabupaten`: set lama (nama
huruf besar) dan set baru (ID = kode Kemendagri). **Set baru = kanonik.**

- **Provinsi:** ID kanonik = `COALESCE(kode_id_sdata::bigint, provinsi_id)`.
- **Kabupaten/kota:** `dim_kabupaten.kode_id_sdata` **salah** — jangan dipakai. Pakai peta tetap
  `peta_kab` (salin apa adanya):

```sql
WITH peta_kab(id_lama, id_baru) AS (VALUES
    (79,1406),(80,1402),(81,1408),(82,1403),(83,1404),(84,1407),
    (85,1409),(86,1405),(87,1401),(88,1410),(89,1471),(90,1473))
SELECT kn.nama_kabupaten, count(*)
FROM public.fact_pengawasan f
LEFT JOIN peta_kab m  ON m.id_lama = f.kabupaten_iklan_id
JOIN dim_kabupaten kn ON kn.kabupaten_id = COALESCE(m.id_baru, f.kabupaten_iklan_id)
GROUP BY 1 ORDER BY 2 DESC;
```

Wilayah di luar 12 kabupaten/kota Riau tidak dipetakan — tampilkan nama aslinya apa adanya
(jangan dipaksa lewat `kode_id_sdata`).

## Konsep yang ditanyakan tetapi tidak ada di domain ini

| Diminta | Status |
|---|---|
| golongan **obat keras** | tidak ada penandanya |
| materi/naskah/gambar iklan | tidak direkam (hanya keterangan lokasi) |
| sebab patahan volume antar periode | tidak direkam — bisa menunjukkan **bahwa** turun, bukan **kenapa** |
| siapa yang menyetujui / self-approval | makna `user_id` tidak dapat dipastikan (`45-status-dan-alur.md`) |
| narasi untuk semua komoditi | keterisian beda per kategori — cek dulu (`40-ketidaksesuaian.md`) |
| tindak lanjut TMK sisi Balai (`tltmk`) | tidak terekam; TL sisi pusat tersedia (`35-sisi-pusat.md`) |

## Cara menjawab NOT COVERED

Tiga kalimat, tidak lebih: (1) sebut apa yang ditanyakan dan bahwa konsepnya tidak tersedia;
(2) sebut di mana kemungkinan besar konsep itu berada; (3) tawarkan hal terdekat yang benar-benar
bisa dijawab, dan sebutkan bedanya.

Jangan menjawab dengan kolom yang namanya mirip lalu berharap pembaca memahami bedanya.

## Bahasa jawaban untuk batas dan cakupan

Saat menyatakan batas/cakupan, gunakan bahasa pengguna - JANGAN istilah teknis data.

- Sebut: "cakupan data ini" atau "cakupan data tidak tersedia pada akun ini".
- JANGAN sebut: grant/di-grant, akun, reader, nama tabel/bridge internal, staging, database, balai_id.
- Sebutkan lingkup (semua balai / balai tertentu) setiap kali menyajikan angka lintas balai.
- Contoh kalimat benar: "untuk cakupan data ini, naskah/materi iklan tidak direkam - yang bisa disajikan adalah keterangan lokasi media."


## Matriks operasi

| Kolom | Menyaring | Mengelompokkan | Men-join | Memeringkat |
|---|---|---|---|---|
| `balai_id` | pertanyaan per-balai/lintas balai: filter wajib | langsung | `dim_balai` | biasa |
| `provinsi_iklan_id` / `kabupaten_iklan_id` | **ID kanonik** (P11) | ID kanonik | `dim_provinsi` / `dim_kabupaten` | bisa |
| `regional_name` | **jangan** dijadikan filter wilayah | kelompok informasional saja | — | — |

## Cara memastikan sebuah konsep benar-benar tidak ada

```sql
-- konsep tidak direkam? cek katalog kolom (P5) — bukan menebak dari nama yang mirip
SELECT column_name FROM information_schema.columns
WHERE table_name = 'fact_pengawasan' AND column_name ILIKE '%<konsep>%';
```

## Rute

- Kembali ke peta halaman → `SEEKNAL_ASK.md`
- Kekosongan kolom → **lihat** `90-kualitas-data.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `fact_pengawasan` | `balai_id`, `provinsi_iklan_id`, `kabupaten_iklan_id` | `balai_id=10` |
| `dim_balai` | `balai_id`, `nama_balai`, `regional_name`, `id_parent` | `regional_name` bukan filter wilayah |
| `dim_provinsi` | `provinsi_id`, `kode_id_sdata` | kanonik: `COALESCE(kode_id_sdata::bigint, provinsi_id)` |
| `dim_kabupaten` | `kabupaten_id`, `kode_id_sdata` | `kode_id_sdata` **jangan dipakai**; peta `peta_kab` |
