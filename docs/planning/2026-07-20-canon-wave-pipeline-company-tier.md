# seeknal-bpom-neo: Canon Wave — Pipeline, Company, Tier, Labels

**Document type:** Implementation note  
**Date:** 2026-07-20  
**Status:** Applied to the three hypothesis variants; baseline `forecast anomaly` untouched (control).  
**Scope:** `context/predikat.md` (twin v5==v2) · `context/filter_code_reference.md` (twin v5==v2) · `skills/bpom-analyst/SKILL.md` (×3 stylings) · `SEEKNAL_ASK.md` (×3 channels)  
**Constraint:** context / skill / SEEKNAL_ASK only — zero engine-code change, **zero test-file change**.  
**Baseline for evidence:** run `2026-07-20/024223` (UAT-v2-compact-II, 4 variants, production DB).

---

## 1. Purpose

Run 024223 (9-11/17 per variant) showed the remaining failures cluster on concepts with **no
canonical definition** — all four variants converged on defensible-but-different readings
(PIPELINE-TOTAL, SKALA-1/2, PRODUSEN 4/4 fail), plus one label-language miss, one
sum-vs-distinct method slip, one clarify-as-prose dead end, and one discovery-timeout class.
Design principle: write the canon so the **fixture's number reappears as a labelled row** in
the canonical answer (§12 decomposition) — fixtures stay untouched and become the
falsification instrument for the canon.

## 2. New canon (what was written, where)

| # | Rule | v5/v2 location | refactor location (resident) |
|---|---|---|---|
| 1 | **"Sedang diproses (petugas)"** = officer queue (Evaluator+Verifikator+Direktur/Deputi/KB+Data Tambahan) is the canonical headline; **"belum selesai (total)"** = NOT-IN-terminal always attached as labelled companion; bottleneck = ONE GROUP BY ranking stage buckets | `filter_code_reference.md` §2 rules | `SEEKNAL_ASK.md` pipeline section |
| 2 | Company entity = `trader_id` within a system — name-dedupe ONLY for the cross-system merged headline, per-system `trader_id` counts always shown labelled | `filter_code_reference.md` §1 | ASK counting-entity section |
| 3 | Company population default = trader MASTER (no product join); join only on "yang punya produk/NIE"; both live → both labelled | `filter_code_reference.md` §1 | ASK counting-entity section |
| 4 | "Berapa produsen/importir" canonical = `is_status_industri_*='1'` (TEXT) flags on master, entity `trader_id`; `status_usaha` 31/33 counts PRODUCTS, never the company headline | `filter_code_reference.md` §4b bullet | ASK dictionary-router STATUS_USAHA entry |
| 5 | "Saat ini" ALONE is not an aktif trigger — "terdaftar … saat ini" stays terdaftar; both tiers live → lead terdaftar + attach aktif labelled; no expiry narrowing unless "masih berlaku" | `predikat.md` §3 | ASK status-filters table row |
| 6 | Headline total from ONE global DISTINCT query — never the sum of period-table rows (revisions put one `nomor` in several periods) | `predikat.md` §12-C | ASK answer-contract Shape |
| 7 | English dictionary literals presented as Indonesian label + code + literal ("Risiko Rendah — `301` (Pangan Low Risk)") | `predikat.md` §12-B | ASK risk section |
| 8 | Bounded free-text search: ONE combined `(nama ILIKE … OR merk ILIKE …)` + LIMIT, max 2 probes, then honest "tidak ditemukan" | `bpom-analyst` Discovery bounds (v5/refactor) · Stop rules (v2, counts against budget) | same skill file |
| 9 | Clarification is ALWAYS a `request_clarification`/`ask_user` tool call — plain-text clarifying questions are never answered | ASK clarify gate + analyst skill (all 3) | ASK clarify gate |

Evidence each rule answers: #1 → 60.169 vs 11.119 4/4-divergence; #2/#3 → SKALA name-dedupe
and join drift; #4 → v5's 31/33 reading (14.592 vs 13.703); #5 → v5 TOTAL-1 aktif+expiry
(189.420 vs 316.628); #6 → NOTIF 4.207 = per-year sum vs 3.718 global; #7 → v5 RISK-1 numeric-
exact but failed on "Low/High Risk" wording; #8 → SUSU-1 4/4 timeout (ILIKE probe storm on
255k rows); #9 → v2 PRODUSEN dead turn (clarification typed as prose, 0 SQL).

## 3. Test files — deliberately NOT touched (backlog only)

Current fixtures become reachable through canon #1-#7 (their numbers must now appear as
labelled rows). Remaining test-side items are recorded here as backlog, pending explicit
approval:

- **SUSU-1 / discovery-heavy runs**: use runner `--timeout` ≥ 600 at run time (command-line,
  not a file edit); canon #8 attacks the root.
- **UAT-v2 (27-question master set) staleness audit** — 12 old-style fixtures with exact
  substrings needing a compact-II-pattern refresh **later**: BTP-TREN (950/1.089/1.523),
  CHAR-PANGAN-BAYI-ERLA ("81 produk"), DRAFT-PROSES (20.020), INVESTIGASI-KOMITMEN
  (28.720/11.688/10.233/5.198 — 11.688 & 5.198 proven stale), KOMITMEN-DIBATALKAN (5.198;
  live ≈5.457), KOMITMEN-PROSES (10.233), MT-MINOR-MEI26 ("17 NIE"), OPS-BOTTLENECK (24.959),
  PIPE-BAYAR (6.988), PIPELINE-EVAL (5.469; transient, needs tol 10), RISIKO-4 (prefix-hack
  "80."), TOP-PERUSAHAAN (2.077; scope-tagged groups needed). Plus 3 fixtures with
  `tolerance_pct: 0` to relax (GARAM, JP-MAYOR-2025, JP-TREN). No yml was modified.

## 4. Validation

Rerun UAT-v2-compact-II (then the full UAT-v2 27) across the 4 variants, production DB,
baseline as control. Expected flips if the canon binds: PIPELINE-TOTAL, SKALA-1/2, PRODUSEN,
TOTAL-1 (v5), RISK-1 (v5) turn green with unchanged fixtures; NOTIF stays red only if the
sum-vs-distinct slip persists; SUSU passes with a longer runner timeout. Any fixture that
still fails after canon-compliant answers is then provably a fixture problem — that evidence
gates the backlog in §3.

## 5. Rollback

All edits are additive blocks / single-row table amendments in the three variant dirs;
restore from git to revert. Twin discipline verified: `predikat.md` and
`filter_code_reference.md` byte-identical v5 == v2. Baseline diff = zero.

---

## 6. WAVE 2 (2026-07-20, sore) — hasil rerun + keputusan bisnis + tindak lanjut

**Bukti rerun subset-9 (run 0323-0347) + SUSU 041051:** kanon Wave-1 terbukti mengikat —
varian kontrak naik 2-3/9 → 5-6/9, kontrol datar 4/9 (atribusi kausal bersih). SUSU:
v5 & refactor PASS pertama kalinya (bounded search bekerja); v2 timeout tanpa jejak (backlog
G7); kontrol gagal semata kata ("tidak ada" vs "tidak ditemukan").

**Keputusan bisnis (user, 20 Jul):** "belum selesai" vs "sedang diproses" TIDAK dipilih salah
satu — **transparansi**: kedua bacaan sah, jawaban kanonik menampilkan keduanya berlabel, dan
test file mengakomodasi keduanya. Aspek engine-unavailable TIDAK ditulis ke context/skill —
cukup dipastikan operasional (lihat Ops di bawah).

**Perubahan test file (disetujui user; verifikasi live 20 Jul):**

| Fixture | Perubahan |
|---|---|
| UAT-PIPELINE-TOTAL-1 | 2 grup: NOT-IN-terminal 60.169 ATAU antrian petugas 6.977 (03-08xx; gab+BTP ±7.141); tol 10 |
| UAT-SKALA-2 | 3 grup populasi: punya-produk 1.354 · master 1.477 · punya-NIE-sah 1.273 |
| UAT-TOTAL-1 | 2 grup tier: terdaftar 316.628→anchor 316.013 ATAU aktif-0999 gabungan 307.868; note menandai penjumlahan-per-status (173.077) sebagai METODE SALAH, bukan bacaan |
| UAT-SUSU-1 | any_of frasa nol: "tidak ditemukan" ATAU "tidak ada"; catatan produk MBG (24 Apr 2026) + saran --timeout ≥600 |

**Perubahan prosa Wave 2 (3 varian, baseline utuh):**
1. **CSV Store Contract v2 — urutan & idempoten**: ekspor = tool call TERAKHIR turn (setelah
   evidence + CHECK/Gate 5, sebelum jawaban); upload prematur tidak boleh diulang; dilarang
   dobel. Ditanam sebagai step bernomor **EXPORT** di alur analyst (v5/refactor step 5;
   v2 Gate-5 wording), klausa di forecaster/detect-anomaly, dan di ketiga SEEKNAL_ASK.
   Bukti: upload@5-9 dari 10-18 step; dobel di v5 PIPELINE-TOTAL, v5 SKALA-1, refactor SUSU.
2. **Fix gap Wave-1**: Gate 5 ASK v2 masih memuat pemicu lama "distribusi saat ini → aktif"
   (penyebab regresi TOTAL-1 v2) — diselaraskan dengan predikat §3.
3. **Generalisasi anti-penjumlahan** (§12 + ASK refactor): total dilarang dari penjumlahan
   partisi APA PUN (periode, status, sistem) — kasus 173.077 (jumlah per-status) & 4.207
   (jumlah per-tahun).
4. **Master-print** (§1 reference + ASK refactor): hitungan MASTER wajib tercetak pada
   pertanyaan perusahaan-per-atribut, meski bacaan join memimpin.
5. **Pipeline companion = SATU angka** (§2 reference + ASK refactor): pendamping NOT-IN
   dicetak sebagai satu total eksplisit; uraian bagian boleh menyusul, tak menggantikan.
6. **CHECK scope == scope klarifikasi** (3 skill analyst + Gate 5 v2): dilarang menyempit
   diam-diam ke satu sistem setelah klarifikasi gabungan (kasus TOTAL-1 v5 ERBA-only).

**Ops (bukan prosa, bukan kode konteks):** seluruh uji forecast/anomaly 20 Jul berjalan tanpa
engine — `IBA_ENGINE_URL` tak diset & container iba-engine mati; semua `run_forecast`/
`detect_anomaly` mengembalikan "Engine belum dikonfigurasi" (0.1KB). Sebelum uji forecast
berikutnya: nyalakan iba-engine + set `IBA_ENGINE_URL` di `.env`, lalu rerun ANOMALY-1,
FORECAST-ANOMALY-1, NIE-FORECAST-2 — perilaku tabel proyeksi asli belum pernah teruji
pasca-kontrak.

**Backlog tetap:** v2×SUSU timeout tanpa jejak (butuh patch flush-parsial harness, G7);
refresh 12 fixture basi UAT-v2 + 3 tol-0 (menunggu persetujuan); keputusan kanon lanjutan
"apakah ditolak ikut 'belum selesai'" kini TIDAK memblokir (kedua grup diakomodasi).

### 6b. Wave 2b (2026-07-20, malam) — kontrak transparansi & konsistensi (general)

Arahan user: transparansi berlaku GENERAL (forecast pun per-kode & per-periode; CSV mencakup
horizon penuh yang diminta) dan KONSISTENSI (pertanyaan sama → jawaban sama, termasuk
follow-up, lintas sesi). Ditanam:
- `predikat.md` **§12-F Consistency** (twin v5==v2): same wording → same interpretation →
  same SQL → same numbers; satu-satunya beda sah = data drift (stamp as-of date); berlaku
  semua tipe jawaban.
- `bpom-forecaster` **6.2.0** (×3): blok "Answer Contract applies to forecasts too"
  (per-periode + bounds, history penuh, per-series berlabel, CSV = horizon jawaban, cap 36
  dinyatakan di jawaban+ekspor) + hard rule "Consistency contract".
- `detect-anomaly` (×3): consistency contract + per-flag labelled row.
- `forecast_guide.md` §5 (3 file, twin v5==v2): bullet transparansi & konsistensi.
- Ketiga `SEEKNAL_ASK`: seksi Follow-ups → "Follow-ups & consistency".

**BLOCKER dicatat (bukan prosa):** permintaan "5 tahun ke depan" (60 langkah) TIDAK mungkin
dipenuhi penuh — `_MAX_HORIZON=36` hardcoded (`tools/forecast.py:31`, mirrored engine).
Prosa kini mewajibkan cap dinyatakan eksplisit; delivery 60 bulan sungguhan butuh perubahan
engine (dua sisi) + peringatan statistik (history ≤46 bulan). Non-determinisme residual
(temperature tak di-set, tanpa ledger antar-sesi) juga struktural — prosa = mitigasi,
fix sejati = engine (registry series terkode / temperature / cache).

### 6c. Wave 2c (2026-07-20, malam) — analisis fail-case v6 (26 run) + verdict "sudah cukup baik atau belum"

User meminta penilaian menyeluruh: apakah pemetaan context/skill sudah cukup, atau sisa fail
adalah edge case. Dibedah 3 pola fail tersisa dari `v6-after-finding-compact`:

1. **UAT-KOMITMEN-DISETUJUI-1 (refactor, `054935`)** — sistem BENAR (15.309 = kode `4` 2.914 +
   kode `7` 12.395, tabel per tahun, persis kontrak §12), gagal HANYA karena kata "Menengah
   Rendah" tidak pernah muncul (jawaban pakai "Medium Risk (MR)"). **Testfile tidak salah —
   assert menuntut istilah Indonesia yang memang seharusnya selalu ada.** Bug penamaan,
   ditutup Wave 2c-naming (di bawah).
2. **UAT-PIPELINE-VERIF-1 (`045210`, `053117`)** — tiga varian kontrak MENDARAT DI ANGKA YANG
   SAMA (1.844 headline sempit + 7.140 companion "belum selesai") lewat kanon pipeline §6/6a —
   bukti kanon mengikat. Fixture anchor lama (1.618, tol 10%) sudah dilewati drift riil (14%).
   **Testfile basi, sistem benar** — masuk backlog refresh (belum dieksekusi, menunggu
   persetujuan terpisah).
3. **UAT-OFF-3 / UAT-OFF-4 (`UAT-v2-compact`, bukan `-II`)** — `verification_date: 2026-06-26`
   (24 hari), `assert_contains` exact tanpa toleransi; OFF-4 note sendiri bilang "TRANSIENT —
   re-verify tiap run" tapi assert tak pernah ikut berubah. **Testfile basi** — lokasi baru,
   ditambahkan ke backlog (sebelumnya backlog hanya mencakup fixture di `UAT-v2` 27-soal).

**Verdict**: BELUM sepenuhnya "tinggal edge case" — dua titik context/skill genuine dan murah
diperbaiki (naming MR, lihat 6c di bawah) sudah dieksekusi; sisanya (baseline-only fail,
timeout infra 4/4-varian) memang sengaja dibiarkan (kontrol) atau di luar kendali (flaky infra
— scenario yang sama sukses di run lain hari yang sama).

### 6d. Wave 2c — Naming: istilah singkatan wajib disertai bentuk penuh (GENERAL, bukan MR-only)

Permintaan user eksplisit: perbaikan tidak boleh khusus MR/Menengah Rendah saja — harus
berlaku umum untuk semua singkatan domain. Klarifikasi istilah: **"MR" = Menengah Rendah**
(istilah resmi BPOM), BUKAN sekadar "Medium Risk" — terjemahan "Medium Risk" polos tidak
presisi karena menghilangkan pembeda Rendah/Tinggi yang justru INTI klasifikasinya.

Ditanam sebagai prinsip umum di **`predikat.md` §12-B** (twin v5==v2), bukan aturan
risiko-spesifik: *"any abbreviation or shorthand used in the answer spells out its full term
at least once"* — dengan daftar contoh terbuka: MR→Menengah Rendah, MT→Menengah Tinggi,
JP→Jenis Permohonan, BTP→Bahan Tambahan Pangan, NIE→Nomor Izin Edar, AMDK→Air Minum Dalam
Kemasan, UMKM→Usaha Mikro Kecil Menengah, "dan singkatan lain apa pun yang dipakai dokumen
ini". Baris MR/MT lama di `filter_code_reference.md` §3 disusutkan jadi rujukan satu baris ke
aturan umum ini (tidak diajarkan dua kali). refactor (resident) dapat versi inline yang sama
persis di `SEEKNAL_ASK.md`.

### 6e. Wave 2d — Hygiene: hapus kalimat "Eksklusi" berdiri sendiri, pertahankan gaya bullet "Catatan"

Temuan user dari sampel jawaban live: sistem kadang menulis **"**Eksklusi:** Akun uji coba
(test accounts) telah dikeluarkan dari perhitungan."** sebagai kalimat/baris tebal berdiri
sendiri — melanggar semangat §12-E ("hygiene diterapkan, tidak dinarasikan") meski secara
harfiah masih "disebutkan". Sebaliknya, gaya *"Catatan:"* — daftar bullet italic berisi
Scope/Metode/Filter, dengan satu bullet tambahan "*Data telah mengecualikan akun uji coba*" —
dinilai user **sudah baik** (tidak menonjol, berbaur dengan detail metodologi lain yang sah).

**§12-E ditulis ulang** (twin v5==v2 + resident refactor + skill `bpom-analyst` ×3): hygiene
tetap selalu diterapkan; larangan diperjelas — **tidak pernah jadi baris/kalimat tebal
berdiri sendiri**; BOLEH menumpang sebagai SATU bullet polos di dalam daftar
*Catatan/Metodologi* yang sudah ada untuk scope/metode/filter — tidak pernah jadi heading
sendiri, tidak pernah satu-satunya catatan metodologi yang tampil, tidak pernah disebut di
luar konteks daftar semacam itu.

**Verifikasi**: grep konfirmasi frasa baru tersebar di `predikat.md` (twin), `SEEKNAL_ASK.md`
refactor (resident), dan `bpom-analyst/SKILL.md` v5+v2; baseline `forecast anomaly` nol jejak
(bahkan tidak memiliki `predikat.md` — arsitektur lama, terkonfirmasi tak pernah tersentuh).
