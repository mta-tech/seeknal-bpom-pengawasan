---
name: business-question-answering
description: "Strategic business analysis skill for questions about opportunities, priorities, and recommendations. Translates business concepts into actionable insights."
tags: [business, metrics, recommendation, analysis]
version: "1.0.0"
---

# Business Question Answering

Use this workflow for questions like "where is revenue strongest?", "what are
the opportunities?", "which segment should we prioritize?", or "what changed?".

## Workflow

1. **Clarify silently when possible**
   - Infer likely metric, dimension, grain, and time window from available schema and context.
   - Ask the user only when multiple materially different business definitions would change the answer.

2. **Get evidence**
   - If the data lives in a connected database, load `database-analyst` and use `list_tables`/`describe_table`/`execute_sql`.
   - Before writing ad-hoc SQL, always call `list_sql_pairs` to check if an authoritative SQL pair already exists for the question.
   - **IMPORTANT:** `list_sql_pairs` returns a file-level preview only. You MUST call `read_sql_pair` for each potentially relevant file to inspect ALL individual pairs before concluding there is no match.
   - When a SQL pair matches the user's question (by intent or semantic similarity), you MUST call `execute_sql_pair` to run the pair's SQL as-is. Do NOT rewrite or substitute columns from the pair.
   - Only fall back to `execute_sql` when no matching SQL pair exists.
   - Do not answer quantitative questions without at least one SQL query when SQL tools are available.

3. **Validate**
   - Run a total/check query when recommendations depend on shares or rankings.
   - Compare at least two cuts when the user asks for opportunities, e.g. segment and region, or current and prior period.

4. **Recommend**
   - Separate facts from interpretation.
   - Tie every recommendation to a number from the query result.
   - Include a caveat ONLY when it materially affects the result (sample size, filters, grain, partial current year). Do NOT narrate transient connection/tool errors you recovered from.

## Output shape

Use this compact structure unless the user asks otherwise:

1. **Answer** — one sentence with the main finding.
2. **Evidence** — a small table with actual numbers (preferred for per-row values), or short bullets.
3. **Recommendation** — 1–3 actions.
4. **Caveat / next check** — one line, ONLY if it materially affects the result (omit it for transient errors you recovered from).

**Formatting:** use `-` for bullets (NEVER `*` — it collides with bold/italic and breaks table rendering). A table must stand alone with a blank line before and after; do NOT place a bullet/bold line directly adjacent to a table, and do NOT duplicate table contents as bullets.
