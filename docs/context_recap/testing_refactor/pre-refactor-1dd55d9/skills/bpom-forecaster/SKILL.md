---
name: bpom-forecaster
description: "Compute on-demand ERBA submission forecasts: eligibility check, 24-month backtest gate, SN+MA3 ensemble, business floor intervals, and 7-block output. Use when OPERATION = FORECAST. Never invoke for retrospective data questions — those go to bpom-analyst."
tags: [bpom, forecast, sql-first, time-series, orchestration]
version: "1.0.0"
---

# BPOM Forecaster — Orchestrator

**Workflow:** PHASE 0 → PHASE 1 → PHASE 2 → PHASE 2.5 → PHASE 3 → PHASE 4 → PHASE 5 → PHASE 6

This skill directs the thinking flow for BPOM forecasting questions. Its goal is to produce
**consistent, deterministic, honest** projections — same data = same numbers, always.

**Core principle:** LLM never computes numbers. All arithmetic runs in SQL. LLM reads SQL output
columns and formats them into the 7-block output. This is what guarantees determinism.

---

## PHASE 0 — MANDATORY CONTEXT LOAD (before anything else)

**This step is NOT optional.** Load these files unconditionally before PHASE 1:

```
read_project_file('context/forecast_guide.md')
read_project_file('context/forecast_recipes.md')
```

These files contain: data source rules, eligibility thresholds, method formulas, backtest specs,
interval formula with business floor, horizon tiers, output vocabulary, never-show list,
7-block format specification, SQL templates (RECIPE-ELIGIBILITY through RECIPE-F6).

Proceeding without Phase 0 will produce inconsistent or wrong forecasts. There are no exceptions.

---

## PHASE 1 — CAPTURE (understand the forecast request)

1. **Extract four components from the question:**

   ```
   ENTITY:       [permohonan / NIE Terbit / BTP / sub-series: MR/MT/Tinggi]
   TIME_SCOPE:   [N months ahead — default 3 if not stated]
   SYSTEM:       [ERBA only — ERLA is never forecast; default ERBA if not stated]
   SERIES:       [which specific series — see Series Registry in forecast_guide.md §7]
   ```

2. **ERLA branch — refuse + offer alternative:**
   If user asks to forecast ERLA data:
   > "Data ERLA tidak memiliki pola musiman yang stabil dan tidak dapat diforecast dengan andal.
   > Saya bisa menyajikan (a) proyeksi ERBA sebagai perbandingan, dan/atau (b) tren historis ERLA.
   > Mana yang lebih membantu?"

3. **Default scope:**
   - SYSTEM not stated → ERBA only
   - TIME_SCOPE not stated → 3 months (H=1, H=2, H=3)
   - ENTITY not stated → Permohonan Total ERBA
   - Never assume a start year — training window is always full ERBA history from 2022-09

4. **Emit the Forecast Commitment Block before any SQL:**

   ```
   Forecast Scope:
     Entity      : [series name]
     Table       : [t_produk_3_erba or t_btp_3_erba]
     Series Filter: [filter clause from forecast_guide.md §7 or 'none' for total]
     T_first     : [first target month as YYYY-MM-01]
     Horizons    : H=1 to H=[N]
     Target months: [e.g. Jul 2026, Aug 2026, Sep 2026]
   ```

---

## PHASE 2 — DATA CONDITION CHECK

Run RECIPE-F2 with `{T_first}` substituted. Read all 7 output columns.

**Translate results into Kondisi Data checklist entries (save for PHASE 6):**

| Condition | ✓ / ⚠ text |
|---|---|
| gap_months = 0 | ✓ Data lengkap — tidak ada gap dalam 12 bulan terakhir |
| gap_months > 0 | ⚠ Terdapat [N] bulan dengan volume nol — data mungkin tidak lengkap |
| 0.70 ≤ break_ratio ≤ 1.30 | ✓ Volume relatif stabil dalam 6 bulan terakhir |
| break_ratio < 0.70 | ⚠ Penurunan signifikan terdeteksi — 6 bulan terakhir vs 6 bulan sebelumnya |
| break_ratio > 1.30 | ⚠ Kenaikan signifikan terdeteksi — 6 bulan terakhir vs 6 bulan sebelumnya |
| cv_12m ≤ 0.50 | ✓ Volatilitas dalam batas normal |
| cv_12m > 0.50 | ⚠ Volatilitas tinggi — rentang proyeksi akan lebih lebar |

**Do NOT show raw numbers** (break_ratio values, CV values) in Kondisi Data. Translate to plain language.

---

## PHASE 2.5 — ELIGIBILITY PRE-CHECK

Run RECIPE-ELIGIBILITY with `{T_first}` substituted. This gate must pass before running any backtest.

**Gate logic:**

```
n_months_history < 36 → HALT
  → Message: "Data [series] baru tersedia sejak [earliest_month] —
              baru [n_months_history] bulan dari minimum 36 bulan yang dibutuhkan.
              Proyeksi dapat dilakukan mulai [estimated eligible date]."

avg_monthly_vol < 300 → FLAG for volume-adjusted label
  → Continue to PHASE 3, but mark: APPLY_VOL_ADJUSTMENT = TRUE

Both OK → continue to PHASE 3
```

**Special-case messages (do not rely on the gate result alone — check series identity):**

For TinggiNotif (kategori 304):
> "Data Tinggi Notifikasi baru tersedia sejak Maret 2024 — baru 27 bulan dari minimum 36 bulan
> yang dibutuhkan. Proyeksi dapat dilakukan mulai sekitar Maret 2027."

For Dicabut / NIE revocations:
> "Pencabutan NIE adalah keputusan diskretioner berdasarkan temuan pengawasan, bukan proses
> administratif rutin yang berulang. Data ini tidak mengikuti pola time series.
> Saya bisa menyajikan tren historis pencabutan sebagai informasi konteks."

---

## PHASE 3 — BACKTEST GATE (24-Month Rolling Evaluation)

Run RECIPE-F3 with `{T_first}` and `{series_filter}` substituted.

**Read and lock all 9 values from SQL output:**

```
Backtest Lock:
  n_obs              : [from SQL]
  pct_weight_sn      : [from SQL — e.g. 34]
  pct_weight_ma3     : [from SQL — e.g. 66]
  mape_ensemble      : [from SQL — e.g. 19.1]
  mae_ensemble       : [from SQL]
  sigma_ensemble     : [from SQL]
  p10_ensemble       : [from SQL — e.g. -1056]
  p90_ensemble       : [from SQL — e.g. 1904]
  p5_training_volume : [from SQL — the business floor]
```

**These 9 values are LOCKED for the session.** Never recompute or re-estimate them.
Never substitute different values in later phases.

**Apply MAPE gate:**

```
IF APPLY_VOL_ADJUSTMENT = TRUE:
  → Downgrade label by one tier before applying gate:
    raw_mape ≤ 15% → label CUKUP (not BAIK)
    raw_mape 15-25% → label LEMAH (not CUKUP)
    raw_mape 25-35% → label TOLAK (halt)
    raw_mape > 35%  → label TOLAK (halt)
ELSE:
  raw_mape ≤ 15%  → BAIK  → proceed
  raw_mape 15-25% → CUKUP → proceed
  raw_mape 25-35% → LEMAH → proceed with strong caveat
  raw_mape > 35%  → TOLAK → HALT

IF TOLAK:
  → Present historical data only (RECIPE-F1 output)
  → Explain: "Akurasi backtest [mape]% melebihi ambang batas 35%.
              Data terlalu volatil untuk proyeksi yang andal saat ini.
              Berikut data historis untuk konteks."
  → Do NOT show Proyeksi Detail or Rentang Realistis
  → STOP: do not run PHASE 4 or PHASE 5
```

**March flag detection:**
Check if any target month is March (month = 3). If yes, save for PHASE 6:
`MARCH_FLAG = TRUE`

**n_obs warning:**
If `n_obs < 18`, add to Kondisi Data: ⚠ Backtest hanya [n_obs] bulan — selang lebih lebar dari biasanya

---

## PHASE 4 — COMPUTE POINT FORECASTS

For each target month T (H=1 to N), run RECIPE-F4 with actual weight values substituted.

**Critical rule:** Substitute the actual integer values from the Backtest Lock into the SQL.
Do NOT use `{pct_weight_sn}` as a literal placeholder in the executed query — substitute the real number.

Example: if `pct_weight_sn = 34` and `pct_weight_ma3 = 66`, the SQL must contain `(34 / 100.0) * sn`.

**Plausibility check after each H:**
- If ensemble_forecast < 0 → flag anomaly, check data
- If ensemble_forecast > 3 × avg_monthly_vol (from RECIPE-ELIGIBILITY) → flag anomaly
- Never suppress or adjust the SQL result — report the anomaly, then show the number

**MA3 freeze note:**
For H = 1: MA3 uses 3 actual months — fully current.
For H ≥ 2: MA3 is anchored at last 3 actual months before T_first (does not update).
Add to Kondisi Data when H ≥ 2:
`⚠ MA3 terkunci di data aktual terakhir untuk H≥2 (keterbatasan SQL rekursif)`

---

## PHASE 5 — COMPUTE INTERVALS AND QUARTERLY AGGREGATE

Run RECIPE-F6 with all Backtest Lock values substituted.

**Read from SQL output:**
- `perkiraan` — point forecast
- `lower_80` — lower bound with business floor applied
- `upper_80` — upper bound
- `tingkat_keyakinan` — horizon tier label from SQL

**Quarterly aggregate (primary output):**
```
Q_perkiraan = SUM of perkiraan for all H in the quarter
Q_lower     = SUM of lower_80 for all H (approximate — assumes independence)
Q_upper     = SUM of upper_80 for all H
```

The quarterly view is primary. Monthly detail is secondary (Proyeksi Detail block).

**3-Month summary for Ringkasan block:**
```
avg_historis_3m = average of last 3 actual months (from RECIPE-F1)
avg_proyeksi_3m = average of perkiraan for H=1,2,3
pct_change      = ROUND((avg_proyeksi_3m - avg_historis_3m) / avg_historis_3m * 100, 1)
```

---

## PHASE 6 — PRESENT (7-Block Output)

**Communication Alignment — apply before writing any output:**
- Detect user's language (Indonesian or English). Write the entire response in that language.
- Context files are English working tools — they do NOT determine output language.
- Keep unchanged: ERBA, ERLA, BPOM, NIE, BTP, AMDK, MR, MT (system and risk codes are proper nouns).

**Self-check gate — run before sending (12 items from forecast_guide.md §11):**
Verify all 12 items are present. If any is missing, add it before sending.

**Complete the 7-block structure in this exact order:**

---

### Block 1 — Header

```
[SERIES NAME] — PROYEKSI
[First target month] – [Last target month, e.g. Juli–September 2026]
```

---

### Block 2 — PESAN UTAMA

1-2 sentences. Must cover:
- Direction: apakah naik, turun, atau stabil vs 3 bulan terakhir?
- Magnitude: berapa persen perubahannya?
- Context: apakah dalam rentang historis normal atau di luar?

Example:
> "Permohonan ERBA diperkirakan relatif stabil dalam tiga bulan ke depan (+7.5% dibanding rata-rata
> triwulan sebelumnya), masih dalam rentang historis 12 bulan terakhir."

---

### Block 3 — RINGKASAN

```
RINGKASAN
  Rata-rata 3 bulan terakhir   : [value from RECIPE-F1 last 3 months average]
  Rata-rata 3 bulan ke depan   : [avg_proyeksi_3m from PHASE 5]
  Perubahan                    : [pct_change from PHASE 5, with + or - sign]
  Kualitas Proyeksi            : [BAIK / CUKUP / LEMAH — from PHASE 3 gate result]
```

Never show: MAPE number, sigma, p10, p90 in this block.

---

### Block 4 — KONDISI DATA

```
KONDISI DATA
  [checklist items from PHASE 2 + any flags from PHASE 3]
```

Add if applicable:
- ⚠ MA3 terkunci di data aktual terakhir untuk H≥2 (when H ≥ 2)
- ⚠ Maret menunjukkan variasi lebih tinggi secara historis (when MARCH_FLAG = TRUE)
- ⚠ Backtest coverage kurang dari 18 bulan (when n_obs < 18)
- ⚠ Volume bulanan di bawah 300 — proyeksi lebih sensitif terhadap fluktuasi (when vol_adjustment)

**No raw numbers in this block.** Translate everything to plain language.

---

### Block 5 — HISTORIS & PROYEKSI (unified timeline)

Show last 12 actual months from RECIPE-F1, then the separator, then all forecast months.
ONE continuous table — never two separate tables.

```
HISTORIS & PROYEKSI
  [Month -12]    [jumlah]
  [Month -11]    [jumlah]
  ...
  [Month -1]     [jumlah]       ← last known month
  ────────────────── ← sekarang
  [Target H=1]              [perkiraan H=1]
  [Target H=2]              [perkiraan H=2]
  [Target H=3]              [perkiraan H=3]

  12 bulan historis — Rata-rata: [avg] | Tertinggi: [max] | Terendah: [min]
```

Format: use right-aligned numbers. Historical values in left column, forecasts in right column.
Month format: "Jul 2026" (abbreviated month + year). Separator line: "──────────────────".

---

### Block 6 — PROYEKSI DETAIL

```
PROYEKSI DETAIL
  Bulan  | Perkiraan | Rentang Realistis   | Tingkat Keyakinan
  -------+-----------+---------------------+------------------
  [Mon]  | [value]   | [lower] – [upper]   | [Tinggi/Sedang/Rendah]
  ...

  Catatan Quarterly: Q total diperkirakan [sum_perkiraan] (rentang [sum_lower] – [sum_upper])
```

If label is LEMAH, add after the table:
> "⚠ Kualitas proyeksi LEMAH — gunakan rentang realistis, bukan angka perkiraan, untuk perencanaan."

---

### Block 7 — APA ARTINYA?

2-5 bullets. Each bullet is a business interpretation, not a technical statement.

Required bullets:
- Direction and magnitude in operational terms (what does +7.5% mean for workload?)
- Whether forecast is within or outside historical norm
- If CUKUP or LEMAH: acknowledgment of uncertainty in plain language
- If MARCH_FLAG: note on March variability

Optional bullets:
- Sector-specific context (if relevant sub-series)
- Comparison to prior quarter if relevant

Example:
```
APA ARTINYA?
  - Volume permohonan diperkirakan sedikit meningkat, konsisten dengan pertumbuhan ERBA tahun ini
  - Proyeksi masih dalam rentang historis — tidak ada lonjakan atau penurunan ekstrem yang diperkirakan
  - Kualitas proyeksi CUKUP — angka ini sebaiknya digunakan sebagai orientasi, bukan target pasti
```

---

### Block 8 — METODOLOGI

```
METODOLOGI
  Data      ERBA 2022+
  Backtest  MAPE [mape_ensemble]% (24 bulan)
  Metode    [pct_weight_sn]% Seasonal Naive · [pct_weight_ma3]% MA3
  Interval  Persentil empiris residual × √H
  Catatan   [relevant limitation — MA3 freeze if H≥2; March if MARCH_FLAG; etc.]
```

This is the only block where MAPE, weight percentages, and √H can be shown.

---

## Honesty Principles (non-negotiable)

- Every forecast number must trace to SQL output from RECIPE-F4, RECIPE-F5, or RECIPE-F6.
  Never compute a forecast by recalling values, interpolating, or guessing from context.
- Same data = same answer. If a number changes across sessions with identical data, there is a bug
  in the pipeline — report the inconsistency, do not paper over it.
- If a series is ineligible, say so clearly with the reason. Do not produce a "rough estimate"
  for an ineligible series.
- If the MAPE gate returns TOLAK, present historical data honestly without a forecast.
  Never produce a forecast for a TOLAK series.
- The business floor (GREATEST) may make the lower bound higher than the raw p10 result.
  This is correct behavior — state "Rentang Realistis" is floored at the 5th percentile of
  training volume; do not hide this adjustment.
- If any SQL query errors or returns unexpected NULL for SN/MA3 (e.g. no data for that month last year),
  report what happened honestly. Do not fabricate a substitute value.
