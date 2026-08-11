#FORECAST RECIPES - DEPRECATED AFTER ENGINE MIGRATION, ALL CONTENT NOW IN FORECAST GUIDE#

> **This file is no longer loaded by any active skill.** The canonical SQL
> template, series filters, and forbidden-pattern rules now live in
> `context/forecast_guide.md` §1 (Data Source & SQL Template) and §3
> (Eligibility & Series Registry).
>
> Everything previously here (RECIPE-ELIGIBILITY, RECIPE-F1/F2, and the
> deprecated RECIPE-F3–F6 SN+MA3 recipes) described either an eligibility
> gate the engine no longer uses (hardcoded 36-month/300-volume thresholds),
> diagnostics the engine now reports itself (gap/CV/quality label), or a
> pre-AutoETS methodology (SN+MA3) with JOIN/`generate_series` patterns the
> `run_forecast` tool structurally rejects. None of it applies to the
> current ETS-seasonal engine — see `forecast_guide.md` instead.
