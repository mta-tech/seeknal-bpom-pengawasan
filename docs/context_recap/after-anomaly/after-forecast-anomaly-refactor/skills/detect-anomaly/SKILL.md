---
name: detect-anomaly
description: "Anomaly detection skill for identifying unusual patterns in registration time series. Detects outliers and explains data irregularities."
tags: [bpom, forecast, anomaly]
version: "1.1.0"
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

**CSV (Store Contract — one store per question):** `detect_anomaly` does
**not** self-upload (unlike `run_forecast`). If the answer carries data
(flagged periods, trends), call `upload_to_s3` exactly **once** with the
same `sql` you gave to `detect_anomaly` (several series → one SQL with a
series label column), filename `<series>_historis.csv` — the underlying
series is the data behind the answer. The export is the turn's FINAL act:
after all evidence, immediately before the answer — never mid-turn.
**Self-check before calling it:** does `upload_to_s3` already appear in
this turn's tool calls? If yes, skip straight to the answer — never twice.
A "no anomalies found" narrative
with no data → skip the export, don't invent something to upload. Flagged
points live in the tool's markdown and cannot be exported without an
engine change — never re-type them into `data=`/`columns=`.

## Hard rules
- **Never use `execute_python`** for anomaly scoring — the engine is the
  single deterministic source.
- **Follow-up consistency:** if a follow-up asks about the same series,
  reuse the exact SQL from the prior turn — don't rebuild it.
- **Consistency contract:** the same question re-asked (any session) →
  same registry SQL → same flags and numbers; only data drift may differ —
  stamp the as-of date. Every flagged period is reported as its own
  labelled row (period, value, why it stands out).
- If the user also wants a future projection, note that `run_forecast`
  (via `bpom-forecaster`) covers that separately — don't compute a
  forecast from here.
