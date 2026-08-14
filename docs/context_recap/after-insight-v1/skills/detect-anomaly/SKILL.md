---
name: detect-anomaly
description: "Anomaly detection skill for identifying unusual patterns in pengawasan iklan time series. Detects outliers and explains data irregularities."
tags: [bpom, pengawasan, anomaly]
version: "1.0.0"
---

# Detect Anomaly (Trigger)

Routes BPOM anomaly/outlier questions to `detect_anomaly`. Sibling to
`bpom-pengawasan-forecaster` — same series registry, same SQL contract, but explains
unusual periods instead of projecting future ones.

Load `context/data_architecture.md` first — it has the table inventory, join rules, and traps.
The series registry lives in the forecast skill's documentation.

## CAPTURE
Lock `{sql}`.

- Default table = `mv_pengawasan`. Series not stated = Total Pemeriksaan.
- Build the SQL using the template exactly (table + filter from the series registry).
  If the **series** (not the table) is ambiguous, call `request_clarification` first.
- Use the same exclusions as forecast: `tanggal_mulai >= '2020-01-01'`,
  `nama_upt NOT IN ('DEMO BALAI BESAR', 'DEMO TIPE A')`.

## SQL Template

```sql
SELECT date_trunc('month', tanggal_mulai) AS x,
       COUNT(DISTINCT id)                  AS y
FROM   <table>
WHERE  tanggal_mulai >= '2020-01-01'
  AND  tanggal_mulai < date_trunc('month', CURRENT_DATE)
  AND  nama_upt NOT IN ('DEMO BALAI BESAR', 'DEMO TIPE A')
  AND  <series filter, if any>
GROUP BY 1 ORDER BY 1
```

## RUN
Call `detect_anomaly(sql)`. Do NOT compute or guess anomalies yourself.

- `## Kesalahan` -> SQL issue (forbidden pattern, runtime error) — recheck
  template and retry corrected, don't repeat the same query.
- No anomalies found -> say so plainly, don't invent one.

## PRESENT
Read the tool's markdown and compose prose around it — don't invent a new
structure. State explicitly that flagged periods were **not removed**
from the data — this tool explains, it does not clean. Never show raw
`sigma`/internal field names.

**CSV (Store Contract — one store per question):** `detect_anomaly` does
**not** self-upload (unlike `run_forecast`). If the answer carries data
(flagged periods, trends), call `upload_to_s3` exactly **once** with the
same `sql` you gave to `detect_anomaly`, filename `<series>_historis.csv`.
The export is the turn's FINAL act: after all evidence, immediately before
the answer — never mid-turn.
**Self-check before calling it:** does `upload_to_s3` already appear in
this turn's tool calls? If yes, skip straight to the answer — never twice.
A "no anomalies found" narrative with no data -> skip the export.

## Hard rules
- **Never use `execute_python`** for anomaly scoring — the engine is the
  single deterministic source.
- **Follow-up consistency:** if a follow-up asks about the same series,
  reuse the exact SQL from the prior turn — don't rebuild it.
- **Consistency contract:** the same question re-asked (any session) ->
  same registry SQL -> same flags and numbers; only data drift may differ —
  stamp the as-of date. Every flagged period is reported as its own
  labelled row (period, value, why it stands out).
- If the user also wants a future projection, note that `run_forecast`
  (via `bpom-pengawasan-forecaster`) covers that separately — don't compute a
  forecast from here.
- **Custom series:** if the user requests a filter not in the registry,
  build the SQL from the template with their filter.
