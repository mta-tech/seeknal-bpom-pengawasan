glossary · istilah · kamus user · padanan istilah · bahasa user · ambigu

# Glossary istilah user

## Apa yang halaman ini putuskan

Padanan istilah pertanyaan user ↔ kolom/kode domain ini — agar salah tafsir istilah tertangkap
sebelum SQL ditulis.

## Tabel keputusan — istilah ambigu (tanyakan dulu)

| Istilah | Ambiguitasnya |
|---|---|
| "ditolak" | tiga kolom vonis berbeda (`30-vonis.md`) |
| "media" | jenis kasar vs detail per kategori (`20-media-dan-iklan.md`) |
| "jumlah" | event / baris produk / surat / produk unik (`00-menghitung.md`) |
| "kesimpulan" | balai / pusat / akhir (`30-vonis.md`) |
| "selesai" | kode status — artinya belum dikonfirmasi BPOM (`45-status-dan-alur.md`) |

## Pemetaan istilah user → konsep data

| Istilah user | Padanan teknis | Jebakan |
|---|---|---|
| "memenuhi" | kode `MK` | tingkat berjenjang hanya di pusat (`TMK_*`) |
| "TMK" | keluarga `TMK` + `TMK_MINOR`/`TMK_MAYOR`/`TMK_KRITIKAL` | memfilter hanya `TMK` melewatkan yang bergradasi |
| "iklan" | satu kasus = satu iklan yang diawasi | satu event bisa memuat beberapa produk (bridge) |
| "marketplace" · "e-commerce" | `kategori` + `media_iklan_kode='ecommerce'` → `bridge_pengawasan_media_ecommerce` | — |
| "NIE" | `nie` (teks) di bridge produk | bukan objek registrasi di sini |
| "pendaftar" | `pendaftar` (bridge) / `dim_produk.pendaftar` | string tergandakan |
| "produk TIE" | produk tanpa izin edar | tidak ada kolom khusus di domain ini |
| "klaim" | `klasifikasiklaim_id` (otsk/kuasi) · narasi mentah via `fact_pengawasan_narasi` (`40-ketidaksesuaian.md`) | jangan campur dengan vonis |
| "evaluasi pusat" | kolom sisi Pusat (`35-sisi-pusat.md`) | parsial |
| "CAPA" · "tindak lanjut" | `tindak_lanjut_pusat_id` (kosmetik) | TL Balai tidak terekam (`95-batas-domain.md`) |
| "WebReg" | sistem registrasi produk (di luar data ini) | sinkron 1×24 jam — bukan tabel di sini |
| "tanggal pengambilan iklan" | `tgl_pengambilan_iklan` | sparsial; beda dari `tgl_start` |
| "entri" · "input" | `created_at` · `created_by` (`70-atribusi-kasus.md`) | kesegaran data lewat `created_at` |

## Cara mencari padanan istilah yang tidak ada di tabel

```sql
-- konsep tidak direkam? cek katalog kolom dulu (P5), jangan menebak
SELECT column_name FROM information_schema.columns
WHERE table_name = 'fact_pengawasan' AND column_name ILIKE '%<konsep>%';
```

## Jebakan

| Gejala | Penyebab | Cara memastikan |
|---|---|---|
| jawaban tidak konsisten antar sesi | istilah ambigu dipilih diam-diam | ikat padanannya di Gate 1 dan sebutkan di jawaban |
| kolom mirip dipakai sebagai jawaban | nama mirip ≠ makna sama | jalankan protokol NOT COVERED (`95-batas-domain.md`) |
| kode diartikan sendiri | kamus belum dikonfirmasi BPOM | tampilkan kode + sebutkan statusnya |

## Aturan klarifikasi

- Istilah dengan **lebih dari satu makna** → klarifikasi dulu (Gate 1), satu pertanyaan pada satu
  waktu, maksimal dua putaran.
- Istilah yang konsepnya **tidak direkam** → jawab batasnya, tawarkan hal terdekat yang benar.

## Rute

- Batas domain & wilayah → **lihat** `95-batas-domain.md`
- Entity & grain → **lihat** `00-menghitung.md`
- Vonis → **lihat** `30-vonis.md`

## Manifes

| Tabel | Kolom | Literal |
|---|---|---|
| `fact_pengawasan` | `kesimpulan_balai_id`, `kesimpulan_pusat_id`, `kesimpulan_akhir_id`, `status_id`, `jenis_iklan_id`, `tgl_pengambilan_iklan`, `created_at`, `created_by` | — |
| `dim_kesimpulan_penilaian` | `kode` | `MK`, `TMK`, `TMK_MINOR`, `TMK_MAYOR`, `TMK_KRITIKAL` |
