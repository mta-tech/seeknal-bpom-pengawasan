---
name: bpom-forecaster
description: "BPOM-specific trigger for the generic forecasting skill. Routes ERBA forecast requests to run_forecast with BPOM CAPTURE parameters. All compute is deterministic (IBA forecast engine, ETS seasonal)."
tags: [bpom, forecast]
version: "6.0.0"
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
- **Horizon translation:** `periods` is a step count on the SQL's own grain
  (e.g. monthly grain + "3 tahun ke depan" → `periods=36`). Cap at 36; if the
  request needs more, say so and offer the largest supported horizon.
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

**Anomaly:** if the tool's markdown has an `## Anomali` block, include it
and state the points were **not removed**. If the user asks about
anomalies directly, call `detect_anomaly(sql)` yourself (works whether or
not a forecast ran this turn) — see `forecast_guide.md` §6.

**CSV:** `run_forecast` self-uploads its projection points on success —
do NOT call `upload_to_s3` yourself for those points (would duplicate the
CSV). Only call `upload_to_s3` explicitly for a *different* dataset (e.g.
the underlying historical series). Never paste the raw download URL/link
in your answer — the Download button renders automatically.

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
