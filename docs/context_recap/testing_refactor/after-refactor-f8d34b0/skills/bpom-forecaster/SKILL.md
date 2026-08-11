---
name: bpom-forecaster
description: "Run simple, deterministic ERBA forecasts from transactional data using eligibility check, backtest gate, and SQL-computed ensemble output."
tags: [bpom, forecast, sql-first, time-series]
version: "2.0.0"
---

# BPOM Forecaster

**Workflow:** `LOAD -> CAPTURE -> CHECK -> BACKTEST -> FORECAST -> PRESENT`

Keep forecasting simple.
This skill is for forward-looking projection only, not ordinary historical analysis.

## LOAD

Always load:

- `context/forecast_guide.md`
- `context/forecast_recipes.md`

## CAPTURE

Lock these fields first:

```text
Series:
System:
First target month:
Horizon:
Requested output:
```

Rules:

- default system = ERBA
- default horizon = 3 months
- ERLA forecast requests should be refused and redirected to historical analysis or ERBA forecast comparison

## CHECK

Run, in order:

1. eligibility query
2. diagnostics query
3. monthly history pull

If the series is too short, too sparse, or clearly event-driven:

- stop forecasting,
- explain briefly why,
- offer historical trend instead.

## BACKTEST

Run the 24-month backtest query.

Read and lock:

- `n_obs`
- `pct_weight_sn`
- `pct_weight_ma3`
- `mape_ensemble`
- `sigma_ensemble`
- `p10_ensemble`
- `p90_ensemble`
- `p5_training_volume`

Apply quality gate:

- `BAIK` if MAPE <= 15%
- `CUKUP` if 15% < MAPE <= 25%
- `LEMAH` if 25% < MAPE <= 35%
- `TOLAK` if MAPE > 35%

If average monthly volume is below 300, downgrade the quality by one level.

If final result is `TOLAK`:

- do not forecast,
- return historical trend only,
- state that forecast quality is not reliable enough.

## FORECAST

For each target month:

1. run point forecast query,
2. run interval query,
3. keep the result exactly as returned by SQL.

LLM must not do arithmetic that can change the forecast numbers.

## PRESENT

Write the response in the user's language.
Context language does not control output language.

Recommended output:

1. short headline summary
2. confidence label: `BAIK` / `CUKUP` / `LEMAH`
3. projected months with point forecast
4. realistic range
5. one short methodological caveat when needed

Default caveats to mention only when relevant:

- low volume,
- short history,
- high volatility,
- longer horizon weakness,
- MA3 anchored on last actual months.

Do not dump internal technical parameters unless the user explicitly asks for methodology details.
