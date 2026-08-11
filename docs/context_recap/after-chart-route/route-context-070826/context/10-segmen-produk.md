Segmen produk — jenis pangan: bayi, formula, kopi, instan, AMDK, garam, sirup, mi, susu, roti, anggur, serbuk, BTP

## Urutan mengunci segmen

1. **Kolom berkode dulu** — `jenis_pangan` (INDUK) / `kategori_pangan` (ANAK). Murah, persis, bisa dipakai ulang.
2. **Baru teks bebas** — `nama_kategori`. Keterisiannya **berbeda jauh antar sistem**; periksa dulu
   (`00-menghitung.md` §5) dan probe **kedua sistem**. Memperlakukannya sebagai kolom satu sistem
   membuang katalog sisi lain yang bisa jadi justru lebih lengkap.
3. `nama` / `merk` hanya bila segmennya memang nama produk/merek. `nama_produk` **tidak ada**.

**ILIKE untuk MENEMUKAN, `=` untuk MENGHITUNG.** Jalankan ILIKE sekali (berlingkup, satu query,
pakai `LIMIT`) untuk melihat nilai persisnya, lalu hitung dengan `=` pada nilai itu. Menghitung
lewat pola menjaring nilai-nilai tetangga yang tidak ditanya, dan selisihnya tidak terlihat di
hasil — query tetap jalan, angkanya tetap masuk akal.

## Dua aturan struktural

**Namespace tidak dibagi antar sistem.** `jenis_pangan` **nol irisan** ERBA↔ERLA — bukan "sebagian
besar berbeda", tapi tidak satu nilai pun sama. Kode yang dibawa lintas sistem **selalu** memberi 0,
dan 0 itu berarti "namespace salah", bukan "segmen tidak ada di sini". Resolusikan tiap sisi
sendiri, setiap kali. `kategori_pangan` hanya sebanding pada prefiks 2 digit.

**Induk sebelum anak.** `kategori_pangan` adalah level ANAK dari `jenis_pangan`, bukan kolom
paralel. Mulai dari induk; turun ke anak hanya bila pertanyaan menyebut varian spesifik itu.
Memilih anak untuk pertanyaan tingkat keluarga membuang saudara-saudaranya diam-diam. Untuk melihat
apakah induk yang dipilih punya beberapa anak:
`SELECT kategori_pangan, COUNT(*) … WHERE jenis_pangan='<induk>' GROUP BY 1`.

## Tutup setnya — berlaku untuk teks bebas juga

Satu ILIKE biasanya cocok ke beberapa nilai `nama_kategori`, dan **nilai-nilai itu tidak setara**.
"Kopi" mencakup belasan: Kopi Bubuk, Kopi Instan, Minuman Kopi, Biji Kopi, Minuman Serbuk Kopi —
sedangkan "kopi instan" hanya satu. Menjawab "berapa produk kopi" dengan baris Kopi Instan saja
adalah versi teks-bebas dari mengambil satu kode dari sebuah set.

**Tetangga bisa LEBIH BESAR dari yang diminta.** Kategori bersaudara sering punya nama yang hanya
berbeda satu kata (`Sirup Berperisa` vs `Sirup Encer Berperisa`), dan yang tidak diminta bisa lebih
besar. Melebarkan pola karenanya bukan sekadar menambah — ia bisa **membalik urutan besaran** dan
menyerahkan jawaban ke segmen yang tidak ditanya. Lihat daftar hasil probe sebelum memutuskan lebar.

**Ejaan bervariasi di dalam kolom yang sama** (mis. varian *i/y* pada istilah serapan) — dua nilai
untuk satu gagasan. Pola yang berlabuh pada satu ejaan kehilangan yang lain tanpa suara; periksa
daftar hasil probe, jangan berasumsi ejaannya seragam.

Sebutkan nilai-nilai yang cocok di jawaban supaya pembaca melihat lingkup yang dipakai. Lebarnya
ditentukan pertanyaan, bukan kemiripan string — bila benar-benar ambigu, tanya (Gate 1).

## Jangan pernah

- Menjawab dengan **tren tahunan** karena segmennya tidak teresolusi. Pertanyaan tentang segmen
  dijawab tentang segmen; tren hanya bila tren yang diminta.
- Menyimpulkan "tidak ada" dari 0 baris tanpa mendaftar nilai milik sistem itu sendiri.

## Rute

- Segmen punya kode / pertanyaan menyebut varian spesifik → **TURUN** `11-kode-segmen.md`
- Segmen teks bebas, perlu probe → **TURUN** `12-nama-kategori.md`
- Pertanyaan juga menyebut negara / asal / impor / lokal → **SEBERANG** `60-asal-produksi.md`
- Pertanyaan juga menyebut kemasan → **SEBERANG** `40-kemasan.md`
- Segmennya BTP (pewarna, pengawet, perisa) → **SEBERANG** `70-btp.md`
- Probe memberi 0 baris di satu sistem → itu namespace, bukan ketiadaan; daftar nilai sistem itu
  (`SELECT DISTINCT <kolom>, COUNT(*) … GROUP BY 1`) sebelum menyimpulkan apa pun.
