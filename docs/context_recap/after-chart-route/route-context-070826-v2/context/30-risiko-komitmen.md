Risiko & komitmen — kategori risiko, menengah rendah/tinggi, MR, MT, komitmen, pemenuhan, dibatalkan, disetujui

**Komitmen** ERBA-only secara struktural (`status_komitmen`, `jenis_penolakan_komitmen` hanya ada di
`t_produk_3_erba`) — nyatakan batas itu. **Risiko TIDAK begitu**; baca bagian di bawah sampai habis.

## Risiko — DUA kolom, DUA skema, dan kodenya TIDAK sepadan

Ini jebakan paling mahal di database ini. Risiko hidup di kolom yang berbeda per sistem, dan
nomor kode yang sama **menunjuk kelas yang berbeda**.

| | Kolom | `sumber` di dictionary | Kode |
|---|---|---|---|
| **ERBA** | `kategori_dokumen` | **ERBA saja** | `301` Tinggi · `302` Menengah Tinggi · `303` Menengah Rendah · `304` Tinggi Notifikasi |
| **ERLA** | `jenis_dokumen` | **ERLA dan ERBA** | `000` Belum Dikategorikan · `301` Pangan Low Risk · `302` Pangan High Risk · `303` Pangan Medium Risk |

⚠️ **`kategori_dokumen` ADA dan TERISI di keempat tabel — termasuk ERLA.** Itu bukan izin memakainya.
Dictionary mencatat kategorinya bersumber **ERBA saja**, jadi nilai `301`–`304` di sisi ERLA
**bukan** skema risiko BPOM. Meng-UNION-nya menjumlahkan dua skema berbeda dan menghasilkan angka
yang tidak berarti apa pun — tanpa error, dengan hasil yang terlihat wajar.

**Jangan pernah menaruh `kategori_dokumen` dan `jenis_dokumen` dalam satu query.**

### Padanan antar skema — 3 kelas, bukan 4

Kedua kolom hidup berdampingan di `t_produk_3_erba`, jadi padanannya adalah fakta struktural yang
bisa diturunkan sendiri (`GROUP BY kategori_dokumen, jenis_dokumen` di ERBA), bukan tebakan:

| ERBA `kategori_dokumen` | ERLA `jenis_dokumen` |
|---|---|
| `301` Tinggi | `302` Pangan High Risk |
| `302` Menengah Tinggi | `303` Pangan Medium Risk |
| `303` Menengah Rendah | `301` Pangan Low Risk |
| `304` Tinggi Notifikasi | **tidak punya padanan bersih** — sebut sebagai kelas khusus ERBA |

Perhatikan `301` dan `303` **bertukar arti** antar skema. Memakai kode ERBA di ERLA tidak memberi
error — ia memberi kelas yang salah. Skema ERLA hanya punya tiga tingkat, jadi "Tinggi Notifikasi"
tidak bisa dipisahkan di sana.

### LINGKUP — default ERBA, dinyatakan; jangan bertanya, jangan menggabung diam-diam

Skema risiko BPOM adalah skema ERBA. Karena itu:

| Pertanyaan | Lakukan |
|---|---|
| Risiko, sistem tidak disebut | **Jawab ERBA** dan **katakan** bahwa skema risiko ini milik ERBA. Jangan `request_clarification` — lingkupnya sudah ditentukan skemanya sendiri |
| Menyebut ERLA / "gabungan" / "nasional" secara eksplisit | Pakai `jenis_dokumen` di sisi ERLA lewat tabel padanan, sajikan **per sisi berlabel**, dan sebutkan bahwa kedua sistem memakai skema berbeda |

Yang dilarang bukan menjawab ERBA — itu default yang benar. Yang dilarang adalah **menggabungkan
tanpa padanan** (`kategori_dokumen` dua sisi) dan **menyajikan angka ERBA sebagai angka nasional
tanpa menyebut batasnya**.

- Pertanyaan yang menyentuh KELUARGA risiko melaporkan tiap kelas sebagai angka berlabel sendiri.
  **Jangan melebarkan satu kelas yang diminta ke tetangganya** — "produk MR" = Menengah Rendah saja.
- "Risiko Tinggi" di skema ERBA = `IN ('301','304')` — Tinggi mencakup Tinggi Notifikasi.
- MR/MT adalah singkatan resmi BPOM untuk Menengah Rendah/Menengah Tinggi. Tulis lengkap minimal
  sekali; "Medium Risk" saja menghilangkan perbedaan Rendah/Tinggi, dan di skema ERLA
  "Medium" justru padanan Menengah **Tinggi**.

## Komitmen — kolom `status_komitmen`

**Format ganda.** Tersimpan TEXT campuran: sebagian `'5'`, sebagian `'5.0'` untuk nilai logis yang sama.

```sql
WHERE status_komitmen = '5'                              -- SALAH, kehilangan baris '5.0'
WHERE ROUND(status_komitmen::numeric)::int::text = '5'   -- BENAR
WHERE status_komitmen LIKE '5%'                          -- BENAR, lebih ringkas
```
Kode terdampak: `0, 1, 4, 5, 7, 8, 9`. Normalisasi berlaku untuk **setiap** filter `status_komitmen`.

**"Disetujui" kanonik = `4` + `7` digabung**, tetapi jawaban SELALU menampilkan pecahan berlabel:
`4` Komitmen Disetujui (murni) · `7` Komitmen Disetujui Dengan Catatan · gabungan sebagai jumlah
berlabel. Kode `8` (Validasi Pembatalan) transien menuju `5` — cantumkan tanggal bila memakainya.

**Alasan penolakan komitmen** — `jenis_penolakan_komitmen` (ERBA-only, kode 1–10) **bernilai jamak**,
dipisah pipe (`'1|3'`). Cocokkan dengan `string_to_array(kolom,'|') @> ARRAY['<kode>']`,
**tidak pernah dengan kesamaan biasa** — kesamaan biasa kehilangan setiap baris berkombinasi.
Untuk peringkat alasan: `unnest(string_to_array(jenis_penolakan_komitmen,'|'))` lalu `GROUP BY`.

## Dua bacaan komitmen — putuskan dari SUBJEK, sebelum menulis SQL

| Bacaan | Pemicu | Filter |
|---|---|---|
| **A — NIE berstatus komitmen X** | pertanyaan menyebut "NIE"/"izin edar" sebagai yang DIHITUNG | pertahankan SEMUA filter NIE (status, jenis_permohonan) **dan** tambahkan filter `status_komitmen` |
| **B — permohonan yang komitmennya [hasil]** | pertanyaan menanyakan berapa yang "dibatalkan/ditolak/disetujui" sebagai hasil daur hidup | **LEPAS** filter `status` NIE sah dan `jenis_permohonan` |

Alasannya struktural, bukan angka: **sebagian besar peristiwa komitmen terjadi sebelum NIE terbit**,
jadi populasi bacaan B sebagian besarnya belum punya NIE. Mensyaratkan status NIE aktif di situ
menyaring habis populasi yang justru ditanya.

Putuskan dari subjek pertanyaan, **jangan** dari besar-kecilnya hasil — memilih bacaan karena
angkanya "terlihat lebih masuk akal" adalah menyetel filter ke arah jawaban yang diharapkan.

## Rute

- Perlu arti kode `status_komitmen` yang belum terdaftar → dictionary kategori `STATUS_KOMITMEN`,
  sumber `ERBA` (jalur P2 Gate 2).
- Pertanyaan juga menyebut tahapan proses → **SEBERANG** `20-status-pipeline.md`
- Pertanyaan juga menyebut jenis permohonan → **SEBERANG** `15-permohonan.md`
- Pertanyaan berkata "belum ditetapkan kategori risikonya" → **SEBERANG** `90-kualitas-data.md`
  (itu `jenis_dokumen='000'`, dan filter status justru DILEPAS).
- Pertanyaan menyebut periode → **SEBERANG** `80-waktu-periode.md`
