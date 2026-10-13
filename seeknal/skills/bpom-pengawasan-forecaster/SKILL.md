---
name: bpom-pengawasan-forecaster
description: "Forecasting skill for predicting future trends from the pengawasan iklan time series (fact_pengawasan). Deterministic projections via the IBA engine."
tags: [bpom, pengawasan, forecast, nasional]
version: "1.1.0"
---

# BPOM Pengawasan Forecaster (nasional — semua balai)

Routes BPOM forecast requests to `run_forecast`. This skill owns only the CAPTURE parameters — all
compute is deterministic (ETS seasonal fit inside the IBA forecast engine). The LLM does **no**
forecast arithmetic.

Load `context/00-menghitung.md` first — entity, grain, and join rules. This file covers only the
tool workflow.

## CAPTURE

Lock `{sql, periods}`.

- Default table = `public.fact_pengawasan` — akun mencakup semua balai;
  filter `balai_id` bila user menanyakan balai tertentu.
- Series not stated = Total Pengawasan (event).
- **Horizon translation:** `periods` is a step count on the SQL's own grain —
  monthly: 6 bulan -> 6, 1 tahun -> 12, 3 tahun -> 36, 5 tahun -> 60 -> capped.
  Cap at 36; the tool clamps silently, so when the request exceeds it, SAY in
  the answer that 36 months is the maximum supported horizon and present those.
- **"hingga/sampai {X}"** = every step from the period after the last actual
  **through the end of X** — the intermediate periods are part of the request.
  **Always pass `periods` explicitly** — the tool defaults to 3 when omitted.
- **"bulan depan" / "next month"** = the next **COMPLETE** month — i.e. the month
  AFTER the current running month, not the first forecast step. E.g. data complete
  through June + July running -> first step = Juli, **"bulan depan" = Agustus**.
  So use `periods >= 2` and name that complete month (Agustus) as the answer's target.
- Build the SQL using the template exactly (table + filter). If the **series** is
  ambiguous, call `ask_clarification` first.

## SQL Template

```sql
SELECT date_trunc('month', tgl_start) AS x,
       COUNT(DISTINCT id)             AS y
FROM   public.fact_pengawasan
WHERE  tgl_start >= '2020-01-01'
  AND  tgl_start < date_trunc('month', CURRENT_DATE)
  AND  <series filter, if any>
GROUP BY 1 ORDER BY 1
```

Default Y = `COUNT(DISTINCT id)`. Default grain = monthly. No JOINs, no
`generate_series`, no recursive CTE (tool rejects these). Univariate only.

**Date column:** `tgl_start` — tanggal kanonik kegiatan. Jangan memakai `created_at`
kecuali pertanyaannya memang tentang jeda input data. Bound the date range explicitly on `tgl_start`
(kolom ini bisa memuat tanggal jadwal di masa depan).

**Semua balai termasuk unit PUSAT ada di fakta** — pertanyaan per-balai wajib filter `balai_id`;
baris DEMO sudah dibersihkan di sumber.

## Series Registry

| Series | Filter (pada kolom fakta — tanpa JOIN) |
|---|---|
| Total Pengawasan | none |
| Pengawasan TMK (pusat) | `kesimpulan_pusat_id IN (2,3,4,5)` — keluarga TMK; resolve ID kamus di query terpisah, jangan hafal |
| Pengawasan MK (pusat) | `kesimpulan_pusat_id = 1` |
| Pengawasan per kategori produk | `kategori = '<value>'` — nilai dari kolom, bukan dari domain lain |
| Pengawasan per jenis media (kasar) | `jenis_iklan_id = <id>` — resolve id via `dim_pengawasan_jenis_iklan` di query terpisah |

Ketidaksesuaian per bulan **tidak didukung** — butuh JOIN ke bridge, dan tool menolak JOIN.

⚠️ **Count events (`COUNT(DISTINCT id)`).** View ini 1 baris = 1 event, tetapi tetap sebutkan entity
di jawaban. Untuk series berbasis vonis: **keluarkan NULL** (`kesimpulan_pusat_id IS NOT NULL`) dan
sebutkan porsinya — review Pusat parsial, tanpa itu tren terbaca menurun palsu.

## RUN

Call `run_forecast(sql, periods)`. Do NOT compute forecast numbers yourself.

- **After a clarification is answered (user picks a scope):** call `run_forecast`
  FRESH this turn for the resolved scope. The forecast numbers in your answer MUST
  come from a `run_forecast` result produced **this turn** — NEVER restate/quote
  numbers from a previous turn's answer or the conversation history.
- `## Kesalahan` with "policy check (STEP 0.5)" -> SQL has a JOIN/
  `generate_series`/recursive CTE — rebuild flat per the template, don't retry the same pattern.
- `## Kesalahan` with "STEP 1: EXECUTE" -> runtime error — recheck template and retry corrected.
- `## Ditolak` -> present the engine's reason (usually insufficient history),
  offer historical trend instead; don't retry unless the request changes.

## PRESENT

Read the tool's markdown and compose prose around it — don't invent a new
structure. Lead with the quality label. Follow the forecast guide for
vocabulary (never show raw `sigma`/`sub_type`/field names/CV number).

**Present the full computed horizon.** Every predicted period the tool returned
appears in the answer — never truncate to the first months or to the named
year only.

**The Answer Contract applies to forecasts too (transparency, general).**
Every projected period is its own row (point + Rentang Realistis); the
tool's history block is presented in full alongside the projection, never
dropped; multiple series -> per-series labelled sections (code + description
per series). The stored CSV (tool-owned, combined) covers exactly
the horizon presented: all historical periods (`kind=historis`) AND all
projected periods (`kind=proyeksi-*`) in one file. When the request exceeds the 36-step cap,
the answer AND the export presentation both state "36 bulan (maksimum yang
didukung)" — never silently deliver less than asked.

**Anomaly:** if the tool's markdown has an `## Anomali` block, include it
and state the points were **not removed**. If the user asks about
anomalies directly, call `detect_anomaly(sql)` yourself (works whether or
not a forecast ran this turn) — see the anomaly skill.

**CSV (Store Contract — one combined store per question):** on a SUCCESSFUL
forecast, `run_forecast` self-uploads ONE combined CSV — historical + projection
together. **Do NOT call `upload_to_s3` yourself on a successful forecast.**
Only when the forecast was **refused/failed** and you fall back to a
historical-trend answer may you export the history via `upload_to_s3`.
Multi-series (each its own `run_forecast`) -> each call self-uploads its
own combined CSV. Never `data=`/`columns=`. Never paste the raw URL.

## Stock vs Flow

| Question pattern | Kind | Y expression |
|---|---|---|
| "pengawasan **baru**/selesai per bulan" | flow | `COUNT(DISTINCT id)` |
| "total pengawasan **akumulasi**" | stock | `SUM(COUNT(DISTINCT id)) OVER (ORDER BY date_trunc(...))` |

For stock queries, the fit may show some upward drift but doesn't
reliably track a real cumulative total's growth rate — say so.

## Hard rules

- **Never use `execute_python` for forecast arithmetic.** LLM-generated
  Python varies per turn -> inconsistent numbers for the same question.
  `run_forecast` is the single deterministic source.
- **Follow-up consistency:** if a follow-up asks about the same series
  (different horizon, clarifying question), reuse the exact SQL from the
  prior turn — don't rebuild it from scratch.
- **If the projection ran but its chart did not render**, the numbers still
  stand: present the full projection in words and note the chart could not be
  shown — never re-run `run_forecast` just to force the visual.
- **Same question -> same SQL:** resolve the series from the registry exactly
  (same wording -> same registry row, no improvised filters).
- **Consistency contract:** the same question (same series, grain, horizon)
  MUST produce the same numbers in any session and in follow-ups — the
  engine is deterministic, so any difference means you built a different
  SQL or `periods`. Resolve from the registry verbatim, pass `periods`
  explicitly, and for follow-ups reuse the prior turn's exact SQL.
- **Custom series:** if the user requests a filter not in the registry,
  build the SQL from the template with their filter. Document the filter
  in the answer so it can be reproduced.
