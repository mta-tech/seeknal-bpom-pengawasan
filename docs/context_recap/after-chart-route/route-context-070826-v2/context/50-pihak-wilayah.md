Pihak & wilayah — perusahaan, pendaftar, pabrik, produsen, importir, industri, KBLI, skala, daerah, provinsi

## Tiga pihak yang berbeda — jangan tertukar

| Pihak | Kolom | Arti |
|---|---|---|
| **Pendaftar** | `nama_trader` / `trader_id` | perusahaan yang MENDAFTARKAN izin edar |
| **Pabrik** | `nama_pabrik` | tempat produk DIBUAT |
| **Produsen** | `nama_produsen` / `produsen_id` | periksa keterisiannya sebelum dipakai — sering hampir kosong |

**Peringkat ketiganya berbeda, bukan mirip.** Pemilik merek memesan produksi ke pabrik pihak ketiga
(pola makloon) — itu sebabnya pendaftar dan pabrik berpisah. Menjawab pertanyaan pabrik dengan
`nama_trader` memberi daftar nama yang **sepenuhnya lain** meski angkanya tampak masuk akal.

Cara memastikan kolom mana yang dimaksud: jalankan peringkatnya pada kedua kolom sekali, dan lihat
apakah nama-namanya berbeda. Berbeda → pertanyaan memang membedakan keduanya; sebut kolom yang dipakai.

Pabrik luar negeri ikut terhitung dan itu benar bila pertanyaan tidak membatasi negara. Untuk
membatasi ke dalam negeri perlu `negara_pabrik` → `60-asal-produksi.md`.

## Nama diformat BERBEDA antar sistem — periksa, lalu normalisasi

Satu sistem menyimpan nama badan usaha **dengan** prefiks bentuk hukum ("PT. …"), sistem lain
**tanpa** prefiks. Perusahaan yang sama karenanya muncul sebagai dua entri berbeda saat digabung.

Periksa dulu, jangan diasumsikan arahnya:
```sql
SELECT '<sistem>' sys, COUNT(*) FILTER (WHERE nama_trader ~* '^PT[. ]') berprefiks,
       COUNT(*) total FROM (SELECT DISTINCT nama_trader FROM <tabel itu>) x;
```

Bila kedua sisi berbeda pola, normalisasi **sebelum** `GROUP BY` lintas sistem:
```sql
regexp_replace(upper(btrim(nama_trader)), '^PT\.?\s+', '')
```

Tanpa normalisasi, satu perusahaan terpecah dua dan peringkatnya **salah urut** — bukan sekadar
kurang rapi, karena entri yang terpecah bisa kalah dari entri yang tidak terpecah.

**`trader_id` TIDAK berlaku lintas sistem.** Perusahaan yang sama memakai id yang berbeda di tiap
sistem — id-nya milik sistemnya, bukan milik perusahaannya. `COUNT(DISTINCT trader_id)` atas UNION
karenanya menghitung setiap perusahaan **dua kali**. Di dalam SATU sistem, entity perusahaan SELALU
`trader_id`; jangan dedupe by name di dalam satu sistem (nama bertabrakan antar cabang).
Dedupe by name **hanya** untuk headline gabungan lintas sistem, dan cacah `trader_id` per-sistem
tetap ditampilkan sebagai baris berlabel di sampingnya.

## Populasi perusahaan — master atau lewat produk?

Default "berapa perusahaan skala X / produsen / importir" = **master trader**
(`m_trader_rba` / `m_trader_rla`), TANPA join ke tabel produk. Join ke produk hanya bila pertanyaan
berkata "yang punya produk/NIE". Bila kedua bacaan hidup, tampilkan keduanya berlabel
("terdaftar: X · punya produk: Y") — angka master **wajib** muncul.

`is_status_industri_produsen` / `is_status_industri_importir` di `m_trader_rba` bertipe TEXT
`'1'`/`'0'` (bukan boolean), entity `trader_id`. **ERBA-only secara struktural** — `m_trader_rla`
tidak punya kolom ini, jadi tidak ada angka ERLA dan tidak ada angka gabungan. Nyatakan batas itu.

⚠️ **Peran BUKAN saling meniadakan.** Satu perusahaan bisa produsen **dan** importir sekaligus —
keduanya flag terpisah, bukan satu kolom berkategori.

```sql
COUNT(*) FILTER (WHERE is_status_industri_produsen='1') AS produsen,   -- BENAR
COUNT(*) FILTER (WHERE is_status_industri_importir='1')  AS importir
```
```sql
CASE WHEN is_status_industri_produsen='1' THEN 'Produsen'              -- SALAH
     WHEN is_status_industri_importir='1'  THEN 'Importir' END
```

Rantai `CASE WHEN` memberi baris berperan ganda **hanya ke cabang pertama**, sehingga kelompok kedua
kurang hitung diam-diam. Bila totalnya perlu disajikan, sebutkan bahwa jumlah per peran melebihi
cacah perusahaan karena tumpang tindih — jangan "merapikannya" dengan membuat peran eksklusif.

**Berlaku umum untuk setiap kolom berflag `'1'`/`'0'`** di database ini, bukan hanya dua kolom ini.
Tandanya: beberapa kolom boolean berdampingan untuk satu konsep. Hitung tiap flag independen.
`status_usaha` (`31` produsen · `33` importir) di tabel produk menghitung **PRODUK**, bukan
perusahaan — pakai hanya bila subjeknya memang produk.

## Bidang usaha vs skala industri — dua hal berbeda

| Konsep | Kolom | Catatan |
|---|---|---|
| **Bidang usaha (KBLI)** | `kode_kbli` pada **`t_produk_3_erba` / `t_btp_3_erba`** | tabel trader TIDAK punya kolom ini — query ke sana error. Menghitung PRODUK per bidang usaha; untuk menghitung perusahaan, agregasikan ke `trader_id` dan katakan |
| **Skala industri** | `m_trader_rba.skala_industri_id` / `m_trader_rla.skala_industri` (nama kolom berbeda) | `1` mikro · `2` kecil · `3` menengah · `4` besar; UMKM = 1+2+3 |

Pertanyaan "industri apa yang paling banyak mendaftarkan" berarti **bidang usaha (KBLI)**, bukan
skala. Menjawabnya dengan skala memberi "Besar/Menengah/Kecil" — kategori yang benar untuk
pertanyaan lain. Bila ragu mana yang dimaksud, keduanya jawaban yang sah untuk pertanyaan berbeda →
Gate 1, tanya.

**Sentinel KBLI.** `kode_kbli` menyimpan `'0'` sebagai penanda belum diisi — tidak terdaftar di
dictionary dan bukan bidang usaha, tetapi bisa **memuncaki peringkat**. Kenali sentinel dari sifatnya
(tidak punya baris dictionary, atau deskripsinya kosong/`-`), bukan dari besar cacahnya. Kecualikan
`'0'` dan `''` dari peringkat; sebut terpisah sebagai catatan kualitas data.

**Skala kosong berarti Importir**, dan disimpan berbeda di tiap sistem (satu memakai spasi, satu
memakai string kosong/NULL). Selalu `COALESCE(NULLIF(TRIM(kolom::text),''),'Importir')` — jangan
pernah `GROUP BY` kolom mentah, karena kategori "Importir" akan pecah menjadi dua baris kosong
yang berbeda.

## Wilayah — tiga kolom yang TIDAK berperilaku sama

`daerah_trader` · `daerah_pabrik` · `daerah_produsen` · `kotakab_id`. Dictionary menyimpan bentuk
**bertitik** (`31.75`), kolomnya **tanpa titik** (`3175`) — join dengan `REPLACE(kode,'.','')`.
Kategorinya hanya memuat kabupaten/kota, sehingga **`provinsi_id` tidak punya baris sendiri** dan
sebagian `kotakab_id` jatuh di luarnya — laporkan wilayah tak terpetakan, jangan dibuang.

**Pilih kolomnya dari pihak yang ditanya**, dan ketahui arti kosongnya — ketiganya berbeda:

| Kolom | Wilayah siapa | Arti kosong |
|---|---|---|
| `daerah_trader` | pendaftar | terisi merata; kosongnya tidak menandai kelompok apa pun |
| `daerah_pabrik` | tempat produksi | **kosong tepat ketika pabriknya di luar negeri** |
| `daerah_produsen` | produsen | jarang terisi di kedua kelompok — sebagian besar populasi tidak punya nilai |

⚠️ **`daerah_pabrik IS NOT NULL` adalah filter "produk lokal saja" yang menyamar sebagai
pembersihan data.** Menaruhnya di query yang tidak menanyakan wilayah membuang seluruh produk impor
tanpa error dan tanpa jejak di kalimat jawaban. Bila yang dimaksud memang lokal, filter yang jujur
adalah `negara_pabrik` (`60-asal-produksi.md`) — bukan keterisian wilayah.

**Karena itu penjaga `daerah_* <> 'NULL' / <> '9999'` bersifat BERSYARAT, bukan wajib.** Pakai hanya
ketika pertanyaannya memang mengelompokkan atau menyaring wilayah, dan hanya pada kolom pihak yang
ditanya. Uji "eksklusi vs penyempitan" ada di `00-menghitung.md` §3.

## Rute

- Pertanyaan menyebut negara asal / impor / lokal → **SEBERANG** `60-asal-produksi.md`
- Pertanyaan menyebut segmen produk ("perusahaan yang mendaftarkan kopi instan") →
  **SEBERANG** `10-segmen-produk.md`, lalu AND-kan keduanya dalam satu WHERE
- Entity: perusahaan → `trader_id` **dalam satu sistem**; lintas sistem → nama ternormalisasi
  (`00-menghitung.md` §1)
- Kolom pihak/wilayah lain yang tidak ada di sini → `95-dimensi-lain.md`
