# seeknal-bpom-neo: Follow-Up Inheritance Refinement — "Inherit Answers, Re-derive Methods"

**Document type:** Implementation Record (perbaikan regresi)
**Project:** seeknal-bpom-neo (BPOM RPO Analytics Agent)
**Status:** Implemented (2 putaran — lihat §9 untuk putaran 2 pasca-run 2026-06-11)
**Date:** 2026-06-11
**Scope:** `SEEKNAL_ASK.md` · `seeknal/skills/bpom-analyst/SKILL.md` · `context/business_glossary.md` · `context/data_quality_rules.md` · `context/code_resolution.md` · `context/query_recipes.md`
**Mengamandemen:** `docs/planning/2026-06-09-decision-operating-system.md` (§0.5 State Comparison Engine)

---

## 1. Latar Belakang

Decision Operating System (9 Juni 2026) menambahkan tiga layer keputusan di atas execution
engine: Conversation Gate, Decision Layer (Intent Extraction + State Comparison Engine), dan
Communication Alignment. Tujuannya benar dan tetap dipertahankan.

Namun setelah Decision OS aktif, **akurasi multiturn turun tajam — khusus pada aspek follow-up
question**, sementara singleturn tetap tinggi. Dokumen ini mencatat diagnosis dan perbaikan
yang dilakukan, dengan tetap setia pada filosofi Decision OS: **ajarkan cara berpikir, jangan
mentimbun jawaban di context.**

### 1.1 Bukti Regresi

Perbandingan run multiturn dengan struktur identik (13 skenario, 117 turn):

| Tanggal | SEEKNAL_ASK.md | Multiturn | Singleturn |
|---|---|---|---|
| 2026-05-26 | v3 (tanpa state layer) | **106/117 = 91%** | tinggi |
| 2026-06-09 | v4 Decision OS masuk (`a1c3b9e`) | — | 85–86% |
| 2026-06-10 | v4 Decision OS | **61/117 = 52%** | 85% |

Yang anjlok **hanya multiturn**. Singleturn — yang tidak punya turn sebelumnya untuk
diwarisi — tetap stabil. Ini menunjuk langsung ke mekanisme yang khusus dipakai follow-up.

*Catatan: sebagian gap 91%→52% juga disebabkan YAML test yang sudah usang (nilai assert lama
vs jawaban agent baru yang sebenarnya benar); itu sudah diperbaiki terpisah. Namun ada regresi
perilaku agent yang nyata dan independen, yang menjadi fokus dokumen ini.*

---

## 2. Root Cause Tunggal

State Comparison Engine sudah benar memisahkan *"apakah ada evidence?"* dari *"apakah evidence
masih relevan?"*. Tetapi ia **tidak membedakan dua jenis hal yang menumpuk antar-turn**, dan
memperlakukan keduanya sebagai "evidence" yang sama-sama bisa diwarisi:

| Jenis | Contoh | Sifat | Seharusnya |
|---|---|---|---|
| **JAWABAN (fakta)** | "NIE MR ERBA 2023 = 9.649" | hasil tervalidasi | ✅ boleh diwarisi |
| **METODE (reasoning)** | kolom `tanggal_aju`, "UMKM = 1+2", filter kode 5+8 | langkah berpikir | ❌ harus diturunkan ulang |

Aturan lama di §0.5 (*"Evidence from a prior turn is trusted and reusable without
re-querying"*) bersama instruksi skill (PHASE 1 *"inherit unchanged components, proceed to
delta only"* dan PHASE 5 *"do not re-audit"*) menyebabkan follow-up **mewarisi metode lama dan
melewati fase RESOLVE/REFLECT** — fase yang justru menegakkan kontrak data.

Akibatnya agent memperlakukan langkah reasoning lama (yang bisa salah) sebagai "fakta
terpercaya". Pilihan kolom/definisi/filter yang keliru di turn N menyebar diam-diam ke turn
N+1.

### 2.1 Bukti Penguat

Dari 6 bug perilaku yang teramati, **tiga terjadi padahal context-nya sudah benar**:

| Bug | Gejala | Context saat itu | Sumber |
|---|---|---|---|
| B-2 | permohonan pakai `tanggal_aju`, bukan `tanggal_bayar` | **sudah benar** | inheritance drift |
| B-3 | UMKM = Mikro+Kecil (Menengah hilang) | **sudah benar** (1,2,3) | inheritance drift |
| B-5 | filter ERLA salah pada gabungan NIE | **sudah benar** (R2) | inheritance drift |
| B-1 | label "Tinggi" tanpa prefix "Risiko" | gap ontologi | knowledge gap |
| B-4 | NIE BTP pakai `user_id`/`tanggal_aju` | implisit | knowledge gap |
| B-6 | "dibatalkan" memasukkan kode 8 | gap ontologi (kode 8 tak terdaftar) | knowledge gap |

Jika context benar tetapi agent tetap salah **hanya di follow-up** → satu-satunya penjelasan:
follow-up tidak membaca ulang context, ia mewarisi metode. Ini mengkonfirmasi akar masalah =
mekanisme inheritance, bukan kualitas context.

---

## 3. Paradigma Solusi

Tetap pada mindset Decision OS — perkuat *decision capability*, bukan tambah *knowledge*:

| Reflex hardcoding (ditolak) | Reflex teach-the-thinking (dipakai) |
|---|---|
| Tambah tabel invariant "UMKM = 1,2,3" ke kontrak | Ajarkan satu prinsip: metode selalu diturunkan ulang |
| Daftar larangan per kasus follow-up | Satu aturan umum berlaku ke semua kasus, termasuk yang baru |
| Simpan raw history sebagai memori | Pelihara ledger terdistilasi berisi jawaban+scope |

### 3.1 Prinsip Inti — "Inherit ANSWERS, re-derive METHODS"

> Inheritance berlaku untuk **jawaban** (angka tervalidasi untuk scope tertentu), tidak pernah
> untuk **metode** (pilihan kolom, definisi, filter, cast). Follow-up **tetap menjalankan
> RESOLVE** — menurunkan ulang cara menyusun query dari Information Need Resolution hierarchy —
> dan hanya memakai ulang jawaban turn sebelumnya sebagai input (mis. aritmetika lintas-turn).

Prinsip ini general: agent menerapkannya ke semua kasus, termasuk yang belum pernah ditemui.
Tidak ada enumerasi definisi di kontrak — definisi tetap hidup sebagai ontologi di
`business_glossary.md`, tempat yang benar, dan diturunkan ulang tiap turn.

### 3.2 State yang Benar — "Conversation Ledger"

State **tidak dihapus** — ekspektasi bahwa state membantu follow-up itu benar (mis. MT-005 T4
= 9.649 − 6.236 − 2 = 3.411 mustahil tanpa state). Yang diperbaiki: state harus berisi
**jawaban + scope, bukan metode**, dan State Comparison Engine membandingkan terhadap ledger
ringkas ini, bukan raw history yang makin noise dan dikompres harness.

---

## 4. Perubahan per File

### 4.1 SEEKNAL_ASK.md

**Jenis perubahan:** Modifikasi §0.5 State Comparison Engine — tambah prinsip inheritance dan
definisi Conversation Ledger.

#### MODIFIKASI — Tabel klasifikasi State Comparison Engine

**Sebelumnya:**
- `MODIFY_SCOPE` → "Delta query only; inherit all unchanged components"
- `EXTEND_SCOPE` → "Additional query only; inherit overlapping evidence"
- `EXPLAIN_EVIDENCE` → "No new query; proceed directly to GENERATE with prior evidence"

**Sesudah:**
- `MODIFY_SCOPE` / `EXTEND_SCOPE` → "**Run RESOLVE for this turn**, then a delta/additional
  query. Inherit prior **answers**; re-derive the **method**."
- `EXPLAIN_EVIDENCE` → dipertegas: hanya untuk penjelasan/aritmetika atas jawaban yang sudah
  ada di ledger — **never when a new number is required**.

#### TAMBAH — Prinsip "Inherit ANSWERS, re-derive METHODS"

Tabel eksplisit yang membedakan ANSWER (fakta, boleh diwarisi) vs METHOD (reasoning, selalu
diturunkan ulang), dengan penegasan: *"Treating a prior method as trusted fact is the cause of
follow-up drift."*

#### TAMBAH — Definisi Conversation Ledger

Mengganti frasa berbahaya *"Evidence from a prior turn is trusted and reusable without
re-querying"*. State Comparison Engine kini membandingkan terhadap Ledger (bukan raw history),
dengan struktur:

```
Active scope:      entity=… · system=… · year=…
Established facts:  - <number> = <scope> (from: <one-line query description>)
Pending:           <unresolved clarification, or none>
```

Ledger menyimpan **answers and scope only — never methods**.

---

### 4.2 seeknal/skills/bpom-analyst/SKILL.md

**Jenis perubahan:** Tiga modifikasi di tiga phase — menutup celah yang menyuruh agent
melewati fase penegak kebenaran.

#### MODIFIKASI — PHASE 1 step 1 (CAPTURE)

**Sebelumnya:** "If `MODIFY_SCOPE` or `EXTEND_SCOPE`, inherit unchanged components and proceed
to PLAN/EXECUTE for the delta only." → melewati RESOLVE.

**Sesudah:** Follow-up **tetap masuk RESOLVE**; reuse prior **answers** dari Ledger hanya
sebagai input; re-derive **method** dari Information Need Resolution hierarchy. Hanya
`EXPLAIN_EVIDENCE` murni yang skip ke GENERATE.

#### MODIFIKASI — PHASE 2 (RESOLVE)

**Ditambahkan:** "RESOLVE runs every turn — including follow-ups." Penegasan bahwa metode (date
column, count column, definisi, filter, cast) diturunkan ulang dari sumber otoritas, **bukan
diwarisi** dari turn sebelumnya. Hanya jawaban yang carry over (via Ledger), sebagai input.

#### MODIFIKASI — PHASE 5 (REFLECT)

**Sebelumnya:** "`MODIFY_SCOPE` or `EXTEND_SCOPE` → audit only the delta query... Prior evidence
for unchanged components is already trusted — do not re-audit it."

**Sesudah:** Delta query dari turn ini **diaudit penuh** terhadap mandatory filter checklist,
sama seperti query baru — karena metode-nya baru diturunkan turn ini dan wajib divalidasi.
Hanya nilai numerik lama (yang sudah lulus REFLECT saat pertama dihitung) yang dipercaya tanpa
re-query.

#### MODIFIKASI — PHASE 6 (GENERATE)

**Sebelumnya:** "Restate scope & key numbers in the TEXT... text is what survives for future
turn context."

**Sesudah:** Diperluas menjadi "**Update the Conversation Ledger**" tiap turn data — catat
scope aktif dan tiap angka sebagai `<number> = <scope> (from: <query>)`. Ledger merekam
**answers and scope only — never the method**.

---

### 4.3 context/business_glossary.md — melengkapi ontologi (B-6, B-1)

**Jenis perubahan:** Melengkapi pengetahuan domain yang hilang, bukan menimbun jawaban.

#### TAMBAH — Commitment status kode 8 + konsep final vs transient (B-6)

Tabel Status Komitmen sebelumnya hanya memuat kode 1, 4, 5, 7, 9 — **kode 8 tidak ada**,
sehingga agent menebak ia termasuk "dibatalkan". Ditambahkan baris `8 = Validasi Pembatalan`
dengan kolom **State** (final/transient), plus prinsip umum:

> "A 'dibatalkan' count means the *final* cancelled state — code 5 only. Code 8 is an
> in-progress validation, not a completed cancellation. The same logic applies generally: count
> final-state codes, not transient codes still moving through the workflow."

#### TAMBAH — Konvensi presentasi label risiko (B-1)

> "A risk level is always presented with its full qualified name — 'Risiko Tinggi', 'Risiko
> Menengah Tinggi', 'Risiko Menengah Rendah' — not the bare adjective. Use the canonical labels
> verbatim rather than the raw `data_dictionary.deskripsi`."

---

### 4.4 context/data_quality_rules.md — identitas kolom BTP (B-4)

**Ditambahkan** pada §Date column rules: penegasan struktural bahwa BTP adalah tabel produk
juga. NIE = `COUNT(DISTINCT nomor)` pada `tanggal`; permohonan = `COUNT(DISTINCT produk_id)`
pada `tanggal_bayar`; registran via `trader_id`. **Entity** yang menentukan kolom, bukan fakta
tabelnya BTP — dan tidak ada penghitungan berbasis `user_id` untuk BTP.

---

## 5. Yang Tidak Diubah (sengaja)

| Komponen | Alasan |
|---|---|
| §0 Conversation Gate | Bukan sumber regresi; berguna untuk filter SMALL_TALK/OUT_OF_SCOPE |
| §0.5 Intent Extraction (Semantic Commitment) | Tetap berguna untuk konsistensi interpretasi |
| §3 Schema State (tanpa row count) | Doc 9 Juni sengaja hapus snapshot statistik; tidak dikembalikan (akan jadi hardcode usang) |
| §5 Info Resolution / §6 Guardrails / §7 Comm Alignment | Tidak terkait regresi |
| Core 6-phase workflow | Benar sebagai execution engine |
| Query recipes R1–R11 | Cukup sebagai reference adaptif |
| Context B-2 / B-3 / B-5 | **Sudah benar** — sembuh otomatis lewat prinsip "re-derive methods"; tidak disentuh |
| `seeknal_agent.yml` (microcompact, sql_result_compactor) | Sudah aktif; Ledger di teks agent justru yang bertahan saat hasil SQL dikompres. `auto_summarization` sengaja tetap OFF (summarizer generik berisiko menghilangkan presisi angka) |

---

## 6. Ringkasan Perubahan

| File | Tambah | Modifikasi |
|---|---|---|
| `SEEKNAL_ASK.md` | Prinsip "Inherit ANSWERS, re-derive METHODS" · definisi Conversation Ledger | Tabel klasifikasi SCE (action `MODIFY/EXTEND/EXPLAIN_EVIDENCE`) · ganti frasa "trusted & reusable without re-querying" |
| `bpom-analyst/SKILL.md` | — | PHASE 1 (RESOLVE wajib di follow-up) · PHASE 2 (RESOLVE tiap turn) · PHASE 5 (audit delta penuh) · PHASE 6 (update Ledger) |
| `business_glossary.md` | Kode 8 + konsep final/transient · konvensi label "Risiko ..." | Tabel Commitment status (+ kolom State) |
| `data_quality_rules.md` | Identitas kolom BTP struktural | §Date column rules |

Total: 4 file, ±85 baris.

---

## 7. Dampak yang Diekspektasikan

| Aspek | Sebelum | Sesudah (ekspektasi) |
|---|---|---|
| Multiturn pass rate | 52% (06-10) | ≥ 88% (mendekati baseline 91% pra-Decision OS) |
| Follow-up field drift (B-2) | `tanggal_aju` di turn 9+ | RESOLVE menurunkan `tanggal_bayar` tiap turn |
| Definisi UMKM (B-3) | drop Menengah jadi 10.357 | re-derive dari glossary → 12.295 |
| Filter ERLA gabungan (B-5) | undercount | re-derive dari R2 |
| Label risiko (B-1) | "Tinggi" | "Risiko Tinggi" |
| Field BTP (B-4) | `user_id`/`tanggal_aju` | `nomor`/`tanggal`/`trader_id` |
| Status dibatalkan (B-6) | kode 5+8 = 3 | kode 5 = 2 |
| Turn panjang (MT-012/013) | drift menumpuk | Ledger ringkas → State Comparison stabil |

**Mekanisme yang menghasilkan dampak:** satu prinsip — *"warisi jawaban, turunkan ulang
metode"* — menutup BAIK follow-up drift (metode selalu segar dari sumber otoritas) MAUPUN
kontrol turn panjang (Ledger jadi rujukan ringkas yang andal).

---

## 8. Verifikasi (untuk dijalankan saat tunnel DB aktif)

```bash
cd seeknal-bpom-neo
uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/multiturn
# Skenario follow-up paling sensitif:
uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/multiturn --scenario MT-005
```

Kriteria lulus:
- Multiturn ≥ 88%; bandingkan per-scenario dengan baseline 2026-05-26 (106/117).
- Turn follow-up benar-benar menjalankan RESOLVE (bukan skip).
- Conversation Ledger pada jawaban berisi jawaban+scope, bukan metode.
- Bug B-1 s/d B-6 tidak muncul lagi.

---

## 9. Putaran 2 — Penyesuaian Pasca-Run 2026-06-11

### 9.1 Hasil Putaran 1

Run `multiturn_results_20260611_013139.json`: **89/117 = 76%** (naik dari 52%). Enam skenario
100% (MT-002/003/004/007/008/011). Conversation Ledger terbukti **benar-benar diemit** di output.

**Analisis lensa adil** (drift ≤5% dari data 2026 yang berubah + abaikan beda ejaan/gaya + YAML
usang = bukan kesalahan agent): re-judging 28 kegagalan → **agent correctness ~90-92%**,
mendekati baseline pra-Decision OS (91%). Perbaikan Putaran 1 berhasil memulihkan regresi.

**Catatan validitas:** dari 89 pass, hanya 48 (54%) terikat angka spesifik; 19 (21%) cek
label/konsep yang sesuai; 22 (25%) lulus hanya via token lemah (tak menguji angka). Jadi lantai
terverifikasi ~41%, plafon adil ~92%. Sebagian besar sisa "kegagalan" adalah **metodologi test**
(exact-match tanpa toleransi + assertion lemah + YAML usang), bukan reasoning agent.

### 9.2 Gap Nyata Tersisa (8 turn, di luar toleransi)

| Pattern | Turn | Angka | Akar |
|---|---|---|---|
| UMKM drop Menengah | MT-001 T5, MT-013 T5 | 10.353 vs 12.295 (16%) | definisi dari asumsi, bukan glossary |
| `tanggal_aju` di turn dalam | MT-013 T15/T17/T40 | 51.025 vs 42.329 (20%) | RESOLVE tak segar di turn 15+ |
| "disetujui" tak deterministik | MT-012 T7 | 7.643 vs 6.236 (22%) | filter komitmen bervariasi antar-skenario (6.238/6.407/7.643) |
| NIE ERBA overcount/scope | MT-009 T4/T5 | 32.888 / 50.438 | filter/scope (investigasi tertunda) |

### 9.3 Perubahan Putaran 2 (4 penyesuaian tertarget)

Prinsip tetap: ajarkan cara berpikir, bukan hardcode jawaban.

#### Poin 1 — `context/code_resolution.md` — label risiko di TITIK resolusi (B-1 lanjutan)
Fix Putaran 1 (imbauan presentasi di glossary) **tidak nyangkut** — agent tetap output "Tinggi".
**Sebab:** label lahir dari resolusi `kategori_dokumen → data_dictionary → "Tinggi"`, jauh dari
imbauan presentasi. **Perbaikan:** pindahkan aturan ke titik resolusi kode. Ditambah subseksi
"Risk level label" + tabel `Tinggi → Risiko Tinggi`, dst., diterapkan saat kode menjadi label.

#### Poin 2 — `context/query_recipes.md` R6 — disetujui deterministik
**Sebelumnya:** `status_komitmen IN ('4','7')` (string polos) → meleset baris `'4.0'`, hasil
tak konsisten. **Sesudah:** `ROUND(status_komitmen::numeric)::int IN (4,7)` + catatan tegas:
disetujui = {4,7} FINAL saja (larang 1/8/9 transient), dibatalkan = {5} saja, selalu normalisasi
ROUND.

#### Poin 3 — `seeknal/skills/bpom-analyst/SKILL.md` PHASE 2 — provenance check definisi
Ditambahkan: setiap definisi bisnis (UMKM, "pangan olahan", kode komitmen, segment) WAJIB
diturunkan dari `business_glossary.md`/`data_dictionary`, bukan asumsi dunia. Pertanyaan
eksplisit: *"definisi ini dari glossary turn ini, atau saya mengasumsikan?"* — contoh
UMKM = 1+2+3, jangan default ke makna kolokial Mikro+Kecil.

#### Poin 4 — `seeknal/skills/bpom-analyst/SKILL.md` PHASE 2 — re-baca sumber di turn panjang
Ditambahkan: **"re-derive = re-READ source, bukan recall"**. Di turn 15+, context load turn-0
pudar dari attention → agent buka ulang `data_quality_rules.md` untuk kolom-tanggal per entity
(permohonan→`tanggal_bayar`, NIE→`tanggal`), bukan mengandalkan ingatan.

### 9.4 Tidak Diubah pada Putaran 2 (sengaja)

| Komponen | Alasan |
|---|---|
| §0.5 prinsip + Conversation Ledger | Sudah cukup — masalah inti tertangani |
| Fix B-4 (BTP) & B-6 (kode 8) Putaran 1 | Turn terkait kini lulus/within-tolerance |
| MT-009 overcount | **Investigasi dulu** SQL aktual sebelum ubah — bisa interpretasi scope yang sah |
| Metodologi test (runner exact-match, 22 assertion lemah, YAML usang) | Bukan ranah agent — diperbaiki di `scripts/test_multiturn_v3.py` & YAML, bukan context/skill |

### 9.5 Confidence & Ekspektasi Putaran 2

| Poin | Confidence | Ekspektasi |
|---|---|---|
| 1 label Risiko | TINGGI | MT-001/012/013 T3 lulus — label benar di sumber resolusi |
| 2 R6 deterministik | TINGGI | "disetujui" konsisten 6.236±drift, MT-012 T7 pulih |
| 3 provenance UMKM | SEDANG | mengurangi drift UMKM (nondeterministik — tak dijamin 100%) |
| 4 re-baca sumber | SEDANG | mengurangi `tanggal_aju` di turn dalam (lawan attention-decay) |

### 9.6 Ringkasan Perubahan Putaran 2

| File | Perubahan |
|---|---|
| `context/code_resolution.md` | TAMBAH §Risk level label (prefix "Risiko " di titik resolusi) + tandai baris `kategori_dokumen` |
| `context/query_recipes.md` | MODIFIKASI R6: ROUND-normalize + kode final {4,7}/{5} eksplisit |
| `bpom-analyst/SKILL.md` | TAMBAH di PHASE 2: provenance check definisi + re-read-source di turn panjang |

Total Putaran 2: 3 file. SEEKNAL_ASK.md tidak diubah (prinsip inti sudah cukup).
