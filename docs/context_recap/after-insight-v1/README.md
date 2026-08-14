# Varian `after-insight-v1` — domain `pengawasan`

**Dibuat:** 14 Agustus 2026 · **Status:** belum dijalankan terhadap suite.
**Basis:** seluruh temuan di `docs/temuan_database/` — profiling live, eksekusi 88 pair
`context_stores`, dan 13 `SQL Training` dari `BPOM User Relevant Query`.
**Pola penyusunan:** mengikuti `seeknal-bpom-neo/docs/context_recap/after-chart-route/route-context-070826-v6`
— dokumen orkestrator yang **merutekan dan menggerbang**, aturan data dipecah ke halaman topik kecil.

Menggantikan struktur v1 (`predikat.md` + `filter_code_reference.md` + `data_architecture.md`),
bukan menambahinya.

---

## Struktur

```
after-insight-v1/
├── SEEKNAL_ASK.md          orkestrator: PAGE MAP + Gate 0-5
├── seeknal_agent.yml       hanya blok prompt.custom yang diubah dari v1
├── context/                11 halaman topik
│   ├── 00-menghitung.md            WAJIB tiap pertanyaan data
│   ├── 10-komoditi.md              dimensi yang mengunci empat perilaku sekaligus
│   ├── 20-media-dan-iklan.md       penulisan media, lokasi tak-terkelompokkan, pembuat iklan terkunci
│   ├── 30-vonis.md                 tiga kolom vonis, himpunan nilai berbeda, gap balai-pusat
│   ├── 40-ketidaksesuaian.md       klausul pelanggaran, terkunci satu komoditi
│   ├── 45-status-dan-alur.md       kode penolakan tanpa label, id di luar fakta, batas "siapa"
│   ├── 50-produk-dan-pendaftar.md  teks bebas, string tergandakan, sentinel NIE yang bermakna
│   ├── 60-waktu-dan-durasi.md      kolom "durasi" yang sebenarnya penanda, ketepatan waktu
│   ├── 85-target-capaian.md        join beda kapitalisasi, unit pusat, anti-join yang kosong
│   ├── 90-kualitas-data.md         tabel fakta tanpa SQL NULL sama sekali
│   └── 95-batas-domain.md          NOT COVERED + kemiripan dengan domain penandaan
└── skills/
    ├── bpom-pengawasan-analyst/     DITULIS ULANG (v2.0.0)
    ├── bpom-pengawasan-forecaster/  mekanik disalin dari sibling, hanya domain diganti
    ├── detect-anomaly/              idem
    └── visualize-chart/             salinan verbatim dari v1
```

**Aturan chart, ekspor S3, forecast, dan anomaly tidak diubah sama sekali.** `visualize-chart`
disalin byte-identik dari v1, dan blok terkait di `SEEKNAL_ASK.md` Gate 0 & Gate 5 disalin verbatim.

⚠️ **Catatan khusus domain ini:** v1 **merujuk** `bpom-pengawasan-forecaster`, `detect-anomaly`,
dan `forecast_guide.md` di `SEEKNAL_ASK.md`, tetapi **berkasnya tidak pernah ada** — rujukan
menggantung. v2 memperbaikinya dengan menyediakan kedua skill: **mekanikanya disalin apa adanya**
dari domain sibling (CAPTURE, horizon, stock-vs-flow, aturan ekspor, larangan menghitung sendiri),
dan **hanya bagian domain bisnisnya** yang diganti — tabel, series registry, dan dua peringatan
khas domain ini (hitung event bukan baris; keluarkan sentinel dari deret berbasis vonis).
`forecast_guide.md` **tidak dibuat** karena mengarangnya berarti mengarang aturan forecast; metode
sepenuhnya dibawa skill.

`forecast`, `anomaly`, dan `upload_to_s3` kini `enabled: true` di `seeknal_agent.yml`, sejajar
dengan tiga domain lain. v1 mewariskan `false` untuk forecast dan anomaly — nilai yang tidak
konsisten dengan `SEEKNAL_ASK.md` v1 sendiri, yang justru merutekan ke kedua skill tersebut.

Pada `seeknal_agent.yml`, yang diubah adalah `prompt.custom` dan **tiga flag kapabilitas di blok
`agent`** itu. Sisa blok `agent`, serta `sources` dan `agent_harness`, byte-identik dengan v1.

**Dua skill v1 (`bpom-pengawasan-target`, `bpom-pengawasan-timeline`) tidak dibawa sebagai skill.**
Aturannya dipindahkan menjadi halaman context (`85-target-capaian.md`, `60-waktu-dan-durasi.md`) —
mengikuti pola referensi: skill tipis untuk penegakan, aturan data di halaman.

---

## Prinsip yang membedakannya dari v1

**1. Merutekan, bukan menimbun.** `00-menghitung.md` selalu dibuka; sisanya hanya bila kondisinya
menyala.

**2. Mengajarkan pemetaan, bukan angka.** Halaman-halaman ini **tidak memuat satu pun cacah baris,
persentase, atau nilai agregat**. Angka bergeser tiap ETL; context berangka menua menjadi salah dan
mengundang agent menjawab dari ingatan.

**3. Komoditi diperlakukan sebagai dimensi pengatur.** Kekhasan domain ini: satu dimensi menentukan
grain, keterisian kolom vonis akhir, keterisian pembuat iklan, dan ada-tidaknya klausul pelanggaran
— empat hal yang tampak tidak berhubungan. `10-komoditi.md` menyatukannya, dan tiap halaman terkait
merujuk balik ke sana.

**4. Sentinel diperlakukan sebagai aturan tabel, bukan per kolom.** Tabel fakta domain ini **tidak
punya SQL NULL sama sekali** — sesuatu yang tidak berlaku di tiga domain lain. Aturannya ditulis
sebagai butir pertama di `90-kualitas-data.md` dan diulang di Gate 5.

---

## Temuan yang menjadi alasan tiap halaman

| Halaman | Temuan yang mendasarinya |
|---|---|
| `00-menghitung` | Tiga tingkat entity memberi angka berbeda; grain multi-produk hanya berlaku sebagian komoditi sehingga perbandingan lintas komoditi bias |
| `10-komoditi` | Satu dimensi terbukti mengunci empat perilaku; komposisi volume berubah tajam antar periode sehingga tren total menyesatkan |
| `20-media-dan-iklan` | Penulisan nilai media tidak seragam gayanya sehingga pencarian frasa pengguna gagal; kolom pembuat iklan terkunci satu komoditi; kolom lokasi nyaris unik per baris |
| `30-vonis` | Tiga kolom vonis punya himpunan nilai berbeda — satu tingkat gradasi hanya ada di kolom pusat; kolom akhir terkunci komoditi; gap hanya sah bila kedua sisi terisi |
| `40-ketidaksesuaian` | Seluruh klausul melekat pada satu komoditi saja; satu event bisa punya beberapa klausul |
| `45-status-dan-alur` | Blok kode penolakan tidak punya label; log dan timeline memuat id di luar fakta; semantik pelaku ambigu |
| `50-produk-dan-pendaftar` | Kolom pendaftar memuat string tergandakan yang melebihkan cacah perusahaan; sentinel NIE justru bermakna |
| `60-waktu-dan-durasi` | Satu kolom selisih hanya bernilai beberapa kemungkinan — penanda, bukan durasi; kolom tanggal memuat tanggal masa depan |
| `85-target-capaian` | Join gagal karena beda kapitalisasi, bukan karena nama berbeda; unit pusat memang tidak bertarget; anti-join "yang tidak melaporkan" selalu kosong |
| `90-kualitas-data` | Tabel fakta tanpa SQL NULL; empat kolom dengan kekosongan deterministik; schema dimension basi |
| `95-batas-domain` | Kolom wilayah sudah dihapus dari skema; tidak ada penanda golongan obat; kemiripan dengan domain penandaan paling menjebak |

---

## Yang wajib diperiksa saat pilot

| Metrik | Gerbang |
|---|---|
| PASS suite yang ada | **tidak turun** |
| Jawaban pada skenario yang sudah benar | **nol yang bergerak** |
| SQL per turn | **tidak naik** |
| Pertanyaan "berapa pengawasan" | **klarifikasi entity**, bukan memilih diam-diam |
| Filter keluarga TMK | memakai pola awalan, bukan kesamaan persis |
| Pertanyaan wilayah produsen | dijawab NOT COVERED, **bukan** diganti wilayah kerja balai |
| Join ke log/timeline | dimulai dari tabel fakta |

⚠️ Dua hal yang tidak akan tertangkap suite mana pun: apakah kolom vonis yang dipilih benar ketika
ketiganya sama-sama menghasilkan angka yang masuk akal, dan apakah cakupan komoditi disebut di
kalimat jawaban. Keduanya perlu pembacaan manual.
