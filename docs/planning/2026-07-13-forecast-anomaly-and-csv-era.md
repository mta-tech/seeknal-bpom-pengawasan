# seeknal-bpom-neo: Forecast Anomaly + CSV Auto-Upload Era

**Document type:** Implementation note  
**Date:** 2026-07-13 (consolidated; covers commits 2–13 Jul 2026)  
**Status:** Applied to active runtime files  
**Scope:** `seeknal/skills/bpom-forecaster/SKILL.md` · `seeknal/skills/detect-anomaly/SKILL.md` (NEW) · `seeknal/skills/bpom-analyst/SKILL.md` · `context/forecast_guide.md` · `context/forecast_recipes.md` · `seeknal_agent.yml`  
**Reference commits:** `8f79a9e` (FC2c, 2 Jul), `287f5f5` (R4, 7 Jul), `e0ffafd` (FC2d, 9 Jul)  
**Baseline:** post `2026-06-25-forecasting-simplification-note.md`

---

## 1. Purpose

Three commits and one new skill landed between 2 and 13 July 2026. Together they:

1. migrated forecast compute out of the LLM into the deterministic IBA forecast engine (FC2c),
2. added period inference, stock-vs-flow guidance, and an `execute_python` ban on top of that (R4),
3. retired the per-query CSV auto-upload hook in favour of a deliberate once-per-turn agent decision (FC2d),
4. and introduced a `detect-anomaly` skill as a sibling trigger for "data tidak biasa" questions (FC2a).

This file records what those changes did and why, in one place — the same role `2026-06-25-forecasting-simplification-note.md` played for the June simplification.

---

## 2. Why This Was Needed

After the June simplification the forecaster was still a 484-line skill carrying SN+MA3 arithmetic, sigma formulas, backtest queries, and inverse-MAE weights inside the LLM. Three problems followed:

- **Non-deterministic output.** Same question, different turn → different numbers, because the LLM recomputed them.
- **CSV spam.** The `csv_upload_reminder` hook auto-uploaded every `execute_sql` result unconditionally (>=1 row), including throwaway diagnostic queries.
- **No anomaly path.** The agent had no answer to "apakah ada anomali / data tidak biasa / kenapa proyeksi ini kurang akurat".

---

## 3. What Stayed the Same

These principles from the June simplification are unchanged:

- forecasting is separate from ordinary analytical Q&A,
- forecasting is ERBA-only (ERLA's CV is always too high),
- forecasting is SQL-first and deterministic,
- eligibility + backtest quality label are still enforced,
- output still follows the user's language,
- the `LOAD -> CAPTURE -> RUN -> PRESENT` skill shape is retained,
- follow-up consistency (reuse the prior turn's SQL for the same series).

---

## 4. What Changed

### 4.1 FC2c — `bpom-forecaster` thin-trigger + AutoETS lock (`8f79a9e`, 2 Jul)

Replaced the 391-line SN+MA3 orchestrator skill (v1.0.0) with an ~86-line thin trigger (v3.0.0; currently 76 lines at v6.0.0). Domain CAPTURE parameters (tables, casts, exclusions, baseline) stay in the skill; all compute moves to the deterministic `run_forecast` tool backed by the IBA forecast engine (ETS seasonal, `seasonal_periods=12`).

Method change in `context/forecast_guide.md`:

- full history -> rolling 24-month adaptive window,
- >=36 months -> >=24 months eligibility,
- SN+MA3 -> ETS(A,N,N) with `sigma * sqrt(min(h,2))` bounds,
- LLM-driven backtest -> engine-run holdout.

Config: `agent.forecast.enabled: true` (`max_horizon: 12`) and `agent.upload_to_s3.enabled: true` were added to `seeknal_agent.yml`.

### 4.2 R4 — Period inference + stock vs flow + `execute_python` ban (`287f5f5`, 7 Jul)

Added +321 lines across `bpom-forecaster/SKILL.md`, `bpom-analyst/SKILL.md`, and `forecast_recipes.md`:

- 8-rule **period inference algorithm** (e.g. monthly grain + "3 tahun ke depan" -> `periods=36`), capped at 36,
- **stock vs flow** guidance (flow = `COUNT(DISTINCT produk_id)`; stock = cumulative window, with explicit caveat that `run_forecast` does not reliably project stock growth rate),
- **ban on `execute_python` for forecast arithmetic** — `run_forecast` is the single deterministic source,
- follow-up consistency rule: same series -> reuse prior SQL exactly.

### 4.3 FC2d — CSV auto-upload sync (`e0ffafd`, 9 Jul)

A small but principled change. The `csv_upload_reminder` hook (which auto-uploaded every `execute_sql` result unconditionally, >=1 row) is **retired**. CSV export is now a deliberate once-per-turn agent decision, owned by the answering workflow itself (`bpom-analyst/SKILL.md`), using `upload_to_s3` explicitly for the SQL behind the final answer. `run_forecast` self-uploads its own projection points; the agent must not call `upload_to_s3` for those again.

Also fixed a stale `season_length` value (1 -> 12) in `forecast_guide.md` to match the engine's actual `model.py` / `evaluate.py`.

### 4.4 FC2a — `detect-anomaly` skill (new, ~13 Jul, uncommitted)

Sixth skill, sibling to `bpom-forecaster`. Same series registry, same 2-column SQL contract, but explains unusual periods instead of projecting future ones. Routes `detect_anomaly(sql)`; never removes data, never forecasts. Auto-fires when a forecast's backtest MAPE > 25%; otherwise on direct request. The agent calls `upload_to_s3` once explicitly if anomalies were found, and skips it on a "no anomalies" narrative-only answer.

---

## 5. Size / Impact

Forecast-specific files were reduced further; non-forecast context grew because the orchestrator absorbed workflow content:

| File | Before (f8d34b0) | After (snapshot 13 Jul) |
|---|---:|---:|
| `bpom-forecaster/SKILL.md` | 2,388 B | 3,733 B |
| `forecast_guide.md` | 3,097 B | 4,649 B |
| `forecast_recipes.md` | 6,656 B | 797 B (header only, "Superseded") |
| `bpom-analyst/SKILL.md` | 4,086 B | 33,445 B (FC2d CSV workflow absorbed) |
| `detect-anomaly/SKILL.md` | — | 2,819 B (new) |
| **Total snapshot** | ~16,200 tok | ~40,600 tok |

The forecast path itself is materially lighter; the snapshot's overall growth is driven by the `bpom-analyst` orchestrator and non-forecast context files, not by forecast skill weight.

---

## 6. Design Direction After This Era

- **Forecast compute = engine, not LLM.** Same input -> same output, always.
- **Each capability = one thin-trigger skill** with the same CAPTURE -> RUN -> PRESENT shape (`bpom-forecaster`, `detect-anomaly`).
- **CSV export = agent decision**, once per turn, for the SQL behind the final answer — not a per-query hook.
- **Anomaly and forecast share the same 2-column SQL contract** so the engine can run either side from the same input.

---

## 7. Governance Rule

If future changes alter forecast compute, anomaly detection, or CSV export policy:

- do not re-introduce LLM arithmetic for forecast or anomaly scoring,
- do not re-enable per-query auto-upload hooks,
- keep each thin-trigger skill narrow — resist monolith drift,
- update this document together with the active runtime files.
