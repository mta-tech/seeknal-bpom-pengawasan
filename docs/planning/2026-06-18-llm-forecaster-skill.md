# seeknal-bpom-neo: LLM-Orchestrated Forecasting Skill (bpom-forecaster)

**Document type:** Implementation Plan — New Skill
**Project:** seeknal-bpom-neo (BPOM RPO Analytics Agent)
**Status:** Designed and validated — pending implementation (updated 2026-06-18 post-simulation)
**Date:** 2026-06-18
**Scope:** `seeknal/skills/bpom-forecaster/SKILL.md` (NEW) · `context/forecast_recipes.md` (NEW) · `context/forecast_guide.md` (REWRITE) · `context/intent_mapping.md` (ADD FORECAST) · `SEEKNAL_ASK.md` (ADD ROUTING)
**Integrates with:** `seeknal/skills/bpom-analyst/SKILL.md` · `context/query_recipes.md` · `context/intent_mapping.md` · `context/data_quality_rules.md`
**Evidence base:** `bpom-forecast-v2/FINAL_REPORT.md` (2026-06-03) · `bpom-forecast-v2/specs/2026-06-03-audit-forecasting-engine.md` · `bpom-forecast-v2/specs/2026-06-04-Forecasting Evaluation Redesign Plan.md` · live `rpo_v2` statistical conditions (ADF p=0.0003, ACF lag-12=0.025, 2026-06-17)
**Prior forecasting system:** `warehouse.public.forecast_permohonan` — **will be dropped** (defects documented below); this plan supersedes any guidance that references that table

---

## 1. Background

### 1.1 Why Forecasting

BPOM stakeholders routinely ask questions that go beyond what the current agent can answer:

> "Kira-kira bulan depan permohonannya berapa?"
> "Q3 2026 trennya kemana?"
> "Target NIE semester dua realistis tidak?"

These are not retrospective data queries — they require a projection forward in time. The current
`bpom-analyst` skill has no mechanism to answer them. The agent either deflects or, worse,
produces an ad-hoc verbal estimate with no statistical basis.

### 1.2 What Exists (and Why It Was Dropped)

`warehouse.public.forecast_permohonan` was the previous forecasting table — a pre-computed batch
of predictions generated on 2026-05-18. The audit identified five structural defects:

| Defect | Evidence |
|---|---|
| Intervals not calibrated | Empirical coverage ~57%, nominal claim is 80–95% |
| Intervals do not widen with horizon | Constant-width bands from H=1 to H=60 — violates any valid probabilistic model |
| Predictions flat / mean-reverting | No trend or seasonal adaptation — all 2026 forecasts collapsed to the same value |
| Zero validation overlap | Predictions start May 2026; available actuals end April 2026 — no testable period |
| Retrospective batch | All 111 rows have `predicted_at = 2026-05-18` — not a live forecasting system |

This table will be dropped. The `forecast_guide.md` context file that documents it is equally
obsolete and will be completely rewritten.

### 1.3 Design Constraints from Business Context

From the meeting and UX notes:

1. **Results are never stored** — forecasting is ad-hoc, on-demand; no separate forecast database
2. **ERBA 2022+ only** — ERLA data and pre-2022 data are from a different regime (documented below)
3. **LLM as orchestrator, not calculator** — all arithmetic is done by SQL; LLM reads results and presents them
4. **Transparency first** — show historical data before forecast; explain which method and why; state uncertainty
5. **Consistency mandatory** — the same question on the same data must yield the same answer in any conversation
6. **SQL-first, no Python** — all forecasting computation happens in SQL. Python is not used. The same formulas that work in SQL (SN, MA3, ensemble, percentile intervals) produce adequate accuracy for operational planning without additional complexity
7. **Data may not always be forecastable** — the backtest gate and eligibility pre-check exist precisely to handle this. If data does not pass the gate, the system presents historical data and states the reason. Presenting honest limits is preferred over forcing a forecast on unsuitable data

### 1.4 Validation Summary (2026-06-18 Live Simulation)

Before implementation, a live SQL simulation was run against `rpo_v2` using the complete ERBA
history from September 2022 to May 2026. Results validated the design:

| Series | Backtest MAPE (24M) | Gate Label | Retroactive MAPE (Jan–Mei 2026) |
|---|---|---|---|
| Permohonan ERBA | 19.1% | CUKUP | 10.3% |
| NIE Terbit ERBA | 14.4% | BAIK | 9.1% |
| BTP Permohonan | 24.4% | CUKUP | — |
| MR (303) | 12.8% | BAIK | 11.4% |
| MT (302) | 25.0% | CUKUP | ~35.7% (small volume distortion) |
| Tinggi (301) | 28.3% | LEMAH | 10.0% (gate conservative) |
| TinggiNotif (304) | 40.5% | TOLAK | — (insufficient history, 27 months) |
| NIE Dicabut | 660% | TOLAK | — (event-driven, unforceable by design) |

Key finding from simulation: the improvement in forecast quality came almost entirely from
(1) extending residual window from 12 to 24 months (p10 changed from +208 to −744, bilateral),
and (2) using full ERBA history from 2022 as the training base. No model change was necessary.
Quarterly MAPE was 1.3% vs monthly MAPE of 10.3% — quarterly aggregation is the primary output.

---

## 2. Statistical Foundation — Why ERBA 2022+ Only

This is the most important constraint in the entire design. Mixing ERBA and ERLA data — or
including pre-2022 data — produces statistically invalid forecasts regardless of the model used.

### 2.1 System Regime Break

| Period | System | Characteristic |
|---|---|---|
| Pre-2022 | ERLA | Declining volume, different process, different classification codes |
| 2022-09 onward | ERBA | Growing volume, new system, stationary distribution |
| 2022-09 specifically | Transition | Both systems active — ERLA declining as ERBA ramps |

ERBA volume per year: 2022=4,167 · 2023=42,329 · 2024=46,444 · 2025=69,964. ERLA is declining
across the same period. They are not the same time series — they are two parallel processes with
different dynamics. Stacking them produces a non-stationary composite that defeats every model.

### 2.2 Stationarity Evidence

Augmented Dickey-Fuller test on ERBA 2022+ series (44 months):

| Metric | Value | Interpretation |
|---|---|---|
| ADF p-value | **0.0003** | Strongly stationary (reject unit root) |
| ACF lag-12 | **0.025** | No seasonal signal (threshold ≈ 0.1 for relevance) |
| CV (coefficient of variation) | ~0.25 | Moderate variability — forecastable |

ADF on ERLA series: p=0.94 — strongly non-stationary (unit root not rejected). ERLA cannot be
reliably forecasted with any standard method.

**Consequence:** 44 months of homogeneous, stationary ERBA data are more valuable than 10 years
of mixed data. A model trained on a stable regime generalizes correctly within that regime. A
model trained on a mixed regime generalizes to nothing.

### 2.3 No Seasonal Signal

ACF lag-12 = 0.025 means month-of-year has no predictive power over the next observation.
Seasonal models (MSTL, Theta, Holt-Winters) are therefore inappropriate — they would find
structure that does not exist. This is confirmed by the bpom-forecast-v2 spike where MSTL and
Theta underperformed even Seasonal Naive on 2026 actuals.

Seasonal Naive's competitive performance in 2026 is NOT because of seasonality. It is because
the ERBA volume level in 2025 happened to be close to the 2026 level — same-month-last-year
effectively captures the prevailing level. This is confirmed by near-zero bias (-45/month).

---

## 3. Model Selection — Evidence-Based, Not Intuition

The bpom-forecast-v2 spike ran 7 models across 9 evaluation windows. The relevant results for
production selection (PM2026 = 5 months of actual 2026 data, the most recent ground truth):

| Model | MASE_ext PM2026 | Bias/month | SQL-implementable? |
|---|---|---|---|
| Chronos (zero-shot T5) | 0.587 | +160 | ❌ Python + 634 MB model |
| **Seasonal Naive** | **0.730** | **−45** | ✅ |
| Moving Average 12M | 0.787 | −537 | ✅ |
| AutoETS | 0.815 | −579 | ❌ Python AIC search |
| Theta | 0.924 | −721 | ❌ Python decomposition |
| MSTL | 1.035 | −801 | ❌ Python STL |
| TimesFM | 2.109 | −1,876 | ❌ Python + 1.8 GB model |

Key finding: **among SQL-implementable models, Seasonal Naive has the lowest MASE and nearly
zero bias in 2026 actuals**. This is a data-driven conclusion, not an assumption about seasonality.

Moving Average at 3 months (MA3, shorter than the 12M tested) is included in the ensemble as a
complement — it is more reactive to recent level changes. The spike tested MA12; MA3's actual
performance will be determined by the mandatory backtest gate (§5.3).

No single model dominates across all evaluation windows — the 2024 and 2025 windows show
completely different rankings. This is why an ensemble is mandatory.

---

## 4. Files to be Built and Modified

### 4.1 `seeknal/skills/bpom-forecaster/SKILL.md` — New

A standalone forecasting skill separate from `bpom-analyst`. It is invoked when the intent
is forward-looking (predict / forecast / estimasi / projection / tren ke depan / berapa nanti).

The skill orchestrates a 6-phase pipeline. All numeric computation is delegated to SQL — the
LLM never performs arithmetic. See §6 for the full phase specification.

### 4.2 `context/forecast_recipes.md` — New

SQL template library for the forecasting pipeline. Same pattern as `query_recipes.md` but
dedicated to forecasting operations. Each recipe is parameterized with explicit placeholders
`{T_first}`, `{H}`, `{window_start}`, etc. so every invocation is unambiguous.

| Recipe | Purpose |
|---|---|
| `RECIPE-F1` | Monthly time series pull — ERBA 2022+, full history |
| `RECIPE-F2` | Data condition diagnostics — gap check, structural break, CV |
| `RECIPE-F3` | Backtest gate — 12-month rolling evaluation, returns weights + residual stats |
| `RECIPE-F4` | Point forecast for single target month T (SN + MA3, weighted) |
| `RECIPE-F5` | Multi-month forecast — repeat F4 for H=1 to N |
| `RECIPE-F6` | Combined output — point + 80% and 95% intervals, all horizons in one query |

### 4.3 `context/forecast_guide.md` — Complete Rewrite

Current content documents the dropped `forecast_permohonan` table and must be replaced.
New content: no-store protocol, ERBA 2022+ scope definition, window rules, formula reference,
horizon tier table, √H disclaimer.

---

## 5. Forecasting Approach — Detail

### 5.1 Training Window — Full ERBA History from 2022

The training window is the **full ERBA history from September 2022** to the month before the
target. For any target month T:

```
window_start = '2022-09-01'   -- ERBA regime begins
window_end   = T              -- exclusive
```

Example: predicting July 2026 uses all ERBA data from September 2022 to June 2026 (44 months).

This supersedes the earlier rolling 36-month design. Live simulation confirmed that full history
produces richer learning:

| Period | Value captured |
|---|---|
| 2022–2023 | ERBA growth phase — establishes baseline trajectory |
| 2024 | Volume stabilization — adds stationary behavior evidence |
| 2025 | High-variability period — trains residual distribution on real extremes |
| 2026 | Becomes validation period in backtest |

A 36-month rolling window would systematically exclude the 2022–2023 growth phase from later
targets, losing exactly the evidence that calibrated the baseline. Full history avoids this loss
while the stationarity of the ERBA regime (ADF p=0.0003) ensures the 2022 data is still
statistically compatible with 2026 observations.

**Structural break override:** if the 6-month trailing mean versus the 6-month prior mean differs
by more than 30% (ratio > 1.30 or < 0.70), the effective training window is compressed to the
most recent 12 months to exclude the pre-break period. Structural break is detected in PHASE 2
before any forecast computation.

**SN anchor:** Seasonal Naive (SN) uses same-month-last-year, so it always references a single
data point 12 months ago — training window length does not affect SN directly. MA3 uses the
3 most recent actual months before the target. The training window affects the backtest residual
distribution, not the individual component forecasts.

### 5.2 Point Forecast Methods

Two methods, implemented purely in SQL:

**Seasonal Naive (SN):**
```
SN(T) = COUNT(DISTINCT produk_id) WHERE bulan = T - 12 months
```
Interpreted as: "what was the actual count in the same month last year." This is the level
anchor. It has near-zero bias in 2026 actuals (−45/month).

**Moving Average 3 months (MA3):**
```
MA3(T) = AVG(COUNT DISTINCT) for months T-3, T-2, T-1
```
A short-window average that captures the recent level without chasing individual spikes.
More reactive than SN to level changes; less reactive than the most recent single month.

**Ensemble:**
```
ensemble(T) = ROUND(w_sn × SN(T) + w_ma3 × MA3(T))
```
Weights `w_sn` and `w_ma3` are determined by the backtest gate (§5.3), not hardcoded.
If the two models' MAE difference is < 10%, fall back to 50-50 and state this.

### 5.3 Eligibility Pre-Check — Before Backtest

Before running any backtest, the series must pass an eligibility pre-check. This prevents
running a backtest on data that is structurally unsuitable for time-series forecasting.

```
Eligibility criteria (ALL must pass):
  1. History ≥ 36 months from 2022 baseline
  2. Average monthly volume ≥ 300
  3. Series reflects a recurring administrative process (not discrete events)
```

**Eligibility by series (as of 2026-06):**

| Series | Status | Reason |
|---|---|---|
| Permohonan ERBA (total) | **Eligible** | 45 months, avg ~4,500 |
| NIE Terbit ERBA (total) | **Eligible** | 45 months, avg ~5,000 |
| BTP Permohonan | **Eligible** | 45 months, avg ~127 — borderline; caveat |
| MR (303) | **Eligible** | 45 months, avg ~1,329 |
| MT (302) | **Eligible, flag** | 45 months, avg ~387 — small volume, downgrade label |
| Tinggi (301) | **Eligible** | 45 months, avg ~3,147 |
| TinggiNotif (304) | **Ineligible** | 27 months only — eligible ~Mar 2027 |
| NIE Dicabut | **Never eligible** | Event-driven revocations — not a time series |
| Complaints, SLA violations | **Never eligible** | Discrete incident counts — not forecastable |

**Volume-adjusted label:** if avg monthly volume < 300, downgrade the quality gate result by
one tier (BAIK → CUKUP, CUKUP → LEMAH). This corrects for MAPE distortion on small-volume
series: a 68-unit error on MT (avg=387) gives MAPE=17.5%, but the same error on Permohonan
(avg=4,500) gives MAPE=1.5%. The label should reflect operational uncertainty, not mathematical
ratio amplification.

**Specific refusal messages:**
```
TinggiNotif (304): "Data TinggiNotif baru tersedia sejak Maret 2024 — perlu minimal 36 bulan
  riwayat (tersedia sekitar Maret 2027)."
DICABUT/revocations: "Pencabutan NIE adalah keputusan diskretioner, bukan pola time series —
  tidak dapat diproyeksikan. Saya bisa menampilkan tren historis pencabutan sebagai gantinya."
```

---

### 5.4 Backtest Gate — Quality Assessment (Mandatory Before Any Forecast)

Before computing any forward forecast, the system runs a **24-month rolling evaluation**.
The 24-month window (not 12) was validated by simulation: with 12 months, the p10 residual
was +208 (all-positive, biased intervals); with 24 months, p10 = −744 (bilateral, realistic).

**Validated backtest results (simulation 2026-06-18):**

| Series | MAPE 24M | w_SN | w_MA3 | σ | p10 | p90 | Floor (p5) |
|---|---|---|---|---|---|---|---|
| Permohonan ERBA | 19.1% | 34% | 66% | 1,093 | −1,056 | +1,904 | 1,617 |
| NIE Terbit ERBA | 14.4% | 48% | 52% | 867 | −666 | +1,302 | 661 |
| BTP Permohonan | 24.4% | 41% | 59% | 45 | −55 | +70 | 56 |
| MR (303) | 12.8% | 46% | 54% | 201 | −156 | +304 | (pending) |
| MT (302) | 25.0%* | 36% | 64% | 102 | −142 | +120 | (pending) |
| Tinggi (301) | 28.3% | 34% | 66% | 896 | −917 | +1,309 | (pending) |

*MT MAPE adjusted to LEMAH tier after volume-adjustment (avg < 300 threshold not met at 387).

The backtest SQL template is in `forecast_recipes.md` as RECIPE-F3. The query runs the full
24-month rolling evaluation and returns all 7 parameters in one result row.

**Gate decision (updated thresholds — validated by simulation):**

| MAPE (after volume adjustment) | Action | Label |
|---|---|---|
| ≤ 15% | PROCEED with confidence | **BAIK** |
| 15–25% | PROCEED with caution | **CUKUP** |
| 25–35% | PROCEED with strong caveat | **LEMAH** |
| > 35% | HALT — present historical only | **TOLAK** |

The gate was tightened from the earlier 40% threshold based on simulation evidence: at MAPE
25–35% (LEMAH), the retroactive validation showed acceptable results for planning orientation
(Tinggi 301: backtest MAPE 28.3% but retroactive 10%), while series above 35% showed no
actionable predictive signal.

**Legacy note:** The SQL template at §5.3 (original document) used 12-month backtest.
That template must be replaced with the 24-month version in `forecast_recipes.md`.

---

### 5.5 Backtest Gate SQL — (to be moved to RECIPE-F3)

Before computing any forward forecast, the system runs a 24-month rolling evaluation:

```sql
WITH monthly AS (
  SELECT
    date_trunc('month', tanggal_bayar::timestamp)::date AS bulan,
    COUNT(DISTINCT produk_id)                           AS jumlah
  FROM warehouse.public.t_produk_3_erba
  WHERE tanggal_bayar >= '2022-01-01'
    AND tanggal_bayar <  date_trunc('month', CURRENT_DATE)
    AND tanggal_bayar IS NOT NULL AND tanggal_bayar != ''
    AND trader_id NOT IN (5,17,50,85)
  GROUP BY 1
),
backtest AS (
  SELECT
    m.bulan                                             AS target,
    ly.jumlah                                           AS sn_forecast,
    AVG(prev3.jumlah) OVER (
      ORDER BY m.bulan
      ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
    )                                                   AS ma3_forecast,
    m.jumlah                                            AS actual
  FROM monthly m
  JOIN monthly ly ON ly.bulan = m.bulan - interval '12 months'
  WHERE m.bulan >= date_trunc('month', CURRENT_DATE) - interval '12 months'
    AND m.bulan <  date_trunc('month', CURRENT_DATE)
),
stats AS (
  SELECT
    AVG(ABS(actual - sn_forecast))   AS mae_sn,
    AVG(ABS(actual - ma3_forecast))  AS mae_ma3,
    AVG(ABS(actual - ROUND((sn_forecast + ma3_forecast)/2.0)))         AS mae_ensemble,
    AVG(ABS(actual - ROUND((sn_forecast + ma3_forecast)/2.0))
        / NULLIF(actual, 0)) * 100                                      AS mape_ensemble,
    STDDEV(actual - ROUND((sn_forecast + ma3_forecast)/2.0))           AS sigma_ensemble,
    PERCENTILE_CONT(0.10) WITHIN GROUP (
      ORDER BY actual - ROUND((sn_forecast + ma3_forecast)/2.0))        AS p10_ensemble,
    PERCENTILE_CONT(0.90) WITHIN GROUP (
      ORDER BY actual - ROUND((sn_forecast + ma3_forecast)/2.0))        AS p90_ensemble,
    COUNT(*)                                                             AS n_obs
  FROM backtest
)
SELECT
  mae_ensemble,
  mape_ensemble,
  (1.0/mae_sn) / (1.0/mae_sn + 1.0/mae_ma3)   AS weight_sn,
  (1.0/mae_ma3) / (1.0/mae_sn + 1.0/mae_ma3)  AS weight_ma3,
  sigma_ensemble,
  p10_ensemble,
  p90_ensemble,
  n_obs
FROM stats
```

**Gate decision:** See §5.4 (updated gate table). The parameters returned — `weight_sn`,
`weight_ma3`, `sigma_ensemble`, `p10_ensemble`, `p90_ensemble` — are used unchanged for all
subsequent computations. The LLM does not recalculate or reinterpret them.

### 5.6 Prediction Intervals with Business Floor

Intervals are computed from the **ensemble residual distribution** — the historical differences
between actuals and ensemble forecasts. Using SN residuals alone would create a mismatch between
the point forecast (ensemble) and the uncertainty (SN-only); this is a structural inconsistency
corrected here.

```
residual(t) = actual(t) − ROUND(w_sn × SN(t) + w_ma3 × MA3(t))
σ           = STDDEV(residuals) from 24-month backtest window
p10, p90    = 10th and 90th empirical percentiles of residuals (bilateral after 24M window)
```

Interval formulas per horizon H (1-indexed from first target month):

```
σ_H = σ × SQRT(H)                                      [pragmatic approximation — see §5.7]

raw_lower_80 = point(T) + ROUND(p10 × SQRT(H))         [empirical — can be negative]
raw_upper_80 = point(T) + ROUND(p90 × SQRT(H))         [empirical]

Lower 80% = GREATEST(raw_lower_80, p5_of_training_volume)   [business floor applied]
Upper 80% = raw_upper_80
```

**Business floor:** `GREATEST(raw_lower_80, p5_of_training_volume)` prevents lower bounds
from falling below operationally plausible minimums. The p5 of training volume captures the
lowest realistic operating level from actual history (not a hypothetical minimum).

Validated floor values from simulation:
- Permohonan ERBA: p5 = 1,617
- NIE Terbit ERBA: p5 = 661
- BTP Permohonan: p5 = 56

Why needed: with √H scaling, the lower bound for H=3 can extend to forecast−1,800, producing
values like 3,785 for Permohonan. While the formula is mathematically correct, an interval that
suggests "as low as 3,700" when the series has never gone below 4,000 in 44 months of history
overstates downside risk and misleads planning. The floor anchors the lower bound in history.

The 80% empirical interval with business floor is the **only** interval shown to the user.
The 95% parametric interval is computed internally for audit purposes but never shown by default.

### 5.7 Multi-Domain Pipeline — How Multiple Forecastable Series Are Handled

When a user asks about a domain that maps to multiple forecastable series, or when the system
needs to pull from multiple tables/filters, the pipeline follows a structured approach.

**Step 1 — Entity Resolution**

The ENTITY extracted in PHASE 1 maps to exactly one source configuration:

| Entity | Source Table | Date Column | Filter |
|---|---|---|---|
| Permohonan ERBA (total) | `public.t_produk_3_erba` | `tanggal_bayar::timestamp` | trader_id::bigint NOT IN (5,17,50,85) |
| NIE Terbit ERBA (total) | `public.t_produk_3_erba` | `tanggal::timestamp` | same + status via dict |
| BTP Permohonan | `public.t_btp_3_erba` | `tanggal_bayar` (native timestamp) | trader_id NOT IN (5,17,50,85) |
| Permohonan by risk | `public.t_produk_3_erba` | `tanggal_bayar::timestamp` | + kategori_dokumen IN ('{code}') |
| NIE by risk | `public.t_produk_3_erba` | `tanggal::timestamp` | + kategori_dokumen IN ('{code}') |

Note: `t_produk_3_erba` has TEXT columns for `tanggal_bayar` and `trader_id` — casts are
mandatory. `t_btp_3_erba` has native types — no casts needed.

**Step 2 — Series Independence**

Each forecastable series runs its own independent pipeline:
- Own eligibility check
- Own backtest gate with own MAPE, weights, σ, p10, p90, floor
- Own forecast values

Series are never averaged together or combined into a single forecast unless the user explicitly
asks for a total that spans multiple sub-series (e.g., "total semua risiko"). In that case,
forecast the total series directly, not by summing sub-series forecasts (which accumulates errors).

**Step 3 — Multi-Series Output**

When multiple eligible series are forecasted in one response (e.g., user asks for "semua risiko"),
present each with its own 5-layer block, then add a cross-series comparison table:

```
Perbandingan Proyeksi Q3 2026

Series        Forecast Q3   Kualitas   Catatan
MR (303)       ~4,267        BAIK       Paling andal
Tinggi (301)   ~9,951        LEMAH      Lihat catatan batas bawah
MT (302)       ~869          CUKUP      Volume kecil, interpretasi hati-hati
```

**Step 4 — Ineligible Series in Multi-Series Context**

If user asks for a series that fails eligibility, do not silently skip it. State explicitly:
> "TinggiNotif (304) tidak dapat diproyeksikan karena riwayat data baru 27 bulan.
>  Menampilkan data historis TinggiNotif sebagai referensi."
Then show historical table for that series alongside the forecasts for the eligible ones.

### 5.8 Quarterly-First Output Rule

Simulation evidence: monthly MAPE ≈ 10%, quarterly MAPE ≈ 1.3%. The primary output for any
forecast covering 2+ months is the **quarterly aggregate**. Monthly detail is secondary.

**Why:** BPOM decision-making operates at quarter/semester planning cycles, not monthly.
A monthly forecast of "Jul=5,710 / Aug=5,618 / Sep=5,614" is operationally indistinguishable.
A quarterly forecast of "Q3 ≈ 16,942 (range 14,000–19,600)" is directly actionable.

Output rule: for any H≥2 response, lead with quarterly or semester aggregate, then show monthly
detail as a breakdown. For H=1 only, monthly detail is the primary output.

**March Flag:** All series show systematically elevated MAPE in March (22–28%) — likely a Q1-end
administrative effect. Whenever a target month includes March, append to LAYER 2 Kondisi Data:
> "⚠ Bulan Maret secara historis menunjukkan variasi lebih tinggi dari bulan lain.
>   Proyeksi Maret sebaiknya diperlakukan sebagai kisaran lebar."

### 5.9 √H Scaling — Explicitly a Pragmatic Approximation

`σ_H = σ × √H` derives from the assumption that forecast errors accumulate as a random walk.
For real business data — which has capacity constraints, policy cycles, and administration
rhythms — this assumption is imperfect. The actual error growth may be faster or slower than √H.

**Horizon tiers encode this honestly:**

| Horizon | Tier | Interpretation |
|---|---|---|
| H = 1 | **Primary estimate** | Most reliable; √H approximation error negligible |
| H = 2–3 | **Acceptable** | Approximation error small; use for planning |
| H = 4–6 | **Directional** | Interval noticeably wider; treat as plausible range |
| H = 7–12 | **Context only** | Substantial uncertainty; √H likely underestimates true error |
| H > 12 | **Do not forecast** | Beyond reasonable extrapolation for this series |

Every interval output must be labeled with its tier. The phrase "context only" in the output
signals to the user that the number is a rough orientation, not a projection to act on.

### 5.6 Data Condition Checks

Executed before the backtest gate (PHASE 2), these establish whether forecasting is even
appropriate for the current data state:

**Gap check:**
```sql
-- Detect any month with zero or null volume in the last 36 months
SELECT bulan FROM monthly
WHERE jumlah = 0 OR jumlah IS NULL
  AND bulan >= date_trunc('month', CURRENT_DATE) - interval '36 months'
ORDER BY 1
```
If gaps found → report them; they inflate σ and distort residuals.

**Structural break check:**
```sql
-- Compare last 6 months average vs prior 6 months average
SELECT
  AVG(CASE WHEN bulan >= date_trunc('month', CURRENT_DATE) - interval '6 months'
           THEN jumlah END)  AS avg_recent,
  AVG(CASE WHEN bulan <  date_trunc('month', CURRENT_DATE) - interval '6 months'
            AND bulan >= date_trunc('month', CURRENT_DATE) - interval '12 months'
           THEN jumlah END)  AS avg_prior
FROM monthly
-- ratio = avg_recent / avg_prior
-- if > 1.30 or < 0.70 → structural break → use 12-month window
```

**Volatility check:**
```sql
SELECT STDDEV(jumlah) / AVG(jumlah) AS cv FROM monthly
WHERE bulan >= date_trunc('month', CURRENT_DATE) - interval '12 months'
-- if cv > 0.50 → high volatility → add caveat to output
```

---

## 6. Skill Phase Structure

```
PHASE 0: Load Context (mandatory)
  → Load forecast_guide.md (window rules, formulas, horizon tiers)
  → Load forecast_recipes.md (SQL templates)
  → Do not proceed without both files

PHASE 1: Capture
  → Extract: ENTITY (permohonan / NIE / BTP), TIME_SCOPE (how many months ahead?),
             SYSTEM (default: ERBA only), DIMENSION (segment / risk category / none)
  → If time scope ambiguous: default to 3 months
  → If ERLA mentioned: acknowledge ERLA cannot be forecasted (non-stationary);
    offer to forecast ERBA and describe ERLA historical trend
  → Confirm understanding before executing any SQL

PHASE 2: Data Condition Check
  → Run RECIPE-F2: gap check + structural break + volatility
  → Report findings to user as a brief health summary
  → Apply window override if structural break detected (full history → 12M)
  → If severe data issues (e.g., consecutive multi-month gaps): halt; describe findings

PHASE 2.5: Eligibility Pre-Check (NEW — runs before backtest)
  → Check: history ≥ 36 months from 2022 baseline
  → Check: avg monthly volume ≥ 300 (if < 300: proceed but flag for label downgrade)
  → Check: series is process-driven (not event-driven like revocations)
  → If ineligible: HALT with specific reason message (see §5.3)
  → If borderline volume (100–300): PROCEED but set volume_flag=true for label downgrade

PHASE 3: Backtest Gate (24-month window)
  → Run RECIPE-F3: 24-month rolling evaluation (not 12 months)
  → Read returned columns exactly: mape_ensemble, weight_sn, weight_ma3,
    sigma_ensemble, p10_ensemble, p90_ensemble, n_obs
  → Apply volume adjustment: if volume_flag=true from PHASE 2.5, downgrade label one tier
  → Apply gate:
      MAPE ≤ 15%  → BAIK, PROCEED
      MAPE 15–25% → CUKUP, PROCEED
      MAPE 25–35% → LEMAH, PROCEED with strong caveat
      MAPE > 35%  → TOLAK, HALT — present historical only
  → LOCK the parameters: these values are used unchanged in PHASE 4 and 5
  → Report backtest quality: "Kualitas BAIK/CUKUP/LEMAH (MAPE {mape}%); metode {w_sn}% SN + {w_ma3}% MA3"

PHASE 4: Compute Point Forecast
  → For each target month T (H=1 to N), run RECIPE-F4:
    - Query SN(T): count for same month last year
    - Query MA3(T): average of T-3, T-2, T-1
    - ensemble(T) = ROUND(weight_sn × SN(T) + weight_ma3 × MA3(T))
  → Read column values from SQL result — do not calculate in LLM
  → Check each result for plausibility (within ±3σ of training mean); flag outliers

PHASE 5: Compute Intervals (all in SQL via RECIPE-F6)
  → For each H (1-indexed from first target month):
    sigma_H      = sigma_ensemble × SQRT(H)    -- stated as approximation
    raw_lower_80 = ensemble(T) + ROUND(p10_ensemble × SQRT(H))
    upper_80     = ensemble(T) + ROUND(p90_ensemble × SQRT(H))
    lower_80     = GREATEST(raw_lower_80, p5_training_volume)  -- business floor
  → Assign horizon tier (H=1 Tinggi, H=2-3 Sedang, H=4-6 Rendah, H>6 Sangat Rendah)
  → Run RECIPE-F6 to compute all values in SQL — LLM reads columns, never computes

PHASE 6: Present (5-layer output — see §9 for full specification)
  → LAYER 1 Executive Summary: quality label + Q aggregate range + one-line data status
  → LAYER 2 Data Condition: ✓/⚠ checklist (gap, structural break, volatility, March flag)
  → LAYER 3 Historical Data: 12-month actuals table + mean/max/min summary stats
  → LAYER 4 Forecast: QUARTERLY AGGREGATE FIRST, then monthly breakdown
      Primary: "Q{N} diperkirakan sekitar {sum_low}–{sum_high} total"
      Secondary: Bulan | Forecast | Rentang Realistis | Tingkat Keyakinan
      If March in targets → append ⚠ March variability footnote
  → LAYER 5 Narrative: 2–4 sentences interpreting operational meaning
  → ALWAYS append: compact Metodologi block (source, window, backtest MAPE, method weights)
  → NEVER show to user: sigma, p10, p90, ADF, ACF, Lower 95%, Upper 95%
  → Respond in user's language (match the question's language)
  → Quality label mapping (updated — validated by simulation):
      MAPE ≤ 15%  → "BAIK"   — reliable for operational planning
      MAPE 15–25% → "CUKUP"  — directional, use with caution
      MAPE 25–35% → "LEMAH"  — rough indication, caveat strongly
      MAPE > 35%  → HALT — no forecast; present historical + explain why
```

---

## 7. Integration with Existing Architecture

### 7.1 Relationship to bpom-analyst

`bpom-analyst` handles retrospective questions: what happened, how many, comparison, trend of
the past. `bpom-forecaster` handles forward-looking questions: what will happen, projection,
target feasibility.

The two skills share:
- Database connection and credentials (localhost:5533/rpo_v2, readonly_user)
- Data filters from `data_quality_rules.md`: `trader_id NOT IN (5,17,50,85)`, ERBA TEXT casts
- Intent decomposition vocabulary from `intent_mapping.md`
- Output language detection rule

The skills do NOT share SQL templates — `forecast_recipes.md` is separate from `query_recipes.md`
to keep the deterministic pipeline isolated. A recipe from `query_recipes.md` should never be
used in a forecast computation path.

### 7.2 Invocation Trigger

The forecast skill is triggered when the intent is forward-looking. Trigger signals:

| Phrase type | Examples |
|---|---|
| Explicit forecast | "prediksi", "proyeksi", "forecast", "estimasi ke depan" |
| Time future | "bulan depan", "Q3", "semester dua", "tahun depan", "6 bulan ke depan" |
| Target feasibility | "bisa mencapai", "realistis tidak", "target terpenuhi" |
| Trend forward | "tren ke depan", "arahnya kemana" |

If the intent mixes past and future (e.g., "tren 2024–2026"), the retrospective portion is
answered from `bpom-analyst` logic (actual data) and the future portion from `bpom-forecaster`
logic (forecast). They are presented together as a continuous timeline.

### 7.3 Context Loading Protocol

Same pattern as `bpom-analyst` loading `code_translation_protocol.md` in PHASE 0:

```
PHASE 0 of bpom-forecaster:
  → ALWAYS read forecast_guide.md before any SQL
  → ALWAYS read forecast_recipes.md before any SQL
  → Never proceed on cached memory of what these files contain
  → This is the determinism guarantee: formulas and SQL templates are loaded from
    files at runtime, not recalled from LLM training weights
```

This is the core mechanism that ensures consistency across conversations. If the formula is in
the file, every conversation reads the same formula and applies it identically. LLM memory is
excluded from the computation path.

---

## 8. LLM Forecasting Principles

These principles are non-negotiable. They distinguish this approach from naive LLM-based forecasting.

### Principle 1 — SQL is the Calculator, LLM is the Presenter

The LLM never computes a numeric forecast. It constructs a SQL query from a template, submits it,
reads the returned columns, and presents the values. Every number in the output trace directly
back to a SQL column value.

```
WRONG: LLM estimates "(6,500 + 6,200) / 2 ≈ 6,350"
RIGHT: LLM executes SELECT ROUND((sn + ma3)/2.0) AS ensemble FROM ...;
       reads result column; reports "6,348" (the exact SQL output)
```

This matters because LLM arithmetic — even on simple two-number averages — can vary by 1–2 units
across runs, and the choice of rounding convention can differ. When the formula is in SQL, the
result is deterministic for the same data state.

### Principle 2 — Same Data State = Same Answer

Determinism requirement: if the underlying data has not changed, the same question must produce
the same numbers in every conversation. This is guaranteed by:

1. Fixed data filters (hardcoded in recipe templates, never paraphrased)
2. Fixed formulas (hardcoded in forecast_recipes.md, never derived by LLM)
3. Fixed rounding (ROUND() in SQL, not LLM judgment)
4. Locked backtest parameters (values read from SQL, not re-estimated)

The only legitimate reason for an answer to change is if new data entered the database — in which
case the change is correct and expected.

### Principle 3 — Show Evidence of Quality Before Showing Forecast

Every forecast output begins with a backtest quality report. The user sees how well the method
performed on the last 12 months before seeing any projection. This is not optional — it is the
trust-building mechanism.

```
Example output header:
  "Berdasarkan backtest 12 bulan terakhir:
   MAPE: 14.2% | SN weight: 52% | MA3 weight: 48%
   Ini berarti model rata-rata meleset ±14% dari aktual bulan-bulan sebelumnya."
```

### Principle 4 — Honest Uncertainty, Not False Precision

Forecasts are presented with intervals. Intervals widen with horizon. Horizon tiers are labeled.
The system never presents a single point number as "the" forecast without an interval — that would
create false precision and misrepresent uncertainty.

The system also gates on MAPE > 40% — if recent performance is poor, it explicitly declines to
forecast and says so. An honest "saya tidak bisa memberikan proyeksi yang andal untuk metrik ini"
is a better answer than a number with no basis.

### Principle 5 — Garbage In, Stated Out

Data condition problems (gaps, breaks, high volatility) are reported to the user before any
forecast is computed. The user learns about data quality as a product of asking a forecast
question. This "garbage in, stated out" principle prevents the model from silently producing a
forecast on corrupted input.

---

## 9. Output Communication Design

The backtest gate, SQL computation, and interval formulas are internal machinery. The user sees
none of that. This section specifies exactly what the user sees — in what order, in what form,
and with what vocabulary.

### 9.1 Core Design Principle — One Story, Not Two Tables

The fundamental mistake in traditional forecast UX is presenting history and forecast as separate
blocks. This forces the user to context-switch mentally: "okay now I've seen the past, let me
switch to reading the future." The human brain reads trends, not context-switches.

The correct design: **one unified timeline** where history transitions directly into forecast.
The user reads a single continuous series: past → separator → future. They immediately see
whether the forecast continues, reverses, or accelerates the visible trend.

```
Historis           →   Proyeksi
────────────────────────────────
Mar  5.036
Apr  6.028
Mei  5.311
Jun  5.870
─────────── ← batas saat ini
Jul            5.981
Agu            6.425
Sep            6.102
```

This is the mental model. All structural output elements support this single story.

### 9.2 Internal vs User-Facing Translation

| Internal (computation) | User-facing (output) |
|---|---|
| σ, p10, p90, n_obs | Not shown |
| weight_sn = 0.54, weight_ma3 = 0.46 | "54% Seasonal Naive · 46% Moving Average 3 Bulan" |
| Lower 95% / Upper 95% | Not shown |
| lower_80, upper_80 | "Rentang Realistis: 5.169 – 6.615" |
| mape_ensemble = 11.8% | "Kualitas Proyeksi: BAIK" |
| avg_recent/avg_prior = 1.38 | "⚠ Perubahan level terdeteksi (+38%)" |
| ADF p-value, ACF lag-12 | Not shown |
| H tier = Primary/Acceptable | "Tingkat Keyakinan: Tinggi / Sedang" |
| forecast = 5,981 | "Perkiraan: 5.981" (word "Perkiraan" not "Forecast") |

Vocabulary rule: use **Proyeksi** or **Perkiraan** in all user-facing output — never "Forecast"
(too technical), never "Prediksi" (implies higher precision than we have). "Rentang Realistis"
not "80% CI". "Apa Artinya?" not "Interpretasi" (more conversational).

### 9.3 The 7-Block Output Structure

Every forecast response follows this exact block order. No blocks may be reordered or omitted.

---

**BLOK 1 — Pesan Utama**

Purpose: pimpinan reads only this. One or two sentences that summarize the entire forecast.
Completed before the user has scrolled down. Must not contain any number that requires context.

```
PROYEKSI PERMOHONAN ERBA
Juli–September 2026

Permohonan diperkirakan meningkat sekitar 7–8% dibanding 3 bulan
terakhir dan masih berada dalam rentang historis normal.
```

Rules:
- State direction (meningkat / menurun / stabil) and magnitude (roughly %)
- State whether it is within or outside historical range
- If LEMAH quality: add "(proyeksi bersifat indikasi, gunakan dengan hati-hati)"
- Never include exact numbers — that is Blok 2's job

---

**BLOK 2 — Ringkasan Perbandingan**

Purpose: the most actionable comparison — what was vs what will be, in under 5 seconds.
Pimpinan reads this as a KPI dashboard.

```
Ringkasan

Rata-rata 3 bulan terakhir   :  5.739
Rata-rata 3 bulan ke depan   :  6.169
Perubahan                    :  +7.5%
Kualitas Proyeksi            :  BAIK
```

Rules:
- "3 bulan terakhir" = avg of last 3 actual months before cutoff
- "3 bulan ke depan" = avg of forecast months
- % change = (forecast_avg - historical_avg) / historical_avg × 100
- Quality label mapping:

| MAPE (volume-adjusted) | Label | Makna |
|---|---|---|
| ≤ 15% | **BAIK** | Dapat digunakan untuk perencanaan operasional |
| 15–25% | **CUKUP** | Indikasi arah; gunakan sebagai referensi, bukan target pasti |
| 25–35% | **LEMAH** | Kisaran kasar; sampaikan keterbatasan ke pengambil keputusan |
| > 35% | TOLAK | Tidak ditampilkan; hanya historis yang disajikan |

*Volume adjustment: series avg < 300/bulan → naik satu tingkat (BAIK→CUKUP, CUKUP→LEMAH)*

---

**BLOK 3 — Kondisi Data**

Purpose: "garbage in, stated out" — user sees data health before numbers.
Format: ✓/⚠ checklist only. No raw ratios, no technical terms.

Normal case:
```
Kondisi Data

✓ Tidak ada bulan kosong dalam riwayat data
✓ Tidak ada perubahan level signifikan — periode stabil
✓ Volatilitas dalam batas normal
```

With issues:
```
Kondisi Data

✓ Tidak ada bulan kosong
⚠ Terdeteksi perubahan level di semester II 2025 — window pelatihan dipersempit ke 12 bulan
✓ Volatilitas dalam batas normal
⚠ Target mencakup bulan Maret — secara historis Maret menunjukkan variasi lebih tinggi
```

Rules:
- Only ✓ and ⚠ — never raw numbers, ratios, or technical terms like "break_ratio", "CV"
- March flag: always add ⚠ if any target month is March
- One-sentence summary at end only if there is at least one ⚠

---

**BLOK 4 — Historis & Proyeksi (Unified Timeline)**

Purpose: the key cognitive advantage — user reads one continuous series with a separator line.
Show last 4 actual months then separator then all forecast months.

```
Historis & Proyeksi

Mar 2026    5.036
Apr 2026    6.028
Mei 2026    5.311
Jun 2026    5.870
────────────────── ← sekarang
Jul 2026              5.981
Agu 2026              6.425
Sep 2026              6.102
```

Rules:
- Historis: 4 most recent actual months (no column header needed — implied)
- Separator: dashed line with "← sekarang" or "← batas proyeksi"
- Proyeksi: point forecast only in this view (not interval — that is Blok 5)
- Format: month left-aligned, actual left-aligned, forecast right-aligned
- Do NOT show summary stats or headers in this block — keep it visual

Followed immediately by summary stats for the historis:
```
12 bulan historis — Rata-rata: 6.078  |  Tertinggi: 7.214 (Agu 2025)  |  Terendah: 5.036 (Mar 2026)
```

---

**BLOK 5 — Proyeksi Detail (with Rentang Realistis)**

Purpose: the full detail table for users who need to plan specific months.

```
Proyeksi Detail

Bulan      Perkiraan    Rentang Realistis    Tingkat Keyakinan
Jul 2026     5.981        5.169 – 6.615          Tinggi
Agu 2026     6.425        5.044 – 7.321          Sedang
Sep 2026     6.102        4.650 – 7.697          Sedang
```

"Rentang Realistis" = 80% empirical interval with business floor applied.
"Tingkat Keyakinan" user labels:

| H | Label |
|---|---|
| H = 1 | Tinggi |
| H = 2–3 | Sedang |
| H = 4–6 | Rendah |
| H > 6 | Sangat Rendah — orientasi saja |

Rules:
- Column header: "Perkiraan" not "Forecast"
- Column header: "Rentang Realistis" not "80% CI" not "Lower 80%"
- Never show: Lower 95%, Upper 95%, sigma
- If H > 3 is included: add footnote "Proyeksi H>3 menggunakan aproksimasi — gunakan sebagai orientasi"

---

**BLOK 6 — Apa Artinya?**

Purpose: the interpretation that no dashboard can provide. Bullet points, not prose paragraphs.
User reads this to understand what to do with the numbers, not to re-read the numbers.

```
Apa Artinya?

• Volume diperkirakan sedikit meningkat dibanding kondisi saat ini.
• Tidak terlihat indikasi lonjakan permohonan di periode ini.
• Pola masih berada dalam kisaran historis normal — tidak ada sinyal anomali.
• Angka September mulai melebar — gunakan sebagai kisaran, bukan angka pasti.
```

Rules:
- 3–5 bullet points, each one actionable observation
- Never repeat exact numbers from the table (user can read those)
- Always compare: vs last year same period, vs last 3-month actual
- If LEMAH: add bullet "• Proyeksi bersifat indikatif — validasi dengan data operasional sebelum digunakan"
- If March target: add bullet "• Maret secara historis lebih sulit diprediksi — rentang lebih lebar dari biasanya"
- LLM derives these bullets from actual SQL output — no hallucination

---

**BLOK 7 — Metodologi (always append)**

Purpose: audit trail and reproducibility reference. Compact, not explanatory.

```
Metodologi

Data         ERBA 2022+ (trader_id tidak termasuk akun uji)
Backtest     MAPE {mape}% ({window} bulan terakhir)
Metode       {w_sn}% Seasonal Naive · {w_ma3}% Moving Average 3 Bulan
Interval     Rentang Realistis = persentil empiris residual × √H
```

If structural break active: add "Window dipersempit ke 12 bulan — perubahan level terdeteksi."
If dimension filter: add "Entitas: {entity} (e.g., BTP, MR, NIE Terbit)."

---

### 9.4 What Is Never Shown

| Never shown | Available if user explicitly asks "detail teknis" |
|---|---|
| σ (sigma) | On explicit audit request |
| p10, p90 (raw percentiles) | On explicit audit request |
| ADF p-value | On explicit audit request |
| ACF lag-12 value | On explicit audit request |
| Lower 95% / Upper 95% CI | On explicit audit request |
| weight_sn, weight_ma3 as decimals | Shown as % in Metodologi footer only |
| n_obs | On explicit audit request |
| "Forecast" (word) | Replace with "Proyeksi" or "Perkiraan" |
| "Interpretasi" (word) | Replace with "Apa Artinya?" |

---

### 9.5 Output Self-Check (before presenting)

```
□ Blok 1 Pesan Utama: direction + magnitude + in/out of historical range
□ Blok 2 Ringkasan: avg last 3M / avg next 3M / % change / quality label
□ Blok 3 Kondisi Data: ✓/⚠ format, no raw ratios, March flag if applicable
□ Blok 4 Unified timeline: 4 historis months + separator + forecast months
□ Blok 5 Proyeksi Detail: "Perkiraan" + "Rentang Realistis" + "Tingkat Keyakinan"
□ Blok 6 Apa Artinya: 3–5 bullets, no number repetition, at least one actionable insight
□ Blok 7 Metodologi: MAPE % + method weights + interval formula
□ No sigma / p10 / p90 / ADF / ACF / Lower95 / Upper95 anywhere
□ Language matches user's question language
□ If quality LEMAH: caveat present in Blok 1 and Blok 6
```

If any box is unchecked, revise before sending.

---

## 10. Simulation — What Execution Looks Like

The following traces the complete execution path for the question:
> "Berapa prediksi permohonan bulan Juli, Agustus, September 2026?"

### PHASE 0: Load Context
Load `forecast_guide.md` and `forecast_recipes.md`. Confirm formulas are in scope.

### PHASE 1: Capture
- ENTITY: permohonan (applications, not NIE)
- SYSTEM: ERBA (default — ERLA non-stationary)
- HORIZON: H=1 (July 2026), H=2 (August), H=3 (September)
- Current month: June 2026 → date_trunc = 2026-06-01
- T_first = 2026-07-01

### PHASE 2: Data Condition Check (RECIPE-F2)
```sql
-- Structural break check
SELECT
  AVG(CASE WHEN bulan >= '2026-01-01' THEN jumlah END) AS avg_recent,
  AVG(CASE WHEN bulan BETWEEN '2025-07-01' AND '2025-12-31' THEN jumlah END) AS avg_prior
FROM monthly
-- Result: avg_recent = 5,715 / avg_prior = 6,190 → ratio 0.92 → no break (within 0.70–1.30)
```
Report: no gap, no structural break (ratio=0.92), CV=0.18 (low volatility). Proceed.

### PHASE 3: Backtest Gate (RECIPE-F3)
Run 24-month rolling evaluation (Jun 2024 – May 2026).
```
Result (from live simulation 2026-06-18):
  mape_ensemble = 19.1%
  weight_sn     = 0.34
  weight_ma3    = 0.66
  sigma         = 1,093
  p10           = −1,056
  p90           = +1,904
  n_obs         = 24
```
MAPE 19.1% → label CUKUP, PROCEED. Lock parameters. weights: SN=34%, MA3=66%.

### PHASE 4: Point Forecast (RECIPE-F4 × 3)

```sql
-- Jul 2026 (H=1): SN = count Jul 2025 = 6,804
--                 MA3 = avg(Apr,May,Jun 2026) = avg(5677,5086,~5870) ≈ 5,544
--                 ensemble = ROUND(0.34×6804 + 0.66×5544) = ROUND(2313+3659) = 5,972

-- Aug 2026 (H=2): SN = count Aug 2025 = 6,535
--                 MA3 FROZEN = avg(Mar,Apr,May 2026) = avg(4675,5677,5086) = 5,146
--                 ensemble = ROUND(0.34×6535 + 0.66×5146) = ROUND(2222+3396) = 5,618

-- Sep 2026 (H=3): SN = count Sep 2025 = 6,521
--                 MA3 FROZEN = same as H=2 = 5,146
--                 ensemble = ROUND(0.34×6521 + 0.66×5146) = ROUND(2217+3396) = 5,613
```

Note: MA3 is frozen from H=2 onward (limitation §11.1) — Jul/Aug/Sep projections use the same
MA3 base. This causes the convergence visible in the timeline. Quarterly aggregate absorbs this.

### PHASE 5: Intervals with business floor (RECIPE-F6)

| Bulan | H | Perkiraan | σ_H=1093×√H | raw_lower | floor(p5=1617) | lower_80 | upper_80 | Tier |
|---|---|---|---|---|---|---|---|---|
| Jul 2026 | 1 | 5,972 | 1,093 | 4,916 | 1,617 | 4,916 | 7,876 | Tinggi |
| Agu 2026 | 2 | 5,618 | 1,546 | 4,506 | 1,617 | 4,506 | 7,618 | Sedang |
| Sep 2026 | 3 | 5,613 | 1,893 | 4,513 | 1,617 | 4,513 | 7,613 | Sedang |

Floor: raw_lower > p5=1,617 in all cases → floor not binding here.

### PHASE 6: Present (7-block format per §9.3)

```
PROYEKSI PERMOHONAN ERBA
Juli–September 2026

Permohonan diperkirakan berada pada level yang mirip dengan
3 bulan terakhir — tidak ada indikasi perubahan signifikan.

Kualitas Proyeksi: CUKUP

────────────────────────────────────

Ringkasan

Rata-rata 3 bulan terakhir   :  5.358  (Apr–Jun 2026)
Rata-rata 3 bulan ke depan   :  5.734  (Jul–Sep 2026)
Perubahan                    :  +7.0%
Kualitas Proyeksi            :  CUKUP

────────────────────────────────────

Kondisi Data

✓ Tidak ada bulan kosong dalam riwayat data
✓ Tidak ada perubahan level signifikan — periode stabil
✓ Volatilitas dalam batas normal

────────────────────────────────────

Historis & Proyeksi

Mar 2026    4.675
Apr 2026    5.677
Mei 2026    5.086
Jun 2026    5.870
────────────────── ← sekarang
Jul 2026              5.972
Agu 2026              5.618
Sep 2026              5.613

12 bulan historis — Rata-rata: 5.710  |  Tertinggi: 6.496 (Feb 2026)  |  Terendah: 4.675 (Mar 2026)

────────────────────────────────────

Proyeksi Detail

Bulan      Perkiraan    Rentang Realistis    Tingkat Keyakinan
Jul 2026     5.972        4.916 – 7.876          Tinggi
Agu 2026     5.618        4.506 – 7.618          Sedang
Sep 2026     5.613        4.513 – 7.613          Sedang

────────────────────────────────────

Apa Artinya?

• Volume diperkirakan sedikit lebih tinggi dibanding kondisi Apr–Jun 2026.
• Tidak ada tanda-tanda lonjakan permohonan di Q3 2026.
• Pola masih dalam kisaran historis normal — tidak ada sinyal anomali.
• Proyeksi ini bersifat indikatif (kualitas CUKUP) — gunakan sebagai
  referensi perencanaan, bukan angka target pasti.

────────────────────────────────────

Metodologi

Data         ERBA 2022+ (trader_id tidak termasuk akun uji)
Backtest     MAPE 19.1% (24 bulan, Jun 2024 – Mei 2026)
Metode       34% Seasonal Naive · 66% Moving Average 3 Bulan
Interval     Rentang Realistis = persentil empiris residual × √H
```

---

## 11. Known Limitations and Open Items

### Limitation 1 — MA3 Frozen for H≥2 (True SQL Limitation)

This is the only TRUE SQL limitation identified in the design. For H=2+, MA3 for month T
ideally uses T-3, T-2, T-1 — but T-1 is itself a forecasted month, and SQL cannot recursively
use forecast output as input to the next iteration in a single query.

Resolution: MA3 uses only actual months. For H=2, MA3 is computed from months T-4, T-3, T-2
(the three actual months preceding the first forecast target). For H=3 it uses T-5, T-4, T-3.

This means Jul, Aug, Sep 2026 all use the same frozen MA3 base (Mar–Mei 2026 actuals), which
explains why monthly forecasts at H=2 and H=3 look similar. This is not a model failure — it
is a deliberate choice to avoid cascading forecast-of-forecast error propagation. The quarterly
aggregate absorbs this flattening effect: Q3 2026 as a total is still useful even if Aug and
Sep individual forecasts are close to Jul.

Document this explicitly in `forecast_guide.md` as: "MA3 freeze limitation — applicable only
to monthly H≥2. Use quarterly aggregate as primary output for H≥2."

### Limitation 2 — March Effect (Systematic, Unfixed)

All series show elevated MAPE in March (22–28% vs 5–12% in other months). This is likely a
Q1-end administrative pattern in BPOM's processing calendar. Both SN (same month last year) and
MA3 (prior 3 months) fail to capture this effect because March in the training year also shows
the same deviation — SN effectively anchors to it, while MA3 smooths over it.

This is not fixable with the current SQL-only approach without adding a March-specific adjustment
factor. For now: document the limitation, apply the March flag in PHASE 6 output whenever March
is a target month, and recommend users treat March projections as lower confidence.

### Limitation 3 — Small-Volume Series (MAPE Distortion)

For series with avg monthly volume < 300 (BTP borderline, MT=387), MAPE becomes an unreliable
gate metric. A 68-unit absolute error on MT (avg=387) yields MAPE=17.5%, while the same error
on Permohonan (avg=4,500) yields MAPE=1.5%. The volume-adjusted label (§5.3) partially corrects
this, but the fundamental issue remains: small-volume forecasts have high relative variability
that the MAPE gate cannot fully characterize.

For operational use: present small-volume forecasts with an explicit caveat that the absolute
error is small even when percentage error appears high.

### Limitation 4 — 24-Month Backtest Still Not Enough for 95% Coverage Validation

With 24 observations, coverage estimation is still unreliable (requires 30+). The gate uses
MAPE (a point-estimate metric). This is flagged as a known limitation, not a design flaw. The
80% empirical interval is presented as the primary uncertainty range; the claim is not that it
achieves exactly 80% coverage, but that it reflects the historical spread of forecast errors.

---

## 12. Acceptance Criteria

| Criterion | Test |
|---|---|
| Same question, same data → same answer (3 runs) | Run identical forecast question 3× in new sessions; assert point forecasts match exactly |
| Backtest gate halts on TOLAK series | Dicabut/revocations → system presents historical only and states reason |
| Eligibility pre-check works | "prediksi TinggiNotif" → system states insufficient history and gives eligible date |
| Intervals widen with horizon | H=3 Rentang Realistis must be strictly wider than H=1 |
| H≥4 labeled "Rendah" | Output for H≥4 must show "Tingkat Keyakinan: Rendah" |
| ERLA forecast refused | "prediksi permohonan ERLA" → system states ERLA non-stationary, offers ERBA alternative |
| 5-layer structure enforced | Output: Executive Summary → Kondisi Data → Historis → Proyeksi → Interpretasi → Metodologi |
| Quarterly aggregate as primary | For H≥2 questions, response leads with Q aggregate before monthly breakdown |
| No technical stats leaked | Output must not contain: sigma, p10, p90, ADF, ACF, Lower 95%, Upper 95% |
| Quality label present | Response contains "Kualitas forecast: BAIK / CUKUP / LEMAH" |
| "Rentang Realistis" used | Interval column header is "Rentang Realistis", not "80% CI" or "Lower 80%" |
| March flag shows | When March is a target month, output includes ⚠ March variability note |
| Business floor applied | Lower bound must be ≥ p5 of training volume (never presents negative lower bound) |
| Volume caveat on small series | MT (302) output includes note about small volume interpretation |
| Narrative is non-mechanical | Interpretasi does not repeat table values; contains at least one operational inference |
| LLM never computes numbers | No arithmetic expression in LLM output that isn't quoting a SQL result column |

---

## 13. Files to Build — Complete Inventory

### Files to CREATE (new)

| File | Purpose | Priority |
|---|---|---|
| `seeknal/skills/bpom-forecaster/SKILL.md` | 6-phase forecasting pipeline skill | 1 |
| `context/forecast_recipes.md` | SQL templates F1–F6 + RECIPE-ELIGIBILITY | 1 |
| `seeknal/tests/v1/singleturn/FORECAST-*.yml` | UAT test cases for forecasting scenarios | 2 |

### Files to REWRITE

| File | Change Needed | Priority |
|---|---|---|
| `context/forecast_guide.md` | Complete rewrite — current content documents dropped `forecast_permohonan` table | 1 |

### Files to UPDATE (add FORECAST support)

| File | What to Add | Priority |
|---|---|---|
| `context/intent_mapping.md` | Add FORECAST as 9th operation entry with trigger words (ID + EN) | 2 |
| `SEEKNAL_ASK.md` | Add routing branch: if OPERATION=FORECAST → invoke bpom-forecaster (minimal edit) | 2 |

### Implementation Order

```
1. context/forecast_guide.md  — rewritten (PHASE 0 depends on it)
2. context/forecast_recipes.md — created (PHASE 0 depends on it)
3. seeknal/skills/bpom-forecaster/SKILL.md — created (depends on both context files)
4. context/intent_mapping.md — FORECAST operation added
5. SEEKNAL_ASK.md — routing branch added
6. seeknal/tests/v1/singleturn/FORECAST-*.yml — UAT cases created
```

### Content Spec: `context/forecast_guide.md`

Replace entirely. New structure:
- §1 Data Source: always `public.t_produk_3_erba` (ERBA), full history from 2022-09, mandatory casts
- §2 Training Window: full history from 2022-09 (not rolling 36M)
- §3 Eligibility Criteria: history ≥36M, avg_vol ≥300, process-driven
- §4 Method Reference: SN, MA3, ensemble weights, floor formula
- §5 Backtest: 24-month window, MAPE gate (≤15/15-25/25-35/>35), volume adjustment
- §6 Interval Formula: σ_H=σ√H, lower_80=GREATEST(raw, p5_floor), upper_80
- §7 Horizon Tiers: H1 Tinggi / H2-3 Sedang / H4-6 Rendah / H>6 Sangat Rendah
- §8 Output Vocabulary: Rentang Realistis, Tingkat Keyakinan, quality labels
- §9 Never-Show List: sigma, p10, p90, ADF, ACF, Lower95, Upper95
- §10 5-Layer Self-Check: 9-item checklist before presenting
- §11 Known Biases: March effect, MA3 freeze at H≥2, small-volume distortion
- §12 Series Registry: table of forecastable series with source, date col, filter, eligibility

### Content Spec: `context/forecast_recipes.md`

New file with SQL templates:
- RECIPE-ELIGIBILITY: checks history count and avg volume
- RECIPE-F1: monthly time series pull (ERBA 2022+, parameterized by entity + filter)
- RECIPE-F2: data condition diagnostics (gap, structural break, CV)
- RECIPE-F3: 24-month backtest gate (returns mape, weights, σ, p10, p90, floor)
- RECIPE-F4: point forecast for single target month T (SN + MA3 + ensemble)
- RECIPE-F5: multi-month forecast loop (H=1 to N in one query)
- RECIPE-F6: combined output with intervals and business floor

Each recipe has: explicit placeholders `{T_first}`, `{H}`, `{filter}` with fill instructions.
Mandatory filter block in every recipe: `trader_id::bigint NOT IN (5,17,50,85)`,
`tanggal_bayar IS NOT NULL AND tanggal_bayar != ''`, ERBA TEXT casts.

### Content Spec: `context/intent_mapping.md` Addition

Add as 9th OPERATION entry:
```
FORECAST
Trigger words (ID): prediksi, proyeksi, estimasi ke depan, berapa nanti, bulan depan,
  tahun depan, semester depan, Q1/Q2/Q3/Q4, tren ke depan, akan ada berapa,
  target realistis, bisa mencapai, kemungkinan, perkiraan, berapa ke depan
Trigger words (EN): forecast, predict, projection, next month, next quarter, outlook
Default TIME_SCOPE: 3 months if not stated
Default SYSTEM: ERBA only
Routes to: bpom-forecaster
Note: if question mixes TREND (past) + FORECAST (future) → handle TREND portion with
  bpom-analyst logic + FORECAST portion with bpom-forecaster; present as continuous timeline
```

### Content Spec: `SEEKNAL_ASK.md` Addition

Minimal: add one routing condition in the existing workflow section (after Semantic Commitment
Block identifies OPERATION):
```
IF OPERATION = FORECAST:
  → Use bpom-forecaster (seeknal/skills/bpom-forecaster/SKILL.md)
  → Do NOT invoke bpom-analyst for this turn
ELSE:
  → Continue with existing bpom-analyst routing (unchanged)
```
