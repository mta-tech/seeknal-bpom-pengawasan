Klasifikasi & sifat produk — kategori makanan, kategori minuman, berklaim, organik, diet, herbal, iradiasi, GMO, peruntukan khusus

## "Kategori makanan / minuman" ada DUA arti — pilih sebelum menulis SQL

Kata yang sama menunjuk dua kolom yang sama sekali berbeda:

| Bacaan | Kolom | Kapan |
|---|---|---|
| **Kelas berkode** (halaman ini) | `klasifikasi_id` `301`/`302` | "kategori makanan", "produk minuman", "klasifikasi", pembagian dua-kubu makanan vs minuman |
| **Segmen pangan bebas** (`10-segmen-produk.md`) | `nama_kategori` teks bebas | jenis pangan konkret: kopi, roti, AMDK, susu, mi |

Ujinya: **apakah yang diminta sebuah KELAS resmi, atau sebuah JENIS pangan?** Kelas → kolom berkode
di halaman ini. Jenis → teks bebas di `10`. `nama_kategori ILIKE '%makanan%'` bukan cara menghitung
kelas Makanan — ia memindai nama produk, bukan klasifikasinya, dan melewatkan seluruh produk yang
namanya tidak memuat kata itu.

Bila keduanya sama-sama masuk akal → Gate 1, tanya.

## `klasifikasi_id` — 13 kode, bukan 6

| Kode | Kelas |
|---|---|
| `3` | Deputi 3 (Pangan) — **bucket residual, bukan kelas bisnis** |
| `301` | Makanan |
| `302` | Minuman |
| `303` | Bahan Tambahan Pangan |
| `304` | Minuman Beralkohol |
| `305` | **Pangan Berklaim** |
| `306` | Pangan Dengan Herbal |
| `307` | Pangan Iradiasi |
| `308` | Pangan Rekayasa Genetika |
| `309` | Organik — **decoy**, lihat binding di bawah |
| `310` | Pangan Diet |
| `311` | Pangan Bayi & Anak |
| `312` | Pangan Ibu Hamil & Menyusui |

Beberapa kelas mungkin belum terisi baris sama sekali. Itu tidak menjadikannya tidak ada —
`SELECT klasifikasi_id, COUNT(*) … GROUP BY 1` menunjukkan yang mana, dan kode kosong tetap boleh
ada di filter tetapi **tidak boleh disajikan sebagai anggota penyumbang** di jawaban.

## Bucket residual — jebakan dua sisi, keduanya harus dihindari sekaligus

`klasifikasi_id='3'` "Deputi 3 (Pangan)" bukan kelas bisnis; ia unit organisasi pemilik rekaman.
Cara mengenalinya: **deskripsinya menyebut unit organisasi atau sebuah default, bukan sifat produk**,
dan cacahnya besar dibanding kelas-kelas di sekitarnya (`GROUP BY` sekali memperlihatkannya).

- **Jangan menjawab pertanyaan kelas dengan kode residual.** "Berapa produk makanan" =
  `klasifikasi_id='301'` dan tidak lebih. Melipat bucket direktorat ke Makanan menggelembungkan
  jawaban dengan rekaman yang tidak pernah diklasifikasi sebagai makanan.
- **Jangan pula menyajikan kelas-kelasnya seolah menghabiskan populasi.** Makanan + Minuman bukan
  seluruh ERBA terdaftar, karena satu blok besar duduk tak terklasifikasi di `3`.

**Jalan keluarnya:** hitung porsi residual **di query yang sama** dengan breakdown-nya, lalu
sajikan sebagai baris berlabel. Jawaban jujur soal cakupan, dan setiap angkanya tetap dari query
turn ini.

Bentuk umumnya: bila sebuah kode memegang porsi besar keluarganya **dan** deskripsinya menyebut
unit organisasi atau sebuah default (bukan kelas bisnis), perlakukan sebagai bucket residual —
bukan jawaban, bukan pula tak terlihat: **sisa berlabel**. `pemrosesan='300'` "Tanpa Proses
Tertentu" adalah kasus yang sama.

## Sifat pemrosesan — `pemrosesan`

`300` Tanpa Proses Tertentu (residual) · `301` **Organik** · `302` Rekayasa Genetik (GMO) ·
`303` — · `304` **dua deskripsi berbeda** di dictionary ("Pangan Very Low Risk" dan "Iradiasi")
— tabrakan internal; sebutkan bila memakainya.
Dikatalogkan sumber "ERLA dan ERBA".

## Peruntukan — dua bacaan sah, satu headline

`peruntukan`: `0000` umum · `0201` **khusus**. Data juga menyimpan kode non-umum tak
terdokumentasi (`0103`/`0104`/`0105`/`0106`, ERLA juga `010101`) yang bukan keduanya.

Pimpin dengan **`peruntukan='0201'`** — itu kode yang didefinisikan bisnis. Bila pertanyaan meminta
*seluruh* produk berperuntukan khusus, lampirkan "semua kecuali `0000`" sebagai angka pendamping
berlabel dan sebut kode tak terdokumentasi yang ikut terbawa. **Yang tidak boleh** adalah memilih
bacaan lebih lebar diam-diam — angkanya bergerak dan tidak ada yang menjelaskan kenapa.

## Binding tetap — jangan pernah ditukar

Sisi yang salah mengembalikan angka **masuk akal tapi salah**, bukan error:

| Konsep | Pakai | JANGAN |
|---|---|---|
| berklaim | `klasifikasi_id='305'` | kolom `klaim` (teks bebas) |
| organik | `pemrosesan='301'` | `klasifikasi_id='309'` — namanya sama, populasinya jauh berbeda |
| peruntukan khusus | `peruntukan='0201'` | `'0000'` — itu kode **umum**, kebalikan dari yang diminta |
| impor | `status_produk='302'` | `302` di kolom lain (`jenis_permohonan`=mayor, `kategori_dokumen`=Menengah Tinggi) |
| makloon / kontrak | `status_produk='304'` | kolom `status` (alur kerja) |
| ranking perusahaan | `m_trader_*.nama` lewat `trader_id` | kolom `nama_perusahaan` di tabel produk (tidak ada) |

## Rute

- Konsepnya impor / makloon / asal negara → **SEBERANG** `60-asal-produksi.md`
- Konsepnya kategori **risiko** (bukan klasifikasi) → **SEBERANG** `30-risiko-komitmen.md`
  — `kategori_dokumen` dan `klasifikasi_id` dua hal berbeda, jangan dicampur dalam satu query
- Konsepnya segmen pangan (roti, kopi, garam) → **SEBERANG** `10-segmen-produk.md`
- Kode `klasifikasi_id` nol baris ≠ tidak ada — beberapa kelas memang belum terisi; katakan begitu,
  jangan melebarkan ke kelas tetangga.
