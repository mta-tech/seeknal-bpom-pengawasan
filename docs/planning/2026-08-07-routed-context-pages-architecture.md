# Context berutas — dari satu buku yang dibaca utuh menjadi halaman yang dipanggil sesuai kebutuhan

**Tanggal:** 7 Agustus 2026
**Varian yang dibangun:** `docs/context_recap/after-chart-route/route-context-070826/`
**Status:** dibangun & lolos verifikasi statis; **belum dijalankan** terhadap suite
**Basis bukti:** audit 6–7 Agu 2026 atas 232 run — berada di **repo audit terpisah**,
`seeknal_audit/docs/audit_context/2026-08-06-after-chart-execution/` (bukan di repo ini) ·
verifikasi langsung ke `rpo_v2` (7 Agu) · 116 berkas UAT compact I–VIII ·
`docs/planning/2026-08-04-context-mapping-fidelity-and-coverage-closure.md` §5

---

## 1. Objektif

Menurunkan biaya context per turn **tanpa menurunkan cakupan maupun akurasi**, dengan menyerang
penyebab strukturalnya, bukan gejalanya.

Tiga sasaran terukur, ketiganya berlaku untuk **seluruh** 116 kasus compact I–VIII, bukan satu batch:

| Sasaran | Baseline terukur | Target |
|---|---|---|
| Token context per turn data | **~17.700** | ≤ 6.000 |
| Aturan yang tak pernah efektif terbaca | §5, §12-C, §4d — tenggelam di bagian belakang berkas | nol bagian belakang: tak ada halaman > ~135 baris |
| Dimensi yang tak punya jalan masuk | `nama_pabrik`, `nama_trader`, `pengolahan`, `peruntukan`, `klasifikasi_id`/`klaim` — **0 dari 170 SQL** menyentuhnya | tiap dimensi punya rute masuk yang terverifikasi |

Non-sasaran yang dinyatakan eksplisit: **bukan** menulis ulang aturan, **bukan** menyederhanakan
domain, **bukan** mengubah engine Seeknal.

---

## 2. Kondisi awal — apa yang sebenarnya dibayar tiap turn

| Berkas | Baris | ~token | Cara masuk |
|---|---|---|---|
| `SEEKNAL_ASK.md` | 173 | 3.002 | disuntik `context_files` — tiap turn, tak pernah terpotong |
| `context/predikat.md` | 402 | 6.140 | Gate 2 **blocking** |
| `context/filter_code_reference.md` | 472 | 8.547 | Gate 2 **blocking** |
| **total** | **1.047** | **~17.691** | sebelum satu SQL pun jalan |

Komposisinya: payload deklaratif (tabel, daftar kode) **157 baris (15 %)**; prosa murni tanpa satu
backtick pun **425 baris (41 % baris, 46 % karakter)**.

Sementara itu, diukur dari 116 GT: satu pertanyaan rata-rata hanya menyentuh **1,5 dimensi variabel**
(16 % kasus nol, 34 % satu, 34 % dua). Sebagian besar yang dibaca tiap turn tidak dipakai.

---

## 3. Hipotesa akar masalah

### H-A · Pola aksesnya berubah di bawah dokumen yang dirancang untuk pola akses lain

Pemangkasan 24 Juni 2026 berhasil (918 → ~340 baris) dengan alasan yang ditulis eksplisit di
`2026-06-24-context-simplification-and-followup-protocol.md` §3.1:

> *"Context files are **fact repositories loaded on demand** — they are NOT loaded every turn …
> the attention-dilution problem … does NOT apply to context files."*

Premis itu **sudah tidak berlaku**. Gate 2 sekarang berbunyi *"blocking; exactly two reads"*. Dua
repositori fakta terbesar berubah menjadi biaya per-turn. Berkasnya tumbuh karena alasan yang sah —
tiap temuan F-1…F-17 (audit 4 Agu) menambah fakta terverifikasi — tetapi **pola aksesnya berubah di
bawahnya**. Inilah sebab pemangkasan sebelumnya termakan kembali, dan sebab memangkas isi lagi tidak
akan menahannya.

### H-B · Bentuk aturan menentukan kepatuhan, dan bentuk termahal justru yang paling tidak dipatuhi

`2026-08-04-context-mapping-fidelity-and-coverage-closure.md` §5 mengukurnya dari jejak nyata:

| Bentuk | Kepatuhan agent |
|---|---|
| **Deklaratif** — daftar kode diserahkan jadi (§2 bucket pipeline) | **90–100 %** |
| **Prosedural** — agent disuruh menurunkan sendiri (§4 compound/OR) | **20 %** |

46 % biaya karakter ada pada bentuk yang kepatuhannya 20 %.

### H-C · "Termuat" bukan "terpanggil"

Audit 6–7 Agu: `filter_code_reference.md` dibaca **118 dari 120 kali**, dan §5 ada di dalamnya —
namun `GARAM`, `KOPI-INSTAN`, `SIRUP-MY`, `RED-WINE` semuanya gagal pada aturan §5. Sebabnya §5
duduk di baris 403–471 dari 471, bersaing dengan 470 baris lain. Ini **berbeda** dari pemotongan
jendela baca (yang hanya terjadi di varian uji ber-`read_max_lines: 200`); di produksi berkasnya
muat utuh dan aturannya tetap tidak berpengaruh.

### H-D · Dimensi tanpa jalan masuk tidak akan pernah dicoba

`nama_pabrik` dan `kode_kbli`: **0 dari 170 SQL** compact-VIII menyentuhnya, di kedua varian. Bukan
kegagalan menalar — kolomnya tidak pernah masuk ruang pencarian, karena tidak disebut di context mana
pun (atau disebut dengan alamat tabel yang salah).

---

## 4. Konsep

**Buku yang mengajari pembacanya halaman mana berikutnya.**

```
DAFTAR ISI   SEEKNAL_ASK.md — menempel tiap turn, berisi RUTE, bukan aturan data
HALAMAN 00   dibaca setiap pertanyaan data (entity · tier status · eksklusi · cast · UNION)
HALAMAN 10–95  dibuka bila komponennya ada di pertanyaan
HALAMAN 11/12/21/41  anak, dibuka dari induknya
```

### Tiga cara berpindah

| Gerak | Kapan |
|---|---|
| **TURUN** | konsep perlu detail lebih dalam (`40-kemasan` → `41-sub-kemasan`) |
| **SEBERANG** | pertanyaan melintasi dimensi lain (`10-segmen` → `60-asal-produksi`) |
| **KEMBALI** | tak teresolusi → peta, atau Gate 1 (tanya) |

### Satu pertanyaan boleh menyalakan beberapa halaman

Pertanyaan diuraikan menjadi **komponen** lebih dulu, lalu semua halamannya dibuka **dalam satu
panggilan**:

> *"permohonan produk kopi dari negara mana yang izinnya sudah kedaluwarsa?"*
> → `00` + `15` (permohonan) + `10` (segmen) + `60` (negara) + `80` (kedaluwarsa)

Tiap komponen diselesaikan di kolomnya sendiri lalu di-AND-kan dalam satu `WHERE`. Komponen yang
halamannya tidak dibuka **hilang dari filter tanpa jejak** — query tetap jalan, angkanya tetap masuk
akal. Itu mode kegagalan yang paling sulit terlihat, dan alasan mengapa rute lintas-topik bukan
fitur opsional.

### Hukum bentuk: lebar murah, dalam mahal

Diukur dari 232 run: **185 turn membaca 2 berkas context pada detik yang sama**, 42 turn membaca 3
serentak, hanya 2 turn satu-per-satu. Agent **sudah** membuka beberapa halaman dalam satu tarikan.
Yang menyerialkan adalah **rantai** — halaman B baru diketahui setelah A dibaca.

→ Halaman menunjuk **beberapa tujuan sekaligus**; kedalaman jalur umum dijaga **≤ 2**.

---

## 5. Prinsip desain

### P1 · Pisahkan berdasarkan pola akses, bukan topik

Ini mengembalikan premis yang membuat pemangkasan Juni berhasil, ke tempat yang sekarang
melanggarnya (H-A). Yang universal menempel/selalu dibaca; yang bersyarat dibaca bersyarat.

### P2 · **Halaman adalah PETA, bukan contekan jawaban** — prinsip paling menentukan

Halaman memuat: kolom mana untuk konsep apa · kode mana milik kategori mana · di mana kedua sistem
berbeda · **query pemeriksa** untuk memastikannya.
Halaman **tidak** memuat: cacah populasi, persentase, rasio, perbandingan besaran.

| Ditolak (jawaban) | Dipakai (peta + pemeriksa) |
|---|---|
| "berhenti di induk = 287× terlalu besar (14.628 vs 51)" | "label induk berbunyi *Kaca **ATAU** Keramik* — setiap kali deskripsi induk memuat 'atau', induk tidak bisa menjawab pertanyaan yang menyebut salah satunya" + query `GROUP BY sub_kemasan_id` |
| "`negara_produsen` terisi 1,8 % — buang 98 % data" | query `COUNT(*) FILTER (WHERE …)` untuk kedua kolom kandidat → "pilih yang terisi luas, sebutkan kolom yang dipakai" |
| "Case A vs Case B — beda 254 vs 5.198" | "sebagian besar peristiwa komitmen terjadi **sebelum** NIE terbit — putuskan dari subjek pertanyaan, **jangan** dari besar-kecilnya hasil" |
| "menumpuk filter NIE sah: 30.074 → 1.951 (−94 %)" | "baris yang belum berkategori umumnya belum sampai terbit NIE — tanyakan: populasi ini didefinisikan oleh terbitnya NIE, atau oleh keadaan lain?" |

Dua alasannya berdiri sendiri:
1. **Angka di context menjadi basi** seiring data bergerak, dan berisiko dikutip agent sebagai hasil
   hitungan padahal tidak dihitung turn itu.
2. Lebih berat: angka mengajari sistem **menghafal jawaban** alih-alih **menemukan data**. Yang
   diuji suite ini adalah kemampuan menemukan; menaruh hasilnya di context membuat pengujian itu
   kehilangan makna.

Prinsipnya ditulis di kernel supaya mengikat penyuntingan berikutnya:
> *"Halaman adalah PETA, bukan contekan jawaban … Bila sebuah halaman terasa memberi jawaban
> langsung, itu keliru: jalankan pemeriksanya sendiri."*

### P3 · Deklaratif di depan, prosedural sebagai pemeriksa

Menjawab H-B. Yang diserahkan jadi: kode, kolom, set. Yang diserahkan sebagai prosedur: **cara
memeriksa**, bukan cara menurunkan aturan.

### P4 · Aturan umum, bukan tambalan per kasus

Setiap aturan ditulis pada tingkat topik. Contoh: bukan "keramik = `sub_kemasan_id='102'`", tetapi
"material spesifik wajib turun ke kolom anak; kenali dari deskripsi induk yang memuat 'atau'".

### P5 · Pengetahuan di context, penegakan di skill

`load_skill` memerlukan `<project>/seeknal/skills/` dan **gagal senyap** bila symlink hilang — itu
yang membuat generasi `after-chart-030826` tak terukur (390 dari 390 error). Halaman context hanya
memerlukan direktori `context/`. Pengetahuan karenanya tidak boleh tinggal di skill.

---

## 6. Pendekatan pengerjaan — diturunkan dari data, bukan dari intuisi

| Langkah | Sumber | Hasil |
|---|---|---|
| Batas topik | ko-okurensi kolom di 116 GT | pasangan ≥3 kasus digabung jadi satu halaman (mis. `kategori_dokumen`+`status_komitmen` 11×) |
| Isi halaman | `predikat.md`/`filter_code_reference.md`/`data_architecture.md` produksi | **dipindahkan**, bukan ditulis ulang dari ingatan |
| Kosakata rute | prompt pengguna nyata, di-skor diskriminatif (khas grup vs umum) | kata pemicu tiap baris peta |
| Fakta struktural | `information_schema` + `data_dictionary` di `rpo_v2` | ERLA subset murni ERBA (94 irisan · 6 hanya-ERBA · 0 hanya-ERLA); tabrakan kode `301`/`302` di 9 kategori; label kembar di `STATUS` |
| Verifikasi rute | simulasi indeks terhadap 116 prompt | keterjangkauan, kedalaman, yatim, siklus |

Iterasi nyata yang tercatat: keterjangkauan awal **78 %** → memperbaiki kosakata rute dan menambah
halaman `35-klasifikasi-sifat` (untuk `klasifikasi_id`/`klaim` yang belum punya rumah) → **97 %**.
Lubangnya ditemukan **sebelum** satu turn pun dijalankan.

---

## 7. Yang dibangun

```
route-context-070826/
  SEEKNAL_ASK.md                146 baris   gate + peta rute (menempel)
  context/00-menghitung.md      135         entity · tier status · eksklusi · cast · UNION
        /10-segmen-produk.md     63    /11-kode-segmen.md      51    /12-nama-kategori.md  65
        /15-permohonan.md        49
        /20-status-pipeline.md   67    /21-kode-status.md      51
        /30-risiko-komitmen.md   67
        /35-klasifikasi-sifat.md 84         ← BARU (klasifikasi_id · klaim · pemrosesan · peruntukan)
        /40-kemasan.md           58    /41-sub-kemasan.md      41
        /50-pihak-wilayah.md     97         ← BARU (nama_pabrik · nama_trader · KBLI · skala · daerah)
        /60-asal-produksi.md     81
        /70-btp.md               52
        /80-waktu-periode.md     68
        /90-kualitas-data.md     64         ← BARU
        /95-dimensi-lain.md      77         ← BARU (prosedur menemukan dimensi tak terdaftar)
        /data_architecture.md    67    /forecast_guide.md     113 (tak disentuh)
  skills/bpom-analyst           70         ditulis ulang: anggaran · stop rule · tanpa duplikasi
        /visualize-chart       182         disalin apa adanya — BELUM diringkas
        /bpom-forecaster       141         sengaja tidak disentuh (pipeline deterministik)
        /detect-anomaly         72         tidak disentuh
```

Penomoran hanya mengatur urutan tampil di `list_context_files()`; hubungan induk–anak yang berlaku
ada di blok **Rute**. Subdirektori sengaja **tidak** dipakai: `sorted()` menempatkan folder sebelum
berkas induknya, sehingga anak muncul lebih dulu di indeks — dan folder kosong mudah tertinggal.

### Perubahan aturan yang ikut

1. **Plafon SQL disatukan ke 6** — sebelumnya bertentangan (Gate 4 = 4 · skill = 6 · yml = 6).
2. **Baris bukti terikat pada SQL turn ini** — jawaban tanpa query turn itu tidak boleh memuat nomor
   NIE, nama pabrik, atau merek. Ini menutup fabrikasi 3 nomor NIE yang ditemukan audit (giliran
   `sql=0`, `tool_calls=0`, dan **lolos tes**).
3. **Prosedur beda ERBA/ERLA** di `00-menghitung` §5 — periksa keberadaan kolom, keterisiannya, dan
   rentang nilainya per sistem sebelum UNION; tiga bacaan hasilnya dinyatakan eksplisit.
4. `read_max_lines: 300` sebagai pagar struktural (halaman terpanjang 135).

---

## 8. Ekspektasi hasil — hipotesa yang akan diuji

Dinyatakan sebagai **prediksi yang bisa dibantah**, bukan klaim.

| # | Hipotesa | Metrik | Baseline | Prediksi |
|---|---|---|---|---|
| E1 | Beban context turun tanpa kehilangan cakupan | token/turn (median, 116 prompt) | 17.691 | **~6.000 (−66 %)** — sudah terukur secara simulasi |
| E2 | Aturan yang dulu tenggelam kini berpengaruh | kepatuhan eksklusi akun uji pada query pencacahan | 65 % (E) / 38 % (D) | **≥ 80 %** |
| E3 | Dimensi tanpa jalan masuk jadi tersentuh | SQL yang menyentuh `nama_pabrik` / `kode_kbli` / `pengolahan` | 0 dari 170 | **> 0** |
| E4 | Pertanyaan lintas dimensi tidak kehilangan komponen | kasus segmen×negara yang filter negaranya hilang | terjadi di `KOPI-INSTAN-*` | **0** |
| E5 | Fabrikasi identifier berhenti | jawaban memuat NIE/merek tanpa SQL turn itu | 1 kasus terverifikasi | **0** |
| E6 | Plafon query ditegakkan | turn > 6 SQL | 23 % (E) / 32 % (D) | **≤ 15 %** |
| E7 | Akurasi tidak turun | headline dalam toleransi GT (compact-VIII) | E 0/11 · D 3/11 | **tidak turun** |

**E7 adalah gerbangnya.** Bila E1–E6 tercapai tetapi E7 turun, arsitekturnya salah dan harus
dibatalkan — penghematan token tidak membeli apa pun bila jawabannya memburuk.

### Yang bisa membantah arsitektur ini

- Rute salah menyala pada pertanyaan yang tidak diprediksi 116 kasus (kosakata terlalu sempit).
- Agent membuka halaman tetapi tetap tidak mematuhinya — artinya masalahnya bukan letak, melainkan
  bentuk, dan H-C keliru.
- Membuka beberapa halaman menambah langkah yang justru menurunkan akurasi — `2026-08-04` §5
  mencatat bahwa menambah langkah tidak membuat jawaban lebih benar.

---

## 9. Verifikasi

### Lapis 1 — statis, tanpa LLM (sudah dijalankan)

| Gerbang | Hasil |
|---|---|
| Tautan mati | **0** |
| Halaman yatim (tanpa rute masuk) | **0** |
| Kedalaman dari peta | semua **d0/d1** (target ≤2) |
| **Keterjangkauan atas 116 prompt UAT** | **113/116 = 97 %** |
| Halaman topik menyala per pertanyaan | rata-rata **1,6**, maks 4 |
| Angka hasil yang bocor ke context | **0** (sisa dua hit adalah kode: `LIKE '5%'`, `'12010103'`) |

Tiga sisa keterjangkauan diperiksa satu per satu dan semuanya artefak ekstraksi — GT menyebut kolom
justru untuk **melarangnya** (`kategori_dokumen` di `IMPOR-1` ditulis sebagai *"WASPADA KOLOM MIRIP"*),
dan halaman yang benar tetap menyala.

Skrip: `cek_rute.py` (struktur) dan `cek_recall.py` (keterjangkauan) — keduanya membaca berkas
varian dan 116 YAML, tanpa memanggil model.

### Lapis 2 — pilot (belum dijalankan)

27 skenario (compact-IV 16 dimensi umum + compact-VIII 11 dimensi ekor), lalu suite penuh.

**Prasyarat yang memblokir:**
1. Varian butuh `.env`, `.seeknal/`, dan **`seeknal/skills/` → `../skills`**. Tanpa itu `load_skill`
   gagal dan lapisan penegakan tidak termuat.
2. **Kolom PASS/FAIL harness tidak boleh dipakai apa adanya.** Pada compact-VIII, **10 dari 14 PASS
   terbukti palsu** — lolos lewat kode status, tahun, angka negara lain, dan fragmen tanggal dari
   record yang dikarang. Penilaian harus membandingkan headline jawaban dengan `note` GT.

---

## 10. Risiko & yang belum selesai

| Risiko | Mitigasi / status |
|---|---|
| Kosakata rute terlalu sempit untuk pertanyaan di luar 116 kasus | Peta menyatakan katanya sebagai **contoh**, rutekan berdasarkan konsep; `95-dimensi-lain` sebagai penampung + prosedur penemuan |
| Halaman dibuka tapi tidak dipatuhi | Gate 5 butir 1 menuntut `00-menghitung` terbaca sebelum query pencacahan; metrik pilot memeriksanya dari `tool_trace` |
| Membuka beberapa halaman menambah round-trip | Rata-rata 1,6 halaman, dan pembacaan terbukti dibatch (185 dari 229 turn) |
| Halaman tumbuh kembali seperti berkas lama | `read_max_lines: 300` + pemeriksa ukuran di `cek_rute.py` |
| Angka hasil menyusup kembali saat penyuntingan | Prinsip ditulis di kernel; pemindaian regex angka-hasil bisa dijadikan gerbang CI |

**Belum dikerjakan:** `visualize-chart/SKILL.md` masih 182 baris dan dimuat di setiap pertanyaan data
— beban per-turn yang belum disentuh, dan satu-satunya bagian rencana yang tertinggal.

**Sengaja tidak dikerjakan:** `bpom-forecaster` (detail adalah jaminan determinismenya,
`2026-06-24` §3.2) · `detect-anomaly` · engine Seeknal (nol perubahan).

---

## 11. Hubungan dengan dokumen lain

- `2026-06-24-context-simplification-and-followup-protocol.md` — pemangkasan sebelumnya; §3.1 memuat
  premis yang kini tidak berlaku, dan itulah H-A.
- `2026-08-04-context-mapping-fidelity-and-coverage-closure.md` — §4 pilar yang tidak boleh diubah,
  §5 pengukuran deklaratif vs prosedural (H-B). Isi F-1…F-17 dipindahkan ke halaman, tidak dibuang.
- `2026-08-05-sql-execution-path-and-column-type-context.md` — asimetri tipe kolom, masuk
  `00-menghitung` §4 dan `data_architecture`.
- **`seeknal_audit/docs/audit_context/2026-08-06-after-chart-execution/`** — di repo audit terpisah,
  bukan di `seeknal-bpom-neo/docs/audit_context/`. Sumber H-C, H-D, temuan fabrikasi nomor NIE, dan
  bukti PASS-palsu yang menentukan cara pilot dinilai. Berkasnya: `00-RINGKASAN.md` ·
  `01-TEMUAN-INSTRUMEN-DAN-KONFIG.md` · `02-rincian-kegagalan.md` ·
  `03-compact-VIII-dan-verifikasi-database.md`.
