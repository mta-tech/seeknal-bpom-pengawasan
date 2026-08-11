---
name: bpom-forecaster
description: "Forecasting skill for predicting future registration trends. Computes projections deterministically from historical data with quality labels."
tags: [bpom, forecast]
version: "6.2.0"
---

# BPOM Forecaster (Trigger)

Routes BPOM forecast requests to `run_forecast`. This skill owns only the
BPOM CAPTURE parameters — all compute is deterministic (ETS seasonal fit
inside the IBA forecast engine). The LLM does **no** forecast arithmetic.

Load `context/forecast_guide.md` first — it has the data source, SQL
template, series registry, quality thresholds, and output rules. This file
covers only the tool workflow.

## CAPTURE
Lock `{sql, periods}`.

- Default system = ERBA; series not stated = Permohonan Total.
- **Horizon translation:** `periods` is a step count on the SQL's own grain —
  monthly: 6 bulan → 6 · 1 tahun → 12 · 3 tahun → 36 · 5 tahun → 60 → capped.
  Cap at 36; the tool clamps silently, so when the request exceeds it, SAY in
  the answer that 36 months is the maximum supported horizon and present those.
- **"hingga/sampai {X}"** = every step from the period after the last actual
  **through the end of X** — the intermediate periods are part of the request,
  not just the named year/month. **Always pass `periods` explicitly** — the
  tool defaults to 3 when omitted.
- ERLA request → refuse, offer ERBA projection or ERLA historical trend.
- Build the SQL using `forecast_guide.md` §1's template exactly (table +
  filter from §3's registry). If the source/series is ambiguous, call
  `request_clarification` first.

## RUN
Call `run_forecast(sql, periods)`. Do NOT compute forecast numbers yourself.

- `## Kesalahan` with "policy check (STEP 0.5)" → SQL has a JOIN/
  `generate_series`/recursive CTE — rebuild flat per the template, don't retry the same pattern.
- `## Kesalahan` with "STEP 1: EXECUTE" → runtime error — recheck against
  `forecast_guide.md` §1/§3 and retry corrected.
- `## Ditolak` → present the engine's reason (usually insufficient history),
  offer historical trend instead; don't retry unless the request changes.

## PRESENT
Read the tool's markdown and compose prose around it — don't invent a new
structure. Lead with the quality label. Follow `forecast_guide.md` §5 for
vocabulary (never show raw `sigma`/`sub_type`/field names/CV number).

**Present the full computed horizon.** Every predicted period the tool returned
appears in the answer — never truncate to the first months or to the named
year only. A "hingga {X}" answer runs from the first predicted period through
the end of X (add per-year subtotals when it spans years).

**The Answer Contract applies to forecasts too (transparency, general).**
Every projected period is its own row (point + Rentang Realistis); the
tool's history block is presented in full alongside the projection, never
dropped; multiple series → per-series labelled sections (code + dictionary
description per series). The stored CSVs must cover exactly the horizon
presented: projection CSV = ALL projected periods (tool-owned), historis
CSV = the full history window. When the request exceeds the 36-step cap,
the answer AND the export presentation both state "36 bulan (maksimum yang
didukung)" — never silently deliver less than asked.

**Anomaly:** if the tool's markdown has an `## Anomali` block, include it
and state the points were **not removed**. If the user asks about
anomalies directly, call `detect_anomaly(sql)` yourself (works whether or
not a forecast ran this turn) — see `forecast_guide.md` §6.

**CSV (Store Contract — one store per question):** `run_forecast`
self-uploads its projection points on success — that file is tool-owned:
never re-upload projection points yourself. Your export is the ONE store
this question gets (`SEEKNAL_ASK.md` CSV Store Contract): the data behind
the answer, i.e. the historical series —
`upload_to_s3(filename="<series>_historis.csv", sql=<the exact SQL passed
to run_forecast, no LIMIT>)` — called as the turn's FINAL act: after every
forecast/evidence call is done, immediately before writing the answer,
never right after `run_forecast` with more queries still to come.
**Self-check before calling it:** does `upload_to_s3` already appear in this
turn's tool calls? If yes, skip straight to the answer — never twice.
Several series in one question → still ONE
export: one SQL with a series label column
(`SELECT 'MR' AS series, x, y FROM ... UNION ALL SELECT 'MT', ...`);
include refused/fallback series there too. Never `data=`/`columns=` —
numbers you type are not evidence. Never paste the raw URL; the Download
button renders automatically.

## Stock vs Flow

| Question pattern | Kind | Y expression |
|---|---|---|
| "NIE **baru**/**terbit**/permohonan per bulan" | flow | `COUNT(DISTINCT produk_id)` |
| "NIE **aktif**/**terdaftar**/total sekarang" | stock | `SUM(COUNT(DISTINCT produk_id)) OVER (ORDER BY date_trunc(...))` |

For stock queries, the fit may show some upward drift but doesn't
reliably track a real cumulative total's growth rate — say so; a genuinely
reliable stock projection needs a separate deliberate arithmetic step
(last known stock + flow × periods), not `run_forecast` alone.

## Hard rules

- **Never use `execute_python` for forecast arithmetic.** LLM-generated
  Python varies per turn → inconsistent numbers for the same question.
  `run_forecast` is the single deterministic source.
- **Follow-up consistency:** if a follow-up asks about the same series
  (different horizon, clarifying question), reuse the exact SQL from the
  prior turn — don't rebuild it from scratch. Only rebuild for an
  explicitly different series/grain/filter.
- **Same question → same SQL:** resolve the series from `forecast_guide.md`
  §3 exactly (same wording → same registry row, no improvised filters) and
  always keep the template's current-month cutoff — a slightly different
  history SQL produces a visibly different projection (the adaptive window
  can flip).
- **Consistency contract:** the same question (same series, grain, horizon)
  MUST produce the same numbers in any session and in follow-ups — the
  engine is deterministic, so any difference means you built a different
  SQL or `periods`. Resolve from the registry verbatim, pass `periods`
  explicitly, and for follow-ups reuse the prior turn's exact SQL. The only
  legitimate difference is data drift — stamp the as-of date.
