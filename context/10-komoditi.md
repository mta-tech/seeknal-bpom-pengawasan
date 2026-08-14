Komoditi — dimensi yang mengatur hampir semua perilaku di domain ini.

## Kolom `komoditi`

Berisi golongan produk yang iklannya diawasi. Nilainya huruf besar, mencakup obat, kosmetika,
produk pangan, obat tradisional, suplemen kesehatan, obat kuasi, dan rokok.

Ambil daftar nilainya bila ragu — jalur **P2**.

## ⚠️ Ejaan berbeda dari domain pemeriksaan

Domain ini memakai **`KOSMETIKA`** dan **`OBAT TRADISIONAL (OT)`**; domain pemeriksaan memakai
`KOSMETIK` dan `OBAT TRADISIONAL`. Domain penandaan punya satu nilai tambahan yang tidak ada di
sini. **Jangan menyalin daftar komoditi antar domain.**

## Komoditi mengunci empat perilaku sekaligus

Ini kekhasan domain ini — satu dimensi menentukan hal-hal yang tampak tidak berhubungan:

| Perilaku | Ringkas |
|---|---|
| **Grain** | hanya sebagian komoditi yang punya banyak produk per event — `00-menghitung.md` §2 |
| **Kolom vonis akhir** | hanya terisi untuk sebagian komoditi — `30-vonis.md` |
| **Pembuat iklan** | hanya terisi untuk satu komoditi — `20-media-dan-iklan.md` |
| **Klausul ketidaksesuaian** | hanya melekat pada satu komoditi — `40-ketidaksesuaian.md` |

> **Aturan umum:** sebelum menyajikan angka lintas komoditi, periksa apakah kolom yang dipakai
> terisi merata. Bila tidak, angka "nasional" sebenarnya angka sebagian komoditi.

Cara memeriksanya: `GROUP BY komoditi` dengan `count(*)` dan `count(*) FILTER (WHERE kolom <> sentinel)`
berdampingan.

## Istilah pengguna yang ambigu

| Istilah | Tindakan |
|---|---|
| **"obat"** / "obat-obatan" | golongan obat saja, atau termasuk obat tradisional, kuasi, suplemen? **tanya** |
| **"obat keras"** | **tidak ada penandanya** di database ini — lihat `95-batas-domain.md` |
| **"makanan"** | golongan produk pangan |
| **"OT; suplemen; obat kuasi"** | tiga golongan, sertakan ketiganya |

## Komposisi berubah tajam antar periode

Volume per komoditi **tidak stabil sepanjang waktu** — ada komoditi yang praktis berhenti diawasi
pada satu titik, dan ada yang baru mulai diintensifkan. Akibatnya:

> Tren **total** pengawasan tanpa memecah komoditi menyembunyikan patahan komposisi, dan mudah
> disalahartikan sebagai kenaikan/penurunan kinerja.

**Aturan:** tren lintas tahun sebaiknya dipecah per komoditi, atau sertakan catatan bahwa
komposisinya berubah. Jangan menyimpulkan sebab dari data ini — sebabnya tidak direkam.

## Rute

- Menyebut vonis → **seberang** `30-vonis.md`.
- Menyebut media/pembuat iklan → **seberang** `20-media-dan-iklan.md`.
- Menyebut klausul → **seberang** `40-ketidaksesuaian.md`.
