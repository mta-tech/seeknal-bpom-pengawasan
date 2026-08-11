# Problem-Solving Mechanics Audit — kenapa loop step-by-step sistem pecah (2026-07-16)

> **Cakupan audit.** Dokumen ini **bukan** menilai jawaban benar/salah, dan **bukan** menilai soal
> uji apa yang dipakai. Audit ini menilai **bagaimana sistem menentukan rangkaian langkah
> problem-solving**: apakah loop-nya konvergen, berbasis resolusi, dan tertib — atau drift,
> berbasis eksplorasi tanpa akhir. Verdict pass/fail sengaja diabaikan; yang dievaluasi adalah
> **mekanika penalaran**.
>
> **Sumber bukti.** Trace step-by-step `seeknal/tests/outputs/2026-07-16/v4/20260716_083412/`
> (4 varian × skenario BAYI). Pendekatan: kontras varian yang loop-nya sehat (A) vs yang pecah
> (C, baseline) pada soal identik, lalu generalisasi pola ke mode kegagalan.

---

## 0. Ringkasan eksekutif (satu paragraf)

Sistem tidak bekerja bukan karena jawabannya salah, melainkan karena **saat langkah RESOLUSI
gagal, sistem mengubah sifat tugas dari "terapkan kode yang sudah ada" menjadi "cari tahu apa
kodennya" — dan pencarian itu tidak punya akhir. Resolusi gagal dalam **empat cara berbeda**,
dan keempatnya bermuara ke satu pola yang sama: eksplorasi ILIKE/probing yang tak konvergen
(22–32 SQL pada soal yang seharusnya selesai dalam 1–3 query). Varian A membuktikan loop sehat
itu mungkin — dan kuncinya bukan prosedur yang lebih banyak, melainkan **satu coupling yang tak
bisa di-skip: skill wajib membaca authority yang tepat sebelum SQL**.

**Dua temuan tambahan yang menonjol (detail di §0.5):**

- **Satu baris berdampak sistemik.** Headline context (baris pertama) dan `description` skill
  bukan kosmetik — itu **pintu masuk seluruh loop**. Pada baseline, mengubah satu baris headline
  tiap context + satu baris `description` tiap skill **membuat hasil lebih buruk** (turun ke 0/4).
- **`bpom-analyst` sebagai amplifier kebingungan.** Lintas trace spiral, `bpom-analyst` adalah
  faktor common: ia memberi prosedur tapi **tidak memaksa baca authority**, sehingga justru
  memberi agen "izin" mengeksekusi SQL berulang tanpa pengetahuan yang menyempit.

---

## 0.5 Temuan kunci — satu baris headline/description berdampak sistemik

### 0.5.1 Observasi empiris (baseline, sebelum vs sesudah)

Pada baseline, mengubah **satu baris headline dari tiap context file + satu baris `description`
dari tiap skill** membuat hasil **lebih buruk** — baseline turun ke 0/4 pada set BAYI, dengan
spiral 25 SQL pada `UAT-BAYI-3` (Mode B, salah authority). Ini bukti langsung bahwa perubahan
"satu baris" itu **berdampak nyata**, bukan sekadar kosmetik.

### 0.5.2 Kenapa satu baris bisa mengguncang segala aspek

Karena headline/description itu **bukan metadata, melainkan gerbang masuk seluruh loop**:

- **Headline context** (`list_context_files.py:92-109`) = satu-satunya sinyal yang dilihat agent
  saat `list_context_files` — dipotong 140 char dari baris pertama. Inilah yang menentukan
  **authority mana yang akan dipilih** untuk dibaca. Headline berubah → pilihan authority bergeser.
- **`description` skill** (`toolset.py:460-486`) = sinyal **always-on** di blok `<available_skills>`
  setiap turn. Menentukan **routing** dan **ekspektasi perilaku**. Description berubah → ekspektasi
  terhadap kapan/bagaimana skill dipakai ikut berubah.

Keduanya hidup di **langkah ke-1 dan ke-2 loop** (klasifikasi → resolusi). Menggesernya merembet
ke seluruh downstream: resolusi → eksekusi → verifikasi → jawaban. Itulah sebabnya "satu baris"
berdampak sistemik — ia adalah upstream gate, bukan detail di pinggir.

### 0.5.3 `bpom-analyst` — amplifier kebingungan & SQL berulang

Lintas trace yang spiral, `bpom-analyst` adalah **faktor yang selalu hadir**:

| Trace | SQL | `bpom-analyst` termuat? | Authority dibaca? |
|---|---|---|---|
| C `UAT-BAYI-1` | 32 | ✅ | ❌ 0 file |
| Baseline `UAT-BAYI-3` | 25 | ✅ | ⚠️ salah authority (PHASE-0 trio) |
| B `UAT-BAYI-1` | 24 | ✅ | ❌ |
| A `UAT-BAYI-DICABUT-1` | 22 | ✅ | ✅ tapi tak lengkap utk konsep |

**Mekanisme amplifikasi:** `bpom-analyst` **memberi prosedur (understand→resolve→execute→check)
tanpa memaksa membaca authority**. Saat authority tak terbaca/salah/tak-lengkap, prosedur itu
justru menjadi "izin struktural" mengeksekusi banyak query — agen punya kerangka "saya sedang
bekerja sesuai skill" padahal tak punya kode untuk menyempit. Maka `bpom-analyst` **lebih sering
muncul di spiral** bukan karena ia cacat secara intrinsik, melainkan karena ia **kendaraan
default**: dimuat paling awal, paling sering, tapi tak mengunci read-authority. Solusinya bukan
membuangnya, tapi **memaksa coupling-nya dengan authority** (lihat §10 rekomendasi #1).

---

## 1. Metode audit

Dievaluasi: **alur keputusan step-by-step** dari `tool_trace` kronologis per turn (tool, origin,
argumen, ukuran hasil, status). Tidak dievaluasi: kebenaran angka jawaban, kasus uji, pass-rate.

Norma pembanding: **loop problem-solving ideal** (§2). Tiap varian dibandingkan terhadap norma
itu, lalu titik penyimpangan dicatat sebagai mode kegagalan.

Kontras utama yang dipakai sebagai bukti (soal identik — `UAT-BAYI-1`/`BAYI-3`, "total produk
formula bayi"):

| Varian | Trace | Loop | SQL | Context dibaca |
|---|---|---|---|---|
| A (v5-predikat-trim) | `v5-predikat-trim/UAT-BAYI-1.md` | sehat | 1 | predikat + filter_code |
| C (refactor-v2) | `after-forecast-anomaly-refactor-v2/UAT-BAYI-1.md` | pecah | 32 | **0 file** |
| Baseline | `forecast anomaly/UAT-BAYI-3.md` | pecah | 25 | 3 file (PHASE-0, **salah authority**) |

---

## 2. Model normatif: loop problem-solving yang diharapkan

```
1. KLASIFIKASI  → route ke skill yang benar
2. RESOLUSI     → baca AUTHORITY yang tepat untuk dapat KODE & ATURAN
3. KOMITMEN     → kunci rencana (entity, kolom, kode kanonik, filter)
4. EKSEKUSI     → 1–2 SQL tertarget dengan kode yang sudah diresolusi
5. VERIFIKASI   → cek hasil vs intent
6. JAWAB
```

Inti: soal BPOM adalah tugas **RESOLUSI** (terapkan kode kanonik yang sudah ada di authority),
BUKAN tugas **EKSPLORASI** (cari tahu apa kodenya dari nol). Distingsi ini adalah kunci seluruh
audit — semua mode kegagalan bermuara ke pengaburan distingsi ini.

---

## 3. Empat mode kegagalan loop (dengan bukti)

### Mode A — RESOLUSI DI-SKIP (skill termuat, context tak dibaca sama sekali)

**Bukti:** C `after-forecast-anomaly-refactor-v2/UAT-BAYI-1.md`

```
step 1  load_skill(bpom-analyst)        ← prosedur termuat
step 2  execute_sql  dict ILIKE %bayi%  ← langsung SQL, TANPA baca context
step 3  execute_sql  dict ILIKE %susu%
...
step 35 execute_sql                     ← 32 SQL, 0 context file dibaca
```

Agent mempunyai prosedur (skill) tapi **tidak punya pengetahuan** (kode). Akibatnya ia memperlakukan
soal sebagai eksplorasi: mancing kode lewat `data_dictionary` ILIKE, menebak `klasifikasi_id`,
lalu jatuh ke **name-match** (`nama ILIKE '%formula bayi%'`) yang meleset karena nama produk tak
kanonik. Jawaban akhir berbasis name-match → metode salah.

### Mode B — RESOLUSI MEMBACA AUTHORITY YANG SALAH (context dibaca, tapi bukan yang punya kode)

**Bukti:** Baseline `forecast anomaly/UAT-BAYI-3.md`

```
step 1  load_skill(bpom-analyst)                 ← skill 32.2KB (orchestrator PHASE 0–6)
step 2  read_project_file  business_glossary.md
step 3  read_project_file  data_quality_rules.md
step 4  read_project_file  code_translation_protocol.md   ← PHASE-0 trio (mandatory load)
step 5  execute_sql  dict ILIKE %formula bayi%  ← tetap eksplorasi!
...
step 31 upload_to_s3                            ← 25 SQL total
```

Baseline **taat** baca 3 context file (PHASE-0 mandatory), **tetapi ketiganya tidak memuat kode
segmen** (`jenis_pangan` 1301/1302 ERBA, 604/622/624 ERLA). Kode itu hidup di `filter_code_reference.md`
yang tidak dimiliki baseline. Membaca authority yang salah sama parahnya dengan tidak baca sama
sekali — agent tetap harus menemukan kode lewat probing.

### Mode C — RESOLUSI MEMBACA AUTHORITY YANG BENAR, TAPI TIDAK LENGKAP UNTUK KONSEP INI

**Bukti:** A `v5-predikat-trim/UAT-BAYI-DICABUT-1.md` (22 SQL, varian yang biasanya sehat)

```
step 1  load_skill(bpom-analyst)
step 3  read_project_file  predikat.md
step 4  read_project_file  filter_code_reference.md   ← authority yang benar dibaca
step 6  execute_sql  dict STATUS kode IN('0000','0009','0099')   ← tetap mancing kode dicabut!
...
step 22 execute_python   ← putus asa, coba python
... 22 SQL total
```

A membaca authority yang tepat (predikat + filter_code), **tetapi mapping "dicabut/dibatalkan =
kode 0099/0009" tidak tertulis jelas di sana** untuk konsep ini. Maka untuk konsep yang
tak-tertulis itu, agent kembali ke eksplorasi. Pesan: **authority yang benar pun tidak selalu
cukup; setiap celah pengetahuan jadi pintu masuk spiral.**

### Mode D — KONTRAK JAWAB DILANGGAR (angka tanpa SQL)

**Bukti:** A `v5-predikat-trim/UAT-BAYI-2.md` turn-1

```
turn 1: 0 SQL, diakhiri request_clarification
"jawaban akhir": "172 aktif / 84 tidak berlaku / 256 total"   ← angka konkret tanpa query!
```

Agent mengeluarkan angka kuantitatif pada turn klarifikasi tanpa satu pun SQL di belakangnya —
melanggar kontrak paling keras. Ini failure mode berbeda: bukan spiral, melainkan **fabrikasi**.
Angka turn-2 (setelah SQL jalan) berbeda total (265/864) → angka turn-1 murni halusinasi.

---

## 4. Akar penyebab tunggal: kegagalan langkah RESOLUSI

Empat mode di atas berbeda di permukaan, tapi bermuara ke satu titik:

> **Langkah 2 (RESOLUSI) adalah mata air.** Selama agent tidak memegang kode kanonik yang tepat
> untuk konsep yang ditanyakan saat memulai SQL, ia otomatis mengubah tugas menjadi eksplorasi —
> dan eksplorasi lewat ILIKE/probing **tidak punya kriteria berhenti**.

Kenapa eksplorasi tak konvergen (bukan kebetulan):

| Sifat data BPOM | Konsekuensi bagi eksplorasi |
|---|---|
| Nama produk tak kanonik ("formula bayi" vs "susu lanjutan" vs brand) | ILIKE pada `nama` meleset tak tentu |
| `data_dictionary` deskripsi sparse | ILIKE pada `deskripsi` banyak false-negative |
| `klasifikasi_id` multi-makna (301/302/305 beda kategori) | tebak kode = kena tabrakan |
| Kode `jenis_pangan` berbeda per sistem (ERBA 1301 vs ERLA 604) | satu sistem tak bisa dipakai ke sistem lain |

Setiap sudut yang dicoba agent membuka lima sudut baru → spiral 22–32 SQL. Agent **berhenti
karena kelelahan/budget, bukan karena selesai**.

---

## 5. Anatomi loop yang bekerja (varian A — control case)

A bukan lebih pintar; A **patuh pada satu instruksi kunci**: baca authority yang tepat sebelum
SQL. Trace `v5-predikat-trim/UAT-BAYI-1.md`:

```
load_skill → list_context → read predikat → read filter_code
           → clarify(strict vs broad)      ← ambigu dikunci jadi 1 target
           → 1 SQL dgn kode 1301/1302       ← kode kanonik, langsung tepat
           → jawab
```

Membaca `filter_code_reference.md` memberi kode kanonik → 1 query cukup → tak ada eksplorasi →
klarifikasi mengunci ambigu. **A membuktikan loop normatif tercapai**, dan kuncinya minimal:
satu coupling (skill ⟺ baca-authority-yang-tepat).

Catatan jujur: A sendiri tidak imun — pada konsep yang tak-tertulis di authority (Mode C,
`dicabut`), A juga spiral 22 SQL. Jadi A bekerja **saat authority memenuhi konsep**, bukan karena
prosedurnya lebih hebat.

---

## 6. Mekanika kegagalan sekunder (turunan)

| # | Mekanika pecah | Bukti | Konsekuensi |
|---|---|---|---|
| M1 | **Skill-authority decoupling** — skill termuat, authority tak dibaca | C BAYI-1 (0 file) | prosedur ada, pengetahuan tak ada |
| M2 | **Salah authority** — baca context, tapi bukan yang punya kode | Baseline BAYI-3 (PHASE-0 trio) | tetap eksplorasi |
| M3 | **Authority tak lengkap utk konsep** — file benar, kode konsep tak tertulis | A DICABUT-1 | spiral lokal pada konsep itu |
| M4 | **Tanpa kriteria konvergensi** — tak tahu kapan berhenti eksplorasi | C: 5+ pivot method | spiral 22–32 SQL |
| M5 | **Method drift** — tiap pivot = start baru, bukan refinement | C: dict→klasifikasi→name→kategori_pangan | tak ada akumulasi |
| M6 | **Klarifikasi skip** — tak tanya strict/broad | C, baseline: 0 klarifikasi vs A: 1 | target ambigu → kejar banyak sekaligus |
| M7 | **Gate diabaikan** — prosedur seremonial tak ditaati | C (gated ≤6 SQL) laku 32 SQL | gate = ornamen, bukan enforcement |
| M8 | **Fabrikasi** — angka tanpa SQL | A BAYI-2 turn-1 (172/256 dgn 0 SQL) | kontrak jawab dilanggar |

---

## 7. Paradoks varian C — lebih banyak gerbang ≠ lebih banyak disiplin

C adalah varian "GATED" (5 gerbang + budget ≤6 SQL). **Justru C yang paling parah spiral-nya**
(32 SQL) — melanggar budgetnya sendiri. A ("minimal", tanpa gate keras) justru paling taat (1 SQL).

Implikasi mekanika: **disiplin problem-solving bukan fungsi jumlah gerbang**, melainkan
**apakah instruksi intinya ditaati**. Instruksi sederhana A ("READ predikat + filter_code
sebelum SQL") ditaati; upacara 5-gerbang C di-skip. **Menambah gate tidak memperbaiki loop** —
malah mungkin melatih agent untuk "lewati prosedur" ketika prosedurnya terlalu berat.

---

## 8. Mode kegagalan terpisah: NON-EKSEKUSI (0-detik)

Banyak sel di B/C/baseline: `0 turns · 0 SQL · 0.0s` — loop **tak pernah dimulai**. Ini **bukan**
masalah problem-solving; ini **failure infra/init** (kemungkinan exception awal / race / batas
resource). Audit ini mencatatnya sebagai failure mode tersendiri, bukan menyimpulkannya sebagai
"sistem salah jawab." Wajib didiopsis terpisah karena mengotori setiap perbandingan antar-varian.

---

## 9. Atribusi: perubahan headline/description = kontribusi nyata (dibuktikan baseline)

**Bukti langsung (baseline, sebelum vs sesudah):** mengubah satu baris headline tiap context +
satu baris `description` tiap skill pada baseline membuat hasil **lebih buruk** (0/4 pada set
BAYI, spiral 25 SQL di BAYI-3). Jadi perubahan headline/description **kontribusi nyata**, bukan
confound timing. Ini mengoreksi catatan awal yang menyebut "header tak terbukti" — sekarang
terbukti pada baseline.

**Tapi bukan satu-satunya faktor.** A dan C punya **context byte-identik** (header sama persis,
terverifikasi via `diff`), namun A=1 SQL sedangkan C=32 SQL pada soal yang sama. Artinya headline
**bukan variabel tunggal** — **compliance membaca authority** (A taat, C skip) juga menentukan
outcomenya, bahkan saat headlinenya identik.

**Sintesis mekanisme (gabungan bukti baseline + A-vs-C):**

```
outcome = HEADLINE/DESCRIPTION (trigger)  ×  COMPLIANCE membaca authority (prosedur)
```

- Headline baik + compliance tinggi → loop sehat (A BAYI-1/2/3: 1–3 SQL).
- Headline berubah/jelek → authority salah pilih → spiral (baseline BAYI-3: 25 SQL, salah authority).
- Headline identik tapi compliance rendah → tetap spiral (C BAYI-1: 32 SQL, skip read).

**Kesimpulan:** perubahan headline/description adalah **tuas berlever-tinggi** karena ia gerbang
upstream (menentukan authority mana yang dipilih). Tapi ia **perlu dilengkapi compliance** —
mengandalkan headline saja tak cukup, karena agent bisa skip read meski headline benar (kasus C).
Inilah yang membuat rekomendasi §10 #1 (paksa coupling, bukan andalkan headline) menjadi tuas utama.

---

## 10. Rekomendasi (level mekanika, bukan konten)

Diurutkan dari tuas berlever-tinggi ke rendah:

1. **Paksa coupling skill⟺authority (M1, M2).** Body skill `bpom-analyst` langkah RESOLVE
   **harus** `read_project_file('context/filter_code_reference.md')` + `context/predikat.md`
   **sebelum** `execute_sql` apa pun diizinkan. Ini bukan gate prose — eksekusi literal yang
   tak bisa di-skip. A sudah membuktikan pola ini bekerja.
2. **Lengkapi authority untuk konsep berisiko (M3).** Mapping status `dicabut/dibatalkan`
   wajib tertulis eksplisit di `filter_code_reference.md` (kode per sistem). Setiap konsep
   yang sempat memicu spiral = lubang yang harus ditambal di authority, bukan di prosedur.
3. **Tambah kriteria konvergensi (M4, M5).** Jika 2 query ILIKE/probing berturut-turut tak
   konvergen → WAJIB kembali baca authority atau klarifikasi, **bukan** pivot method baru.
   Pivot tanpa akumulasi = akar spiral.
4. **Jangan tambah gate (M7).** Bukti C: gate diabaikan. Sederhanakan ke instruksi imperatif
   tunggal seperti A.
5. **Verifikasi read via instrumentasi (audit lanjut).** Jika `load_skill('bpom-analyst')`
   terjadi tapi 0 `read_project_file` di turn itu → flag anomali di trace.
6. **Cegah fabrikasi (M8).** Turn klarifikasi dilarang mengandung angka kuantitatif (0 SQL di
   turn = 0 angka di turn itu).
7. **Diagnosa non-eksekusi (§8) sebelum verdict apa pun** — ini confound terbesar.

---

## 11. Lampiran bukti — rujukan trace

| Klaim | Rujukan |
|---|---|
| Loop sehat (1 SQL, kode benar) | `v4/.../v5-predikat-trim/UAT-BAYI-1.md` |
| Mode A: resolusi di-skip (32 SQL, 0 context) | `v4/.../after-forecast-anomaly-refactor-v2/UAT-BAYI-1.md` |
| Mode B: salah authority (25 SQL, 3 file PHASE-0) | `v4/.../forecast anomaly/UAT-BAYI-3.md` |
| Mode C: authority tak lengkap (22 SQL, dicabut) | `v4/.../v5-predikat-trim/UAT-BAYI-DICABUT-1.md` |
| Mode D: fabrikasi (angka dgn 0 SQL) | `v4/.../v5-predikat-trim/UAT-BAYI-2.md` turn-1 |
| Skill load by NAME (bukan description) | `pydantic_deep/toolsets/skills/toolset.py:364` |
| Skill trigger = `<available_skills>` always-on | `pydantic_deep/toolsets/skills/toolset.py:460-486` |
| Context hint = baris-1 stripped `#`, potong 140 | `seeknal/src/seeknal/ask/agents/tools/list_context_files.py:92-109` |

---

## 12. Open decisions (perlu konfirmasi pemilik)

1. Eksperimen isolasi header: ubah header SAJA, set soal & varian konstan — untuk mengonfirmasi
   atau membantah atribusi header secara definitif (§9).
2. Apakah rekomendasi #1 (paksa read authority) diimplementasikan sebagai **instruksi skill**
   (kontekstual, bisa di-skip lagi) atau **enforcement harness** (tak bisa di-skip)?
3. Autoritas `dicabut/dibatalkan` (M3) — kode kanonik per sistem perlu dikonfirmasi dari
   `data_dictionary` sebelum ditambal ke `filter_code_reference.md`.
