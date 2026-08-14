Tiga kolom vonis — dan kenapa ketiganya tidak bisa dipertukarkan.

## Kolom

| Kolom | Menilai | Diisi oleh |
|---|---|---|
| `kesimpulan_penilaian_balai` | hasil verifikasi UPT/balai | balai |
| `kesimpulan_penilaian_pusat` | hasil verifikasi pusat | pusat |
| `kesimpulan_penilaian_akhir` | kesimpulan akhir | turunan |

## Ketiganya punya himpunan nilai yang BERBEDA

Ini jebakan utama domain ini.

- Kolom **balai** memuat vonis dasar plus gradasi mayor dan minor.
- Kolom **pusat** memuat semua itu **plus satu tingkat gradasi tertinggi** yang **tidak pernah
  muncul di kolom balai**.
- Kolom **akhir** hanya biner — gradasi hilang saat diturunkan.

> Konsekuensi praktis: `kesimpulan_penilaian_pusat = 'TMK'` **melewatkan** seluruh baris bergradasi
> di kolom itu. Keluarga TMK harus dicocokkan dengan pola awalan, bukan kesamaan persis:
> `LIKE 'TMK%'`.
>
> Dan karena keluarganya berbeda antar kolom, **jangan menyalin himpunan kode dari satu kolom ke
> kolom lain.** Ambil daftar nilai per kolom — jalur **P2**.

## Kolom akhir terkunci komoditi

`kesimpulan_penilaian_akhir` **hanya terisi untuk sebagian komoditi**; untuk komoditi lain seluruh
barisnya bersentinel.

> Menghitung tingkat kepatuhan dari kolom akhir **menghapus komoditi yang tidak terisi secara
> diam-diam**. Untuk cakupan menyeluruh, pakai kolom **pusat** dengan fallback ke **balai**, dan
> sebutkan kolom mana yang dipakai.

Cara memastikan komoditi mana yang terisi: silangkan keterisian ketiga kolom dengan `komoditi` —
satu query, jalur **P2**.

## Hukum penurunan kolom akhir

Ketika kolom akhir terisi, isinya mengikuti kolom pusat bila pusat sudah menilai, dan mengikuti
kolom balai bila pusat belum. Hukum ini **konsisten**, sehingga kolom akhir tidak membawa
informasi baru — ia hanya meringkas.

Karena itu, bila pertanyaannya menuntut cakupan penuh, kolom pusat+balai lebih informatif daripada
kolom akhir.

## Pertanyaan "gap balai vs pusat"

Gap hanya terdefinisi pada baris yang **kedua kolomnya terisi**. Baris bersentinel di salah satu
sisi bukan "perbedaan pendapat" — melainkan salah satu pihak belum menilai.

> **Aturan:** saring `balai <> sentinel AND pusat <> sentinel` lebih dulu, baru bandingkan.
> Sebutkan berapa bagian populasi yang dikeluarkan karena belum lengkap.

Perbandingan juga harus sadar gradasi: balai menulis gradasi mayor/minor sedangkan pusat bisa
menulis tingkat yang lebih tinggi. Bandingkan pada tingkat yang sama (keluarga TMK versus MK),
atau nyatakan bahwa gradasi diperlakukan sebagai satu keluarga.

## Sentinel

Ketiga kolom memakai **string** sebagai penanda belum-dinilai, bukan SQL NULL. `IS NULL` di sana
mengembalikan nol baris. Lihat `90-kualitas-data.md`.

Setiap tren berbasis vonis **wajib menyertakan kelompok bersentinel** atau menyebut porsinya —
pada periode terbaru porsinya besar karena prosesnya belum selesai, dan tanpa disebut periode itu
terlihat membaik padahal hanya belum dinilai.

## Istilah pengguna

| Istilah | Cara mengikat |
|---|---|
| "yang lulus" / "memenuhi ketentuan" | vonis dasar positif — **tanya kolom mana** |
| "TMK" | keluarga TMK, pakai pola awalan |
| "hasil verifikasi balai/UPT" | kolom balai |
| "hasil verifikasi pusat" | kolom pusat |
| "kesimpulan akhir" | kolom akhir — ingat keterbatasan komoditinya |

## Rute

- Menyebut komoditi: buka `10-komoditi.md`.
- Menyebut klausul pelanggaran: buka `40-ketidaksesuaian.md`.
- Menyebut status alur: buka `45-status-dan-alur.md`.

---

<!-- MANIFES
tabel: -
kolom: kesimpulan_penilaian_akhir, kesimpulan_penilaian_balai, kesimpulan_penilaian_pusat, komoditi
nilai: -
-->
