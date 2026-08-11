# seeknal-bpom-neo: Decision Operating System Enhancement

**Document type:** Implementation Plan
**Project:** seeknal-bpom-neo (BPOM RPO Analytics Agent)
**Status:** Ready for Implementation
**Date:** 2026-06-09
**Scope:** `SEEKNAL_ASK.md` · `seeknal/skills/bpom-analyst/SKILL.md` · `context/intent_mapping.md` · `seeknal/skills/evidence-auditor/SKILL.md`

---

## 1. Latar Belakang

Audit manual 9 Juni 2026 (61 test case, 96.72% pass rate) mengidentifikasi bahwa masalah yang tersisa **bukan tentang kurangnya knowledge** — melainkan tentang lemahnya **decision-making**.

Dokumen-dokumen sebelumnya (03 dan 04 Juni 2026) sudah memperkuat execution engine: SQL yang lebih tepat, reasoning yang lebih kuat, information-centric approach. Enhancement ini mengerjakan lapisan yang berbeda: **lapisan sebelum execution**.

### 1.1 Paradigma Shift

Selama ini sistem dibangun sebagai **BPOM Agent** — reflex pengembangan: tambah context, tambah recipe, tambah contoh, tambah glossary.

Enhancement ini mengubah cara pandang: sistem ini adalah **Decision Operating System** untuk BPOM Agent — reflex pengembangan: tambah decision capability, bukan knowledge.

| BPOM Agent mindset | Decision OS mindset |
|---|---|
| Tambah recipe baru untuk case baru | Perkuat framework agar bisa handle case baru tanpa recipe baru |
| Tambah contoh pertanyaan | Perkuat semantic commitment agar format pertanyaan tidak mempengaruhi interpretasi |
| Tambah kode produk baru | Ajarkan cara discovery yang benar |
| Simpan snapshot data di context | Ajarkan cara memvalidasi dari data itu sendiri |

### 1.2 Root Cause Tunggal

Semua masalah yang tersisa berasal dari **tidak adanya orchestration layer** sebelum execution engine:

| Masalah yang ditemukan | Root cause |
|---|---|
| Inkonsistensi — pertanyaan sama, format berbeda, hasil berbeda | Tidak ada semantic commitment sebelum SQL |
| Follow-up kehilangan konteks turn sebelumnya | Tidak ada State Comparison Engine |
| Evidence di-recompute padahal sudah trusted | Tidak ada State Comparison Engine (treat semua sebagai NEW_QUESTION) |
| Jawaban dalam bahasa Inggris walaupun user Indonesia | Tidak ada enforcement di titik output; context English mendominasi |
| Overthinking pada "halo", "sip", "terima kasih" | Tidak ada conversation routing |
| Discovery query berlebihan untuk hal yang ada di glossary | Tidak ada resolution hierarchy dengan stop condition |

---

## 2. Arsitektur Target

Menambahkan tiga layer baru **di atas** workflow yang sudah ada, bukan menggantikannya.

```
USER INPUT
    │
    ▼
[CONVERSATION GATE]                        ← BARU
Klasifikasi input sebelum apapun
    ├── SMALL_TALK   → jawab natural
    ├── META         → jelaskan kapabilitas
    ├── OUT_OF_SCOPE → nyatakan keterbatasan
    └── DATA_QUESTION
            │
            ▼
    [DECISION LAYER]                       ← BARU
    │
    ├─ Intent Extraction
    │   Semantic Commitment Block
    │   (Entity · Operation · Dimensions · Time · Shape)
    │
    └─ State Comparison Engine
        Bandingkan intent baru vs state percakapan
        Output: NEW_QUESTION / MODIFY_SCOPE / EXTEND_SCOPE / EXPLAIN_EVIDENCE
            │
            ▼
    [INFORMATION NEED RESOLUTION]          ← REFRAME
    Ordered authority dengan stop condition:
    Ontology → Dictionary → Schema → Discovery → Clarification
            │
            ▼
    [EXISTING WORKFLOW]                    ← TIDAK BERUBAH
    PHASE 0 → CAPTURE* → RESOLVE → PLAN → EXECUTE → REFLECT*
    (* penambahan kecil: Semantic Commitment Block & SCE output check)
            │
            ▼
    [GENERATE]
    + Communication Alignment Contract     ← BARU
      (language match · terminology mirror · domain terms unchanged)
```

---

## 3. Perubahan per File

### 3.1 SEEKNAL_ASK.md

**Jenis perubahan:** Restrukturisasi major — tambah 3 section baru, hapus 1 section, modifikasi 1 section.

---

#### HAPUS — §2 "Critical Data State"

**Apa yang dihapus:** Seluruh konten statistik operasional — row counts, persentase distribusi, angka snapshot apapun yang mencerminkan kondisi database pada waktu tertentu.

**Alasan:**
Statistik operasional berubah setiap transaksi masuk. Ketika disimpan di context sebagai "fakta", dua hal berbahaya terjadi:
1. Agen bisa melakukan sanity check terhadap angka yang sudah kadaluarsa dan salah memvalidasi hasil query yang sebenarnya benar
2. Agen bisa salah kalibrasi ekspektasi — angka "lebih kecil dari yang tersimpan" dianggap error, padahal itu memang kondisi database saat ini

**Konsep:** Context menyimpan *cara berpikir*, bukan *isi database hari ini*. Statistik operasional bukan system knowledge — mereka adalah **validation documentation** yang harus dijaga terpisah dan diupdate secara berkala, bukan dimasukkan ke runtime context.

**Yang dipertahankan dari §2:**
- Column type information (ERBA = ALL TEXT, ERLA = TIMESTAMP/BIGINT) — ini schema contract yang stabil, bukan statistik
- System date range coverage (ERBA: mulai Sep 2022, ERLA: mulai 2012) — ini structural boundary, tidak berubah kecuali ada migrasi sistem

Semua angka lain — row counts, persentase NULL, contoh nilai spesifik — dipindahkan ke validation documentation (audit notes, bukan runtime context).

**Hasil setelah hapus:** Agen tidak lagi bisa "tersesat" oleh snapshot yang kadaluarsa. Validasi dilakukan dari data itu sendiri, bukan dari ingatan context.

---

#### TAMBAH — §0 "Conversation Gate" (section paling awal)

**Apa yang ditambahkan:** Klasifikasi input sebelum workflow apapun berjalan.

**Alasan:**
Saat ini "halo" diperlakukan hampir sama dengan "berapa NIE 2024?" — keduanya bisa memicu PHASE 0 context load, tool calls, SQL planning. Ini menghabiskan token, memperlambat respons, dan menghasilkan overthinking untuk input yang tidak butuh itu.

**Konsep:** "Apakah saya perlu berpikir?" harus dijawab sebelum "Apa jawabannya?"

**5 kategori output:**

| Kategori | Trigger | Tindakan |
|---|---|---|
| `SMALL_TALK` | Greeting, acknowledgment, terima kasih, feedback singkat | Jawab natural, tidak trigger workflow apapun |
| `META` | Pertanyaan tentang kapabilitas sistem, cara kerja, apa yang bisa dilakukan | Jelaskan kapabilitas tanpa SQL |
| `OUT_OF_SCOPE` | Domain pemeriksaan, pengujian, balai, inspeksi (tidak terkoneksi) | Nyatakan keterbatasan secara jujur, jangan query |
| `CLARIFICATION` | User merespons pertanyaan klarifikasi dari turn sebelumnya | Lanjutkan dari titik yang tertunda |
| `DATA_QUESTION` | Pertanyaan tentang data registrasi BPOM (NIE, permohonan, produk, dll.) | Lanjut ke Decision Layer |

**Hasil setelah tambah:** Latency berkurang untuk non-data input; sistem tidak overthink "halo".

---

#### TAMBAH — §0.5 "Decision Layer"

**Apa yang ditambahkan:** Dua mekanisme yang berjalan berurutan: Intent Extraction dan State Comparison Engine.

**Alasan:**
Masalah inkonsistensi (pertanyaan sama, format berbeda, hasil berbeda) dan masalah lost context (follow-up tidak mewarisi scope) berasal dari sumber yang sama: agen langsung masuk ke execution tanpa pernah membuat **komitmen eksplisit** tentang apa yang sedang dicari dan apa yang sudah diketahui.

**Konsep inti — Intent Extraction sebelum State Comparison:**

"Follow-up" bukan sifat dari sebuah input. "Follow-up" adalah **kesimpulan** dari proses perbandingan antara intent baru dengan state lama. Agen tidak bisa mengetahui apakah sesuatu adalah follow-up sebelum ia tahu intent barunya. Urutan yang benar: ekstrak intent dulu, baru bandingkan dengan state.

Ini berbeda fundamental dari pendekatan sebelumnya ("Evidence Continuity") yang hanya bertanya "apakah ada evidence sebelumnya?" — karena pertanyaan itu hampir selalu dijawab "ya", sehingga semua pertanyaan berisiko diperlakukan sebagai follow-up.

---

**Mekanisme 1 — Intent Extraction (Semantic Commitment):**

Sebelum SQL apapun, agen wajib mengisi blok ini dan memperlakukannya sebagai komitmen semantik yang mengikat:

```
Entity:       [NIE / PERMOHONAN / BTP / PERUSAHAAN]
Operation:    [COUNT / TREND / BREAKDOWN / TOP / COMPARE / LIST]
Dimensions:   [list semua dimensi — tandai DEPENDENT atau INDEPENDENT]
Time Scope:   [tahun spesifik / rentang / ALL-TIME — eksplisit, bukan implisit]
Output Shape: [scalar / 1D-time / 1D-dim / 2D / multi-query synthesis]
```

Ketika blok ini sudah terisi, variasi format pertanyaan tidak lagi relevan — "(10 tahun terakhir)" dan "10 tahun terakhir" menghasilkan blok yang identik karena agen sudah komit pada **makna**, bukan **surface form**. Inilah solusi untuk masalah inkonsistensi.

---

**Mekanisme 2 — State Comparison Engine:**

Setelah Intent Extraction, engine ini membandingkan intent baru dengan state percakapan secara komponen per komponen, lalu mengklasifikasikan hasilnya:

```
Perbandingan komponen:
  Entity:       sama / berbeda
  System:       sama / berbeda
  Year scope:   sama / berbeda
  Dimensions:   sama / subset / superset / berbeda
  Filters:      sama / berbeda
```

Output klasifikasi:

| Klasifikasi | Kondisi | Tindakan |
|---|---|---|
| `NEW_QUESTION` | Entity berbeda, atau scope berbeda secara fundamental | Full workflow dari awal; tidak warisi apapun |
| `MODIFY_SCOPE` | Satu parameter berbeda, yang lain sama | Delta query saja; warisi semua komponen yang sama |
| `EXTEND_SCOPE` | Dimensi baru ditambahkan, entity + year + system sama | Query tambahan; warisi komponen yang overlap |
| `EXPLAIN_EVIDENCE` | Semua komponen sama; user bertanya tentang hasil, bukan data baru | Tidak perlu query; gunakan evidence yang sudah trusted |

**Perbedaan kritis State Comparison Engine vs Evidence Continuity:**

Evidence Continuity bertanya: "Apakah ada evidence sebelumnya?" — hampir selalu "ya", berisiko memperlakukan semua pertanyaan sebagai follow-up.

State Comparison Engine bertanya: "Apakah evidence sebelumnya **masih relevan** terhadap intent baru?" — ini adalah perbandingan semantik, bukan keberadaan. Hasilnya berupa klasifikasi yang eksplisit, bukan asumsi biner.

Evidence dari turn sebelumnya hanya dipakai jika klasifikasi bukan `NEW_QUESTION`. Untuk `NEW_QUESTION`, agen selalu mulai dari awal terlepas dari ada atau tidaknya evidence lama.

**Hasil setelah tambah:**
- Konsistensi parsing meningkat — semantic commitment mengeliminasi pengaruh format
- Follow-up accuracy meningkat — klasifikasi eksplisit menggantikan deteksi biner
- Re-query berkurang — EXPLAIN_EVIDENCE dan MODIFY_SCOPE tidak perlu full query
- False follow-up hilang — NEW_QUESTION selalu diproses dari awal

---

#### MODIFIKASI — §4 "Information Taxonomy" → "Information Need Resolution Hierarchy"

**Apa yang diubah:** Framing dari "di mana mencari informasi" (lokasi) menjadi "bagaimana menyelesaikan kebutuhan informasi" (resolusi) dengan urutan otoritas yang eksplisit dan stop condition per level.

**Alasan:**
Taxonomy saat ini mengajarkan *lokasi* — "untuk tahu X, baca file Y". Ini adalah **Intent Pattern Matching**: tahu pattern pertanyaannya, tahu file-nya. Pendekatan ini gagal ketika pertanyaan tidak cocok dengan pattern yang dikenal.

Yang dibutuhkan adalah **Information Need Resolution**: agen tahu apa yang ia butuhkan, dan tahu *dari mana otoritas untuk memenuhi kebutuhan itu berasal* — terlepas dari apakah pertanyaannya dikenal atau tidak.

**Perbedaan Intent Pattern Matching vs Information Need Resolution:**

| Intent Pattern Matching | Information Need Resolution |
|---|---|
| "Pertanyaan tentang X → baca file Y" | "Butuh tahu Z → mulai dari level otoritas tertinggi" |
| Gagal pada pertanyaan yang belum dikenal | Bisa handle pertanyaan baru dengan framework yang sama |
| Menambah pattern = menambah maintenance | Framework tetap sama, hanya konten yang berkembang |

**Konsep:** "Agen gagal bukan karena tidak tahu jawabannya — tetapi karena mencari informasi yang benar di tempat yang salah, atau di level yang salah."

**Resolution Hierarchy (ordered, dengan stop condition):**

```
Level 1 — Business Ontology  (business_glossary.md)
  Gunakan untuk: definisi konsep, makna entitas, perbedaan ERBA/ERLA
  Stop jika: konsep sudah jelas, tidak butuh kode spesifik
  Jangan skip ke level berikutnya jika level ini sudah cukup

Level 2 — Dictionary  (code_resolution.md + data_dictionary)
  Gunakan untuk: arti kode, resolve ke label, mapping kategori
  Stop jika: kode sudah resolve ke label yang dibutuhkan
  Jangan query data hanya untuk verify kode yang sudah ada di dictionary

Level 3 — Schema  (data_architecture.md)
  Gunakan untuk: tabel yang tepat, kolom yang tepat, join rules, UNION topology
  Stop jika: tabel, kolom, dan join sudah diketahui
  Jangan pergi ke discovery jika schema sudah cukup

Level 4 — Data Discovery  (exploratory query)
  Gunakan untuk: kode segment yang tidak ada di glossary, pola data yang tidak terdokumentasi
  Stop jika: discovery query sudah menemukan jawaban
  Pattern: nama_kategori ILIKE → konfirmasi dengan sample

Level 5 — User Clarification
  Gunakan hanya jika: Level 1-4 tidak cukup DAN ambiguitasnya adalah ambiguitas bisnis
  Jangan gunakan untuk: ambiguitas teknis (itu tangani sendiri)
  Jangan gunakan untuk: lazy shortcut menghindari discovery
```

**Hasil setelah modifikasi:** Discovery query hanya dijalankan ketika benar-benar dibutuhkan; agen tidak "menghafal ulang" sesuatu yang sudah ada di context.

---

#### TAMBAH — §6 "Communication Alignment Contract"

**Apa yang ditambahkan:** Kontrak bagaimana agen berkomunikasi dengan user.

**Alasan:**
Seluruh reasoning terjadi dalam bahasa Inggris (semua context files English). Tanpa instruksi eksplisit di titik output, agen menjawab dalam bahasa yang dominan di context-nya — yaitu Inggris. Instruksi di awal session tidak cukup karena terdilute setelah ratusan token English reasoning.

**Konsep:** Bahasa context bukan bahasa komunikasi. Agen seperti analis bilingual: membaca manual teknis dalam English, tapi mempresentasikan ke klien dalam bahasa klien.

**Tiga prinsip Communication Alignment:**

1. **Language match:** Detect bahasa pertanyaan user. Tulis seluruh narasi dalam bahasa yang sama. Context files English adalah working tools internal — tidak menentukan bahasa output.

2. **Terminology mirroring:** Gunakan istilah yang sama persis dengan yang dipakai user.
   - User pakai "NIE" → pakai "NIE", bukan "Nomor Izin Edar"
   - User pakai "izin edar" → pakai "izin edar", bukan "NIE"
   - User pakai "registrasi" → pakai "registrasi", bukan "permohonan"

3. **Domain terms unchanged:** Proper nouns dan istilah domain sebagaimana muncul di database tidak diterjemahkan ke bahasa apapun:
   - AMDK, BTP, NIE, BPOM, ERBA, ERLA
   - Nama produk, nama kategori, nama perusahaan, nama daerah

**Hasil setelah tambah:** Jawaban dalam bahasa yang sesuai; terminologi natural mengikuti cara user berbicara; istilah teknis domain tidak berubah.

---

### 3.2 seeknal/skills/bpom-analyst/SKILL.md

**Jenis perubahan:** Tiga penambahan kecil di tiga phase berbeda.

---

#### TAMBAH di PHASE 1 CAPTURE — Semantic Commitment Block

**Apa yang ditambahkan:** Output wajib di awal CAPTURE sebelum Scope line.

**Alasan:**
CAPTURE saat ini menghasilkan satu "Scope line" (`Scope: entity=… · system=… · year=…`). Ini baik untuk SQL planning tapi tidak cukup untuk konsistensi parsing. Scope line terlalu compact — agen bisa sampai ke scope yang benar tapi melalui parsing yang salah.

**Konsep:** Dengan memaksa agen menulis Semantic Commitment Block secara eksplisit, parsing menjadi **deterministik** — tidak bergantung pada bagaimana user memformat kalimat (kurung, koma, urutan kata).

**Format yang ditambahkan (sebelum Scope line):**
```
Intent:
  Entity:       [NIE / PERMOHONAN / BTP / PERUSAHAAN]
  Operation:    [COUNT / TREND / BREAKDOWN / TOP / COMPARE / LIST]
  Dimensions:   [list — tandai DEPENDENT atau INDEPENDENT]
  Time Scope:   [eksplisit — resolved dari pertanyaan atau DEFAULT=ALL-TIME]
  Output Shape: [scalar / 1D-time / 1D-dim / 2D / multi-query]
```

**Hubungan dengan Decision Layer:** Decision Layer di SEEKNAL_ASK.md menghasilkan Intent Extraction; Semantic Commitment Block di CAPTURE mengkonfirmasi dan memperluas intent itu sebelum SQL.

---

#### TAMBAH di PHASE 5 REFLECT — State Comparison Engine output check

**Apa yang ditambahkan:** Satu check wajib yang mengaitkan hasil State Comparison Engine ke keputusan re-query.

**Alasan:**
REFLECT saat ini hanya mengaudit evidence yang baru dieksekusi di turn ini. Tidak ada mekanisme untuk memanfaatkan evidence yang sudah trusted dari turn sebelumnya — sehingga agen cenderung re-query semua hal dari awal.

**Konsep:** State Comparison Engine sudah mengklasifikasikan hubungan antara intent baru dan state lama. REFLECT harus menggunakan hasil klasifikasi itu, bukan mengabaikannya.

**Check yang ditambahkan (sebelum audit checklist yang sudah ada):**
> Apa output State Comparison Engine untuk pertanyaan ini?
> - `EXPLAIN_EVIDENCE` → tidak ada query baru yang perlu diaudit; gunakan evidence turn sebelumnya langsung ke GENERATE
> - `MODIFY_SCOPE` atau `EXTEND_SCOPE` → audit hanya query delta yang baru dijalankan; evidence lama sudah trusted
> - `NEW_QUESTION` → audit penuh semua evidence turn ini

---

#### TAMBAH di PHASE 6 GENERATE — Communication Alignment Enforcement

**Apa yang ditambahkan:** Communication Alignment Contract sebagai blok pertama di GENERATE.

**Alasan:**
Instruksi bahasa di SEEKNAL_ASK.md (awal session) terdilute setelah ratusan token reasoning dalam English. Placement di GENERATE — titik terdekat ke output — memastikan enforcement yang efektif.

**Prinsip proximity:** Instruksi yang paling dekat ke titik output memiliki bobot paling tinggi dalam attention. GENERATE adalah titik tersebut.

**Yang ditambahkan (blok pertama di GENERATE):**
> Context files berbahasa Inggris adalah working tools. Bahasa context TIDAK menentukan bahasa output. Tulis seluruh narasi dalam bahasa pertanyaan user. Gunakan terminologi yang sama dengan yang dipakai user. Pertahankan domain terms (AMDK, BTP, NIE, BPOM, ERBA, ERLA, nama produk, nama kategori) tanpa terjemahan.

---

### 3.3 context/intent_mapping.md

**Jenis perubahan:** Penambahan kecil di Step 0.

---

#### TAMBAH di Step 0 — Structural Normalization

**Apa yang ditambahkan:** Normalisasi format struktural sebelum normalisasi typo.

**Alasan:**
Step 0 saat ini menormalisasi typo dan sinonim informal ("jumlh" → COUNT, "izin edr" → NIE) tapi tidak menormalisasi **format struktural** pertanyaan. Akibatnya, variasi punctuation — terutama tanda kurung — bisa menghasilkan parsing yang berbeda.

**Konsep:** Tanda kurung dalam bahasa natural memberi kesan "aside" atau "opsional". LLM memberi bobot lebih rendah pada konten dalam kurung. Normalisasi struktural menghilangkan perbedaan ini sebelum parsing semantik.

**Yang ditambahkan (sebelum normalisasi typo yang sudah ada):**
```
Langkah 0a — Normalisasi struktural (sebelum apapun):
- Konten dalam (...) atau [...] diperlakukan setara dengan konten di luar kurung
  Contoh: "tren per tahun (10 tahun terakhir)" = "tren per tahun 10 tahun terakhir"
- Tanda koma, "dan", "serta", "maupun" adalah pemisah dimensi yang setara
  Contoh: "risiko, skala, tren" = "risiko dan skala dan tren"
- Urutan penyebutan dimensi tidak mempengaruhi interpretasi
Strip kurung, pertahankan konten. Baru lanjut ke normalisasi typo.
```

---

### 3.4 seeknal/skills/evidence-auditor/SKILL.md

**Jenis perubahan:** Hapus satu baris, tambah satu alternatif.

---

#### HAPUS di §E — Semua Statistik Operasional

**Apa yang dihapus:** Semua angka yang mencerminkan kondisi database pada waktu tertentu — row counts per tabel, persentase distribusi, angka contoh dari audit sebelumnya.

**Alasan:**
Angka-angka ini dipakai sebagai referensi sanity check di REFLECT. Ini adalah penggunaan yang berbahaya: ketika database berkembang, angka ini kadaluarsa dan agen bisa menolak hasil query yang benar karena tidak sesuai ekspektasi yang sudah usang.

**Konsep:** System knowledge adalah *cara memverifikasi*, bukan *hasil verifikasi yang tersimpan*. Statistik operasional termasuk **validation documentation** yang dijaga terpisah dan diupdate berkala — bukan runtime context yang selalu dibaca agen.

**Yang menggantikan prinsip verifikasi:**
> "Jika result = 0 dan ada keraguan, verifikasi dengan `SELECT COUNT(*) FROM [tabel]` sebelum menyimpulkan data tidak tersedia. Jangan bandingkan angka hasil query dengan angka yang tersimpan di context — data berubah."

---

## 4. Yang Tidak Diubah

Berikut komponen yang **sengaja tidak disentuh** — mengubahnya akan mengurangi kualitas sistem:

| Komponen | Alasan tidak diubah |
|---|---|
| Core 6-phase workflow (PHASE 0-6) | Sudah benar sebagai execution engine; perubahan di lapisan atas, bukan workflow |
| Query recipes R1-R11 | Sudah cukup sebagai reference; menambah R12+ akan menciptakan pattern matching yang rigid |
| content/business_glossary.md | Domain knowledge stabil dan benar |
| content/data_quality_rules.md (logika) | SQL rules sudah benar; hanya hapus persentase snapshot seperti "22.7% NULL" |
| content/code_resolution.md | Pendekatan sudah benar |
| content/data_architecture.md | Structural knowledge stabil |
| Behavioral contracts di SEEKNAL_ASK.md §1 | Non-negotiable mappings harus tetap sebagai early contract |

**Yang dihapus hanya dari data_quality_rules.md:** Persentase dan angka snapshot yang berubah seiring data ("22.7% of rows have NULL tanggal", contoh angka spesifik "2,498 vs 46").

---

## 5. Ringkasan Perubahan

| File | Tambah | Hapus | Modifikasi |
|---|---|---|---|
| `SEEKNAL_ASK.md` | §0 Conversation Gate · §0.5 Decision Layer (Intent Extraction + State Comparison Engine) · §6 Communication Alignment Contract | §2 semua statistik operasional (row counts, distribusi, persentase) | §4 reframe ke Information Need Resolution Hierarchy |
| `bpom-analyst/SKILL.md` | Semantic Commitment Block di PHASE 1 · State Comparison Engine output check di PHASE 5 · Communication Alignment enforcement di PHASE 6 | — | — |
| `intent_mapping.md` | Structural normalization (Step 0a) sebelum typo normalization | — | — |
| `evidence-auditor/SKILL.md` | Prinsip verifikasi via query langsung | Semua statistik operasional di §E | — |
| `data_quality_rules.md` | — | Semua angka snapshot: persentase distribusi, contoh angka spesifik dari audit | — |

**Catatan:** Statistik operasional yang dihapus dari runtime context dipindahkan ke **validation documentation** (audit notes terpisah) — bukan dihapus sepenuhnya dari ekosistem, tapi tidak boleh ada di context yang dibaca agen saat runtime.

---

## 6. Verifikasi Setelah Implementasi

Test case yang harus dijalankan untuk memvalidasi perubahan:

| Test | Ekspektasi |
|---|---|
| Kirim "Halo" | Tidak trigger PHASE 0 context load; jawab natural |
| Tanya domain pemeriksaan/balai | Respon jujur tanpa query kosong |
| Pertanyaan sama dengan format berbeda (kurung vs tanpa kurung) | Semantic Commitment Block identik untuk keduanya |
| 4-turn conversation: establish NIE 2024 → tanya breakdown per daerah | Turn 2 tidak re-query NIE 2024; gunakan evidence dari turn 1 |
| Pertanyaan dalam Bahasa Indonesia | Seluruh narasi Indonesia; AMDK, BTP, NIE tetap tidak diterjemahkan |
| "berapa NIE AMDK?" | Jawaban pakai "NIE AMDK", bukan "Nomor Izin Edar Air Minum Dalam Kemasan" |
| Segment tidak ada di glossary | Jalankan discovery query; tidak skip ke user clarification dulu |
| Segment ada di glossary (AMDK) | Tidak jalankan discovery query; langsung ke schema level |
