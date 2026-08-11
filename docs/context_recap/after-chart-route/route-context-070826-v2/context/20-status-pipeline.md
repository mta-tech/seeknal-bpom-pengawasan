Tahapan proses — draft, bayar, verifikasi, evaluator, direktur, ditolak, dicabut, antrian, nyangkut, bottleneck

Populasi tahapan didefinisikan **kode statusnya sendiri**. Menumpuk set NIE sah di atasnya
menghapus populasi yang ditanya (`00-menghitung.md` §2).

| Tahapan | Kode ERBA |
|---|---|
| Evaluator | `0301, 0308` |
| Verifikator 1 | `0402, 0403, 0405, 0406, 0407, 0417` |
| Verifikator 2 | `0500, 0502, 0504` (persis ini; `0501, 0503` tak berbaris di ERBA) |
| Direktur | `0600, 0601, 0666` |
| Deputi / Kepala Badan | `0700` / `0800` |
| Draft | `0910, 0912` |
| Bayar (menunggu SPB/HPR) | `0903, 0907` |
| Data Tambahan | `0308, 0402, 0407` (petugas) **+** `0901, 0914, 0915, 0917, 0951` (pendaftar) — **selalu kedua grup** |
| Ditolak Sistem | `0908, 0911, 0918` |
| Ditolak lainnya (penerimaan/verifikasi) | `0902, 0905, 0913` |
| Terbit / Perubahan / Sudah Diubah | `0999` / `0906` / `9999` |
| Dibatalkan / Dicabut / Tidak Berlaku | `0000, 0009, 0099` |

**Daftar di atas menang atas hasil pencarian dictionary.** Deskripsi dictionary berulang di beberapa
kode — "Pendaftar - Perlu Data Tambahan" menempel pada **5 kode sekaligus**, "Pendaftar - Draft"
pada 3. Mengambil satu kode dari label yang berulang kehilangan sisanya tanpa suara.

## Istilah pengguna → bucket: yang jelas, dan yang WAJIB ditanya

Nama tahapan di tabel bukan kata yang dipakai orang. Petakan lebih dulu, jangan menebak dari
kemiripan kata:

| Istilah pengguna | Bucket |
|---|---|
| "di direktur", "menunggu tanda tangan" | Direktur |
| "draft", "belum disubmit" | Draft |
| "menunggu bayar", "belum bayar" | Bayar |
| "minta data tambahan", "dikembalikan ke pendaftar" | Data Tambahan (**kedua grup**) |
| **"menunggu verifikasi", "di verifikasi", "tahap verifikasi"** | **AMBIGU — Gate 1, tanya** |

**"Verifikasi" adalah dua tahapan berurutan, bukan satu.** Verifikator 1 dan Verifikator 2 adalah
antrian terpisah dengan petugas berbeda; besarnya jauh berbeda. Menjumlahkan keduanya dan
menjumlahkan salah satunya adalah dua jawaban yang berbeda — dan tak satu pun bisa disebut default.
Tanyakan mana yang dimaksud, atau **sajikan ketiganya berlabel** (Verifikator 1 · Verifikator 2 ·
gabungan) bila klarifikasi tidak mungkin.

Aturan umumnya: **bila satu istilah pengguna memetakan ke lebih dari satu bucket dalam daftar di
atas, itu Gate 1** — bukan alasan untuk memilih yang terbesar atau yang pertama.

## Tabel mana

- **Pipeline produk: `t_produk_3_erba` saja** — `t_produk_3_rilis_erla` hanya menyimpan keadaan final.
- **Pipeline BTP: KEDUA** `t_btp_3_erba` DAN `t_btp_3_erla` — tabel BTP ERLA memang membawa keadaan
  hidup. Set kodenya lebih kecil: `t_btp_3_erba` tanpa `0009`; `t_btp_3_erla` tanpa `0099` dan
  membawa `0299`; dari trio Verifikator 2 hanya `0502` yang muncul. Jangan menyalin daftar tahapan
  antar tabel tanpa memeriksa.
- "Permohonan/produk" dalam pertanyaan pipeline ambigu soal BTP → sajikan **dua angka berlabel**
  (produk-saja dan produk+BTP, masing-masing dengan tabel sumbernya), atau nyatakan lingkup yang
  dipakai dan alasannya.

## Aturan bentuk

- **Pertahankan setiap kode tahapan, termasuk yang kosong** (`0402`, `0406`, `0601`, `0666`,
  `0700`, `0905` saat ini nol baris). Biaya nol dan tahan bila nanti terisi — tetapi **jawaban**
  tidak boleh menampilkan kode kosong sebagai tahapan penyumbang; sebutkan kode mana yang membawa baris.
- **Bucket `NOT IN` menyerap baris yang tak diklaim tahapan mana pun**: kode langka
  `000X, 0417, 0900, 0909, 0916`, dan yang terbesar — baris ber-`status` **empat spasi**
  (`TRIM(status)=''`, yang `status <> ''` tidak tangkap). Sebutkan penyerapan ini saat menyajikan total `NOT IN`.
- "Sedang di tahapan X" adalah potret sesaat — cantumkan tanggal per-nya.
- **"Sedang diproses (petugas)"** = Evaluator + Verifikator 1/2 + Direktur/Deputi/Kepala Badan +
  Data Tambahan. **"Belum selesai (total)"** = semua yang `NOT IN` keadaan terminal (Terbit/
  Perubahan/Sudah Diubah + Dibatalkan/Dicabut/Tidak Berlaku) — bacaan lebih lebar, termasuk
  Draft/Bayar sisi pendaftar. Pimpin dengan yang pertama dan **selalu** lampirkan yang kedua
  sebagai SATU angka berlabel dari query `NOT IN`-nya sendiri. Keduanya bukan varian satu sama lain:
  bacaan kedua mencakup seluruh antrian sisi pendaftar yang tidak masuk bacaan pertama.
- **"Nyangkut / bottleneck / paling menumpuk"** = peringkatkan TAHAPAN dengan SATU `GROUP BY` atas
  bucket, lalu sebut yang terbesar — tidak pernah satu kode yang dipilih tangan.

## Dicabut ≠ kedaluwarsa — tiga kode yang terus tertukar

| Kode | Arti | Kelas |
|---|---|---|
| `0000` | Dihapus | **TERMINASI** — tindakan otoritas |
| `0009` | Dicabut / Dibatalkan | **TERMINASI** — tindakan otoritas |
| `0099` | Tidak Berlaku | **MASA BERLAKU** — habis sendiri, bukan dicabut |
| `9999` | Sudah Diubah | **VERSI** — digantikan revisi lebih baru, bukan dicabut |

"Dicabut / dibatalkan / diterminasi" = `0000` + `0009` **saja**. Ketiga kode lain menjawab
pertanyaan yang berbeda: `0099` menjawab "kedaluwarsa", `9999` menjawab "direvisi".

**Sebelum mengirim query pencabutan, baca ulang set kodenya.** Bila `0099` ada di dalamnya dan
pertanyaannya tidak menyebut kedaluwarsa, buang. Ini aturan yang paling sering diketahui tetapi
tidak diterapkan — mengetahuinya tidak cukup, set kodenya harus benar-benar diperiksa di teks SQL
sebelum dieksekusi.

## Lingkup produk vs produk+BTP — nyatakan sebelum menghitung

Aturan tabelnya ada di bagian "Tabel mana" di atas, tetapi kegagalan yang terjadi bukan karena tidak
tahu — melainkan karena lingkupnya tidak pernah **diputuskan secara sadar**. Sebelum query pipeline
apa pun: tuliskan lingkupnya (produk-saja / produk+BTP), lalu pastikan tabel yang muncul di `FROM`
cocok dengan yang dituliskan. Bila pertanyaan tidak menyebutnya, produk-saja adalah default —
dan default itu **harus dinyatakan di jawaban**, bukan diam-diam.

## Rute

- Perlu memetakan kode ke label / mencari tahapan yang tak terdaftar → **TURUN** `21-kode-status.md`
- Pertanyaan menyebut risiko atau komitmen → **SEBERANG** `30-risiko-komitmen.md`
- Pertanyaan menyebut periode/tren → **SEBERANG** `80-waktu-periode.md`
- Akun uji menumpuk di Draft — eksklusi wajib, dan di sini ia bisa mengubah kesimpulan
  (`00-menghitung.md` §3).
