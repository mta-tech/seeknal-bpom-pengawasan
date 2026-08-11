Cara menghitung — entity, tier status, eksklusi, cast, UNION. Berlaku untuk SETIAP pertanyaan data.

Tabel produk **berversi**: satu NIE bisa menempati banyak baris (`status='9999'` = sudah diubah).

## 1. Entity — dari SUBJEK pertanyaan, bukan dari kata bendanya

| Subjek | Hitung dengan | Tanggal kanoniknya |
|---|---|---|
| Izin edar / NIE | `COUNT(DISTINCT nomor)`, buang `nomor=''` | `tanggal` (terbit) |
| Permohonan / pengajuan / persetujuan | `COUNT(DISTINCT produk_id)` | `tanggal_bayar` |
| Perusahaan | `COUNT(DISTINCT t.trader_id)` dari **tabel produk**, bukan `m_trader_*` | — |

**Entity dan kolom tanggal adalah SATU keputusan, bukan dua.** Memilih `produk_id` lalu menyaring
dengan `tanggal` (terbit) mencampur dua populasi: yang dihitung permohonan, yang disaring peristiwa
terbit — sehingga permohonan yang belum terbit hilang dan yang terbit di periode lain ikut masuk.
Ambil sepasang dari satu baris tabel di atas, jangan dari dua baris.

- `COUNT(*)` untuk pertanyaan NIE **terlarang** — ia menghitung baris revisi, bukan entitas.
  Tidak ada filter yang menyelamatkannya. Besar penyimpangannya berbeda per tabel dan per filter;
  bila perlu diketahui, bandingkan `COUNT(*)` dan `COUNT(DISTINCT nomor)` pada filter yang sama.
- `produk_id` untuk pertanyaan NIE adalah kesalahan entity yang paling sering terjadi. Satu `nomor`
  membentang ke banyak `produk_id`, jadi menukar entity mengubah jawaban — makin lebar populasinya,
  makin besar selisihnya.
- Pada pertanyaan **permohonan**, `COUNT(*)` dan `COUNT(DISTINCT produk_id)` memberi hasil sama
  (`produk_id` unik) — jangan "mengoreksi" angka permohonan yang sudah benar.
- `tanggal_berkas`, `tanggal_diambil` = tanggal proses, tidak pernah untuk menghitung.
- Berlaku umum untuk keluarga kode mana pun, termasuk kolom yang belum terdaftar di halaman mana pun.

## 2. Dua tier status — dari KATA KERJA pertanyaan

| Tier | Pemicu | ERBA | ERLA |
|---|---|---|---|
| **Terdaftar** (pernah terbit) | "terdaftar", "total", "berapa NIE", "pernah terbit" | `IN ('0999','0906','9999')` | `IN ('0099','0999','0906','9999')` |
| **Aktif** (lebih sempit) | "aktif", "masih berlaku" | `= '0999'` | `= '0999'` |

- "saat ini" SENDIRIAN bukan pemicu aktif — "terdaftar … saat ini" tetap tier terdaftar.
- Dua tier hidup bersama → pimpin terdaftar, lampirkan aktif berlabel. Jangan menukar diam-diam.
- Jangan tambah penyempitan `tanggal_exp` kecuali diminta "masih berlaku".
- **Hanya untuk populasi NIE terbit.** Populasi yang sudah didefinisikan keadaan alur kerja lain
  (komitmen, tahapan pipeline, kualitas data) punya syarat statusnya sendiri; menumpuk set NIE sah
  di atasnya **menghapus populasi yang ditanya**, karena sebagian besarnya memang belum pernah
  terbit NIE. Tanyakan pada diri sendiri: apakah populasi ini didefinisikan oleh terbitnya NIE,
  atau oleh keadaan lain? Bila keadaan lain — jangan tumpuk.
- **Permohonan: lepas filter status sepenuhnya.**

## 3. Eksklusi WAJIB — hanya tiga, dan tidak ada yang keempat

| Apa | ERBA | ERLA |
|---|---|---|
| Akun uji | `trader_id::bigint NOT IN (5,17,50,85)` | `trader_id <> 3384` |
| `nomor` kosong | `nomor <> ''` — hanya bila entity-nya `nomor` | idem |
| `status` kosong ERBA | **empat spasi** — `TRIM(status)=''` menangkapnya, `status <> ''` tidak | — |

Akun uji hampir tak menggeser hitungan NIE, tapi menumpuk di **Draft** — pada hitungan pipeline ia
bisa mengubah kesimpulan sendirian. Terapkan selalu; sebutkan bila angka dibandingkan sumber lain.

### Uji satu kalimat sebelum menambah klausa `WHERE` apa pun

> **Apakah baris yang dibuang klausa ini bisa menjadi jawaban yang benar?**
> **Bisa → itu PENYEMPITAN, dan penyempitan hanya ada bila pertanyaan memintanya.**
> **Tidak bisa → itu eksklusi, dan boleh selalu.**

Akun uji dan `nomor` kosong lolos uji itu: keduanya bukan izin edar sungguhan, apa pun pertanyaannya.
**Kolom yang kosong tidak lolos.** Baris dengan kolom kosong tetap izin edar sungguhan yang ikut
dihitung — kecuali pertanyaannya memang tentang kolom itu.

### Kekosongan yang berkorelasi dengan makna adalah FILTER TERSEMBUNYI

Kolom yang kosongnya tidak acak bukan cacat data — ia menandai sebuah kelompok. Menyaring
"yang terisi" pada kolom seperti itu **diam-diam memfilter kelompok tersebut**, tanpa error dan
tanpa jejak di kalimat jawaban.

Contoh yang wajib diketahui: **`daerah_pabrik` kosong tepat ketika pabriknya di luar negeri.**
`WHERE daerah_pabrik IS NOT NULL` karenanya **identik dengan "produk lokal saja"** — bukan
pembersihan data. Ketiga kolom wilayah bahkan tidak seragam satu sama lain
(`50-pihak-wilayah.md` §Wilayah).

Cara mengenalinya sebelum memakai kolom apa pun sebagai penjaga: tanyakan **apa arti kosongnya**.
Bila kosong berarti "tidak berlaku bagi kelompok X" — bukan "datanya belum diisi" — maka
menyaringnya membuang kelompok X. Bila memang perlu diperiksa, silangkan keterisiannya dengan
kolom yang mendefinisikan kelompok itu, bukan dihitung sendirian.

## 4. Cast — hanya `t_produk_3_erba` (semua kolomnya TEXT)

| Kolom | Cast |
|---|---|
| `tanggal`, `tanggal_bayar`, `tanggal_exp` | `NULLIF(kolom,'')::timestamp` |
| `trader_id` | `::bigint` |
| `status_komitmen` | `ROUND(...::numeric)::int::text` |

⚠️ **Per TABEL, bukan per sistem.** Di `t_btp_3_erba` tanggal sudah `timestamp` dan `trader_id`
sudah `bigint` — membawa cast produk ke sana **menggagalkan query** dan menghabiskan satu-satunya
retry. `t_produk_3_rilis_erla` & `t_btp_3_erla` native, tanpa cast. PostgreSQL saja: tidak ada
`TRY_CAST`/`SAFE_CAST`.

## 5. UNION ERBA + ERLA

```sql
SELECT nomor, tanggal::timestamp AS tanggal, trader_id::bigint AS trader_id
FROM t_produk_3_erba
WHERE tanggal IS NOT NULL AND tanggal <> ''
  AND status IN ('0999','0906','9999')
  AND trader_id::bigint NOT IN (5,17,50,85)
  AND tanggal::timestamp >= '{Y}-01-01' AND tanggal::timestamp < '{Y+1}-01-01'
UNION ALL
SELECT nomor, tanggal, trader_id
FROM t_produk_3_rilis_erla
WHERE status IN ('0099','0999','0906','9999')
  AND trader_id <> 3384
  AND tanggal >= '{Y}-01-01' AND tanggal < '{Y+1}-01-01'
```

WHERE **terpisah per sisi** — set status, akun uji, dan cast memang berbeda. `nomor` tidak
beririsan antar sistem, `UNION ALL` aman.

### Sebelum UNION: empat cara konsep yang sama bisa berbeda antar sistem

**Kolom bernama sama tidak menjamin makna sama.** Empat keadaan, masing-masing menghasilkan angka
salah tanpa error:

| Keadaan | Tandanya | Yang benar |
|---|---|---|
| **Kolomnya tidak ada** di satu sisi | `information_schema` | Pertanyaan itu single-system **secara struktural** — jawab untuk sisi yang punya, nyatakan batasnya. Jangan sajikan sebagai angka nasional |
| **Ada tapi hampir kosong** | keterisian timpang | Sisi itu kemungkinan memakai **kolom lain** untuk konsep yang sama — cari kandidatnya sebelum menyimpulkan |
| **Rentang kodenya berbeda** | nilai dari satu sisi selalu 0 di sisi lain | Namespace terpisah. 0 berarti **kode salah sistem**, bukan "konsepnya tidak ada". Resolusikan tiap sisi pada nilainya sendiri |
| **Ada, terisi, kode mirip — tapi SKEMANYA lain** | tidak ada tanda sama sekali | **Yang paling berbahaya.** Query jalan, angka masuk akal, hasilnya penjumlahan dua skema berbeda. Lihat `30-risiko-komitmen.md` |

Keadaan keempat tidak bisa dideteksi dari keterisian atau dari cacah baris — hanya dari
**deskripsi dictionary**. Sebelum meng-UNION kolom berkode, pastikan `sumber`-nya di
`data_dictionary` mencakup **kedua** sistem. Bila `sumber` hanya menyebut satu sistem, kolom itu
**bukan** kolom yang sama di sisi lain meski namanya sama dan datanya terisi.

Aturan penutupnya: **sebelum melaporkan 0 atau "tidak ada" untuk satu sistem, daftar dulu nilai
milik sistem itu sendiri** — dan sebelum menjumlahkan dua sisi, pastikan keduanya memakai skema yang sama.

## 6. Bentuk angka & eksekusi

- **Headline dari `COUNT(DISTINCT …)` global sendiri, tanpa `GROUP BY`.** Jangan menjumlahkan
  partisi bila satu entitas bisa muncul di lebih dari satu partisi — itu terjadi pada kolom
  versioned (periode, `status`, sistem, keluarga kode), karena satu `nomor` berulang lintas revisi.
  Ujinya sederhana: apakah satu `nomor` bisa punya lebih dari satu nilai di kolom pengelompok itu?
  Bisa → ambil cacah global dan katakan bagian-bagiannya tidak harus berjumlah sama. Kolom yang satu
  entitas hanya punya satu nilai pada satu waktu (`status_komitmen`) boleh dijumlahkan.
- Satu statement per panggilan, tanpa `;`.
- **Jangan `EXTRACT(YEAR …)` untuk memfilter** — memaksa transfer seluruh tabel. Pakai rentang
  berbatas; `EXTRACT` hanya untuk melabeli hasil yang sudah dikelompokkan.
- `ILIKE '%…%'` memindai seluruh kolom — pakai sekali untuk **menemukan** nilai, lalu hitung
  dengan `=` pada nilai itu.

## Rute

- Konsep berkode belum teresolusi → **kembali** ke peta halaman di `SEEKNAL_ASK.md`.
- Menyebut periode / tren / masa berlaku → **seberang** `80-waktu-periode.md`.
- Berkata "belum / tanpa / kosong / belum ditetapkan" → **seberang** `90-kualitas-data.md`
  (di sana filter status justru DILEPAS).
- Menyentuh tabel yang belum di-query turn ini → cek tipe di `data_architecture.md` atau
  `describe_table` sebelum menulis cast.
