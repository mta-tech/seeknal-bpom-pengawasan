Kode status — memetakan kode ke label, menutup set, dan menangani kode yang tak ada di dictionary

Dipakai saat tahapan yang ditanya tidak ada di tabel bucket `20-status-pipeline.md`, atau saat kode
perlu diterjemahkan ke label untuk jawaban.

## Cara mencari

```sql
SELECT kode, deskripsi, sumber FROM data_dictionary
WHERE kategori = 'STATUS' ORDER BY sumber, kode;
```

Kategorinya kecil — **baca seluruhnya**, jangan `ILIKE` lintas kategori.

## Tiga jebakan yang membuat pencarian gagal diam-diam

**1. Kode ERLA disimpan tanpa zero-pad.** Dictionary menyimpan `999`, `99`, `9`, `0`; data menyimpan
empat karakter `0999`, `0099`, `0009`, `0000`. Filter langsung dari hasil dictionary mengembalikan
**nol baris**. Pad dulu: `LPAD(kode,4,'0')`.

**2. Kolom `status` mencampur dua namespace.** Beberapa nilai yang dibawa data ERBA — `0500`,
`0504`, `0417`, `0900`, `0909`, `0916`, dan `0299` di `t_btp_3_erla` — sebenarnya terdaftar di blok
**ERLA** dan punya deskripsi resmi. "Tidak ada di blok ERBA" berarti "cek blok ERLA", **bukan**
"kode tidak dikenal". Melabelinya sebagai anomali membuang informasi yang sebenarnya tersedia.

**3. Satu deskripsi menempel pada beberapa kode.** "Pendaftar - Perlu Data Tambahan" = **5 kode**
(`0901`,`0914`,`0915`,`0917`,`0951`) · "Pendaftar - Draft" = 3 (`0900`,`0910`,`0912`) ·
"Pendaftar - Proses Verifikasi Ditolak" = 3 (`0905`,`0909`,`0916`). Hasil pencarian label
**tampak seperti duplikat padahal bukan** — masing-masing membawa populasinya sendiri.
Ketika deskripsi berulang, **ambil SEMUA kode yang berbagi deskripsi itu**.

## Batas ketertutupan — melebar sama salahnya dengan menyempit

"Ditolak Sistem" (`0908`,`0911`,`0918`) dan "Ditolak petugas" (`0902`,`0905`,`0913`) berbagi kata
*ditolak* tetapi populasinya berbeda. Menggabungkannya karena stringnya mirip menghasilkan angka
yang tidak ditanya siapa pun. **Daftar bucket di `20-status-pipeline.md` adalah tepi setnya, bukan
kata kuncinya** — dan daftar itu menang atas hasil pencarian dictionary.

## Nilai yang tidak akan pernah muncul di dictionary

`status` kosong ERBA tersimpan sebagai **empat spasi** — bukan NULL, bukan `''`.
`TRIM(status)=''` menangkapnya; `status <> ''` tidak. Ini nilai terbesar yang terserap bucket
`NOT IN`; sebutkan saat menyajikan total `NOT IN`.

## Rute

- **KEMBALI** ke `20-status-pipeline.md` setelah kodenya teresolusi — bucket dan aturan bentuk
  jawabannya ada di sana.
- Kode ternyata milik kolom lain (bukan `status`) → `95-dimensi-lain.md`; nilai `301`/`302` hadir di
  **9 kategori berbeda**.
