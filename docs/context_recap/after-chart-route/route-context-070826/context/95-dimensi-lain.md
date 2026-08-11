Dimensi lain — kolom yang tidak diatur halaman mana pun: cara menemukannya, plus peruntukan & pengolahan

Halaman-halaman lain menamai perangkap, bukan setiap kolom. Database punya **152 kolom**; dimensi
yang tidak tercantum di mana pun **bukan berarti tidak ada di data** — temukan sebelum jatuh ke
kolom yang sudah dikenal.

## Prosedur menemukan dimensi

**1. Kolomnya ada di mana?** `describe_table`.
`t_produk_3_rilis_erla` adalah **subset murni** `t_produk_3_erba`: 94 kolom beririsan, **0** kolom
hanya-ERLA, dan hanya **6** kolom hanya-ERBA —
`ecolabel` · `jenis_penolakan_komitmen` · `kode_kbli` · `sni_sukarela` · `status_komitmen` ·
`sub_kemasan_id`. Kolom yang ada di satu sistem saja membuat pertanyaan **single-system secara
struktural**; sebut sistemnya, jangan menyiratkan keduanya menyumbang.

**2. Berkode atau teks bebas?** Kode telanjang tidak berarti apa-apa. Resolusikan di
`data_dictionary` lewat **`kategori` DAN `sumber`**. Cari kategorinya dengan
`WHERE deskripsi ILIKE '%<istilah>%'`, lalu baca seluruh kategori itu.

**3. Tidak ada kategori yang cocok?** Kodenya **tidak terdokumentasi**. Laporkan sebarannya,
nyatakan artinya belum tercatat, tawarkan verifikasi ke pemilik data — dan **jangan pernah
meminjam label dari kategori lain**. Menolak menjawab sama sekali juga salah: bagian yang terhitung
memang valid.

**4. Teks bebas?** `ILIKE` untuk MENEMUKAN nilai persis, lalu hitung dengan `=`
(`10-segmen-produk.md`).

## Kode yang sama berarti hal berbeda — periksa kategorinya

`301` dan `302` masing-masing hadir di **9 kategori berbeda** (`JENIS_DOKUMEN`, `JENIS_PERMOHONAN`,
`JENIS_PRODUK_BTP`, `KATEGORI_DOKUMEN`, `KLASIFIKASI_ID`, `PEMROSESAN`, `STATUS`, `STATUS_PRODUK`,
`SUB_KEMASAN_ID`); `303`/`304` di 7. **Kolom dipilih karena maknanya, tidak pernah karena angkanya
kebetulan cocok.**

Satu label bisa memayungi beberapa kode: `STATUS` ERBA "Pendaftar - Perlu Data Tambahan" menempel
pada **5 kode**, "Pendaftar - Draft" pada 3. Ambil **semua** kode yang berbagi deskripsi itu.

## `pengolahan` ≠ `pemrosesan` — dua kolom, satu kata Indonesia

| Kolom | Kode | Dictionary | Ada di |
|---|---|---|---|
| `pemrosesan` | `300` Tanpa Proses Tertentu · `301` Organik · `302` Rekayasa Genetik (GMO) · `303` — · `304` Pangan Very Low Risk **dan** Iradiasi (dua deskripsi, tabrakan internal) | kategori `PEMROSESAN`, sumber "ERLA dan ERBA" | kedua sistem |
| `pengolahan` | `401`–`408` | **tidak ada kategori apa pun** | **keempat tabel**, tetapi rentang kode yang terpakai dan tingkat keterisiannya berbeda per tabel — periksa tiap sisi (`00-menghitung.md` §5) |

Keduanya berarti "pengolahan" dalam bahasa Indonesia. **Sebutkan kolom mana yang dipakai**, dan bila
pertanyaannya ambigu, katakan bahwa ada dua kolom bernama mirip dengan isi berbeda.
Kode `401`–`408` `pengolahan` **bertabrakan** dengan `SUB_KEMASAN_ID` (401 = Plastik/Aluminium Foil)
dan dengan `STATUS` ERLA (401 = Kepala Seksi - Proses Verifikasi Ditolak) — keduanya **salah** untuk
kolom ini. Artinya tidak dapat diketahui dari data yang ada; katakan begitu.

## Peruntukan

`peruntukan`: `0201` peruntukan **khusus** · `0000` **umum** — dua konsep berlawanan, jadi tertukar
di sini bukan meleset sedikit melainkan menjawab kebalikannya. Kedua sistem juga menyimpan kode tak
terdokumentasi (`0103`/`0104`/`0105`/`0106`, ERLA juga `010101`) yang bukan keduanya.
`SELECT peruntukan, COUNT(*) … GROUP BY 1` memperlihatkan komposisinya sebelum memilih.
Rincian dua bacaan "khusus" → `35-klasifikasi-sifat.md`.

## Celah katalog yang menghasilkan angka salah tanpa error

- **`sumber` yang sama tidak menjamin rentang kode yang sama** (`jenis_btp` → `70-btp.md`).
- **Kode ERLA disimpan tanpa zero-pad** di dictionary (`999`, `99`, `9`) sedangkan data menyimpan
  4 karakter (`0999`) — `LPAD(kode,4,'0')` sebelum memfilter, atau query mengembalikan nol.
  Beberapa `status` ERBA (`0500`, `0504`, `0417`, `0900`, `0909`, `0916`) sebenarnya terdaftar di
  blok ERLA — "tidak ada di blok ERBA" berarti "cek blok ERLA", bukan "kode tak dikenal".
- **Kode ada di data tapi tidak di dictionary** (himpunannya bergerak — periksa ulang):
  `jenis_dokumen` 304 · `peruntukan` 0103–0106 · `pemrosesan` 303/403 · `bentuk_sediaan` 214 ·
  `status_produk` 303/305 (ERLA). Bila filter akan membuang baris seperti ini (`NOT IN`,
  "lainnya"), katakan — jangan menyajikan total sebagai lengkap.
- **Kode terdaftar yang nol baris** — pertahankan di filter, jangan sajikan sebagai penyumbang.

## Rute

- Setelah dimensinya ketemu dan ternyata masuk topik lain → **KEMBALI** ke peta di `SEEKNAL_ASK.md`.
- Dimensinya teks bebas → **SEBERANG** `12-nama-kategori.md`.
- Masih dua kolom kandidat yang sama masuk akal → **KEMBALI** ke Gate 1, tanya. Jangan memilih diam-diam.
