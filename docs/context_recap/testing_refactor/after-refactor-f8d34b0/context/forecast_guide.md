# Forecast Guide

This file defines the minimum runtime rules for forecasting.
Keep it simple. Forecasting is a separate capability from ordinary analytical Q&A.

## 1. Scope

- Forecast only from ERBA transactional data.
- Use submission/payment time series, not ERLA.
- Use database evidence only. No precomputed forecast table.

Primary sources:

- `warehouse.public.t_produk_3_erba`
- `warehouse.public.t_btp_3_erba`

Time column:

- `tanggal_bayar`

Base history start:

- `2022-09-01`

Exclude test traders:

- `trader_id::bigint NOT IN (5, 17, 50, 85)` for `t_produk_3_erba`
- `trader_id NOT IN (5, 17, 50, 85)` for `t_btp_3_erba`

## 2. What may be forecast

Forecast only process-like monthly series.

Common examples:

- total submissions,
- issued-registration flow if the monthly process is stable enough,
- BTP submission flow,
- stable risk/document sub-series.

Do not treat these examples as the full list. Decide from the data pattern.

## 3. Hard refusal cases

Refuse forecasting when the series is:

- event-driven rather than process-driven,
- too short,
- too sparse,
- or too unstable for a credible projection.

Examples of refusal-style cases:

- revocations,
- exceptional compliance actions,
- one-off operational incidents.

## 4. Eligibility gate

All must pass before forecasting:

- history length >= 36 months
- average monthly volume >= 300 for strong confidence
- series behaves like a recurring process

If history is short:

- refuse forecast,
- tell the user since when the data exists,
- tell roughly when it becomes eligible.

If volume is low:

- forecasting may continue,
- but confidence must be downgraded.

## 5. Method

Use a simple ensemble:

- same-month-last-year (`SN`)
- 3-month moving average (`MA3`)

Weights come from the rolling backtest result, not from memory.

Do not invent weights.

## 6. Backtest gate

Run a 24-month rolling backtest before presenting forecasts.

Quality labels:

- `BAIK` if MAPE <= 15%
- `CUKUP` if 15% < MAPE <= 25%
- `LEMAH` if 25% < MAPE <= 35%
- `TOLAK` if MAPE > 35%

If average monthly volume is below 300, downgrade the label by one level.

If result is `TOLAK`:

- do not forecast,
- present historical trend only,
- state clearly that projection quality is not reliable enough.

## 7. Horizon policy

- default forecast horizon: 3 months
- H=1 strongest
- H=2 to H=3 acceptable
- H=4 to H=6 weak / directional only
- H>12 refuse

## 8. Output rules

- answer in the user's language
- proper nouns and domain terms may stay unchanged
- lead with a short practical summary
- show historical context and projected months
- show confidence as `BAIK` / `CUKUP` / `LEMAH`

Do not show raw internal parameters unless the user explicitly asks for methodology details.

Hide by default:

- sigma
- p10 / p90
- raw residual tables
- ADF / ACF diagnostics
- internal weight formulas

## 9. Simplicity rule

When forecast context and skill conflict, prefer the simpler interpretation that:

- stays faithful to the database,
- keeps the method deterministic,
- and avoids over-explaining internal mechanics to the user.
