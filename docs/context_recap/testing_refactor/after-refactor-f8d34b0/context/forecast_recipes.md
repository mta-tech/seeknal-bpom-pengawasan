# Forecast Recipes

These are the core SQL templates for `bpom-forecaster`.
They are intentionally minimal.

Placeholders:

- `{T_first}` = first target month (`YYYY-MM-01`)
- `{T}` = one forecast month
- `{H}` = horizon index
- `{series_filter}` = extra filter for the requested series

## 1. Base filters

For `t_produk_3_erba`:

```sql
WHERE tanggal_bayar IS NOT NULL
  AND tanggal_bayar != ''
  AND tanggal_bayar::timestamp >= '2022-09-01'
  AND tanggal_bayar::timestamp < '{T_first}'
  AND trader_id::bigint NOT IN (5, 17, 50, 85)
  {series_filter}
```

For `t_btp_3_erba`:

```sql
WHERE tanggal_bayar IS NOT NULL
  AND tanggal_bayar >= '2022-09-01'
  AND tanggal_bayar < '{T_first}'
  AND trader_id NOT IN (5, 17, 50, 85)
  {series_filter}
```

## 2. Eligibility

```sql
WITH monthly AS (
  SELECT
    date_trunc('month', tanggal_bayar::timestamp) AS bulan,
    COUNT(DISTINCT produk_id) AS jumlah
  FROM warehouse.public.t_produk_3_erba
  WHERE tanggal_bayar IS NOT NULL
    AND tanggal_bayar != ''
    AND tanggal_bayar::timestamp >= '2022-09-01'
    AND tanggal_bayar::timestamp < '{T_first}'
    AND trader_id::bigint NOT IN (5, 17, 50, 85)
    {series_filter}
  GROUP BY 1
)
SELECT
  COUNT(*) AS n_months_history,
  ROUND(AVG(jumlah), 0) AS avg_monthly_vol,
  MIN(bulan) AS earliest_month,
  MAX(bulan) AS latest_month
FROM monthly;
```

## 3. Monthly history pull

```sql
SELECT
  date_trunc('month', tanggal_bayar::timestamp) AS bulan,
  COUNT(DISTINCT produk_id) AS jumlah
FROM warehouse.public.t_produk_3_erba
WHERE tanggal_bayar IS NOT NULL
  AND tanggal_bayar != ''
  AND tanggal_bayar::timestamp >= '2022-09-01'
  AND tanggal_bayar::timestamp < '{T_first}'
  AND trader_id::bigint NOT IN (5, 17, 50, 85)
  {series_filter}
GROUP BY 1
ORDER BY 1;
```

## 4. Diagnostics

```sql
WITH monthly AS (
  SELECT
    date_trunc('month', tanggal_bayar::timestamp) AS bulan,
    COUNT(DISTINCT produk_id) AS jumlah
  FROM warehouse.public.t_produk_3_erba
  WHERE tanggal_bayar IS NOT NULL
    AND tanggal_bayar != ''
    AND tanggal_bayar::timestamp >= '2022-09-01'
    AND tanggal_bayar::timestamp < '{T_first}'
    AND trader_id::bigint NOT IN (5, 17, 50, 85)
    {series_filter}
  GROUP BY 1
)
SELECT
  COUNT(*) FILTER (
    WHERE bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '12 months'
  ) AS n_12m,
  SUM(CASE WHEN jumlah = 0 THEN 1 ELSE 0 END) FILTER (
    WHERE bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '12 months'
  ) AS gap_months,
  ROUND(
    AVG(jumlah) FILTER (
      WHERE bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '6 months'
    ) /
    NULLIF(
      AVG(jumlah) FILTER (
        WHERE bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '12 months'
          AND bulan < date_trunc('month', '{T_first}'::timestamp) - interval '6 months'
      ), 0
    ),
    2
  ) AS break_ratio,
  ROUND(
    STDDEV(jumlah) FILTER (
      WHERE bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '12 months'
    ) /
    NULLIF(
      AVG(jumlah) FILTER (
        WHERE bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '12 months'
      ), 0
    ),
    2
  ) AS cv_12m
FROM monthly;
```

## 5. Backtest

```sql
WITH monthly AS (
  SELECT
    date_trunc('month', tanggal_bayar::timestamp) AS bulan,
    COUNT(DISTINCT produk_id) AS jumlah
  FROM warehouse.public.t_produk_3_erba
  WHERE tanggal_bayar IS NOT NULL
    AND tanggal_bayar != ''
    AND tanggal_bayar::timestamp >= '2022-09-01'
    AND trader_id::bigint NOT IN (5, 17, 50, 85)
    {series_filter}
  GROUP BY 1
),
backtest_window AS (
  SELECT
    m.bulan AS target,
    m.jumlah AS actual,
    ly.jumlah AS sn_forecast,
    ROUND(AVG(prev.jumlah) OVER (
      ORDER BY m.bulan
      ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
    )) AS ma3_forecast
  FROM monthly m
  LEFT JOIN monthly ly
    ON ly.bulan = m.bulan - interval '12 months'
  LEFT JOIN monthly prev
    ON prev.bulan BETWEEN m.bulan - interval '3 months' AND m.bulan - interval '1 month'
  WHERE m.bulan >= date_trunc('month', '{T_first}'::timestamp) - interval '24 months'
    AND m.bulan < date_trunc('month', '{T_first}'::timestamp)
    AND ly.jumlah IS NOT NULL
),
weights_raw AS (
  SELECT
    AVG(ABS(actual - sn_forecast)) AS mae_sn,
    AVG(ABS(actual - ma3_forecast)) AS mae_ma3
  FROM backtest_window
  WHERE sn_forecast IS NOT NULL AND ma3_forecast IS NOT NULL
),
weights AS (
  SELECT
    (1.0 / mae_sn) / (1.0 / mae_sn + 1.0 / mae_ma3) AS w_sn,
    (1.0 / mae_ma3) / (1.0 / mae_sn + 1.0 / mae_ma3) AS w_ma3
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
  COUNT(*) AS n_obs,
  ROUND(MAX(w.w_sn) * 100, 0) AS pct_weight_sn,
  ROUND(MAX(w.w_ma3) * 100, 0) AS pct_weight_ma3,
  ROUND(AVG(ABS(e.actual - e.ensemble)) / NULLIF(AVG(e.actual), 0) * 100, 1) AS mape_ensemble,
  ROUND(STDDEV(e.residual), 0) AS sigma_ensemble,
  ROUND(PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY e.residual)) AS p10_ensemble,
  ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY e.residual)) AS p90_ensemble,
  ROUND(PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY e.actual)) AS p5_training_volume
FROM ensemble_residuals e, weights w;
```

## 6. Point forecast

```sql
WITH monthly AS (
  SELECT
    date_trunc('month', tanggal_bayar::timestamp) AS bulan,
    COUNT(DISTINCT produk_id) AS jumlah
  FROM warehouse.public.t_produk_3_erba
  WHERE tanggal_bayar IS NOT NULL
    AND tanggal_bayar != ''
    AND tanggal_bayar::timestamp >= '2022-09-01'
    AND tanggal_bayar::timestamp < '{T}'
    AND trader_id::bigint NOT IN (5, 17, 50, 85)
    {series_filter}
  GROUP BY 1
)
SELECT
  '{T}'::date AS target_month,
  ROUND(
    ({pct_weight_sn} / 100.0) * COALESCE((
      SELECT jumlah FROM monthly WHERE bulan = date_trunc('month', '{T}'::timestamp) - interval '12 months'
    ), 0) +
    ({pct_weight_ma3} / 100.0) * COALESCE((
      SELECT AVG(jumlah) FROM monthly
      WHERE bulan BETWEEN date_trunc('month', '{T_first}'::timestamp) - interval '3 months'
                      AND date_trunc('month', '{T_first}'::timestamp) - interval '1 month'
    ), 0)
  ) AS perkiraan;
```

## 7. Interval

```sql
SELECT
  '{T}'::date AS target_month,
  {forecast_value} AS perkiraan,
  GREATEST({forecast_value} + ROUND({p10_ensemble} * SQRT({H})), {p5_training_volume}) AS lower_80,
  {forecast_value} + ROUND({p90_ensemble} * SQRT({H})) AS upper_80;
```
