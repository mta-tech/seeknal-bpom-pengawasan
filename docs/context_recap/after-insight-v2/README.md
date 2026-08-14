# `after-insight-v2` — domain `pengawasan`

**Dibuat:** 14 Agustus 2026 · **Status:** belum dijalankan terhadap suite.
**Basis:** `after-insight-v1` (yang hidup sekarang) + seluruh temuan di `docs/temuan_database/`.
**Acuan:** kondisi database live. Rancangan lengkapnya di `docs/audit_context/rancangan-v2.md`.

Versi lama **tidak dihapus dan tidak dipindah** — `v1-base` dan `after-insight-v1` tetap di
tempatnya.

## Isi

```
after-insight-v2/
├── SEEKNAL_ASK.md         orkestrator: PAGE MAP + Gate 0-5
├── seeknal_agent.yml      tidak berubah dari versi sekarang
├── context/               11 halaman
└── skills/                4 skill, tidak berubah
```

Alat pemeriksanya ada di `docs/audit_context/periksa_manifes.py` — di luar folder ini, karena ia
alat audit, bukan bagian dari context yang dibaca agent.

## Yang berubah dari versi sekarang

| Halaman | Perubahan |
|---|---|
| `40-ketidaksesuaian.md` | katalog enam klausul beserta kodenya |
| `85-target-capaian.md` | kolom target mana yang dipakai, grain balai × komoditi, cakupan tahun |
| `60-waktu-dan-durasi.md` | kolom tahap timeline; peringatan kolom selisih yang sebenarnya penanda |
| `45-status-dan-alur.md` | `status_code`: blok tahap versus blok penolakan |

**Gate 5** bertambah dua butir yang berlaku umum: nilai teks dinormalkan sebelum dikelompokkan
atau disaring, dan pertanyaan rentang waktu memakai penjaga.

## Pemeriksa mandiri

Tiap halaman diakhiri blok `<!-- MANIFES -->` yang mendaftar tabel, kolom, dan literal nilai yang
diajarkannya. `periksa_manifes.py` memeriksa ketiganya terhadap database, **dan** melaporkan kolom
berkode yang belum diajarkan halaman mana pun.

```
WAREHOUSE_URL=... python3 docs/audit_context/periksa_manifes.py \
    docs/context_recap/after-insight-v2/context
```

Ia menyertakan kontrol negatif — nama karangan harus dilaporkan tidak ditemukan. Bila kontrol itu
gagal, hasilnya tidak boleh dipercaya. Saat ditulis: **lulus, nol pelanggaran**.

## Pola bertanya pengguna di domain ini

Dari 88 SQL pair yang dieksekusi: "tampilkan data" sangat dominan, dan hampir separuh pertanyaannya **tidak** meminta agregasi — melainkan daftar rinci.

## Yang sengaja tidak diubah

Aturan chart, ekspor S3, forecast, dan anomaly; struktur gerbang; larangan angka nilai data di
halaman context. Halaman yang sudah benar terhadap database dibiarkan apa adanya.
