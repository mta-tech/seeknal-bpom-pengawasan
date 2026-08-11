# Varian after-forecast-chart-enhance-diffuse (040826)

**Basis:** salinan `after-forecast-chart-enhance` sesudah perbaikan audit 4 Agustus 2026
(`docs/planning/2026-08-04-context-mapping-fidelity-and-coverage-closure.md`). Isi aturannya
**identik** — tidak ada aturan yang ditambah, dihapus, atau dibalik arahnya.

**Yang membedakan hanya panjang penulisannya.** `chart-enhance` menuliskan aturan hasil audit
dalam bentuk padat: satu kalimat perintah, satu contoh, selesai. Varian ini menuliskan aturan yang
sama dalam bentuk terurai — mekanisme kegagalannya dijelaskan, contoh kasusnya dituntaskan, dan
alasan "kenapa" ikut ditulis, bukan hanya "apa".

**Untuk apa varian ini ada.** Audit menemukan bahwa **bentuk** penulisan aturan menentukan
kepatuhan agent: aturan deklaratif (daftar kode diserahkan jadi) dipatuhi 90–100%, aturan
prosedural (agent disuruh menurunkan sendiri) hanya sebagian. Varian ini menguji dimensi kedua —
apakah **panjang penjelasan** juga berpengaruh pada isi aturan yang sama. Keduanya wajib dijalankan
berpasangan; sendirian, tidak satu pun menjawab pertanyaan itu.

**Bagian yang diurai** (di luar ini, byte-identik dengan `chart-enhance`):

| Berkas | Bagian |
|---|---|
| `filter_code_reference.md` | §0 aturan penutupan + prioritas sumber · §4 residual bucket, peruntukan, alasan struktural konsep majemuk · §4d(1)(2) · §5 namespace, induk-anak, teks bebas |
| `predikat.md` | §1 `COUNT(*)` per entity · §4 cabang permohonan · §8 bobot eksklusi · §9 batas aturan cast · §12-D identifier bukti |
| `SEEKNAL_ASK.md` | Gate 2 prioritas sumber + cek cakupan · Gate 5 butir 6–7 |
| `data_architecture.md` | tipe per tabel · namespace segmen |
| `skills/bpom-analyst` | daftar CHECK Gate 5 |
| `skills/visualize-chart` | chart gagal render |

**Yang sengaja TIDAK dikembalikan:** angka presisi (persen kerugian, jumlah baris). Alasannya
berdiri sendiri dan tidak berkaitan dengan panjang tulisan — angka di context akan basi seiring
data bergerak, dan berisiko dikutip agent sebagai hasil hitungan padahal tidak dihitung turn itu
(`predikat.md` §12-B, Gate 5 butir 9). Magnitudo tetap dipakai sebagai urutan prioritas kualitatif
di kedua varian. Seluruh angka terukurnya tersimpan di dokumen audit.

**Harness:** sama dengan varian lain. Folder `after-chart-030826` kini berisi empat varian —
dua baseline, `chart-enhance` (padat), dan `chart-enhance-diffuse` (terurai).
