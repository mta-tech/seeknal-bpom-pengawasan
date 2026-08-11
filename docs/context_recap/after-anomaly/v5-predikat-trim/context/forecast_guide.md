#FORECAST GUIDE (BPOM-FORECASTER) - ETS HOLT-WINTERS METHOD, SQL TEMPLATES, ELIGIBILITY GATES, AND QUALITY LABELS#

> **v5.0 — 2026-07-10.** Engine: **ETS seasonal (Holt-Winters)** — deliberate tradeoff,
> forecast varies per month at the cost of lower accuracy than a flat median (FC2f r3
> spec). Computed on-demand from `t_produk_3_erba`/`t_btp_3_erba`, no pre-computed table.
> **Consistency is critical:** an inconsistently-built SQL across turns produces a
> visibly different answer, not just a different level — follow §2's reuse rule for
> follow-ups, and the template below exactly for new questions.

## §1 Data Source & SQL Template

| Param | Value |
|---|---|
| Tables | `t_produk_3_erba` (pangan olahan), `t_btp_3_erba` (BTP) |
| Date col | `tanggal_bayar` |
| Baseline | `>= '2022-09-01'` |
| Exclusions | `trader_id::bigint NOT IN (5, 17, 50, 85)` (t_produk_3_erba only) |
| System | ERBA only — ERLA's CV is always too high |

`t_produk_3_erba` columns are TEXT: cast `::timestamp`/`::bigint`. `t_btp_3_erba` is
native, no casts. **Production only, never Neon** (Neon is ~20x smaller, looks
artificially erratic).

```sql
SELECT date_trunc('month', tanggal_bayar::timestamp) AS x,
       COUNT(DISTINCT produk_id)                     AS y
FROM   <table from §3>
WHERE  tanggal_bayar::timestamp >= '2022-09-01'
  AND  trader_id::bigint NOT IN (5, 17, 50, 85)      -- t_produk_3_erba only
  AND  <series filter from §3, if any>
  AND  tanggal_bayar::timestamp < date_trunc('month', CURRENT_DATE)
GROUP BY 1 ORDER BY 1
```

Default Y = `COUNT(DISTINCT produk_id)`; use `COUNT(*)` only if the user says
"jumlah transaksi/record". Default grain = monthly. No JOINs, no
`generate_series`, no recursive CTE (tool rejects these). Univariate only.

## §2 Method — ETS Seasonal, Deterministic

Single fit (trend + seasonal, `seasonal_periods=12`) on an adaptive window (24
or 36 months — needs ≥24 for seasonal at all), forecast natively — never
recursive self-append. Same input → same output, always. Point **varies per
month** (intentional, see §6). Bounds: `sigma * sqrt(min(h,2))`, z=1.2816
(80%)/1.9600 (95%) — widens period 1→2, then flat. Never show `sigma`,
`sub_type`, or raw field names; say "Rentang Realistis" (80%) / "Rentang
Ekstrem" (95%).

**Follow-up consistency:** same series, different horizon/clarifying question
→ reuse the prior turn's exact SQL, don't rebuild it. Rebuilding risks a
different-but-"valid" query and a visibly different answer for what the user
considers the same question. Only rebuild for an explicitly different
series/grain/filter.

## §3 Eligibility & Series Registry

Refuse if history < 10 periods or CV > 0.8. Volume alone never refuses — it
widens the range and lowers the quality label instead.

| Series | Table | Filter |
|---|---|---|
| Total ERBA | t_produk_3_erba | none |
| NIE Terbit | t_produk_3_erba | status IN ('0999','0906','9999'), jenis_permohonan IN ('301','305') |
| BTP ERBA | t_btp_3_erba | none |
| MR (303) / MT (302) / Tinggi (301) / TinggiNotif (304) | t_produk_3_erba | kategori_dokumen = '303'/'302'/'301'/'304' |

**Never eligible** (CV always too high, event-driven not recurring): ERLA
(any), NIE Dicabut, Komitmen Dibatalkan. Multi-series question → check each
independently; one ineligible sub-series doesn't block an eligible one.

## §4 Quality Label (walk-forward backtest MAPE)

| MAPE | Label | Keyakinan |
|---|---|---|
| ≤15% | BAIK | Tinggi |
| 15–25% | CUKUP | Sedang |
| 25–35% | LEMAH | Rendah — anomaly auto-attached |
| >35% | TOLAK | Rendah, strong warning — anomaly auto-attached |
| n/a | UNKNOWN | Sedang — don't overstate either way |

One label for the whole projection (MAPE is one number for the fit), even
though the point varies by month.

## §5 Output & Limitations

Read `run_forecast`'s markdown and compose prose around it, don't invent a new
structure. Never say "Forecast" (use "Proyeksi"), never show raw CV/`sigma`/
`sub_type`/`modified_z`/MAD or `window_selection` internals — a one-line
Metodologi summary is enough unless the user asks for detail.

- Seasonal shape isn't guaranteed correct — a historically-high month may not
  be high this year; the quality label is the honest trust signal, shape included.
- March historically shows elevated error for ERBA — flag when it's a target month.
- Bounds cap at h=2, don't keep widening — validated, not a shortcut.
- **CSV Store Contract:** one question = one stored CSV = the data behind the
  answer. `run_forecast`'s auto-uploaded projection CSV is tool-owned and does
  not count; the agent's single export is the historical series SQL (several
  series → one SQL with a series label column). The 36-step horizon cap is
  silent in the tool — stating it in the answer is the agent's job.
- **Transparency & consistency (general):** every projected period appears as
  its own row (point + bounds); multi-series → per-series labelled blocks; the
  CSVs cover the same full horizon as the answer. Same question, same series,
  same horizon → identical numbers in any session (deterministic engine);
  the only legitimate difference is data drift — stamp the as-of date.

## §6 Anomaly Detection (separate tool, awareness only)

`detect_anomaly(sql)` — same 2-column contract, never removes data, never
forecasts. Auto-fires when a forecast's MAPE > 25%; or on direct request
("apakah ada anomali..."). Always state flagged points were **not removed**.
