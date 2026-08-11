---
name: detect-anomaly
description: "BPOM-specific trigger for anomaly/outlier detection on a time series. Routes 'apakah ada anomali/data tidak biasa/pencilan/kenapa proyeksi kurang akurat' questions directly to detect_anomaly — does not run the full bpom-analyst pipeline."
tags: [bpom, forecast, anomaly]
version: "1.0.0"
---

# Detect Anomaly (Trigger)

Routes BPOM anomaly/outlier questions to `detect_anomaly`. Sibling to
`bpom-forecaster` — same series registry, same SQL contract, but explains
unusual periods instead of projecting future ones.

Load `context/forecast_guide.md` first — §1 has the SQL template, §3 has
the series registry (table + filter for Total ERBA, BTP, MR/303, MT/302,
Tinggi/301, TinggiNotif/304). **Use §3 to resolve the series — do not run
a live `data_dictionary` lookup for a code already listed there.** §3's
table already tells you which table and filter each risk code maps to;
re-deriving it via the general code-translation protocol wastes the turn
on lookups the registry already answers.

## CAPTURE
Lock `{sql}`.

- Default system = ERBA; series not stated = Permohonan Total.
- Build the SQL from `forecast_guide.md` §1's template + §3's filter for
  the named series.
- Series not in §3 (genuinely novel code, not one of 301/302/303/304) →
  only then fall back to a normal dictionary lookup.
- ERLA request → refuse, offer the ERBA equivalent series.

## RUN
Call `detect_anomaly(sql)`. Do NOT compute or guess anomalies yourself.

- `## Kesalahan` → SQL issue (forbidden pattern, runtime error) — recheck
  against `forecast_guide.md` §1/§3 and retry corrected, don't repeat the
  same query.
- No anomalies found → say so plainly, don't invent one.

## PRESENT
Read the tool's markdown and compose prose around it — don't invent a new
structure. State explicitly that flagged periods were **not removed**
from the data — this tool explains, it does not clean. Never show raw
`sigma`/internal field names.

**CSV:** `detect_anomaly` does **not** self-upload (unlike `run_forecast`).
If anomalies were found (a list of flagged periods, not just "tidak ada
anomali"), call `upload_to_s3` **once** with the same `sql` you gave to
`detect_anomaly` — the underlying series is the analytical data behind
the answer. A "no anomalies found" answer is narrative-only — skip the
export, don't invent something to upload.

## Hard rules
- **Never use `execute_python`** for anomaly scoring — the engine is the
  single deterministic source.
- **Follow-up consistency:** if a follow-up asks about the same series,
  reuse the exact SQL from the prior turn — don't rebuild it.
- If the user also wants a future projection, note that `run_forecast`
  (via `bpom-forecaster`) covers that separately — don't compute a
  forecast from here.
