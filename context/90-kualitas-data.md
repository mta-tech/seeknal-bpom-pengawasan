Kualitas data — sentinel, kekosongan bermakna, dan teks bebas.

## 1. ⚠️ Tabel fakta domain ini TIDAK punya SQL NULL sama sekali

Setiap kolom di tabel fakta terisi — yang tampak "kosong" sebenarnya **nilai teks penanda kosong**.

| Bentuk sentinel | Di mana |
|---|---|
| **string penanda** empat huruf | tiga kolom vonis |
| **string kosong** | media, pembuat iklan, nomor surat, pendaftar |
| **tanda hubung** (satu atau dua) | nomor surat, NIE |

> **`WHERE kolom IS NULL` selalu mengembalikan nol baris di tabel fakta ini.** Ini jebakan nomor
> satu di domain ini, dan ia tidak memunculkan error apa pun.

Tabel pendamping (log, timeline) **punya** SQL NULL pada sebagian kolom — jadi aturannya berbeda
antar tabel. Periksa per kolom, jalur **P2**.

Domain BPOM lain memakai ejaan sentinel yang berbeda lagi; jangan menyalin aturan dari sana
(`95-batas-domain.md`).

## 2. Kekosongan yang berkorelasi dengan makna = FILTER TERSEMBUNYI

Kolom yang kosongnya **tidak acak** menandai sebuah kelompok. Menyaring "yang terisi" pada kolom
seperti itu **diam-diam memfilter kelompok tersebut**.

Yang berperilaku begitu di domain ini:

| Kolom | Kosongnya berarti |
|---|---|
| `kesimpulan_penilaian_akhir` | komoditi yang tidak memakai kolom akhir — `30-vonis.md` |
| `jenis_pembuat_iklan` | komoditi selain yang merekamnya — `20-media-dan-iklan.md` |
| `kesimpulan_penilaian_pusat` | pusat belum menilai |
| kolom tanggal di timeline | tahap itu belum tercapai — `60-waktu-dan-durasi.md` |

**Cara mengenalinya pada kolom baru:** tanyakan **apa arti kosongnya**. Bila kosong berarti "tidak
berlaku bagi kelompok X", menyaringnya membuang kelompok X. Silangkan keterisiannya dengan
`komoditi` — satu query.

## 3. Teks bebas

`lokasi_iklan`, `nama_produk`, dan `pendaftar` diisi bebas. `lokasi_iklan` nyaris unik per baris
dan sebagian sangat panjang — **jangan dikelompokkan**. `pendaftar` memuat string tergandakan yang
melebihkan cacah perusahaan (`50-produk-dan-pendaftar.md`).

Pola kerja: `ILIKE` **sekali** untuk menemukan (jalur **P3**), lalu hitung dengan nilai persis.

## 4. Populasi log dan timeline lebih luas dari fakta

Keduanya memuat id yang tidak ada di tabel fakta. Sifat id tambahan itu **belum dipastikan** —
jangan menyimpulkan sebabnya. Perlakukan sebagai populasi berbeda dan selalu join dari fakta
(`45-status-dan-alur.md`).

## 5. Label status tidak lengkap

Blok kode penolakan **tidak punya label**. Mengelompokkan alur berdasarkan label akan menyembunyikan
seluruh penolakan — pakai langkah alur (`trx_steps`) untuk mengenalinya.

## 6. Kolom "durasi" yang bukan durasi

Salah satu kolom selisih di timeline hanya bernilai beberapa kemungkinan — ia penanda, bukan
jumlah hari (`60-waktu-dan-durasi.md`). Periksa sebaran nilai kolom durasi mana pun sebelum
meratakannya.

## 7. Schema `dimension`

Database ini punya schema kedua berisi proyeksi nilai distinct. **Isinya tidak sinkron** dengan
tabel utama — ia melewatkan nilai baru tanpa error. **Jangan memakainya untuk menemukan nilai.**

## 8. Menyebutkan cakupan di jawaban

Bila kolom yang dipakai hanya terisi untuk sebagian komoditi atau sebagian tahap, **sebutkan
porsinya sebelum menyajikan peringkat atau persentase**. Satu baris kalimat cukup.

## Rute

- Kembali ke aturan hitung → **naik** ke `00-menghitung.md`.
- Menyebut batas domain → **seberang** `95-batas-domain.md`.
