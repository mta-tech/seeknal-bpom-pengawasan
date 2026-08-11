# Eksperimen 3 Hipotesis — desain varian context + fix harness (2026-07-15)

## Latar

Lima generasi eksperimen context sebelumnya tidak menghasilkan perbaikan yang terukur. Audit
codebase engine (`seeknal/src/seeknal/ask/`) menemukan penyebab dominan justru DI LUAR file
context:

1. **Kompaksi history mati** — `agent_harness.auto_summarization.enabled: false` membuat
   `MicrocompactProcessor` + `SqlResultCompactor` tidak terdaftar (`agents/agent.py:510-540`);
   setiap hasil SQL (≤500 baris/50KB) menumpuk utuh → turn panjang membengkak → model makin
   bingung → makin banyak query (bola salju).
2. **Tanpa anggaran keras** — `request_limit` default 100; "~6 tool calls" hanya prosa.
   Terbukti 39-41 LLM request / 24-36 SQL per turn gagal.
3. **Prompt generik ikut termuat** — identity/workflow seeknal (report/pipeline) tidak relevan
   untuk analyst BPOM.
4. **Alat ukur rusak** — 98% GT basi; UAT-OFF-11 inkonsisten internal (expected 607 = statistik
   semua-NIE utk pertanyaan formula bayi → SEMUA varian termasuk baseline flail); varians
   stokastik besar (3↔11 SQL antar run identik).
5. **File context terlalu panjang/padat** — intent_mapping 20,7KB (~5rb token),
   business_glossary/query_recipes ~16KB — sekali `read_project_file` membanjiri history.

## Desain eksperimen

**Baseline `forecast anomaly` — TIDAK DISENTUH** (context lama 92KB + config lama). Kontrol.

Ketiga varian mendapat **fix harness identik** (supaya A-vs-B-vs-C murni membandingkan context):
- `auto_summarization.enabled: true` + `context_manager: false` (kompaksi deterministik saja)
- `request_limit: 30`
- `prompt.workflow: false` (buang prompt generik)

| Varian | Hipotesis | Desain | Korpus |
|---|---|---|---|
| **A — MINIMAL** (`v5-predikat-trim`) | H1: volume/kepadatan context membuat model bingung | 3 file inti (predikat, filter_code_reference, data_architecture-trim) + forecast; SEEKNAL_ASK 3KB; skill tipis; sisanya `_archive/` | ~20KB |
| **B — SINGLE-SOURCE RESIDENT** (`after-forecast-anomaly-refactor`) | H2: kegagalan di routing/lazy-load (aturan ada tapi tidak dibaca) | SEMUA aturan+kode resident di SEEKNAL_ASK (~11KB, ter-inject tiap call); context/ hanya forecast; skill melarang baca ulang | ~11KB resident |
| **C — GATED PROCEDURE** (`after-forecast-anomaly-refactor-v2`) | H3: masalahnya disiplin proses, bukan isi | Pengetahuan = SALINAN PERSIS A; SEEKNAL_ASK 5 gerbang + anggaran max 6 SQL/turn + stop rules; skill = budget ledger | ~20KB (= A) |

Kontras yang bisa dibaca dari hasil:
- A vs baseline → efek pelangsingan (+harness)
- B vs A → resident vs lazy-load (korpus setara)
- C vs A → murni efek disiplin prosedur (pengetahuan identik)

## Pemetaan ke prinsip planning 01-05

| Prinsip | A | B | C |
|---|---|---|---|
| 01 Anti-hardcode / method-over-memory / one-authoritative-path | predikat+filter_code = satu jalur; kode diresolve, tak dihafal | sama, jalurnya resident | sama dgn A |
| 01 Thin orchestrator / purified context | SEEKNAL_ASK 3KB murni orkestrasi | orkestrasi+pengetahuan digabung (sengaja — itu hipotesisnya) | orkestrasi ketat, pengetahuan terpisah |
| 02 Turn classification / conversation state | Route table + follow-up rule | sama (ringkas) | Gate 0 + follow-up via gates |
| 02 Semantic commitment | implisit | implisit | **eksplisit — Gate 3 (internal, tak pernah dicetak; fix bug kebocoran blok ke jawaban)** |
| 03 Concept-type & source hierarchy | filter_code → dictionary exact-category → probe → ask | resident router | sama dgn A, dibatasi 2 lookup |
| 04 Clarification (hard trigger + ambiguity classes + budget) | ada, ringkas | ada, ringkas | Gate 1 blocking, max 2 ronde |
| 05 Proportional execution / reflect gate / limited-answer / transparency | CHECK step + honest-fail | CHECK step + honest-fail | **anggaran keras + stop rules + honest-stop contract** |
| 05 Provenance / CSV | CSV = SQL di balik jawaban final | sama | sama |

## Cara menjalankan & kriteria keputusan

```bash
uv run python scripts/test_variant_compare.py \
  --variants-path docs/context_recap/after-anomaly \
  --test-path <suite> --workers 1 --timeout 240
```

- **Minimal 3 run per skenario** — varians stokastik terbukti besar; 1 run = membaca noise.
- Metrik per varian: pass-rate (pada fixture yang GT-nya masih valid), median jumlah SQL,
  median durasi, konvergensi pilihan kolom+kode antar run.
- Fixture yang diketahui rusak (UAT-OFF-11: expected 607 ≠ populasi di prompt) dikeluarkan dari
  penilaian sampai diperbaiki.
- Baseline dijalankan apa adanya sebagai pembanding.

## Catatan kejujuran: apakah rombak total ini bijak?

**Argumen mendukung:**
- Lima generasi perbaikan inkremental tidak menghasilkan sinyal — melanjutkan pola yang sama
  bukan pilihan yang lebih aman, hanya lebih familiar.
- Sepenuhnya reversibel: semua file lama utuh di `_archive/` per varian; baseline tak disentuh.
- C = pengetahuan A persis → satu pasang perbandingan benar-benar terisolasi (murni prosedur).

**Risiko yang diakui (bukan disembunyikan):**
- Baseline-vs-varian mengukur GABUNGAN (context+harness) — tidak bisa mengatribusi ke salah
  satunya. Hanya A-vs-B-vs-C yang murni context. Kalau ketiganya membaik serentak vs baseline,
  kemungkinan besar itu efek harness, bukan context — dan itu SENDIRI temuan berharga.
- Konten unik file terarsip (mis. prosedur probing `code_translation_protocol`, sinonim
  `segment_map`, edge-case regional `data_quality_rules`) hilang dari korpus aktif A/C dan
  hanya terwakili ringkas. Kalau skenario tertentu gagal KARENA kehilangan itu, kegagalannya
  informatif (H1 sebagian salah) — tapi harus dikenali, bukan disalahartikan.
- Direktori `docs/context_recap/` untracked di git — snapshot sebelum/sesudah hanya berupa
  `_archive/`. Rekomendasi: `git add` + commit kondisi ini sebagai titik eksperimen (keputusan
  user).

## Perubahan file — SEBELUM → SESUDAH (2026-07-15)

### Harness (`seeknal_agent.yml`, identik di A/B/C; baseline tetap lama)

| Kunci | Sebelum | Sesudah | Alasan |
|---|---|---|---|
| `agent_harness.auto_summarization.enabled` | `false` | `true` | tanpa ini microcompact+sql_result_compactor tidak terdaftar (agent.py:510-540) → history membengkak |
| `…auto_summarization.context_manager` | `true` (tak aktif krn parent false) | `false` | kompaksi deterministik saja; summarizer LLM dimatikan demi determinisme |
| `request_limit` | (absen → default 100) | `30` | turn gagal harus gagal cepat, bukan 39-41 request |
| `prompt.workflow` | `true` | `false` | buang prompt generik report/pipeline yang tidak relevan |
| `prompt.custom` | 1 versi sama semua | disesuaikan per varian (A: klarifikasi; B: "semua aturan resident, jangan baca ulang"; C: ringkasan gerbang) | selaras dengan hipotesis masing-masing |

### Varian A — MINIMAL (`v5-predikat-trim`)

| File | Sebelum | Sesudah |
|---|---|---|
| `SEEKNAL_ASK.md` | 7,0KB (orkestrator v8: gate/ledger/precedence 12 item) | 2,2KB (route · clarify gate · 5 aturan · follow-up) |
| `context/` | 12 file, 119,8KB | 5 file, ~29KB: `predikat.md` (11,3KB, tetap), `filter_code_reference.md` (9,3KB, tetap), `data_architecture.md` **8,3KB→3,5KB** (+koreksi klaim salah "klasifikasi_id deprecated"), forecast_guide+recipes |
| `skills/` | 6 skill, 28,7KB | 3 skill: `bpom-analyst` **7,1KB→1,8KB** (5 langkah), forecaster & detect-anomaly tetap |
| Diarsip → `_archive/` | — | intent_mapping (20,7KB), business_glossary (15,7KB), query_recipes (15,9KB), data_quality_rules (11,9KB), code_translation_protocol (10,9KB), code_resolution (7,5KB), verified_bindings (2,3KB); skill: business-question-answering, database-analyst, evidence-auditor |
| **Total korpus aktif** | **~155KB** | **40KB** |

### Varian B — SINGLE-SOURCE (`after-forecast-anomaly-refactor`)

| File | Sebelum | Sesudah |
|---|---|---|
| `SEEKNAL_ASK.md` | 7,1KB (orkestrator; pengetahuan di 13 file context) | 8,3KB — SEMUA aturan+kode inti resident (tabel/join, entity hitung, status set, JP rule, Case A/B, pipeline codes, risk, bindings/decoys, segmen, router dictionary 21 kategori, exclusions, cast, template UNION, kontrak jawaban) |
| `context/` | 13 file, 128,5KB | 2 file forecast saja (5,4KB) — predikat/filter_code/architecture dsb diarsip karena isinya SUDAH resident |
| `skills/bpom-analyst` | 8,1KB (CAPTURE→…→PRESENT + Step 0) | 1,7KB — 5 langkah + larangan baca-ulang context |
| **Total korpus aktif** | **~164KB** | **22KB** (8,3KB di antaranya resident tiap call) |

### Varian C — GATED (`after-forecast-anomaly-refactor-v2`)

| File | Sebelum | Sesudah |
|---|---|---|
| `SEEKNAL_ASK.md` | 9,3KB (v8 + §5 precedence 3b/3c) | 2,9KB — 5 gerbang blocking + anggaran (2 discovery + 1 final + 1 retry; total ≤6 SQL) + honest-stop |
| `context/` | 12 file, 80,3KB (versi trim-sendiri) | 5 file = **SALINAN PERSIS varian A** (isolasi murni prosedur) |
| `skills/bpom-analyst` | 5,9KB | 2,1KB — budget ledger + stop rules + "Gate-3 block internal, jangan pernah dicetak" (fix bug bocornya blok Intent/SCE ke jawaban user) |
| **Total korpus aktif** | **~99KB** | **41KB** |

## Ekspektasi hasil — apa yang MENGONFIRMASI dan apa yang MEMBANTAH tiap hipotesis

Metrik per skenario (≥3 run): pass-rate pada fixture ber-GT-valid · median jumlah SQL · median
durasi · konvergensi kolom+kode antar run.

| Prediksi | Jika terjadi → kesimpulan |
|---|---|
| A/B/C semua turun drastis jumlah SQL & durasi vs baseline, pass-rate naik moderat | Efek harness dominan (kompaksi+budget) — context bukan tuas utama; pertahankan harness, iterasi context jadi sekunder |
| **H1 benar**: A ≥ baseline pass-rate dengan SQL jauh lebih sedikit & konvergensi naik | Pelangsingan cukup; jadikan A basis produksi |
| **H1 salah**: A gagal spesifik di skenario yang butuh konten terarsip (segmen sinonim, edge-case regional) | Kembalikan HANYA file yang terbukti dibutuhkan dari `_archive/` — bukan semuanya |
| **H2 benar**: B > A pass-rate/konvergensi pada skenario berkode (berklaim/organik/pipeline) dengan `read_project_file`≈0 | Lazy-load memang titik gagal; pertimbangkan resident untuk aturan inti permanen |
| **H2 salah**: B ≈ A atau lebih buruk (model mengabaikan aturan resident yang padat) | Kepadatan resident bukan jawabannya; routing bukan akar masalah utama |
| **H3 benar**: C ≈ A pass-rate tapi SQL & durasi jauh lebih rendah + honest-stop menggantikan flail | Disiplin proses = tuas biaya/stabilitas; gabungkan gerbang C ke pemenang A/B |
| **H3 salah**: C sering berhenti-jujur di soal yang sebenarnya bisa dijawab (budget terlalu ketat) | Naikkan budget bertahap (6→10), ukur ulang — jangan buang konsep gerbangnya |
| Semua varian tetap buruk & tidak konvergen | Masalah di bawah lapisan context/harness (model/fixture) — hentikan iterasi context, eskalasi ke pemilihan model atau perbaikan suite test |

## Prosedur rollback

Per varian: `mv _archive/context/*.md context/ && mv _archive/skills/* skills/`.

File yang DITIMPA di tempat (bukan diarsip) — SEMUA versi lamanya berhasil dipulihkan verbatim
dari transkrip sesi dan disimpan di arsip per varian:

| File lama | Pulih di |
|---|---|
| A `SEEKNAL_ASK.md` (6,9KB, item №10 bindings + №11 filter_code) | `v5-predikat-trim/_archive/pre-experiment-SEEKNAL_ASK.md` |
| A `skills/bpom-analyst/SKILL.md` (6,9KB, Step-0 ganda) | `v5-predikat-trim/_archive/pre-experiment-bpom-analyst.SKILL.md` |
| B `SEEKNAL_ASK.md` (v8) | `after-forecast-anomaly-refactor/_archive/pre-experiment/SEEKNAL_ASK.v8.md` |
| B `skills/bpom-analyst/SKILL.md` | `after-forecast-anomaly-refactor/_archive/pre-experiment/bpom-analyst.SKILL.pre.md` |
| C `SEEKNAL_ASK.md` (9,2KB, 3b+3c) | `after-forecast-anomaly-refactor-v2/_archive/pre-experiment-SEEKNAL_ASK.md` |
| C `skills/bpom-analyst/SKILL.md` (7,9KB) | `after-forecast-anomaly-refactor-v2/_archive/pre-experiment-bpom-analyst.SKILL.md` |
| `seeknal_agent.yml` lama (A/B/C, identik baseline) | `forecast anomaly/seeknal_agent.yml` |
| `data_architecture.md` lama (A) | acuan: `forecast anomaly/context/data_architecture.md`; versi v2 lama ada di `after-forecast-anomaly-refactor-v2/_archive/context/data_architecture.md` |

Rollback penuh per varian = kembalikan `_archive/context/*` + `_archive/skills/*` + file
`pre-experiment-*` di atas.

Pelajaran proses (dicatat sebagai kesalahan eksekusi eksperimen ini): file yang DIUBAH wajib
diarsipkan dulu, bukan hanya file yang dipindah — pemulihan kali ini hanya mungkin karena
kebetulan seluruh isi file pernah lewat di transkrip sesi. Commit snapshot git atas
`docs/context_recap/after-anomaly/` SEBELUM run pertama tetap direkomendasikan.

---

# RONDE 2 (2026-07-16) — hasil ronde 1, audit wiring, hipotesis lanjutan, desain per-gaya

## Hasil ronde 1 (14 file era-lama vs 6 file era-baru; era-baru = subset tersulit, pass-rate
lintas-era TIDAK sebanding — yang sahih hanya perbandingan antar-varian dalam era yang sama)

| Metrik | A minimal | B resident | C gated | baseline |
|---|---|---|---|---|
| ILIKE/turn lama → baru | 1,59 → **0,16** | 1,55 → **1,19** | 1,19 → 0,69 | 1,61 → 1,06 |
| dict-ILIKE lama → baru | 90 → 5 | 77 → 34 | 64 → 15 | 59 → 16 |
| dict-exact era-baru | 42 | **13** | 38 | 31 |
| Pass era-baru | **45%** (14/31) | 35% | 34% | 33% |

Temuan kualitatif: sisa ILIKE varian A 4/5 berbentuk SEHAT (kategori dikunci → label dicari);
decoy berklaim teratasi (A pass `klasifikasi_id='305'`, baseline masih `klaim`); regresi buatan
sendiri: kalimat "official metrics add JP" memicu JP liar (A gagal RISK-1, C gagal BERKLAIM);
C tertangkap `klasifikasi_id='304'` utk risiko (tabrakan nilai kode); aturan aktif-vs-terdaftar
belum diajarkan (C menang di RISIKO-4-KATEGORI tanpa diajari); prosa "max 6 SQL" tidak mengikat.

## Audit wiring pasca-restrukturisasi — UTUH di ketiga varian
Route forecaster/anomaly ✓ · request_clarification/ask_user ✓ (+ enabled yml) · run_forecast +
forecast_guide/recipes ✓ · detect_anomaly ✓ · analyst→upload_to_s3 ✓ · 0 rujukan menggantung.
Tidak perlu skill baru. Catatan: SEEKNAL_ASK A tak menyebut CSV (ada di skill — konsisten gaya).

## Prinsip ronde 2 (arahan user)
Peta kode = contekan/anchor terverifikasi, BUKAN semesta kode — bahaya anchoring: sistem hanya
fokus ke kode tertanam padahal DB punya kode lain. ILIKE tidak dilarang; diatur KAPAN-nya lewat
5 jalur: (P1) anchor persis → pakai; (P2) sekeluarga tapi kode tak tercantum → baca SEMUA baris
kategori exact; (P3) istilah=label → scoped-ILIKE DI DALAM kategori (sah); (P4) segmen bebas →
discovery nama_kategori; (P5) ambigu → tanya.

## Perubahan ronde 2 — gaya per varian (baseline TIDAK disentuh)

| Varian | Hipotesis lanjutan | Perwujudan (idiom sendiri) |
|---|---|---|
| A — MINIMAL+LADDER | H1′: korpus kecil + tangga-jalur eksplisit ⇒ dict-exact dominan DAN anti-anchoring bekerja | `filter_code_reference.md`: header re-frame contekan-≠-semesta + §0 tabel 5-jalur + tabrakan kode + status 2-tingkat + JP kembali RC-2 + COALESCE skala di router; `predikat.md` §3 +2 baris aktif/terdaftar; `data_architecture.md` +3 baris resep 2D |
| B — RESIDENT-SIGNPOSTED | H2′ (uji penentu): resident gagal krn kepadatan tanpa penanda; signposting ⇒ ILIKE ≤0,3/turn. Gagal → H2 DITOLAK final | SEEKNAL_ASK: seksi "⓪ DECISION LADDER" satu layar di paling atas (5 jalur + tabrakan kode); koreksi dianyam inline: tabel status ganti judul "follows the question's VERB" + baris aktif=0999-only; seksi JP diganti "ONLY on explicit baru/terbit"; COALESCE skala di router; resep 2D di bawah template UNION. Tetap nol read_project_file |
| C — GATE-ENFORCED | H3′: disiplin hanya nyata bila di-ENFORCE harness; gate+budget keras ⇒ SQL/turn < A dengan pass setara | Gate 2 += syarat lolos "setiap konsep ditugaskan P1-P5" + cek tabrakan kolom; Gate 5 += 5 cek berurutan (entity, status-tier per verb, JP hanya baru/terbit, anti-tabrakan, exclusions+scope); skill: P2/P3 = pengeluaran budget yang SAH; **yml `request_limit: 20`** (A/B tetap 30 — pembeda C yang disengaja, bagian dari hipotesisnya). Pengetahuan = salinan persis A (isolasi prosedur dipertahankan) |

## Ekspektasi ronde 2 — konfirmasi vs bantahan
- A: skenario luar-anchor (BTP-PEWARNA/SERBUK/CAIR, SKALA-1/2) menemukan kode via kategori-exact
  TANPA fuzzy liar → H1′ terkonfirmasi. Kalau A malah menjawab "tidak ada karena tak tercantum"
  → anchoring masih terjadi, header contekan belum cukup.
- B: ILIKE/turn ≤0,3 & dict-exact naik signifikan → H2′ terkonfirmasi (signposting-lah kuncinya).
  ILIKE tetap ~1,2 → H2 DITOLAK FINAL, varian B diganti pendekatan lain di ronde 3.
- C: SQL/turn < A dengan pass setara & tanpa honest-stop berlebihan → H3′ terkonfirmasi.
  Honest-stop menimpa soal yang sebenarnya terjawab → budget 20 terlalu ketat, naikkan bertahap.
- Ketiganya: tidak ada lagi JP liar pada soal non-"baru"; "aktif/distribusi" memakai 0999-only;
  tidak ada pemilihan kolom karena nilai kode.

## Rerun matriks verifikasi
G1-G3: RISIKO-4-KATEGORI-1, RISK-1, PANGAN-BERKLAIM-1, RISIKO-TINGGI-NOTIF-1.
Anti-anchoring: BTP-PEWARNA-1, BTP-SERBUK-1, BTP-CAIR-1, SKALA-1, SKALA-2.
Regresi wiring: 1 skenario forecast + 1 anomaly.
≥2-3 run per skenario; metrik: pass, SQL/turn, ILIKE liar-vs-scoped, rasio dict-exact:dict-ILIKE,
jumlah clarif; baseline ikut sebagai kontrol.

---

# RONDE 2b (2026-07-16, pasca 5 run 01:23-02:11 UTC) — temuan & perbaikan context-only

## Temuan 5 run terbaru

| Metrik | A minimal | B resident | C gated | baseline |
|---|---|---|---|---|
| turns / pass | 12 / 42% | 11 / 27% | 13 / 31% | 9 / 33% |
| SQL/turn | **2,6** | 2,1 | 3,1 | 9,7 |
| ILIKE liar /turn | **0,17** | 0,36 | 0,77 | 1,00 |
| **Mati `UsageLimitExceeded`** | 2 | **5** | **5** | 0 |

1. **Mode gagal dominan varian = mati kehabisan request budget SEBELUM menjawab** (52% dari
   fail varian). Turn normal hanya butuh 7-11 LLM request (terukur) → yang mati berputar
   non-produktif 20-30 request; pemicu terkuat skenario ambigu by-design (RISK-1 "Risiko
   Rendah" membunuh A+B+C sekaligus) → indikasi loop klarifikasi/deliberasi. Baseline selamat
   karena limit 100 — tapi dengan 9,7 SQL/turn (3,7× lebih boros dari A).
2. **Cacat pengukuran (known-gap script, TIDAK dikerjakan ronde ini):** pada turn exception,
   `llm_requests`/`tools`/`sqls` tercatat 0/kosong padahal elapsed 87-393s — stats parsial
   dibuang; akar loop tak bisa dilihat dari JSON.
3. **Konflik RC-2 terbukti:** OFF-3 "berapa NIE yang TERBIT di 2025" → A & baseline memasang
   JP `('301','305')` = 46.607; expected 53.535 (SEMUA JP, sesuai note fixture). Trigger
   "terbit/diterbitkan di {periode}" di RC-2 salah — setiap NIE "terbit"; hanya "baru" yang
   menyempitkan.
4. Positif: NOTIF-1 dijawab dgn `kategori_dokumen` (tidak ada lagi `klasifikasi_id='304'`);
   A tetap tersehat di semua metrik; B menunjukkan pola jawaban minim-evidence (dict-exact 2;
   SKALA-2 dijawab 631/394 dgn metode join menyimpang).
5. GT stale tetap menyumbang fail nyata (SKALA 8.943 vs live ≥9.032; token prefiks '80.').

## Perubahan Ronde 2b (context/skill + config; baseline tak disentuh)

| # | Perubahan | A | B | C |
|---|---|---|---|---|
| 0 | `request_limit` DIHAPUS dari yml (kembali default 100; arahan user — enforcement harness ditunda) | ✓ | ✓ | ✓ (catatan hipotesis C disesuaikan: disiplin diukur murni dari gerbang) |
| 1 | Anti-loop klarifikasi: satu jawaban klarifikasi = EKSEKUSI; dilarang bertanya dua kali utk ambiguitas yang sama; sisa ragu → nyatakan asumsi di jawaban | +2 kalimat di Clarify gate | inline di Clarify gate | Gate 1: "clarification response CLOSES this gate; re-entry = violation" |
| 2 | RC-2: trigger JP = kata "baru"/"baru notifikasi" SAJA; "terbit" BUKAN trigger ("NIE terbit di 2025" = semua JP; undercount ~13% bila difilter) | predikat §4 + filter_code_reference | seksi jenis_permohonan | = A (salinan identik, cmp verified) |
| 3 | Kontrak evidence B: jawaban kuantitatif wajib ≥1 SQL sukses turn ini | — | +1 kalimat Answer contract | — |

## Ekspektasi Ronde 2b
- Nol (atau nyaris nol) kematian-limit di semua varian; skenario ambigu (RISK-1) selesai dengan
  1 klarifikasi + eksekusi, bukan loop.
- OFF-3 dijawab TANPA JP (≈ nilai semua-jenis-permohonan).
- 0999-only pada soal distribusi/aktif terkonfirmasi pada run yang pasti memakai konteks baru
  (run sebelumnya kemungkinan race dengan penulisan ronde 2).
- Pembantah: bila loop masih terjadi tanpa request_limit (turn berjalan sangat lama tapi tak
  error), akar loop harus didiagnosis lewat perbaikan instrumentasi script (backlog).

---

# RONDE 2c (2026-07-16) — cabut anti-loop klarifikasi + trace step-by-step di script

## 1. Aturan anti-loop klarifikasi Ronde 2b DICABUT (arahan user)
Alasan user: jika belum jelas, WAJIB ditanyakan balik — melarang bertanya ulang akan merembet:
pertanyaan yang seharusnya ditanyakan malah tidak ditanyakan karena AI bingung harus ngapain.
Ketiga SEEKNAL_ASK dikembalikan ke kebijakan lama (klarifikasi bebas saat genuinely unclear;
budget "max 2 ronde per topik" yang memang sudah ada tetap). Yang DIPERTAHANKAN dari Ronde 2b:
fix RC-2 ("terbit" bukan trigger JP) dan kontrak evidence B (jawaban kuantitatif ⇒ ≥1 SQL
sukses). Akar loop klarifikasi/deliberasi akan didiagnosis lewat TRACING, bukan pembungkaman.

## 2. Trace step-by-step di `test_variant_compare.py` (root-cause first)
Field baru per turn di JSON (dan stdout satu-baris-per-step):
- `tool_trace`: ledger DATAR kronologis — SEMUA tool call apa pun namanya, bentuk tetap
  `{step, at_s, tool, arg, origin, result_chars, status}`; `arg` = string pipih `key=value`
  (sql ≤200 char, lainnya ≤160); `origin` diturunkan dari data (path context/ → project-context;
  skill ada di skills/ varian → project-skill vs engine-builtin-skill; SQL/tabel → database;
  klarifikasi → user-interaction); `status` ok/error dari isi return; `result_chars` =
  besarnya muatan yang masuk history (deteksi banjir token).
- `files_read`, `skills_loaded`: array string datar berurutan.
- `trace_partial: true` saat run mati sebelum pesan kembali (UsageLimit/timeout) + jejak lemah
  governor (`timing_events_this_turn`, `tool_calls_this_turn`) — mengganti artefak menyesatkan
  llm=0/tools={} sebelumnya.
Desain diverifikasi ke kode: pairing `ToolCallPart`↔`ToolReturnPart` via `tool_call_id`
(timestamp nyata dari return); governor TIDAK punya log berurutan (hanya counter + timing-event
terbatas) → log penuh sisi-engine dicatat sebagai backlog terpisah.
Uji sintetis lulus: origin/status/derivatif/format terverifikasi.

Tujuan: audit "context/skill mana dibaca, kapan, sebelum SQL mana" bisa dilakukan per-step —
setiap perubahan context berikutnya dinilai dari trace, bukan tebakan.

### Ronde 2c — addendum: origin bukan whitelist nama tool
Kekhawatiran user (tepat): klasifikasi if/else berbasis nama akan salah-melabeli tool seeknal
lain yang tidak terdaftar. Diperbaiki: peta `tool_name → toolset` dibangun dari AGENT HIDUP
(`_build_tool_origin_map` — jalan rekursif ke `agent.toolsets`, `FunctionToolset.tools`,
wrapped/nested), jadi ~30 tool seeknal apa pun otomatis mendapat id toolset aslinya
(`toolset:<id>`). Label semantik hanya untuk segelintir nama bermakna tinggi (database /
user-interaction / compute-export / source-context) + turunan data (project-skill vs
engine-builtin-skill; project-context via path). Nama yang tak terdaftar di mana pun →
`unmapped-tool` — TERLIHAT di audit, tidak diserap diam-diam ke bucket salah.
Teruji sintetis: tanpa peta → unmapped-tool; dengan peta agent → toolset id benar;
`_build_tool_origin_map` terverifikasi pada Agent pydantic-ai sungguhan.

### Addendum — output test dipecah jadi folder per-pertanyaan / file per-varian
JSON monolitik (`variant_compare_results_*.json`) tetap jadi sumber data untuk analisis
lintas-run, TAPI sekarang setiap run juga menghasilkan pohon markdown yang bisa dibaca
langsung tanpa skrip bantu:

```
seeknal/tests/outputs/<date>/v3/traces/<run_ts>/
  _index.md                         ← peta seluruh run: scenario x varian, pass/fail, link
  <scenario_id>/_summary.md         ← 1 tabel banding varian utk 1 pertanyaan
  <scenario_id>/<variant_name>.md   ← transkrip lengkap: prompt → tiap turn → tiap step
                                        (tool/origin/arg/ukuran hasil/status) → jawaban akhir
```

Murni renderer di atas data yang sudah dikumpulkan (`save_trace_files`, dipanggil setelah
`save_json`) — tidak ada pemanggilan agent tambahan. Diverifikasi dengan merekonstruksi
`TurnResult` dari JSON run 033903 (4 skenario x 4 varian) dan merender ulang: struktur folder
benar, link ter-encode (nama varian baseline "forecast anomaly" mengandung spasi — sempat
menghasilkan link markdown patah, sudah diperbaiki dengan `urllib.parse.quote`), dan transkrip
varian B untuk UAT-TOP-PERUSAHAAN-1 langsung menunjukkan 22 langkah SQL tanpa satu pun
klarifikasi — persis temuan yang sebelumnya perlu skrip Python ad-hoc untuk digali.

### Addendum 2 — output varian-sentris + path via .env
Trace direstrukturisasi jadi **folder-per-varian** (bukan per-pertanyaan):
```
<OUTPUT_BASE>/<date>/<VERSION>/            ← keduanya dari .env (SEEKNAL_TEST_OUTPUT_DIR/_VERSION; default lama)
  variant_compare_results_<ts>.json         ← JSON besar lengkap (tak diubah)
  traces/<ts>/
    _index.md                               ← peta: baris=varian, kolom=pertanyaan
    <variant>/_summary.md                   ← roll-up varian: 1 baris per pertanyaan (SQL/klarifikasi/context/skill agregat semua turn)
    <variant>/_data.json                    ← JSON LENGKAP varian ini (semua field per turn, incl tool_trace)
    <variant>/<scenario_id>.md              ← detail transkrip 1 pertanyaan
```
Berlaku walau 1 varian dijalankan (tetap 1 folder varian utuh — terverifikasi). Path output
tak lagi hardcode: `SEEKNAL_TEST_OUTPUT_DIR` (base, relatif→PROJECT_ROOT) + `SEEKNAL_TEST_OUTPUT_VERSION`
(default v3), dibaca dari `.env` yang sudah dimuat di awal main(). Metrik roll-up diagregasi
lintas-turn (bukan turn-1) supaya varian klarifikasi-lalu-AUTO tidak tampak "SQL=0" palsu.
Semua diverifikasi sebagai renderer murni dari JSON run 033903 (tanpa panggil agent).
