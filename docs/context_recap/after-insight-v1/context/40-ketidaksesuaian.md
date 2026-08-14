Klausul ketidaksesuaian — pelanggaran apa yang ditemukan pada iklan.

## Tabel

`mv_pengawasan_ketidaksesuaian` menempel ke fakta lewat `id_pengawasan`. Berisi kode klasifikasi
pelanggaran beserta keterangannya.

Kodenya **berjumlah kecil dan tetap**, dan **keterangannya sudah tersedia di kolom sendiri** —
tidak perlu tabel rujukan terpisah. Ambil daftarnya sekali (jalur **P2**), lalu pakai kodenya.

Konsep yang dicakup klausul-klausul itu: produk yang tidak boleh diiklankan, klaim kesehatan yang
tidak sesuai ketentuan, iklan menyesatkan terhadap karakteristik produk, pelanggaran norma, kalimat
superlatif/komparatif/mendiskreditkan, serta kata/figur/logo yang tidak boleh dipakai.

## ⚠️ Hanya melekat pada satu komoditi

Seluruh baris ketidaksesuaian milik **satu komoditi saja**. Untuk komoditi lain, klausul pelanggaran
**tidak direkam**.

> Pertanyaan "klausul pelanggaran pada iklan obat" atau komoditi lain selain yang tercakup →
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

## Rute

- Menyebut vonis → **seberang** `30-vonis.md`.
- Menyebut komoditi → **seberang** `10-komoditi.md`.
