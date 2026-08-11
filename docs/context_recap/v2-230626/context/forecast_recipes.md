# Forecast Recipes — SQL Templates for bpom-forecaster

> **Status:** v1.0 — June 2026.
> These recipes are SQL templates only — they are NOT used by `bpom-analyst` or `query_recipes.md`.
> Loaded in PHASE 0 of `bpom-forecaster`.
>
> **Determinism contract:** every recipe must produce identical results when run on unchanged data.
> No random seeds, no sampling, no LLM arithmetic — all computation in SQL.
>
> **Placeholders in templates:**
> - `{T_first}` — first target month as `YYYY-MM-01`
> - `{T}` — specific target month as `YYYY-MM-01`
> - `{H}` — horizon index (1 = first target month)
> - `{series_filter}` — WHERE clause for the specific series (see §Series Filters below)

---

## Series Filters Reference

Apply the correct filter for the requested series. Add to WHERE clause in every recipe.

| Series | Filter to add |
|---|---|
| Permohonan Total | (none beyond base filter) |
| NIE Terbit | `AND status IN ('0999','0906','9999') AND jenis_permohonan IN ('301','305')` |
| MR (Menengah Rendah) | `AND kategori_dokumen = '303'` |
| MT (Menengah Tinggi) | `AND kategori_dokumen = '302'` |
| Tinggi | `AND kategori_dokumen = '301'` |
| TinggiNotif | `AND kategori_dokumen = '304'` |
| BTP Permohonan | Use `warehouse.public.t_btp_3_erba` (no casts needed — native types) |

**Base filter block** (apply in every recipe using `t_produk_3_erba`):
```sql
WHERE tanggal_bayar IS NOT NULL
  AND tanggal_bayar != ''
  AND tanggal_bayar::timestamp >= '2022-09-01'
  AND trader_id::bigint NOT IN (5, 17, 50, 85)
```

**BTP base filter** (for `t_btp_3_erba` — native types, no TEXT casts):
```sql
WHERE tanggal_bayar IS NOT NULL
  AND tanggal_bayar >= '2022-09-01'
  AND trader_id NOT IN (5, 17, 50, 85)
```

---

## RECIPE-ELIGIBILITY — Pre-Check Before Any Backtest

Run this before RECIPE-F3. If either threshold fails, halt and explain to user.

```sql
WITH monthly AS (
  SELECT
    date_trunc('month', tanggal_bayar::timestamp) AS bulan,
    COUNT(DISTINCT produk_id)                     AS jumlah
  FROM warehouse.public.t_produk_3_erba
  WHERE tanggal_bayar IS NOT NULL
    AND tanggal_bayar != ''
    AND tanggal_bayar::timestamp >= '2022-09-01'
    AND tanggal_bayar::timestamp <  '{T_first}'
    AND trader_id::bigint NOT IN (5, 17, 50, 85)
    {series_filter}
  GROUP BY 1
)
SELECT
  COUNT(*)                  AS n_months_history,
  ROUND(AVG(jumlah), 0)    AS avg_monthly_vol,
  MIN(jumlah)              AS min_monthly_vol,
  MAX(jumlah)              AS max_monthly_vol,
  MIN(bulan)               AS earliest_month,
  MAX(bulan)               AS latest_month
FROM monthly;
```

**Gate logic:**
- `n_months_history < 36` → HALT: insufficient history (state earliest_month and how many more months needed)
- `avg_monthly_vol < 300` → WARN: volume below threshold, apply volume-adjusted label in RECIPE-F3
- Both OK → proceed to RECIPE-F2

---

## RECIPE-F1 — Monthly Time Series Pull (Full History)

Fetches the complete ERBA monthly series for visual inspection and training.

```sql
SELECT
  date_trunc('month', tanggal_bayar::timestamp) AS bulan,
  COUNT(DISTINCT produk_id)                     AS jumlah
FROM warehouse.public.t_produk_3_erba
WHERE tanggal_bayar IS NOT NULL
  AND tanggal_bayar != ''
  AND tanggal_bayar::timestamp >= '2022-09-01'
  AND tanggal_bayar::timestamp <  '{T_first}'
  AND trader_id::bigint NOT IN (5, 17, 50, 85)
  {series_filter}
GROUP BY 1
ORDER BY 1;
```

Use this to populate the "Historis & Proyeksi" unified timeline (show last 12 months from this result).

**BTP variant** (replace table and remove TEXT casts):
```sql
SELECT
  date_trunc('month', tanggal_bayar) AS bulan,
  COUNT(DISTINCT produk_id)          AS jumlah
FROM warehouse.public.t_btp_3_erba
WHERE tanggal_bayar IS NOT NULL
  AND tanggal_bayar >= '2022-09-01'
  AND tanggal_bayar <  '{T_first}'
  AND trader_id NOT IN (5, 17, 50, 85)
GROUP BY 1
ORDER BY 1;
```

---

## RECIPE-F2 — Data Condition Diagnostics

Run before RECIPE-F3 to check for gaps and structural breaks. Results populate Kondisi Data.

```sql
WITH monthly AS (
  SELECT
    date_trunc('month', tanggal_bayar::timestamp) AS bulan,
    COUNT(DISTINCT produk_id)                     AS jumlah
  FROM warehouse.public.t_produk_3_erba
  WHERE tanggal_bayar IS NOT NULL
    AND tanggal_bayar != ''
    AND tanggal_bayar::timestamp >= '2022-09-01'
    AND tanggal_bayar::timestamp <  '{T_first}'
    AND trader_id::bigint NOT IN (5, 17, 50, 85)
    {series_filter}
  GROUP BY 1
),
recent_6m AS (
  SELECT AVG(jumlah) AS avg_recent
  FROM monthly
  WHERE bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '6 months'
),
prior_6m AS (
  SELECT AVG(jumlah) AS avg_prior
  FROM monthly
  WHERE bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '12 months'
    AND bulan <  date_trunc('month', '{T_first}'::timestamp) - interval '6 months'
),
last12 AS (
  SELECT
    STDDEV(jumlah) AS std_12m,
    AVG(jumlah)    AS avg_12m,
    COUNT(*)       AS n_12m,
    SUM(CASE WHEN jumlah = 0 THEN 1 ELSE 0 END) AS zero_months
  FROM monthly
  WHERE bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '12 months'
)
SELECT
  l.n_12m,
  l.zero_months                                       AS gap_months,
  ROUND(r.avg_recent, 0)                             AS avg_recent_6m,
  ROUND(p.avg_prior, 0)                              AS avg_prior_6m,
  ROUND(r.avg_recent / NULLIF(p.avg_prior, 0), 2)   AS break_ratio,
  ROUND(l.std_12m / NULLIF(l.avg_12m, 0), 2)        AS cv_12m,
  ROUND(l.avg_12m, 0)                                AS avg_12m
FROM last12 l, recent_6m r, prior_6m p;
```

**Interpret for Kondisi Data:**
- `gap_months = 0` → ✓ Data lengkap — tidak ada gap dalam 12 bulan terakhir
- `gap_months > 0` → ⚠ Terdapat [N] bulan dengan volume nol — periksa kelengkapan data
- `break_ratio < 0.70` → ⚠ Terjadi penurunan signifikan (~[persen]%) dalam 6 bulan terakhir
- `break_ratio > 1.30` → ⚠ Terjadi kenaikan signifikan (~[persen]%) dalam 6 bulan terakhir
- `0.70 ≤ break_ratio ≤ 1.30` → ✓ Volume relatif stabil
- `cv_12m > 0.50` → ⚠ Volatilitas tinggi (CV = [value]) — rentang proyeksi lebih lebar
- `cv_12m ≤ 0.50` → ✓ Volatilitas dalam batas normal

---

## RECIPE-F3 — Backtest Gate (24-Month Rolling Evaluation)

The most important recipe. Run this after eligibility check. Extract all 9 output columns and lock them
for the rest of the session. Never recompute mid-session.

```sql
WITH monthly AS (
  SELECT
    date_trunc('month', tanggal_bayar::timestamp) AS bulan,
    COUNT(DISTINCT produk_id)                     AS jumlah
  FROM warehouse.public.t_produk_3_erba
  WHERE tanggal_bayar IS NOT NULL
    AND tanggal_bayar != ''
    AND tanggal_bayar::timestamp >= '2022-09-01'
    AND trader_id::bigint NOT IN (5, 17, 50, 85)
    {series_filter}
  GROUP BY 1
),
backtest_window AS (
  -- 24 months of actuals ending at the month before T_first
  SELECT
    m.bulan                                                   AS target,
    m.jumlah                                                  AS actual,
    ly.jumlah                                                 AS sn_forecast,
    ROUND(AVG(prev.jumlah) OVER (
      ORDER BY m.bulan
      ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
    ))                                                        AS ma3_forecast
  FROM monthly m
  LEFT JOIN monthly ly
    ON ly.bulan = m.bulan - interval '12 months'
  LEFT JOIN monthly prev
    ON prev.bulan BETWEEN m.bulan - interval '3 months'
                      AND m.bulan - interval '1 month'
  WHERE m.bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '24 months'
    AND m.bulan <  date_trunc('month', '{T_first}'::timestamp)
    AND ly.jumlah IS NOT NULL
),
weights_raw AS (
  SELECT
    AVG(ABS(actual - sn_forecast))   AS mae_sn,
    AVG(ABS(actual - ma3_forecast))  AS mae_ma3
  FROM backtest_window
  WHERE sn_forecast IS NOT NULL AND ma3_forecast IS NOT NULL
),
weights AS (
  SELECT
    (1.0 / mae_sn)  / (1.0 / mae_sn + 1.0 / mae_ma3)  AS w_sn,
    (1.0 / mae_ma3) / (1.0 / mae_sn + 1.0 / mae_ma3)  AS w_ma3,
    mae_sn,
    mae_ma3
  FROM weights_raw
),
ensemble_residuals AS (
  SELECT
    b.actual,
    ROUND(w.w_sn * b.sn_forecast + w.w_ma3 * b.ma3_forecast) AS ensemble,
    b.actual - ROUND(w.w_sn * b.sn_forecast + w.w_ma3 * b.ma3_forecast) AS residual
  FROM backtest_window b, weights w
  WHERE b.sn_forecast IS NOT NULL AND b.ma3_forecast IS NOT NULL
)
SELECT
  COUNT(*)                                                          AS n_obs,
  ROUND(w.w_sn * 100, 0)                                          AS pct_weight_sn,
  ROUND(w.w_ma3 * 100, 0)                                         AS pct_weight_ma3,
  ROUND(AVG(ABS(e.actual - e.ensemble)) / NULLIF(AVG(e.actual), 0) * 100, 1)
                                                                   AS mape_ensemble,
  ROUND(AVG(ABS(e.actual - e.ensemble)), 0)                       AS mae_ensemble,
  ROUND(STDDEV(e.residual), 0)                                     AS sigma_ensemble,
  ROUND(PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY e.residual)) AS p10_ensemble,
  ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY e.residual)) AS p90_ensemble,
  ROUND(PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY e.actual))   AS p5_training_volume
FROM ensemble_residuals e, weights w
GROUP BY w.w_sn, w.w_ma3;
```

**Read and lock these 9 values from the result:**
1. `n_obs` — number of backtest observations (should be 18–24; warn if < 18)
2. `pct_weight_sn` — SN weight as percentage
3. `pct_weight_ma3` — MA3 weight as percentage
4. `mape_ensemble` — apply gate (≤15 BAIK, 15-25 CUKUP, 25-35 LEMAH, >35 TOLAK)
5. `mae_ensemble` — for reference
6. `sigma_ensemble` — used in √H scaling
7. `p10_ensemble` — lower bound multiplier (empirical 10th percentile of residuals)
8. `p90_ensemble` — upper bound multiplier (empirical 90th percentile of residuals)
9. `p5_training_volume` — business floor for lower bound

Apply volume-adjusted label: if `avg_monthly_vol < 300` from RECIPE-ELIGIBILITY, downgrade `mape_ensemble`
label by one tier before proceeding.

---

## RECIPE-F4 — Point Forecast for Single Target Month T

Run one instance of this for each target month. Read SN and MA3 from SQL; ensemble is computed in SQL.

```sql
WITH monthly AS (
  SELECT
    date_trunc('month', tanggal_bayar::timestamp) AS bulan,
    COUNT(DISTINCT produk_id)                     AS jumlah
  FROM warehouse.public.t_produk_3_erba
  WHERE tanggal_bayar IS NOT NULL
    AND tanggal_bayar != ''
    AND tanggal_bayar::timestamp >= '2022-09-01'
    AND tanggal_bayar::timestamp <  '{T}'
    AND trader_id::bigint NOT IN (5, 17, 50, 85)
    {series_filter}
  GROUP BY 1
)
SELECT
  -- SN: same month last year
  (SELECT jumlah FROM monthly WHERE bulan = date_trunc('month', '{T}'::timestamp) - interval '12 months')
    AS sn_forecast,
  -- MA3: average of 3 months before T
  (SELECT ROUND(AVG(jumlah)) FROM monthly
    WHERE bulan >= date_trunc('month', '{T}'::timestamp) - interval '3 months'
      AND bulan <  date_trunc('month', '{T}'::timestamp))
    AS ma3_forecast,
  -- Ensemble (weights from RECIPE-F3 — substitute actual values, NOT placeholders)
  ROUND(
    ({pct_weight_sn} / 100.0) *
      (SELECT jumlah FROM monthly WHERE bulan = date_trunc('month', '{T}'::timestamp) - interval '12 months')
    +
    ({pct_weight_ma3} / 100.0) *
      (SELECT ROUND(AVG(jumlah)) FROM monthly
        WHERE bulan >= date_trunc('month', '{T}'::timestamp) - interval '3 months'
          AND bulan <  date_trunc('month', '{T}'::timestamp))
  )                  AS ensemble_forecast;
```

**Note on weights:** substitute the actual integer percentages from RECIPE-F3 result
(e.g. `34` and `66`) for `{pct_weight_sn}` and `{pct_weight_ma3}`. Do not use variable placeholders
in the final executed SQL.

---

## RECIPE-F5 — Multi-Month Forecast Loop (H = 1 to N)

For multi-month forecasts, run RECIPE-F4 once per target month. The MA3 for H ≥ 2 uses the last
3 actual months (not prior forecast values — this is the MA3 freeze limitation documented in
`forecast_guide.md §12 Limitation 2`).

```sql
WITH monthly AS (
  SELECT
    date_trunc('month', tanggal_bayar::timestamp) AS bulan,
    COUNT(DISTINCT produk_id)                     AS jumlah
  FROM warehouse.public.t_produk_3_erba
  WHERE tanggal_bayar IS NOT NULL
    AND tanggal_bayar != ''
    AND tanggal_bayar::timestamp >= '2022-09-01'
    AND tanggal_bayar::timestamp <  '{T_first}'
    AND trader_id::bigint NOT IN (5, 17, 50, 85)
    {series_filter}
  GROUP BY 1
),
targets AS (
  -- Generate N target months starting from T_first
  SELECT
    generate_series(
      date_trunc('month', '{T_first}'::timestamp),
      date_trunc('month', '{T_first}'::timestamp) + interval '{N-1} months',
      interval '1 month'
    ) AS bulan_target
),
forecasts AS (
  SELECT
    t.bulan_target,
    ROW_NUMBER() OVER (ORDER BY t.bulan_target)                       AS h,
    -- SN: same month last year (from actual data)
    hist_sn.jumlah                                                    AS sn_forecast,
    -- MA3: last 3 actual months before T_first (frozen for all H)
    ROUND((
      SELECT AVG(jumlah) FROM monthly
      WHERE bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '3 months'
        AND bulan <  date_trunc('month', '{T_first}'::timestamp)
    ))                                                                AS ma3_forecast
  FROM targets t
  LEFT JOIN monthly hist_sn
    ON hist_sn.bulan = t.bulan_target - interval '12 months'
)
SELECT
  to_char(f.bulan_target, 'Mon YYYY')                               AS bulan,
  f.h,
  f.sn_forecast,
  f.ma3_forecast,
  ROUND(
    ({pct_weight_sn} / 100.0) * f.sn_forecast
    + ({pct_weight_ma3} / 100.0) * f.ma3_forecast
  )                                                                  AS ensemble_forecast
FROM forecasts f
WHERE f.sn_forecast IS NOT NULL
ORDER BY f.bulan_target;
```

Replace `{N-1}` with the actual number of months minus 1 (e.g. for 3 months: `2`).

---

## RECIPE-F6 — Combined Output with Intervals and Business Floor

Combines RECIPE-F5 point forecasts with the interval formula. All σ, p10, p90, p5_floor values
come from RECIPE-F3 — substitute actual numbers.

```sql
WITH monthly AS (
  SELECT
    date_trunc('month', tanggal_bayar::timestamp) AS bulan,
    COUNT(DISTINCT produk_id)                     AS jumlah
  FROM warehouse.public.t_produk_3_erba
  WHERE tanggal_bayar IS NOT NULL
    AND tanggal_bayar != ''
    AND tanggal_bayar::timestamp >= '2022-09-01'
    AND tanggal_bayar::timestamp <  '{T_first}'
    AND trader_id::bigint NOT IN (5, 17, 50, 85)
    {series_filter}
  GROUP BY 1
),
targets AS (
  SELECT
    generate_series(
      date_trunc('month', '{T_first}'::timestamp),
      date_trunc('month', '{T_first}'::timestamp) + interval '{N-1} months',
      interval '1 month'
    ) AS bulan_target
),
forecasts AS (
  SELECT
    t.bulan_target,
    ROW_NUMBER() OVER (ORDER BY t.bulan_target)   AS h,
    hist_sn.jumlah                                AS sn_forecast,
    ROUND((
      SELECT AVG(jumlah) FROM monthly
      WHERE bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '3 months'
        AND bulan <  date_trunc('month', '{T_first}'::timestamp)
    ))                                            AS ma3_forecast
  FROM targets t
  LEFT JOIN monthly hist_sn
    ON hist_sn.bulan = t.bulan_target - interval '12 months'
)
SELECT
  to_char(f.bulan_target, 'Mon YYYY')    AS bulan,
  f.h                                    AS horizon,
  ROUND(
    ({pct_weight_sn} / 100.0) * f.sn_forecast
    + ({pct_weight_ma3} / 100.0) * f.ma3_forecast
  )                                      AS perkiraan,
  -- Lower bound with business floor (p10 from RECIPE-F3, p5_floor from RECIPE-F3)
  GREATEST(
    ROUND(
      ({pct_weight_sn} / 100.0) * f.sn_forecast
      + ({pct_weight_ma3} / 100.0) * f.ma3_forecast
      + ROUND({p10_ensemble} * SQRT(f.h))
    ),
    {p5_training_volume}
  )                                      AS lower_80,
  -- Upper bound
  ROUND(
    ({pct_weight_sn} / 100.0) * f.sn_forecast
    + ({pct_weight_ma3} / 100.0) * f.ma3_forecast
    + ROUND({p90_ensemble} * SQRT(f.h))
  )                                      AS upper_80,
  -- Horizon tier label
  CASE
    WHEN f.h = 1 THEN 'Tinggi'
    WHEN f.h <= 3 THEN 'Sedang'
    WHEN f.h <= 6 THEN 'Rendah'
    ELSE 'Sangat Rendah'
  END                                    AS tingkat_keyakinan
FROM forecasts f
WHERE f.sn_forecast IS NOT NULL
ORDER BY f.bulan_target;
```

**Substitution guide for RECIPE-F6:**
- `{pct_weight_sn}` — integer from RECIPE-F3 `pct_weight_sn` column (e.g. `34`)
- `{pct_weight_ma3}` — integer from RECIPE-F3 `pct_weight_ma3` column (e.g. `66`)
- `{p10_ensemble}` — value from RECIPE-F3 `p10_ensemble` column (e.g. `-1056`)
- `{p90_ensemble}` — value from RECIPE-F3 `p90_ensemble` column (e.g. `1904`)
- `{p5_training_volume}` — value from RECIPE-F3 `p5_training_volume` column (the business floor)
- `{N-1}` — number of forecast months minus 1 (for 3-month forecast: `2`)

---

## Common Errors to Avoid

| Error | Correct approach |
|---|---|
| Using `TRY_CAST` or `SAFE_CAST` | Use PostgreSQL native `::timestamp` with NULL guard |
| LLM computing ensemble arithmetic | All arithmetic in SQL — read result columns, do not recompute |
| Using rolling 36M window | Use full history from 2022-09 (confirmed superior in backtest) |
| 12-month backtest window | Use 24-month (12M gave biased p10=+208; 24M gives p10=-744) |
| Recomputing weights each turn | Lock all 9 RECIPE-F3 values at start; never recompute during session |
| Showing p10/p90/sigma to user | Internal only — user sees Rentang Realistis (lower_80, upper_80) |
| Using EXTRACT(YEAR FROM ...) | Use date range: `tanggal_bayar::timestamp >= 'YYYY-01-01'` |
