# Varian `route-context-070826` — context berutas: halaman dipanggil sesuai kebutuhan

**Dibuat:** 7 Agustus 2026 · **Status:** lolos verifikasi statis, **belum dijalankan** terhadap suite
**Desain lengkap & rasionalnya:** `docs/planning/2026-08-07-routed-context-pages-architecture.md`
**Basis isi:** `predikat.md` (401) + `filter_code_reference.md` (471) + `data_architecture.md` (150)
+ `SEEKNAL_ASK.md` (172) produksi — **dipindahkan**, bukan ditulis ulang dari ingatan.

---

## 1. Objektif

Menurunkan biaya context per turn **tanpa menurunkan cakupan maupun akurasi**.

| Sasaran | Baseline terukur | Target |
|---|---|---|
| Token context per turn data | **~17.700** | ≤ 6.000 |
| Aturan yang tak pernah efektif terbaca | §5, §12-C, §4d tenggelam di bagian belakang berkas | tak ada halaman > ~135 baris |
| Dimensi tanpa jalan masuk | `nama_pabrik`·`nama_trader`·`pengolahan`·`peruntukan`·`klasifikasi_id` — **0 dari 170 SQL** menyentuhnya | tiap dimensi punya rute masuk terverifikasi |

---

## 2. Hipotesa akar masalah

**A. Pola akses berubah di bawah dokumen yang dirancang untuk pola akses lain.** Pemangkasan Juni
berhasil karena context saat itu *loaded on demand*. Gate 2 kini menjadikannya **blocking tiap turn**,
sehingga dua repositori fakta terbesar berubah jadi biaya per-turn. Berkasnya tumbuh karena alasan
sah; **pola aksesnya** yang berubah. Memangkas isi lagi tidak akan menahannya.

**B. Bentuk aturan menentukan kepatuhan.** Terukur di `2026-08-04-*` §5: deklaratif **90–100 %**,
prosedural **20 %**. Dan 46 % biaya karakter ada pada bentuk yang kepatuhannya 20 %.

**C. "Termuat" bukan "terpanggil".** `filter_code_reference.md` dibaca 118 dari 120 kali, §5 ada di
dalamnya — tetapi GARAM/KOPI/SIRUP/RED-WINE semuanya gagal pada aturan §5, karena §5 duduk di baris
403–471 bersaing dengan 470 baris lain.

**D. Dimensi tanpa jalan masuk tidak pernah dicoba.** `nama_pabrik` & `kode_kbli`: 0 dari 170 SQL.
Bukan gagal menalar — kolomnya tak pernah masuk ruang pencarian.

---

## 3. Konsep

Buku yang mengajari pembacanya halaman mana berikutnya.

```
SEEKNAL_ASK.md   gate + PETA RUTE — menempel tiap turn, tanpa aturan data
context/00-*     cara menghitung — dibaca setiap pertanyaan data
context/N0-*     halaman topik — dibuka bila komponennya ada di pertanyaan
context/NN-*     halaman anak (digit kedua ≠ 0) — dibuka dari induknya
```

**Tiga cara berpindah:** **TURUN** ke anak · **SEBERANG** ke topik lain · **KEMBALI** ke peta/Gate 1.

**Satu pertanyaan boleh menyalakan beberapa halaman, dan semuanya dibuka dalam SATU panggilan:**

> *"permohonan produk kopi dari negara mana yang izinnya sudah kedaluwarsa?"*
> → `00` + `15` permohonan + `10` segmen + `60` negara + `80` kedaluwarsa → satu `WHERE`

Komponen yang halamannya tidak dibuka **hilang dari filter tanpa jejak** — query tetap jalan dan
angkanya tetap masuk akal. Itu mode kegagalan yang paling sulit terlihat.

**Lebar murah, dalam mahal.** Diukur dari 232 run: 185 turn membaca 2 berkas context pada detik yang
sama, 42 turn membaca 3 serentak, hanya 2 turn satu-per-satu. Yang menyerialkan adalah **rantai**,
bukan jumlah halaman — karena itu kedalaman dijaga ≤2 dan halaman menunjuk beberapa tujuan sekaligus.

---

## 4. Prinsip yang membedakan varian ini

### Halaman adalah PETA, bukan contekan jawaban

Halaman memuat kolom mana untuk konsep apa, kode mana milik kategori mana, di mana kedua sistem
berbeda, dan **query pemeriksa**. Halaman **tidak** memuat cacah populasi, persentase, atau rasio.

| Ditolak (jawaban) | Dipakai (peta + pemeriksa) |
|---|---|
| "berhenti di induk = 287× terlalu besar" | "label induk berbunyi *Kaca **ATAU** Keramik* — bila deskripsi induk memuat 'atau', induk tak bisa menjawab pertanyaan yang menyebut salah satunya" + `GROUP BY sub_kemasan_id` |
| "`negara_produsen` terisi 1,8 %" | `COUNT(*) FILTER (WHERE …)` untuk kedua kolom kandidat → "pilih yang terisi luas, sebutkan kolom yang dipakai" |
| "Case A vs B — 254 vs 5.198" | "sebagian besar peristiwa komitmen terjadi **sebelum** NIE terbit — putuskan dari subjek, jangan dari besar-kecilnya hasil" |

Dua alasannya berdiri sendiri: angka di context **menjadi basi** dan berisiko dikutip sebagai hasil
hitungan padahal tidak dihitung turn itu; dan lebih berat — angka mengajari sistem **menghafal
jawaban** alih-alih **menemukan data**, sehingga pengujian kehilangan maknanya.

Prinsip lainnya: **pisahkan berdasarkan pola akses** · **deklaratif di depan, prosedural sebagai
pemeriksa** · **aturan umum, bukan tambalan per kasus** · **pengetahuan di context, penegakan di
skill** (karena `load_skill` gagal senyap bila symlink hilang — 390 dari 390 error di generasi lalu).

---

## 5. Cara pengerjaannya diturunkan dari data

| Langkah | Sumber |
|---|---|
| Batas topik | ko-okurensi kolom di 116 GT — pasangan ≥3 kasus digabung |
| Isi halaman | berkas produksi, **dipindahkan** |
| Kosakata rute | prompt pengguna nyata, di-skor diskriminatif |
| Fakta struktural | `information_schema` + `data_dictionary` di `rpo_v2` (7 Agu) |
| Verifikasi rute | simulasi indeks terhadap 116 prompt, tanpa LLM |

Iterasi yang tercatat: keterjangkauan **78 % → 97 %** setelah kosakata rute diperbaiki dan halaman
`35-klasifikasi-sifat` ditambahkan. **Lubangnya ditemukan sebelum satu turn pun dijalankan.**

---

## 6. Isi varian

| Berkas | Baris | Peran |
|---|---|---|
| `SEEKNAL_ASK.md` | 146 | gate + peta rute (menempel tiap turn) |
| `context/00-menghitung.md` | 135 | entity · dua tier status · eksklusi · cast · UNION · **prosedur beda ERBA/ERLA** |
| `10-segmen-produk` · `11-kode-segmen` · `12-nama-kategori` | 63·51·65 | segmen pangan |
| `15-permohonan` | 49 | jenis permohonan |
| `20-status-pipeline` · `21-kode-status` | 67·51 | tahapan proses |
| `30-risiko-komitmen` | 67 | risiko & komitmen (ERBA-only) |
| **`35-klasifikasi-sifat`** | 84 | **BARU** — `klasifikasi_id` · `klaim` · `pemrosesan` · `peruntukan` + binding tetap |
| `40-kemasan` · `41-sub-kemasan` | 58·41 | kemasan induk→anak |
| **`50-pihak-wilayah`** | 97 | **BARU** — `nama_pabrik` · `nama_trader` · KBLI · skala · daerah |
| `60-asal-produksi` | 81 | negara asal & cara produksi |
| `70-btp` | 52 | BTP |
| `80-waktu-periode` | 68 | empat kolom tanggal, tren, masa berlaku |
| **`90-kualitas-data`** | 64 | **BARU** — "belum/tanpa/kosong" |
| **`95-dimensi-lain`** | 77 | **BARU** — prosedur menemukan dimensi tak terdaftar (152 kolom) |
| `data_architecture` · `forecast_guide` | 67·113 | peta DB · forecast (tak disentuh) |
| `skills/bpom-analyst` | 70 | ditulis ulang: anggaran, stop rule, tanpa duplikasi |
| `skills/visualize-chart` | 182 | **disalin apa adanya — belum diringkas** |
| `skills/bpom-forecaster` · `detect-anomaly` | 141·72 | sengaja tidak disentuh |

Penomoran hanya mengatur urutan di `list_context_files()`; hubungan induk–anak yang berlaku ada di
blok **Rute**. Subdirektori sengaja tidak dipakai — `sorted()` menempatkan folder sebelum berkas
induknya, sehingga anak muncul lebih dulu di indeks, dan folder kosong mudah tertinggal.

### Perubahan aturan yang ikut

1. **Plafon SQL disatukan ke 6** (sebelumnya bertentangan: Gate 4 = 4 · skill = 6 · yml = 6).
2. **Baris bukti terikat pada SQL turn ini** — tanpa query turn itu, tidak boleh ada nomor NIE, nama
   pabrik, atau merek. Menutup fabrikasi 3 nomor NIE yang ditemukan audit dan **lolos tes**.
3. **Prosedur beda ERBA/ERLA** — periksa keberadaan kolom, keterisiannya, dan rentang nilainya per
   sistem sebelum UNION; tiga bacaan hasilnya dinyatakan eksplisit.
4. `read_max_lines: 300` sebagai pagar ukuran.

---

## 7. Ekspektasi hasil — prediksi yang bisa dibantah

| # | Metrik | Baseline | Prediksi |
|---|---|---|---|
| E1 | Token/turn (median, 116 prompt) | 17.691 | **~6.000 (−66 %)** — terukur simulasi |
| E2 | Kepatuhan eksklusi akun uji | 65 % / 38 % | ≥ 80 % |
| E3 | SQL menyentuh `nama_pabrik`/`kode_kbli`/`pengolahan` | 0 dari 170 | > 0 |
| E4 | Pertanyaan lintas dimensi kehilangan komponen | terjadi di `KOPI-INSTAN-*` | 0 |
| E5 | Jawaban memuat identifier tanpa SQL turn itu | 1 kasus | 0 |
| E6 | Turn > 6 SQL | 23 % / 32 % | ≤ 15 % |
| **E7** | **Headline dalam toleransi GT (compact-VIII)** | **E 0/11 · D 3/11** | **tidak turun** |

**E7 adalah gerbangnya.** Bila E1–E6 tercapai tapi E7 turun, arsitekturnya salah dan dibatalkan —
penghematan token tidak membeli apa pun bila jawabannya memburuk.

---

## 8. Verifikasi

### Lapis 1 — statis, tanpa LLM (sudah dijalankan)

| Gerbang | Hasil |
|---|---|
| Tautan mati | **0** |
| Halaman yatim | **0** |
| Kedalaman dari peta | semua **d0/d1** |
| **Keterjangkauan atas 116 prompt UAT** | **113/116 = 97 %** |
| Halaman topik menyala per pertanyaan | rata-rata **1,6** · maks 4 |
| Angka hasil bocor ke context | **0** |

Tiga sisa keterjangkauan diperiksa satu per satu: artefak ekstraksi — GT menyebut kolom justru untuk
**melarangnya**, dan halaman yang benar tetap menyala.

### Lapis 2 — pilot (belum dijalankan)

```bash
cd seeknal-bpom-neo
uv run python scripts/test_variant_compare.py \
  --variants-path docs/context_recap/after-chart-route \
  --variants route-context-070826 \
  --test-path seeknal/tests/v1/singleturn/UAT-v2-compact-VIII --workers 1 --timeout 400
```

> **Prasyarat 1 — symlink.** Varian ini berisi berkas saja. Harness memerlukan `.env`, `.seeknal/`,
> dan **`seeknal/skills/` → `../skills`** di direktori varian. Tanpa ketiganya `load_skill` gagal dan
> seluruh lapisan penegakan tidak termuat — itu yang membuat generasi `after-chart-030826` tidak
> terukur (390 dari 390 `load_skill` error).
>
> **Prasyarat 2 — jangan percaya kolom PASS/FAIL.** Pada compact-VIII, **10 dari 14 PASS terbukti
> palsu** — lolos lewat kode status, tahun, angka negara lain, dan fragmen tanggal dari record yang
> dikarang. Bandingkan headline jawaban dengan `note` ground-truth.

---

## 9. Yang belum & sengaja tidak dikerjakan

**Belum:** `visualize-chart/SKILL.md` masih 182 baris dan dimuat di setiap pertanyaan data — beban
per-turn yang belum disentuh, satu-satunya bagian rencana yang tertinggal.

**Sengaja tidak:** `bpom-forecaster` (detail adalah jaminan determinismenya) · `detect-anomaly` ·
engine Seeknal (nol perubahan).
