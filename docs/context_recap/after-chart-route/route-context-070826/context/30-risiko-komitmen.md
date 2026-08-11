Risiko & komitmen — kategori risiko, menengah rendah/tinggi, MR, MT, komitmen, pemenuhan, dibatalkan, disetujui

Keduanya **ERBA-only secara struktural** — kolomnya tidak ada di `t_produk_3_rilis_erla`.
Jangan menjanjikan angka nasional; nyatakan batas itu.

## Kategori risiko — kolom `kategori_dokumen`

| Konsep | Filter |
|---|---|
| Risiko Tinggi | `kategori_dokumen IN ('301','304')` — Tinggi termasuk Tinggi Notifikasi |
| Risiko Tinggi Notifikasi (bila diminta eksplisit) | `= '304'` |
| Risiko Menengah Tinggi (MT) | `= '302'` |
| Risiko Menengah Rendah (MR) | `= '303'` |

- `jenis_dokumen` (`301` Low · `302` High · `303` Medium · `000` belum dikategorikan) adalah
  **penjenisan lintas-sistem yang terpisah** — pakai hanya bila pengguna meminta pandangan itu,
  dan **jangan pernah mencampur kedua kolom dalam satu query**.
- Pertanyaan yang menyentuh KELUARGA risiko melaporkan tiap kelas sebagai angka berlabel sendiri —
  "Menengah Tinggi (`302`): X · Menengah Rendah (`303`): Y". Gabungan hanya sebagai jumlah berlabel.
  **Jangan melebarkan satu kelas yang diminta ke tetangganya** — "produk MR" = `303` saja.
- MR/MT adalah singkatan resmi BPOM untuk Menengah Rendah/Menengah Tinggi. Tulis lengkap minimal
  sekali; "Medium Risk" saja menghilangkan perbedaan Rendah/Tinggi.

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
