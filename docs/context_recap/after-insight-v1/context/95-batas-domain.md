Batas domain — apa yang TIDAK ada di database ini, dan bagaimana menjawabnya.

## Empat domain BPOM yang terpisah

| Domain | Isi | Database |
|---|---|---|
| **pengawasan** (di sini) | pengawasan **iklan** | domain ini |
| pemeriksaan | inspeksi ke sarana/fasilitas | database terpisah |
| pengujian | sampling dan hasil uji laboratorium | database terpisah |
| penandaan | pengawasan **label/penandaan produk** | database terpisah |

Keempatnya **tidak tersambung** di sini.

## Istilah yang menandai pertanyaan salah rute

| Istilah pengguna | Domain sebenarnya | Kenapa mudah tertukar |
|---|---|---|
| **MS / TMS**, "hasil uji", "parameter uji", "sampel", "LHU" | pengujian | domain ini memakai MK/TMK, bukan MS/TMS |
| **sarana**, "sarana distribusi/produksi", "temuan produk", "nilai sitaan" | pemeriksaan | domain ini tidak merekam sarana maupun nilai |
| **label / penandaan produk** | penandaan | keduanya memakai istilah "kesimpulan balai vs pusat" — ini yang paling menjebak |
| **izin edar / registrasi produk** | sistem registrasi | domain ini hanya menyimpan NIE sebagai teks |

> Kemiripan paling berbahaya: domain **penandaan** juga punya kolom kesimpulan balai dan pusat,
> dan juga memakai MK/TMK. Yang membedakan adalah **objek yang dinilai** — iklan di sini, label di
> sana. Bila pertanyaan menyebut "label", "kemasan", atau "penandaan produk", itu domain lain.

Cara memastikan bila ragu: periksa daftar kolom tabel (`information_schema.columns`). Bila tidak
ada kolom yang memuat konsepnya, itu **P5 NOT COVERED**.

## Konsep yang ditanyakan pengguna tetapi tidak ada di sini

| Diminta | Status | Catatan |
|---|---|---|
| **provinsi / kabupaten** (wilayah produsen) | **kolomnya tidak ada** | pernah ada di generasi skema lama, kini dihapus. Satu-satunya jalur geografi adalah wilayah kerja balai — dan itu **bukan** alamat produsen |
| **obat keras** sebagai golongan | tidak ada penandanya | tidak ada kolom yang membedakan golongan obat |
| **jenis pangan** pada iklan pangan | tidak ada | ada di domain lain |
| **materi / naskah / gambar iklan** | tidak ada | hanya keterangan lokasi |
| **siapa yang menyetujui** | tidak dapat dipastikan | semantik pelaku di log ambigu — `45-status-dan-alur.md` |
| **klausul pelanggaran untuk komoditi selain yang tercakup** | tidak direkam | `40-ketidaksesuaian.md` |
| **sebab patahan volume** antar periode | tidak direkam | tidak ada kolom kebijakan/keterangan |

Baris terakhir penting: bila pengguna bertanya *"kenapa turun drastis"*, database ini bisa
menunjukkan **bahwa** turun, tidak bisa menjelaskan **kenapa**. Jawab apa adanya dan tawarkan
pemecahan per komoditi/balai sebagai gantinya.

## Cara menjawab NOT COVERED

Tiga kalimat, tidak lebih:

1. sebut **apa yang ditanyakan** dan bahwa konsepnya tidak direkam di database ini;
2. sebut **di mana kemungkinan besar konsep itu berada**, bila diketahui;
3. tawarkan **hal terdekat yang benar-benar bisa dijawab**, dan sebutkan bedanya.

Yang **tidak boleh**: menjawab dengan kolom yang namanya mirip lalu berharap pembaca memahami
bedanya — misalnya menjawab pertanyaan wilayah produsen dengan wilayah kerja balai. Query semacam
itu jalan, hasilnya rapi, dan pembaca tidak punya cara tahu bahwa yang ditampilkan bukan yang
ditanyakan.

## Rute

- Kembali ke peta halaman → `SEEKNAL_ASK.md`.
- Menyentuh kekosongan kolom → **seberang** `90-kualitas-data.md`.
