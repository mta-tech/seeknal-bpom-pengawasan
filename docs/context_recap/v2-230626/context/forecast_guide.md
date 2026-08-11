# Forecast Guide — bpom-forecaster

> **Status:** v2.0 — June 2026. Replaces the dropped `forecast_permohonan` table reference.
> All forecasts are computed on-demand from transactional data in `t_produk_3_erba` and `t_btp_3_erba`.
> No pre-computed forecast table is used. This file is loaded in PHASE 0 of `bpom-forecaster`.

---

## §1 Data Source

| Parameter | Value |
|---|---|
| Primary table (pangan olahan) | `warehouse.public.t_produk_3_erba` |
| BTP table | `warehouse.public.t_btp_3_erba` |
| Date column | `tanggal_bayar` (payment / submission date) |
| Baseline start | `'2022-09-01'` (ERBA operational from Sep 2022) |
| Excluded traders | `trader_id::bigint NOT IN (5, 17, 50, 85)` |
| System | ERBA only — ERLA is non-stationary (ADF p=0.94), never forecast |

**Mandatory ERBA casts** (all columns are TEXT in `t_produk_3_erba`):
- `tanggal_bayar::timestamp` — cast required in every query
- `trader_id::bigint` — cast required for exclusion filter
- `t_btp_3_erba` uses native types — no casts needed

**Standard base filter block** (apply in every forecast recipe):
```sql
WHERE tanggal_bayar IS NOT NULL
  AND tanggal_bayar != ''
  AND tanggal_bayar::timestamp >= '2022-09-01'
  AND trader_id::bigint NOT IN (5, 17, 50, 85)
```

---

## §2 Training Window

**Rule:** Use the full ERBA history from 2022-09 through the month before the first target month.

- Full history is preferred over rolling windows because ERBA's early growth phase (2022–2023),
  stabilization (2024), and high-variability period (2025) all contribute to better model calibration.
- `window_end = date_trunc('month', T_first)` (exclusive — first target month)
- `window_start = '2022-09-01'` (fixed, always use full history)

**Structural break detection** (from RECIPE-F2): if avg last 6M / avg prior 6M ratio > 1.30 or < 0.70,
flag the break in Kondisi Data — do not change the training window (the full history still captures it).

---

## §3 Eligibility Criteria

Three conditions must ALL pass before any forecast is computed. Fail on any one → refuse with explanation.

| Criterion | Threshold | Reason |
|---|---|---|
| History length | ≥ 36 months from 2022-09 | Backtest needs 24M; 12M reserve for training stability |
| Average monthly volume | ≥ 300 submissions/month | MAPE becomes unreliable below this threshold |
| Process-driven series | Yes | Event-driven data (revocations, complaints) cannot be forecast |

**Known ineligible by design (always refuse, explain why):**

| Series | Status | Explanation |
|---|---|---|
| NIE Dicabut / revocations | Never eligible | Discrete administrative decisions, not process — MAPE ~660% confirmed |
| Komitmen Dibatalkan | Never eligible | Lifecycle event triggered by regulatory action |
| SLA violations | Never eligible | Derived metric, not a recurring submission pattern |

**Known eligible but gated by history:**

| Series | Status | Note |
|---|---|---|
| TinggiNotif (kategori 304) | Ineligible until ~Mar 2027 | Data starts Mar 2024 = 27 months (threshold: 36M) |

**Eligibility check message templates:**

For insufficient history:
> "Data [series] baru tersedia sejak [bulan/tahun] — baru [N] bulan dari minimum 36 bulan yang dibutuhkan.
> Proyeksi dapat dilakukan mulai [estimated eligible date]."

For event-driven series:
> "Pencabutan NIE adalah keputusan diskretioner, bukan pola administratif rutin yang berulang.
> Data ini tidak mengikuti pola time series yang dapat diprediksi.
> Saya bisa menyajikan tren historis pencabutan sebagai konteks, tanpa proyeksi ke depan."

---

## §4 Method Reference

### Point Forecast

```
SN(T)        = volume for same month in prior year (tanggal_bayar in T - 12 months)
MA3(T)       = average volume of 3 months before T (months T-3, T-2, T-1)
ensemble(T)  = ROUND(w_SN × SN(T) + w_MA3 × MA3(T))
```

**MA3 freeze limitation (H ≥ 2):** For H=1 (one month ahead), MA3 uses 3 actual months.
For H ≥ 2, MA3 cannot recursively include prior forecast values in SQL — it uses the last 3 actual months
as a static anchor. This causes MA3 to freeze. Only SN updates naturally for H ≥ 2.
The ensemble still runs, but the MA3 component is anchored at last known data.
State this in Kondisi Data when H ≥ 2 (⚠ MA3 terkunci di data aktual terakhir untuk H≥2).

### Ensemble Weights (from 24-month backtest)

```
w_SN  = (1 / mae_SN) / (1 / mae_SN + 1 / mae_MA3)
w_MA3 = (1 / mae_MA3) / (1 / mae_SN + 1 / mae_MA3)
```

Weights are read from RECIPE-F3 output. Never hardcode weights — they are always derived from the
backtest result for the specific series and time period.

### Business Floor

```
lower_80_raw   = ensemble(T) + ROUND(p10_ensemble × SQRT(H))
lower_80_floor = GREATEST(lower_80_raw, p5_training_volume)
```

`p5_training_volume` = 5th percentile of monthly volumes in the training window, computed via
`PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY jumlah)` in RECIPE-F3.

The floor prevents lower bounds from being unrealistically negative or zero when training residuals
are computed on higher-volume periods.

### Full Interval Formula

```
σ_H          = sigma_ensemble × SQRT(H)    [pragmatic approximation]
upper_80     = ensemble(T) + ROUND(p90_ensemble × SQRT(H))
lower_80     = GREATEST(ensemble(T) + ROUND(p10_ensemble × SQRT(H)), p5_training_volume)
```

p10 and p90 are empirical percentiles of the ensemble residuals, read from RECIPE-F3.
The √H scaling is a pragmatic approximation valid for H ≤ 6; beyond H=6, uncertainty is substantially
underestimated (state this explicitly in Kondisi Data and Metodologi).

---

## §5 Backtest Gate (24 months)

**Why 24 months:** 12-month backtest was tested and produced biased intervals (p10=+208, all-positive).
24-month window gives bilateral residuals (p10=-744 for Permohonan Total). This is the confirmed fix.

**Backtest window:**
- Evaluation period: 24 months before `date_trunc('month', CURRENT_DATE)`
- Uses RECIPE-F3 (see `forecast_recipes.md`)

### MAPE Gate Thresholds

| MAPE (24M backtest) | Label | Action |
|---|---|---|
| ≤ 15% | BAIK | Proceed — forecast with high confidence |
| 15% – 25% | CUKUP | Proceed — communicate moderate uncertainty |
| 25% – 35% | LEMAH | Proceed — strong caveat, directional use only |
| > 35% | TOLAK | Halt — present historical trend only, no projection |

### Volume-Adjusted Label

If `avg_monthly_vol < 300`, downgrade the label by one tier:
- BAIK → CUKUP
- CUKUP → LEMAH
- LEMAH → TOLAK (halt if already at the boundary)

Reason: small-volume series have high MAPE even when absolute errors are small. The MAPE gate alone
is unreliable; volume adjustment prevents overconfidence in sparse series.

### Validated Simulation Results (2026-06-18, cutoff May 2026)

| Series | Avg Vol | MAPE | Label | w_SN | w_MA3 | σ | p10 | p90 | Floor |
|---|---|---|---|---|---|---|---|---|---|
| Permohonan Total ERBA | 4,170 | 19.1% | CUKUP | 34% | 66% | 1,093 | −1,056 | +1,904 | 1,617 |
| NIE Terbit ERBA | 5,500 | 14.4% | BAIK | 48% | 52% | 867 | −666 | +1,302 | 661 |
| BTP Permohonan ERBA | 127 | 24.4% → CUKUP (vol adj) | CUKUP | 41% | 59% | 45 | −55 | +70 | 56 |
| MR (303) | 1,329 | 12.8% | BAIK | 46% | 54% | 201 | −156 | +304 | — |
| MT (302) | 387 | 25.0% | CUKUP | 36% | 64% | 102 | −142 | +120 | — |
| Tinggi (301) | 3,147 | 28.3% | LEMAH | 34% | 66% | 896 | −917 | +1,309 | — |
| TinggiNotif (304) | 356 | 40.5% | TOLAK | — | — | — | — | — | — |
| Dicabut | 58 | 660% | Never eligible | — | — | — | — | — | — |

---

## §6 Horizon Tiers

| Horizon H | Tingkat Keyakinan | Notes |
|---|---|---|
| H = 1 | Tinggi | Most reliable; MA3 uses 3 actual months |
| H = 2–3 | Sedang | Acceptable; MA3 anchored at last actual |
| H = 4–6 | Rendah | Directional only; √H approximation accumulates error |
| H > 6 | Sangat Rendah | Context orientation only — not for planning |
| H > 12 | Do not forecast | Refuse; explain why |

---

## §7 Series Registry

| Series | Table | Filter | Eligibility | Label | Note |
|---|---|---|---|---|---|
| Permohonan Total ERBA | t_produk_3_erba | no jenis_permohonan filter | Eligible | CUKUP | Primary use case |
| NIE Terbit ERBA | t_produk_3_erba | status IN ('0999','0906','9999'), jenis_permohonan IN ('301','305') | Eligible | BAIK | |
| BTP Permohonan ERBA | t_btp_3_erba | no status filter | Eligible | CUKUP (vol adj) | avg_vol=127 < 300 |
| MR (303) | t_produk_3_erba | kategori_dokumen = '303' | Eligible | BAIK | Most reliable sub-series |
| MT (302) | t_produk_3_erba | kategori_dokumen = '302' | Eligible | CUKUP | Small vol risk; flag caveat |
| Tinggi (301) | t_produk_3_erba | kategori_dokumen = '301' | Eligible | LEMAH | Directional only |
| TinggiNotif (304) | t_produk_3_erba | kategori_dokumen = '304' | Ineligible until ~Mar 2027 | — | 27 months of data |
| NIE Dicabut | t_produk_3_erba | status = '9' (or equivalent) | Never eligible | — | Event-driven |

**Multi-domain rule:** when a question asks about multiple series (e.g. total + sub-series), run the
eligibility pre-check for each series independently. An ineligible sub-series does not block the eligible
total. Present eligible results with their label; explain ineligible series separately.

---

## §8 Output Vocabulary (enforced)

| Technical term | User-facing term |
|---|---|
| Forecast | Proyeksi or Perkiraan |
| 80% confidence interval | Rentang Realistis |
| Horizon tier label | Tingkat Keyakinan |
| MAPE gate result | Kualitas Proyeksi |
| Executive summary | Pesan Utama |
| Interpretation | Apa Artinya? |

**Vocabulary rules:**
- Never use "Forecast" (English) in the output
- "Rentang Realistis" = lower_80 to upper_80 only (never show 95% CI to user)
- "Kualitas Proyeksi: BAIK / CUKUP / LEMAH" — never show MAPE number in Ringkasan
- MAPE number belongs only in Metodologi footer

---

## §9 What Is NEVER Shown to User

These internal statistics are for computation only. They must not appear in any user-facing output
block (Pesan Utama, Ringkasan, Kondisi Data, Historis & Proyeksi, Proyeksi Detail, Apa Artinya?).

| Never show | Reason |
|---|---|
| sigma / σ | Internal computation only |
| p10, p90 | Internal percentile values |
| Lower 95%, Upper 95% | Too wide; not communicated |
| ADF p-value | Technical stationarity test |
| ACF values | Technical autocorrelation analysis |
| n_obs (backtest count) | Internal gate parameter |
| weight_sn, weight_ma3 (raw values) | Show as percentage in Metodologi footer only |

Exception: if user explicitly asks "detail metodologi" or "tampilkan semua parameter", these may
be shown as a separate technical appendix — still clearly labeled as internal parameters.

---

## §10 7-Block Output Format

All forecast outputs must follow this exact structure. The self-check gate at the end of PHASE 6
verifies each block is present before sending.

```
[SERIES NAME] — PROYEKSI
[Month range, e.g. Juli–September 2026]

PESAN UTAMA
[1-2 sentences: direction (naik/turun/stabil) + magnitude (persen atau absolut) +
 whether the projected range is within or outside historical normal]

RINGKASAN
  Rata-rata 3 bulan terakhir   : [value]
  Rata-rata 3 bulan ke depan   : [value]
  Perubahan                    : [+/-X%]
  Kualitas Proyeksi            : [BAIK / CUKUP / LEMAH]

KONDISI DATA
  ✓ atau ⚠ — satu baris per kondisi (tanpa angka teknis)
  Contoh: ✓ Data lengkap — tidak ada gap dalam 24 bulan terakhir
          ✓ Volume cukup — rata-rata [N] permohonan/bulan
          ⚠ MA3 terkunci di data aktual terakhir untuk H≥2 (keterbatasan SQL)
          ⚠ Maret menunjukkan variasi lebih tinggi secara historis

HISTORIS & PROYEKSI
  [Last 12 actual months + separator line + forecast months, in ONE continuous table]

  Mar 2026    4.675
  Apr 2026    6.028
  Mei 2026    5.311
  Jun 2026    5.870
  ────────────────── ← sekarang
  Jul 2026              5.972
  Agu 2026              5.618
  Sep 2026              5.613

  12 bulan historis — Rata-rata: X.XXX | Tertinggi: X.XXX | Terendah: X.XXX

PROYEKSI DETAIL
  Bulan | Perkiraan | Rentang Realistis | Tingkat Keyakinan
  Jul   | 5.972     | 4.916 – 7.876    | Tinggi
  Agu   | 5.618     | 4.506 – 7.618    | Sedang
  Sep   | 5.613     | 4.513 – 7.613    | Sedang

APA ARTINYA?
  - [bullet 1: operational implication — what this means for workload/planning]
  - [bullet 2: direction interpretation — is this normal, high, low?]
  - [bullet 3: uncertainty acknowledgment if CUKUP or LEMAH]
  - [bullet 4-5 optional: sector-specific context if relevant]

METODOLOGI
  Data      ERBA 2022+
  Backtest  MAPE [X]% (24 bulan)
  Metode    [w_SN]% Seasonal Naive · [w_MA3]% MA3
  Interval  Persentil empiris residual × √H
  Catatan   [Any known limitation relevant to this output, e.g. MA3 freeze, March flag]
```

**Unified timeline rule:** Historical and forecast months must appear in ONE continuous table
(block HISTORIS & PROYEKSI), separated by a visual line "────── ← sekarang". Never split into two
separate tables. This is the critical UX design decision — users need one story, not two tables.

---

## §11 Self-Check Gate (run before sending any forecast output)

Before sending the output, verify all 12 items:

```
□ Pesan Utama present (1-2 sentences, direction + magnitude)
□ Ringkasan has Rata-rata 3 bulan terakhir, ke depan, Perubahan, Kualitas Proyeksi
□ Kondisi Data is ✓/⚠ checklist — no raw technical ratios or test statistics
□ Historis & Proyeksi shows 12 actual months (not just summary) in continuous table
□ Separator line "────── ← sekarang" present between historical and forecast
□ Historical summary line present (Rata-rata | Tertinggi | Terendah)
□ Proyeksi Detail uses "Perkiraan", "Rentang Realistis", "Tingkat Keyakinan" columns
□ Apa Artinya? has 2-5 bullets with operational interpretation (not just numbers)
□ Metodologi footer present (Data, Backtest, Metode, Interval, Catatan)
□ No sigma / p10 / p90 / ADF / ACF / n_obs anywhere in user-facing blocks
□ Language matches user's question language (Indonesian or English)
□ If March is a target month: ⚠ March flag present in Kondisi Data or Apa Artinya?
```

---

## §12 Known Biases — Document, Do Not Fix in SQL

These are systematic biases that cannot be corrected within the SQL-only approach. They are documented
so the output communicates them honestly rather than hiding them.

### Limitation 1 — March Effect
All ERBA series show elevated MAPE in March (22–28%). Cause: Q1-end administrative pattern.
**Action:** whenever any target month is March, add to Kondisi Data:
`⚠ Maret menunjukkan variasi lebih tinggi secara historis — perkiraan Maret lebih lebar dari biasanya`
And add to Apa Artinya?:
`- Maret secara historis lebih sulit diprediksi (variasi tahunan lebih besar)`

### Limitation 2 — MA3 Freeze at H ≥ 2
For multi-month forecasts (H=2, 3, etc.), MA3 cannot recursively update with prior forecast values in SQL.
MA3 is anchored at the last 3 actual months. This slightly biases ensemble toward SN for H ≥ 2.
**Action:** add to Kondisi Data:
`⚠ MA3 terkunci di data aktual terakhir untuk H≥2 (keterbatasan SQL rekursif)`

### Limitation 3 — Small Volume Series
For series with avg_vol < 300, even small absolute errors produce high MAPE. The volume-adjusted label
(§5) partially mitigates this, but the fundamental uncertainty is higher.
**Action:** add to Apa Artinya? for CUKUP/LEMAH labels:
`- Volume rendah membuat proyeksi lebih sensitif terhadap fluktuasi bulanan`

### Limitation 4 — 24-Month Backtest Coverage
The backtest uses 24 months of data. For series with shorter histories (or after structural breaks),
the backtest may underestimate true uncertainty. √H approximation also diverges from true uncertainty
for H > 6.
**Action:** for H > 6, add to Metodologi:
`Catatan: σ × √H adalah aproksimasi pragmatis; ketidakpastian aktual lebih besar untuk H > 6`
