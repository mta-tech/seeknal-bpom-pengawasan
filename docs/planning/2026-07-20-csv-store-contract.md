# seeknal-bpom-neo: CSV Store Contract + Forecast Horizon Fix

**Document type:** Implementation note  
**Date:** 2026-07-20 (updated through the evening double-call investigation + self-check fix)  
**Status:** Applied to the three hypothesis variants (`docs/context_recap/after-anomaly/`: `v5-predikat-trim`, `after-forecast-anomaly-refactor`, `after-forecast-anomaly-refactor-v2`). Baseline `forecast anomaly` untouched — it stays the causal control.  
**Scope:** `skills/bpom-forecaster/SKILL.md` (6.0.1 → 6.1.0) · `skills/detect-anomaly/SKILL.md` (1.0.1 → 1.1.0) · `skills/bpom-analyst/SKILL.md` (CSV block) · `SEEKNAL_ASK.md` · `context/forecast_guide.md` §5  
**Baseline:** post `2026-07-13-forecast-anomaly-and-csv-era.md`  
**Constraint:** context / skill / SEEKNAL_ASK only — zero engine-code change.  
**Current state (end of day):** double-call rate reduced but not eliminated (see §5f) — user judged results "sudah cukup baik" (good enough) as of runs `080301`/`080538`; a code-level hook (H-C1) remains the option if 0% is ever required.

---

## 1. Purpose

Live webapp testing (variant `forecast anomaly`, real users) surfaced three problems:

1. **Forecast CSV incomplete.** `run_forecast` auto-uploads projection points only; the
   historical series behind the answer was never exported. Correct, but incomplete.
2. **Non-baseline variants exported the wrong CSV.** Their `bpom-analyst` rule ("once per
   turn, the SQL behind the final answer") collides with the forecaster's auto-upload on
   forecast turns: the "SQL behind" a projection does not exist, so the model exports
   something else — an exploratory query, a duplicate, or (worst) `data=` rows it typed
   itself.
3. **Horizon requests misread.** "6 bulan / 1 tahun / 5 tahun" answers presented only a few
   months. Tool-side causes: `periods` defaults to 3 when omitted; requests > 36 are clamped
   **silently**; and the deployed 6.0.0 skill lacked the two horizon rules already present in
   6.0.1 (`periods` always explicit, present the full computed horizon).

## 2. The Contract (one rule, all question types)

> **One question = one stored CSV = the data behind the answer.**

- Applies to tabular, forecast, anomaly, and **descriptive answers that still convey data
  values**. Only a purely conceptual answer ("apa itu NIE" — no data at all) skips the export.
- **Tabular/analytical** → `upload_to_s3(filename=..., sql=<exact final-answer SQL, no
  LIMIT>)`. Never an exploratory query, never more than one.
- **Forecast** → the projection CSV is auto-uploaded by `run_forecast` (tool-owned, does
  **not** count as the agent's store). The agent's one export is the **historical series**:
  the exact SQL passed to `run_forecast`, filename `<series>_historis.csv`.
- **Anomaly** → `detect_anomaly` does not self-upload; the one export is the same SQL given
  to it. Flagged points live in the tool's markdown and cannot be exported without an engine
  change — never re-typed into `data=`.
- **Several series in one question** (multi-`run_forecast` turns) → still ONE export: one SQL
  with a series label column (`SELECT 'MR' AS series, x, y ... UNION ALL SELECT 'MT', ...`),
  refused/fallback series included. This resolves the multi-forecast case without a
  per-call pairing rule.
- **Mode 2 ban:** the agent never calls `upload_to_s3(data=..., columns=...)` — that path is
  reserved for internal tools; agent-typed numbers are not evidence (fabrication channel).

**No new `csvstore` skill.** A skill only acts when the model loads it — a fourth skill adds a
load-dependency failure mode exactly where reliability is needed. Instead the contract lives
**resident** in `SEEKNAL_ASK.md` (the only guaranteed channel) and is bound into the three
existing skills at their CSV decision points.

## 3. Changes Per File (all three variants unless noted)

| File | Before | After |
|---|---|---|
| `skills/bpom-forecaster/SKILL.md` | 6.0.1 — CSV: projection auto-uploaded; extra dataset export optional ("Only call … explicitly"); horizon cap prose only | 6.1.0 — CSV block = Store Contract (historis export mandatory, same SQL, one labelled UNION for multi-series, Mode 2 ban); horizon bullet gains explicit translations (6 bln→6 · 1 thn→12 · 3 thn→36 · 5 thn→60→capped) + duty to state the silent 36 cap; new hard rule "Same question → same SQL" (§3 registry canonical, keep current-month cutoff — adaptive window can flip) |
| `skills/detect-anomaly/SKILL.md` | 1.0.1 — export once with same SQL if anomalies found | 1.1.0 — same rule restated under the Store Contract + multi-series label column + `<series>_historis.csv` naming + explicit note that flagged points are not exportable + Mode 2 ban |
| `skills/bpom-analyst/SKILL.md` | "CSV export (once per turn, only for tabular answers)" — collides with forecaster on forecast turns | "CSV Store Contract (one store per question)" — data-bearing test (descriptive-with-data → export; conceptual → skip) + arbitration: forecast/anomaly turns belong to that skill's export, auto projection CSV doesn't count, never add another, never `data=` (three variant-specific wordings, same content) |
| `SEEKNAL_ASK.md` | v5: no CSV rule. v2 & refactor: one line "CSV: once per turn…" | v5: new `## CSV Store Contract` section. v2: line replaced by 5-line compact contract. refactor (resident channel): full `## CSV Store Contract — one store per question` block with per-question-type bullets |
| `context/forecast_guide.md` §5 | no CSV rule | new bullet: Store Contract summary + "the 36-step cap is silent in the tool — stating it is the agent's job" |

Integrity checks done: `bpom-forecaster` and `detect-anomaly` SKILL.md byte-identical across
the three variants; `forecast_guide.md` twin v5 == v2 preserved (refactor differs only in its
headline style, as before).

## 4. What Prose Cannot Do (known limits, engine follow-ups)

- One **combined** history+projection CSV needs `_upload_forecast_points` to include history
  (H-E1) — per-call, multi-series-safe by construction.
- Hard-blocking agent `data=` uploads needs a PRE_TOOL_USE hook (H-C1).
- Exporting anomaly flagged points needs a `detect_anomaly` self-upload.
- `agent.forecast.max_horizon: 12` in `seeknal_agent.yml` is dead config (engine reads
  `enabled` only; real cap = `_MAX_HORIZON = 36` in `tools/forecast.py`). Left untouched.

This change set is therefore also an experiment: if compliance leaks (missing historis
export, extra exports, `data=` use), that is clean evidence to escalate to H-E1 + H-C1.

## 5. Validation

Forecast/anomaly/tabular scenarios across the 4 variants (baseline as control). Assert at the
upload layer, not just the answer: exactly one agent export per data question (zero for
conceptual), export SQL == forecast SQL on forecast turns, no agent Mode 2 calls, cap
statement present when the request exceeds 36 steps. Note: `test_variant_compare.py` does not
yet capture upload payloads — small harness addition required before the full assert set runs.

## 5b. Amendment (2026-07-20, sore — Wave 2)

Run evidence (0323-0347 + 041051) showed uploads firing mid-turn (step 5-9 of 10-18) and
twice per turn (v5 PIPELINE-TOTAL, v5 SKALA-1, refactor SUSU). The contract now binds
POSITION and COUNT: the export is the turn's FINAL tool call (after all evidence and
CHECK/Gate 5, immediately before the answer); a premature upload may not be repeated; a
second upload is forbidden. Implemented as an explicit **EXPORT** step in the analyst flows
and ordering clauses in forecaster/detect-anomaly/SEEKNAL_ASK — see
`2026-07-20-canon-wave-pipeline-company-tier.md` §6. Engine-unavailable behaviour was
deliberately NOT written into context/skills (user decision): it is an ops prerequisite
(`IBA_ENGINE_URL` + iba-engine container up) — all 2026-07-20 forecast/anomaly runs executed
against a dead engine.

## 5c. Amendment (2026-07-20, malam — Double-call fix)

Run evidence (v6 045210-060259) showed `upload_to_s3` firing twice per turn with identical
filename and SQL (result_chars=51 each). Root cause: CSV Store Contract duplicated in
`SEEKNAL_ASK.md` AND `bpom-analyst/SKILL.md` (5 instruction sources total across SEEKNAL_ASK +
analyst + forecaster + detect-anomaly). The agent followed both instructions, calling
`upload_to_s3` twice with the same data.

Fix (all 3 hypothesis variants):
- Removed `## CSV Store Contract` section from `SEEKNAL_ASK.md` — replaced with one-line
  reference: "CSV export: see `bpom-analyst/SKILL.md` — one store per question."
- Added cross-scope declaration to `bpom-analyst/SKILL.md`: "Applies to tabular, forecast,
  anomaly, and data-bearing descriptive answers alike; purely conceptual answers skip it."
  (the one concept unique to SEEKNAL_ASK.md, not already in any skill file)

Result: single source of truth in `bpom-analyst/SKILL.md` only. Baseline untouched.

## 5d. Independent audit of §5c's fix (2026-07-20, evening) — partially refuted, real bug confirmed with precise root cause

User pointed at a pasted analysis from a separate agent session claiming (a) double-call
"CONFIRMED" across many scenarios, and (b) after the §5c fix, `s3_uploads = 0` in **every**
scenario ("overcorrected"). Independent, objective re-audit directly against `tool_trace`
(not the top-level `_data.json`, which has **no `s3_uploads` field at all** — confirmed by
schema dump) across all 26 runs in `seeknal/tests/outputs/2026-07-20/v6-after-finding-compact`:

- **Claim (b) is FALSE for the runs it should apply to.** File mtimes (WIB) vs run-folder
  names (**UTC** — folder `20260720_071430` = 07:14 UTC = 14:14 WIB, NOT 07:14 WIB) show the
  §5c fix landed 14:01–14:04 WIB (07:01–07:04 UTC). Only 2 of 26 runs are genuinely post-fix:
  `071430` (SUSU-1) and `072116` (TOP-PERUSAHAAN-1). Both show real, non-zero `upload_to_s3`
  calls in `tool_trace` (v5/v2/refactor all uploaded ≥1×). The "0 everywhere" claim is a
  **measurement bug** in the other analysis (checking a field that doesn't exist), not a
  regression.
- **Claim (a) is TRUE, and quantified precisely.** Rate of turns with ≥2 `upload_to_s3` calls,
  as a fraction of turns that uploaded at all, across all 26 runs:

  | Variant | Turns w/ upload | Turns w/ ≥2 | Rate |
  |---|---|---|---|
  | **refactor** (resident) | 24 | **9** (incl. one triple-call) | **37.5%** |
  | forecast anomaly (baseline, untouched) | 14 | 2 | 14.3% |
  | refactor-v2 (gated) | 22 | 2 | 9.1% |
  | v5-predikat-trim | 26 | 2 | 7.7% |

  refactor is the clear outlier (2.6×–4.9× the other variants) — and this held true **even in
  the run post-dating §5c's fix** (`072116`, refactor still u2). §5c's consolidation
  (SEEKNAL_ASK → skill-file pointer) reduced instruction duplication but did not fix the
  underlying behaviour.
- **Two distinct mechanisms identified**, not one:
  1. **True mid-turn duplicate** — same LLM turn, `upload_to_s3` called twice in a row, same
     filename, same SQL, gap 4.2s–178.7s (no consistent direction). Confirmed the tool's own
     design compounds the cost: Mode 1 (`sql=...`) re-executes the query independently on
     *each* call (`ctx.repl.execute_oneshot`, no cache reuse) — a repeat call is not free, it
     re-runs the full query.
  2. **Harness-induced re-turn duplicate** — `request_clarification` does not block
     `execute_sql` (known gap, see prior audits); the model calls it but still completes a
     full answer + upload in the *same* turn; the test harness's `--auto-clarif` then appends
     a synthetic `[AUTO] <option>` follow-up turn purely because `ask_user_calls≥1`, without
     checking whether the first turn already answered — producing a **second independent
     computation with a different final number** (v5/OFF-1a `065420`: 5.385 vs 5.496 NIE) and
     its own upload. This is also a **consistency-contract violation** (§12-F).
- OFF-3/OFF-4 (`UAT-v2-compact`) "stale fixture" claim: confirmed consistent (`verification_date:
  2026-06-26`, exact `assert_contains`, no tolerance) — same disease as the fixtures already
  refreshed in `UAT-v2-compact-II`; not yet on that refresh backlog, added now.
- SUSU-1/TOP-PERUSAHAAN-1 "infra" claims: directionally right but **intermittent, not fixed
  state** — the same scenarios ran cleanly (3–4/4 variants) in other runs the same day; the
  specific failing instance likely coincided with the live model/API instability observed
  independently this session.

## 5e. Fix — self-check procedure (2026-07-20, evening), replacing §5c's bare pointer

Two problems remained after §5c: (1) refactor's elevated rate, (2) a **new gap the user
caught**: §5c's `SEEKNAL_ASK.md` line — `"CSV export: see bpom-analyst/SKILL.md — one store
per question."` — is a bare pointer with **no actual rule content**. `SEEKNAL_ASK.md` is the
only guaranteed-resident channel; the skill body is lazy-loaded and can be absent from a given
turn's context. If `bpom-analyst` isn't loaded, the CSV rule (and the anti-duplicate language)
doesn't exist in context at all for that turn.

Root-cause investigation for why refactor is the outlier: refactor-v2 (gated) already carries
an explicit "Budget ledger — count everything, hard-STOP" cognitive frame throughout its whole
skill; refactor (single-source) has no such self-monitoring frame anywhere. The internal
redundancy inside `bpom-analyst/SKILL.md` (step "EXPORT" mentioning rules "in the section
below", which then restates them) turned out to exist **identically in all three variants** —
not the differentiator.

**Fix applied (all 3 variants + baseline left untouched):**
1. **Self-check procedure**, not a bare prohibition — added to `bpom-analyst`,
   `bpom-forecaster`, `detect-anomaly` SKILL.md (×3 each): *"Before calling `upload_to_s3`,
   scan this turn's own tool calls so far — does `upload_to_s3` already appear (any filename)?
   If yes, do NOT call it again, go straight to the answer."* refactor's step 5 (EXPORT) leads
   with the check inline; the CSV section adds *why* it matters (repeat call re-runs the query
   independently, wastes compute — a reason, not just a rule).
2. **SEEKNAL_ASK.md bare pointer → self-sufficient short block** (all 3, ~5–6 lines): one
   export per question, LAST tool call of the turn, the self-check itself, `data=`/`columns=`
   ban — resident regardless of skill-load state. Not a return to §2's long multi-bullet
   version (that duplication was the §5c-identified problem) — short, and the check is the
   load-bearing part.

## 5f. Verification — runs `080301` (SKALA-2) and `080538` (OFF-1a), post self-check fix

Both runs postdate the self-check edits (mtime 14:52–14:56 WIB; runs at 15:03/15:05 WIB).
Pass rate 4/4 and 3/4 (baseline fail = expected, untouched control reproducing the pre-audit
JP-filter bug on "terbit"). Upload counts: u1 in nearly every cell — **except refactor/SKALA-2
still shows u2**. User's verdict: **"hasilnya sudah cukup baik"** (good enough) — rate is
clearly and substantially reduced from §5d's 37.5% baseline, but not proven at 0%. Documented
honestly rather than claimed as solved: prose (self-check included) demonstrably lowers the
rate; it has not been shown to eliminate it. If 0% is ever required, the remaining path is a
PRE_TOOL_USE hook (H-C1, §4) blocking a second `upload_to_s3` call in one turn — analogous to
the existing `failed_tool_signatures` dedup for failed SQL retries, just for successful
uploads. **Out of scope without explicit approval** (touches engine code, not context/skill).

**B2 (harness `--auto-clarif` fix for mechanism 2 above) was proposed and explicitly
REJECTED by the user** — not pursued, not revisited without a new request.

## 6. Rollback

All edits are additive/self-contained blocks in the three variant dirs; restore any file from
git (`docs/context_recap/after-anomaly/...`) to revert. Baseline was not touched.
