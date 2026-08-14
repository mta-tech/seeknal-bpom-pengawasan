Klausul ketidaksesuaian — pelanggaran apa yang ditemukan pada iklan.

## Tabel

`mv_pengawasan_ketidaksesuaian` menempel ke fakta lewat `id_pengawasan`. Berisi kode klasifikasi
pelanggaran beserta keterangannya.

Kodenya **berjumlah kecil dan tetap**, dan **keterangannya sudah tersedia di kolom sendiri** —
tidak perlu tabel rujukan terpisah. Ambil daftarnya sekali (jalur **P2**), lalu pakai kodenya.

Konsep yang dicakup klausul-klausul itu: produk yang tidak boleh diiklankan, klaim kesehatan yang
tidak sesuai ketentuan, iklan menyesatkan terhadap karakteristik produk, pelanggaran norma, kalimat
superlatif/komparatif/mendiskreditkan, serta kata/figur/logo yang tidak boleh dipakai.

## Hanya melekat pada satu komoditi

Seluruh baris ketidaksesuaian milik **satu komoditi saja**. Untuk komoditi lain, klausul pelanggaran
**tidak direkam**.

> Pertanyaan "klausul pelanggaran pada iklan obat" atau komoditi lain selain yang tercakup
> **P5 NOT COVERED**. Jangan menggantinya dengan kolom vonis; vonis menyatakan *apakah* melanggar,
> bukan *klausul mana*.

Cara memastikan komoditi mana: join ke fakta lalu `GROUP BY komoditi` — jalur **P2**.

## Grain

Satu event bisa punya **beberapa** klausul. Karena itu:

- cacah **baris ketidaksesuaian** ≠ cacah **event yang punya ketidaksesuaian**;
- join ke fakta **melipatgandakan** baris fakta.

Untuk "berapa event yang melanggar", pakai `COUNT(DISTINCT id_pengawasan)`. Untuk "klausul mana
paling sering", cacah baris per kode — dan sebutkan bahwa satu event bisa punya beberapa klausul.

Hanya sebagian kecil event yang punya baris di tabel ini — **LEFT JOIN dari fakta**; INNER JOIN
menjatuhkan mayoritas.

## Kaitan dengan vonis

Adanya klausul ketidaksesuaian **tidak identik** dengan vonis TMK, dan sebaliknya. Keduanya kolom
yang berbeda dan tidak boleh dipakai bergantian. Bila pertanyaannya "iklan TMK karena apa",
gabungkan keduanya — vonis dari fakta, klausul dari tabel ini — dan sebutkan bahwa tidak semua TMK
punya klausul tercatat.


## Enam klausul dan kodenya

Tabel ketidaksesuaian menyimpan klausul pelanggaran dalam **dua kolom yang berpasangan satu-satu**:

| Kolom | Isi |
|---|---|
| `id_klasifikasi` | kode angka klausul |
| `keterangan_ketidaksesuaian` | teks lengkap klausul yang sama |

Karena berpasangan tepat, **memfilter cukup dengan kodenya**; teksnya dipakai untuk menampilkan
label di jawaban. Enam klausul yang ada:

| Kode | Klausul |
|---|---|
| `1` | Iklan produk yang tidak boleh diiklankan — minuman beralkohol, PKMK, formula bayi dan formula lanjutan |
| `2` | Iklan dengan klaim kesehatan yang tidak sesuai dengan ketentuan |
| `3` | Iklan menyesatkan karena tidak sesuai dengan karakteristik atau komposisi produk |
| `4` | Iklan yang melanggar norma yang berlaku — adegan berbahaya, SARA, dan sejenisnya |
| `5` | Iklan dengan kalimat superlatif, komparatif, dan mendiskreditkan, kecuali membandingkan dengan produk sendiri |
| `6` | Iklan dengan kata, figur, logo, atau lambang yang tidak boleh diiklankan |

> **Aturan:** istilah pengguna dipetakan ke kode, bukan dicari sebagai teks bebas. "Klaim kesehatan"
> menunjuk kode `2`; "superlatif" atau "berlebihan" menunjuk `5`; "menyesatkan" menunjuk `3`;
> "produk terlarang" menunjuk `1`; "melanggar norma" atau "SARA" menunjuk `4`; "lambang" atau
> "logo terlarang" menunjuk `6`.
>
> Mencari dengan pola kata di kolom teks berisiko: beberapa klausul memuat kata yang mirip, dan
> teksnya panjang sehingga potongan kata bisa cocok ke klausul yang salah.

**Jangan memeringkat klausul dari ingatan.** Komposisi mana yang terbanyak bergeser seiring data
bertambah; pertanyaan "pelanggaran terbanyak" selalu dijawab dari query saat itu juga.

## Rute

- Menyebut vonis: buka `30-vonis.md`.
- Menyebut komoditi: buka `10-komoditi.md`.

---

<!-- MANIFES
tabel: mv_pengawasan_ketidaksesuaian
kolom: id_klasifikasi, id_pengawasan, keterangan_ketidaksesuaian
nilai: -
-->
