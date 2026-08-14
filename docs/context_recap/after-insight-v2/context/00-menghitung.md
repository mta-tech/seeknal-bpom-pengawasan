Cara menghitung — entity, grain, tanggal kanonik, eksklusi. Berlaku untuk SETIAP pertanyaan data.

Domain ini merekam **pengawasan iklan**: penilaian materi iklan produk. Bukan pemeriksaan sarana,
bukan pengujian laboratorium, bukan penandaan produk. Batasnya di `95-batas-domain.md`.

## 1. Entity — tiga tingkat, semuanya sah, semuanya berbeda

```
nomor_surat (surat pengawasan)
    └── id (event pengawasan)
            └── baris (produk yang dinilai dalam event itu)
```

| Subjek | Hitung dengan |
|---|---|
| Baris produk | `COUNT(*)` |
| Event pengawasan | `COUNT(DISTINCT id)` |
| Surat | `COUNT(DISTINCT nomor_surat)` dengan sentinel dibuang |
| Produk unik | `COUNT(DISTINCT nama_produk)` |
| NIE unik | `COUNT(DISTINCT nie)` dengan sentinel dibuang |
| Pendaftar unik | `COUNT(DISTINCT pendaftar)` — **perlu kehati-hatian**, `50-produk-dan-pendaftar.md` |

> **"Berapa jumlah pengawasan" adalah pertanyaan ambigu.** Ketiga tingkat memberi angka berbeda.
> **Tanya di Gate 1**, atau nyatakan tingkat yang dipakai di jawaban.

## 2. PENTING: Grain tidak setara antar komoditi

Satu event bisa memuat **beberapa produk** — tetapi **hanya untuk sebagian komoditi**. Untuk
komoditi lain, satu event selalu tepat satu produk.

> Karena itu **perbandingan antar komoditi memakai `COUNT(DISTINCT id)`**, bukan `COUNT(*)`.
> Memakai cacah baris memberi keunggulan semu kepada komoditi yang membawa banyak produk per event.

Cara memastikan komoditi mana yang berperilaku begitu:
`GROUP BY komoditi` dengan `count(*)` dan `count(DISTINCT id)` berdampingan — jalur **P2**.

## 3. Tanggal kanonik

`tgl_start` adalah tanggal mulai pengawasan — **default** untuk periode dan tren.
`tgl_end` adalah tanggal selesai; dipakai bila pertanyaannya tentang penyelesaian, dan dipakai
oleh kubus pra-agregasi sebagai basis periodenya.

**Entity dan kolom tanggal adalah SATU keputusan.**

PENTING: `tgl_start` memuat tanggal **di masa depan** relatif hari pengambilan data. Nilai maksimum kolom
ini **bukan** penanda kesegaran data; pakai kolom `sync` untuk itu.

## 4. Eksklusi WAJIB

| Apa | Aturan |
|---|---|
| Unit pusat pada hitungan per-balai | `nama_balai` yang berupa direktorat bukan balai |
| Sentinel pada kolom yang dihitung unik | buang sebelum `COUNT(DISTINCT ...)` |

### Uji satu kalimat sebelum menambah klausa `WHERE` apa pun

> **Apakah baris yang dibuang klausa ini bisa menjadi jawaban yang benar?**
> **Bisa itu PENYEMPITAN, dan penyempitan hanya ada bila pertanyaan memintanya.**
> **Tidak bisa itu eksklusi, dan boleh selalu.**

**Kolom yang kosong tidak lolos uji itu** — baris berkolom kosong tetap pengawasan sungguhan.

## 5. Bentuk angka & eksekusi

- **Angka utama dari query global sendiri**, bukan penjumlahan partisi.
- Satu statement per panggilan, tanpa `;`.
- **Jangan `EXTRACT(YEAR ...)` untuk menyaring** — pakai rentang berbatas. Tidak ada indeks di
  database ini.
- `ILIKE '%…%'` memindai seluruh kolom — pakai **sekali** untuk menemukan nilai, lalu hitung
  dengan nilai persis.
- **`SELECT *` bukan jawaban untuk pertanyaan rekap.** Bentuk jawaban ditentukan kata kerja
  pertanyaan: "berapa" agregat; "tren" kelompok per periode; "tampilkan data" rekap per
  dimensi yang disebut, bukan dump baris.

## 6. Tabel pendamping — arah join

| Tabel | Kunci | Arah aman |
|---|---|---|
| `mv_pengawasan_ketidaksesuaian` | `id_pengawasan` = `mv_pengawasan.id` | dari fakta, LEFT JOIN |
| `mv_pengawasan_log` | idem | **dari fakta (INNER)** — log memuat id yang tidak ada di fakta |
| `mv_pengawasan_timeline` | idem | **dari fakta (INNER)** — sama |
| `mv_pengawasan_agg` | tanpa id | jangan dijoin; lihat §7 |
| `target_balai`, `coverage_balai` | `nama_balai` | `85-target-capaian.md` |

> **Join dari sisi log atau timeline melebihi populasi pengawasan.** Keduanya memuat id yang tidak
> ada di tabel fakta. Bila jawabannya berbicara tentang populasi pengawasan, mulai dari fakta.

Ketidaksesuaian hanya melekat pada sebagian kecil event — INNER JOIN akan menjatuhkan mayoritas.

## 7. Tabel `agg` — dua syarat

`mv_pengawasan_agg` menyimpan kubus pra-agregasi dengan kolom `periode_type` bernilai dua (harian
dan bulanan). **Selalu saring satu `periode_type`**; tanpa itu angkanya tergandakan.

Kubus ini beragregasi berdasarkan **tanggal selesai**, bukan tanggal mulai. Tren dari kubus tidak
sebanding dengan tren dari fakta berbasis `tgl_start` — sebutkan basis mana yang dipakai.

## Kolom di dalam kubus

Kubus `mv_pengawasan_agg` memakai `tanggal_periode` sebagai kolom periodenya dan
`jumlah_pengawasan` sebagai cacah yang sudah diagregasi. Kolom cacah lain mengikuti pola nama yang
sama (`jumlah_`, `avg_durasi_hari`, `min_`, `max_`).

Aturan pemakaiannya tetap seperti di atas: saring satu `periode_type`, dan ingat kubus beragregasi
pada tanggal selesai sehingga trennya tidak sebanding dengan tren dari tabel fakta.

## Rute

- Konsep berkode belum teresolusi buka peta halaman di `SEEKNAL_ASK.md`.
- Menyebut periode / durasi: buka `60-waktu-dan-durasi.md`.
- Berkata "belum / tanpa / kosong": buka `90-kualitas-data.md`.

---

<!-- MANIFES
tabel: coverage_balai, mv_pengawasan, mv_pengawasan_agg, mv_pengawasan_ketidaksesuaian, mv_pengawasan_log, mv_pengawasan_timeline, target_balai
kolom: avg_durasi_hari, id, id_pengawasan, jumlah_pengawasan, nama_balai, periode_type, sync, tanggal_periode, tgl_end, tgl_start
nilai: -
-->
