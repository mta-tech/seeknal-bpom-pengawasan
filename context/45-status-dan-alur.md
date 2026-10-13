Status dan alur persetujuan — dua hal berbeda yang sering ditukar, plus satu tabel alur.

## Dua jalur untuk kata "ditolak"

Kata "ditolak" bisa berarti **vonis** atau **tahapan proses** — jangan campur:

- **Vonis** (hasil penilaian iklan): keluarga `TMK*` pada kolom vonis yang ditanyakan
  (`kesimpulan_pusat_id` / `kesimpulan_balai_id` / `kesimpulan_akhir_id`) — lihat `30-vonis.md`.
- **Tahapan proses** (log approval): langkah berawalan `ditolak_*` di
  `fact_pengawasan_approval` (`ditolak_spv_1`, `ditolak_pusat`, `ditolak_kepala_balai`, dst).

Jangan menyimpulkan penolakan dari `status_code` saja.

## `status_code` — angka, tanpa label

Kode status bertipe **angka**. Ambil daftar nilainya lewat `SELECT DISTINCT` — jangan mengetik
dari ingatan. Untuk membaca makna sebuah kode, pasangkan dengan `trx_steps` pada baris yang sama.

## Alur approval — `fact_pengawasan_approval`

Satu baris per langkah proses: `trx_steps` (nama langkah), `status_code`, `urutan_step`,
`user_id`, `catatan`, `created_at`. Langkah penolakan berawalan **`ditolak_`** — penamaannya
jelas, berbeda dari langkah normal (`draft`, `spv_1`, `kepala_balai`, `pusat`, `direktur`,
`selesai`).

⚠️ **Tabel ini memuat id yang tidak ada di fakta** (populasinya lebih besar daripada
`fact_pengawasan`). Bila jawabannya berbicara tentang populasi pengawasan, **INNER JOIN dari
fakta** lewat `pengawasan_id`. Sifat id tambahan itu belum dipastikan — perlakukan sebagai
populasi berbeda, jangan menyimpulkan sebabnya.

## Batas yang harus dihormati

Pertanyaan *"siapa yang menyetujui"*, *"apakah pemisahan tugas berjalan"*, *"apakah ada
self-approval"* → **P5 NOT COVERED**.

`user_id` terisi penuh, tetapi maknanya tidak dapat dipastikan dari database ini sendirian —
apakah ia pelaku tahap itu, atau pengirim ke tahap itu. Kedua bacaan menghasilkan angka yang sama
dan kesimpulan yang berlawanan, dan kesimpulannya bersifat tuduhan.

Yang **boleh** dijawab dari alur: kapan berkas berpindah tahap, berapa lama tersangkut, dan tahap
mana yang paling banyak menahan berkas — semua tentang **waktu dan volume**, bukan tentang
**siapa**.

## Istilah pengguna

| Istilah | Cara mengikat |
|---|---|
| "sudah selesai" | langkah `trx_steps='selesai'` di approval |
| "belum selesai" / "menggantung" | belum punya langkah `selesai` di approval |
| "ditolak" | **dua jalur di atas** — vonis (keluarga TMK) atau tahapan (`ditolak_*`); tanya bila ambigu |
| "riwayat alur" · "pernah ditolak" | langkah `ditolak_*` di `fact_pengawasan_approval` |

## Rute

- Menyebut durasi/SLA → **seberang** `60-waktu-dan-durasi.md`.
- Menyebut vonis → **seberang** `30-vonis.md`.
