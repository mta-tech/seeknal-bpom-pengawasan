# Forecast/QA E2E — Round 2 Deep-Dive (post tunnel-reconnect clean rerun)

> **2026-07-21 correction pass:** a bug was found in this doc's own CSV-fetch tooling
> (`scripts/fetch_csv_artifacts.py`) — it attributed bucket uploads to run folders by a wide
> time window, which bled entire unrelated batches' files into each other's `csv/` folders.
> The script was rewritten (§3) to attribute by the exact prompt/turn recorded in each run's
> own `_data.json`, all 6 previously-fetched `csv/` folders were wiped and regenerated, and
> every finding below that depended on file counts or scenario attribution (§3, §5, §8, §9)
> was re-derived from that corrected data. Findings §2, §4, §6, §7 were not affected and are
> unchanged from the original pass.

## 0. Context

Round-2's first attempt (QA `20260720_141508` + forecast `20260720_144613`) was contaminated
mid-batch by the SSH tunnel flapping (confirmed via `ps aux`, `psql` connection-refused, and the
`elapsed_s≈10.02 / llm_requests=0 / ConnectError` signature on 5+ scenarios) — that data was
discarded, not analyzed. After the user reconnected the tunnel, a clean rerun was executed:

- **QA round 2 (clean):** `20260720_214143` (18 singleturn) + `20260720_214322` (1 multiturn, QA-C8)
- **Forecast/ batch round 2 (clean):** `20260720_215749`

Round 1 baselines used for comparison:
- **QA round 1 (clean, pre-incident):** `20260720_134252` + `20260720_134627`
- **Forecast/ batch round 1:** none exists clean — the only forecast/ run before the incident was
  itself inside the contaminated window. **`20260720_215749` is therefore the first trustworthy
  forecast/ baseline, not a "round 2," and is reported as such below** rather than compared
  against a fabricated or discarded round 1.

## 1. Pass-rate comparison

| Batch | Round 1 | Round 2 | Note |
|---|---|---|---|
| QA (18 scenarios + 1 multiturn) | 16/18 | **18/18** | see below — one R1 fail is assert-wording noise, the other is a real (if harness-assisted) regression, see §5 |
| forecast/ (13 scenarios) | *(no clean baseline)* | **12/13** | FC-RISIKO-4 fails — real, layered finding, see §6 |

R1's two fails were **not** the same kind of issue, and this doc's first pass conflated them:

- **`QA-C6-H12`** is genuine assert-wording noise: `missing: 'Jan'` — the answer used the
  numeric-month format `2027-01` instead of the literal string "Jan" the assert expected, while
  all 12 months of detail were genuinely present. Benign, passes cleanly on R2's regeneration.
- **`QA-C4`** is **not** wording noise — re-reading its full 2-turn trace (§5) shows a real,
  if partly harness-triggered, defect: R1's first turn correctly calls `request_clarification`
  and passes, but the test harness's own auto-clarification-continuation feature then injects a
  **second, redundant turn** that gets the model to restate the forecast **from memory, with no
  tool calls at all** — and that restatement (a) drifts numerically from the tool-computed
  numbers and (b) doesn't happen to contain the word "tidak," failing the assert. R2 never
  triggers `request_clarification` at all (so no second turn is ever injected) and passes on a
  footnote wording technicality. Net effect: **the scenario that behaves more transparently (R1)
  is the one that fails, and the scenario that silently overrides the user's stated constraint
  (R2) is the one that passes** — see §5 for the full account.

## 2. Core engine determinism — confirmed, byte-for-byte

`HORIZON-6M/1Y/2Y/5Y` (same series, same SQL template, same window selection path) were compared
full-answer-text side by side between R1 (`134252`) and R2 (`214143`). Every point prediction and
every 80%-realistic-range bound is **identical** across the two independent runs, e.g.:

| Periode | R1 | R2 |
|---|---|---|
| Juli 2026 | 5.627 (4.695–6.558) | 5.627 (4.695–6.558) |
| Agustus 2026 | 5.641 (4.324–6.958) | 5.641 (4.324–6.958) |
| ... (36 months checked in HORIZON-5Y/QA-C7) | identical | identical |

This holds for all 36 months exposed via `HORIZON-5Y`/`QA-C7`, and for the 24-month `HORIZON-2Y`
table. **Conclusion: the ETS engine itself is fully deterministic given a stable DB + stable SQL —
reconfirmed independently of the earlier same-day determinism findings.** Only decimal-separator
formatting (`,` vs `.`) and table layout (full list vs "poin terpilih") vary — see §4.

### MAPE 18,4% vs "Akurasi 81,6%" — resolved, not a bug

R1's `HORIZON-3M`/`HORIZON-6M` narration says "MAPE 18.4%"; R2's says "Akurasi: 81,6%" for the
same series/quality. **100 − 18.4 = 81.6** — this is the same underlying number reframed as an
accuracy-percentage instead of an error-percentage, not a computation discrepancy. Checked against
the other HORIZON pairs (1Y/2Y/5Y all consistently say "MAPE 18.4%"/"18,4%" in both rounds) — the
accuracy-framing only appeared once, in R2's `HORIZON-3M`. Benign, but worth a §12 predikat.md note
if strict wording consistency is ever required across regenerations (out of scope to change without
explicit ask, flagged for awareness only).

## 3. CSV-fetch tooling bug found and fixed (`scripts/fetch_csv_artifacts.py`)

The user asked, correctly, why a single QA-C8 run (2 turns, 2 real uploads) produced a `csv/`
folder with 27 files. Investigation traced it to a bug in this session's own audit tooling, not
the product:

- **v1's method:** grab every S3 object uploaded in the *N minutes before the run folder's own
  save timestamp* and dump all of it into that run's `csv/` folder, with no per-scenario boundary
  at all (iba-storage renames uploaded objects to `slugify(question)[:60]-<upload timestamp>`,
  with no run/scenario id embedded, so v1 had no way to filter more precisely).
- **The bug:** QA-C8's multiturn run (`214322`, saved 21:43:22) was launched only ~99s after the
  18-scenario singleturn batch (`214143`, saved 21:41:43). Their 15-minute lookback windows
  overlapped by ~14 of their 15 minutes. Diffing the two folders' `csv/` contents confirmed **all
  24 files genuinely belonging to `214143` were also duplicated into `214322`'s folder** — an
  entire unrelated batch bled into QA-C8's folder. It ran the other way too: 3 files, including
  QA-C8's own genuine turn-2 upload, bled into the unrelated forecast batch folder (`215749`)
  purely because its window's tail overlapped QA-C8's run.
- **Confirmed not a product bug:** QA-C8's own `_data.json` trace shows exactly 2 `upload_to_s3`
  calls (1 per turn) — matching the "one download button per answer" expectation exactly. The
  agent's upload behavior was correct; only the offline fetch script's attribution was wrong.
- **The fix (v2):** for each run, read that run's own `_data.json` (which every
  `test_variant_compare.py` run already writes) and, for every `upload_to_s3` call in trace
  order, recompute the same slug iba-storage would have generated from that turn's own recorded
  `prompt` text. Match bucket objects by a 50-character slug prefix (safely below the storage
  service's 60-char truncation boundary) instead of by time proximity. When a single turn made
  more than one `upload_to_s3` call (see §5's real duplicate-upload finding below), the matching
  bucket objects are paired to that turn's calls in ascending-Mtime / trace order and saved with
  an explicit `_upload1of2`/`_upload2of2` suffix so the duplicate is visible in the filename
  itself. A generous ±6h bucket scan is kept only as a coarse performance/safety bound, not as
  the attribution mechanism.
- **Validated:** re-running the fixed script against `214322` now returns exactly
  `QA-C8__T1__...` and `QA-C8__T2__...` — 2 files, nothing else. All 6 previously-fetched
  `csv/` folders (`124612`, `134252`, `134627`, `214143`, `214322`, `215749`) were wiped and
  regenerated with the fix.
- **Known remaining gap (by design, not silently guessed around):** a handful of `[AUTO]`
  harness-injected continuation turns (auto-selected clarification follow-ups — see §5) log a
  synthetic prompt like `[AUTO] ERBA (Pangan RBA)` rather than real conversational text, and that
  synthetic string doesn't match how iba-storage actually slugified whatever the model's
  underlying turn produced. These turns are reported as **unmatched with an explicit warning**
  rather than guessed via a fallback time window (which would reintroduce exactly the bug being
  fixed). Affected: `QA-C1-C2`, `QA-C3`, `QA-ERBA-NOMIX-1` (both rounds), `FC-RISIKO-4`,
  `FC-BTP-4` (forecast batch). One genuine non-tooling case surfaced by this too: R1's `QA-C5`
  turn made 2 `upload_to_s3` calls but only **one** distinct object exists in the bucket for that
  slug at any time window (checked bucket-wide, not just near this run) — the second call's
  upload did not survive as a separate object, a storage-layer detail worth noting alongside the
  duplicate-upload finding in §5, not a fetch-script artifact.

## 4. QA-C7 boundary-100bulan: detail completeness regressed, assert too loose to catch it

R1 (`134252`) exposed the **full 36-row monthly table** for the 100-bulan→36-bulan-capped request.
R2 (`214143`) exposed only a **7-row "Poin Terpilih" (selected points) table** plus a separate
7-row range table — same underlying values wherever they overlap (2026-07=5.627, 2026-12=4.209,
2027-06=5.383, 2028-06=5.744, 2029-06=6.104, all byte-identical to R1), but roughly 80% less detail
surfaced to the user on this regeneration. `assert_contains: ['36']` only checks the cap number is
mentioned — it does **not** catch this completeness drop, and both runs report ✅ PASS. Given the
user's explicit requirement this session that assertions validate **monthly-breakdown detail**, this
is a real gap in QA-C7's own assert strength (a narrower, more specific fixture — e.g. asserting a
sample of 8–10 distinct month labels — would have caught the R2 regression). Recommend tightening
`QA-C7`'s assert if this pattern recurs; not changed yet since it's a test-fixture edit, not context/
skill, and wasn't explicitly requested.

## 5. Key finding (high severity) — QA-C4: clarification path is non-deterministic, changes final numbers, AND the harness's own auto-continuation mechanic inverts the pass/fail verdict

This is the most important finding of this round, and the full 2-turn trace (re-read directly
from `_data.json` + `QA-C4.md` this correction pass) tells a richer story than the first pass did.

Same question both times: *"Prediksi permohonan ERBA untuk 3 bulan ke depan, tapi hanya pakai data
6 bulan terakhir saja"* (6-month window is DB-verified <10 points — `forecast_guide.md` §3 mandates
refusal below 10).

**R1 (`134252`) — 2 turns:**
- **Turn 1** (the real, YAML-defined turn): loads `forecast_guide.md` → `predikat.md` → calls
  **`request_clarification`**, offering 3 explicit choices (recommended/full data ★, 12-month
  minimum, or historical-trend-only). The harness auto-selects the recommended option, and the
  model continues **within this same turn**: `run_forecast` once → **PASS**, answer contains
  "tidak" (via "...tidak memenuhi syarat minimum teknis") and gives
  **Juli 5.627 / Agustus 5.641 / September 5.327** — identical to the standard ~36-month
  HORIZON numbers.
- **Turn 2 `[AUTO-CLARIF]`** (`prompt: "[AUTO] Gunakan Rekomendasi (Data Lengkap)"`): the test
  harness's own auto-continuation feature re-invokes the model with the *same* auto-selected
  choice **again**, even though turn 1 already completed the flow end-to-end. This turn makes
  **zero tool calls** — the model just restates an answer from conversational memory — and that
  restatement (a) numerically **drifts** from turn 1's tool-computed values
  (**Juli 5.626 / Agustus 5.326 / September 5.645** — note Agustus and September are not just
  off by rounding, they look transposed relative to turn 1's 5.641/5.327) and (b) never contains
  the literal word "tidak" anywhere → **FAIL** (`missing: 'tidak'`).
- **Scenario-level verdict: FAIL** (1 of 2 turns failed) — this is why `QA-C4` shows up as one of
  round 1's two fails in §1, and it is **not** the same kind of issue as `QA-C6-H12`.

**R2 (`214143`) — 1 turn only:** loads the same context files (plus `filter_code_reference.md`,
`data_architecture.md`) → **never calls `request_clarification` at all**, so no auto-continuation
turn is ever injected → runs `run_forecast` (unqualified, degenerate), `execute_sql` directly,
`run_forecast` again → silently narrates "data historis 24 bulan terakhir" in a footnote-style
*Catatan* and proceeds → **Juli 6.065 / Agustus 5.704 / September 5.272** — a real, materially
different forecast (+7.8% on July alone) for the exact same question. Passes because the footnote
happens to contain "tidak dapat dipenuhi."

**Why this matters more than a wording nit:** `forecast_guide.md` §2 does allow an **adaptive
24-or-36-month window** by design, so R2's 24-month choice isn't itself illegal — but the two runs
disagree on **whether the user gets a say** in which fallback is used, and that disagreement
produces two different sets of numbers for one identical prompt. Worse, the current scoring
mechanism actively **rewards the wrong side of that disagreement**: R1 (asks the user, transparent,
consistent numbers) fails because of an unrelated harness artifact (a phantom auto-continuation
turn restating from memory instead of re-invoking a tool); R2 (silently overrides the user's stated
constraint) passes on a footnote technicality. This is a genuine Consistency Contract-relevant
finding (not narration variance) and traces directly to the original external QA report's C.4 item
(P0). Two separate things are worth fixing, at different layers:
1. **Product/policy layer:** make the insufficient-data → clarification path a hard rule in
   `bpom-forecaster`/`predikat.md` rather than a sometimes-taken branch, so the fallback window is
   chosen the same way (and disclosed the same way) every time. Not changed yet — awaiting
   explicit go-ahead since it touches the forecaster's decision policy, not just wording.
2. **Test-harness layer:** the auto-clarification-continuation feature should not re-invoke the
   model with the same auto-selected choice when the *original* turn already completed the flow
   with tool calls and a final answer — or if it does, the model should be expected/instructed to
   re-verify via tool call rather than restate from memory, since memory-restatement is where the
   numeric drift and the assert-breaking wording loss both come from. Flagging for whoever owns
   the `test_variant_compare.py` auto-continuation logic; not changed, not explicitly requested.

## 6. Duplicate `run_forecast` + `upload_to_s3` — authoritative count from `_data.json`, both rounds

The first pass of this doc only spotted this pattern by manually reading two scenarios' `.md`
traces. This pass extracted the exact `upload_to_s3` count per turn directly from every run's
`_data.json` (ground truth, independent of what the CSV-fetch script can recover from the bucket)
across all three runs:

| Run | Scenarios with >1 `upload_to_s3` in one turn |
|---|---|
| R1 QA singleturn (`134252`) | `QA-C5` (4× `run_forecast`, 2× upload), `QA-C7` (2× `run_forecast`, 2× upload) |
| R2 QA singleturn (`214143`) | `HORIZON-6M`, `HORIZON-5Y`, `QA-C9` (all 2× `run_forecast`, 2× upload) |
| R2 forecast batch (`215749`) | `FC-RISIKO-1`, `FC-RISIKO-2` (both 2× `run_forecast`, 2× upload) |
| R1/R2 QA-C8 multiturn (`134627`/`214322`) | none — clean, exactly 1 upload per turn both times |

Roughly 2–3 scenarios per ~15-20 scenario batch exhibit this in both rounds, but **which**
scenarios does not repeat between rounds (QA-C5/QA-C7 in R1 vs HORIZON-6M/5Y/QA-C9 in R2) —
confirming it is a stochastic regeneration artifact, not tied to a specific series or prompt
shape. Reading the tool traces (`QA-C5.md`, `FC-RISIKO-1.md`) shows the same recurring shape every
time: a `run_forecast` call against an **unqualified table name** (e.g. `t_produk_3_erba` instead
of `warehouse.public.t_produk_3_erba`) returns a plausible-looking, small-but-real result instead
of erroring outright, the model uploads it, *then* self-corrects (sometimes via `list_tables`) and
re-runs against the schema-qualified table, uploading again. Because SeaweedFS keys carry the real
upload timestamp, no data is lost or silently overwritten in the common case — this is a
compute/storage-waste and duplicate-download-button UX issue, not a correctness bug in the general
case. (The one exception found this pass: R1's `QA-C5` second upload_to_s3 call has **no**
surviving distinct bucket object at all — see §3's note — meaning in at least one observed case the
"duplicate" silently collapsed to a single file rather than two, which is a slightly different and
arguably worse failure mode than wasted duplicate storage.) Root cause is in the `run_forecast`
retry pattern itself (why does the unqualified-table-name attempt succeed with a plausible result
at all, inviting an early upload, instead of erroring outright?) — out of scope for context/skill-only
changes; flagging for whoever owns `tools/forecast.py`.

## 7. FC-RISIKO-4 (forecast/ batch, only fail) — carried over, still open

`FC-RISIKO-4` ("Prediksi permohonan tinggi notifikasi untuk semester depan") triggers a genuine
code-collision clarification (kd304 "Tinggi Notifikasi" vs kd305 "Baru Notifikasi") and then a
legitimate CV-based refusal (2025–2026 volume for kd304 jumped from <100/month to 300–500+/month, a
real structural break — `run_forecast` correctly declines). The LLM's fallback narrative then
computes its own rough estimate ("estimasi 2.400–2.800") rather than declining outright — bordering
on the "never use manual arithmetic for forecast numbers" rule. This was found before the tunnel
incident and has not changed on this clean rerun (still the sole fail, same shape). Not yet
re-verified for reproducibility across multiple independent runs — only one clean data point exists
so far since forecast/ has no clean round-1 baseline to compare against (see §0).

## 8. Cross-horizon consistency (positive finding)

`FC-BTP-1` (3-month ask) and `FC-BTP-2` (6-month ask, same series) — both round 2 — agree exactly
on the 3 overlapping months: Juli 160 (122–199), Agustus 170 (116–225), September 176 (122–231),
same MAPE 34.6%/LEMAH quality label in both. Confirms horizon-length phrasing doesn't perturb the
underlying series computation, matching the same pattern already established for
`HORIZON-*` above.

## 9. CSV / DB triangulation (round 2, re-verified with corrected attribution)

Re-fetched with the fixed script (§3): `FC-BTP-2`'s CSV is now saved as
`FC-BTP-2__T1__berapa-prediksi-jumlah-registrasi-btp-erba-untuk-6-bulan-ke-...csv` — unambiguously
its own file (unique, specific slug; no other scenario in this or any nearby run asks a
similar-enough question to collide with this prefix). Spot-checked its historical data (Jan–Jun
2026: 173/159/166/153/102/89) against a live `psql` query on `t_btp_3_erba` for the same window —
**exact match**, closing the three-way chat-answer ↔ CSV ↔ live-DB loop for this round the same way
it was closed for the prior round. This conclusion is unchanged from the first pass; the only
difference is the file is now provably correctly attributed rather than merely time-window-adjacent.

## 10. Summary of action items

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | MAPE/Akurasi reframing | cosmetic | no action needed |
| 2 | `fetch_csv_artifacts.py` bled unrelated batches' CSVs into each other via time-window matching | tooling bug | **fixed this pass** — rewritten to attribute by per-turn prompt slug from `_data.json`; all 6 `csv/` folders regenerated |
| 3 | Duplicate `run_forecast`+`upload_to_s3` in a single turn (both QA batches, both rounds, and forecast batch) | moderate | root cause in `tools/forecast.py`'s unqualified-table-name retry pattern — needs engine-side fix, not context/skill |
| 4 | QA-C7 assert too loose to catch detail-completeness regression | moderate | tighten fixture assert (test-only change, not yet made) |
| 5 | QA-C4: clarification path non-deterministic, changes final numbers; harness auto-continuation turn restates from memory and inverts the pass/fail verdict | **high** | product/policy fix needs a hard rule in `bpom-forecaster`/predikat.md (awaiting go-ahead); harness fix needs auto-continuation to not re-invoke without a fresh tool call (flagged, not changed) |
| 6 | FC-RISIKO-4 fallback self-estimate | open, carried over | needs more repeated runs to confirm reproducibility |
| 7 | R1 QA-C5: one of two upload_to_s3 calls has no surviving distinct bucket object | minor, informational | storage-layer nuance, not a fetch-script bug — noted alongside finding #3 |
