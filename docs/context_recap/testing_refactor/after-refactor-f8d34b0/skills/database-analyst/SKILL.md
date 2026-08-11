---
name: database-analyst
description: "Answer business questions from read-only connected databases using deterministic schema discovery and SQL evidence"
tags: [database, connected-source, read-only, business-analysis]
version: "1.3.0"
---

# Database Analyst

Use this workflow when the user asks a business or analytical question and the
project has a connected/read-only database source.

## Principle

Tools stay thin. The skill owns the workflow:

- `list_context_files` / `read_project_file` load hand-written business knowledge
  (glossaries, data quality rules, code resolution guides).
- `list_source_context` / `read_source_context` load generated schema docs
  (column types, table overviews, profiling).
- `list_tables` / `describe_table` discover live schema when needed.
- `execute_sql` runs read-only queries.
- `list_sql_pairs` / `read_sql_pair` / `execute_sql_pair` are reference examples
  for known query patterns — consult when uncertain, not as a mandatory first step.
- `execute_python` is only for statistics/ML/visualization after SQL scopes the
  dataset. A "trend" means a table, not a chart, unless the user asks for a visual.

Do not invent schema. Do not suggest building pipelines unless asked.

For broad executive prompts ("apa yang perlu diperhatikan?", "what should I watch?",
"where should we focus?") — treat as an insight request. Run focused SQL queries
and return priorities, risks, anomalies, and next checks in business language.
Do not describe tool inventory or setup.

## Workflow

1. **Load business context first**
   - Call `list_context_files` to see what's available in `context/`.
   - For BPOM questions, always read:
     - `context/business_glossary.md` — what NIE, permohonan, AMDK, BTP, skala industri mean
     - `context/data_quality_rules.md` — structural correctness rules
     - `context/code_translation_protocol.md` — runtime code binding
     - `context/source_discovery_protocol.md` — runtime discovery for non-trivial business terms
   - For forecast questions, also read `context/forecast_guide.md`.
   - This step is not optional. Context provides reasoning rules; final factual answers
     still must come from executed database evidence.

1.5 **CLARIFY — Ambiguity Gate**

   After loading context, before any schema discovery or SQL, run the ambiguity check.

   Check each dimension of the question against these classes:

   - `ENTITY` — term maps to more than one countable entity type (e.g. "perusahaan" could
     mean produsen, importir, or combined; "produk" could mean NIE or permohonan)
   - `BUSINESS_EVENT` — event term ("aktif", "selesai komitmen", "tidak berlaku", "terbit")
     maps to multiple lifecycle codes in the database; binding changes the row set
   - `SOURCE_PATH` — concept exists in both ERBA and ERLA with different granularity or
     coding; a naive UNION or a system-specific count would produce materially different numbers
   - `EXACT_VS_FAMILY` — term names one exact state or a family (e.g. "disetujui" may mean
     status code 4 only, or codes 4+7, or codes 4+5+7 depending on user intent)
   - `CONCEPT_TYPE` — unclear whether the term is a direct column, a coded concept requiring
     dict lookup, or a discovery-based segment; classification changes the query path
   - `SCOPE` — time window, year, or system scope is absent and different choices would
     materially change the final number

   **DIRECT_EXECUTION** when ALL of the following hold:
   - every dimension above is unambiguously bound from the question alone, OR
   - the same binding was explicitly confirmed in the active conversation topic, OR
   - the remaining uncertainty is cosmetic and would not change the result.
   → Continue to DISCOVER.

   **CLARIFY_FIRST** when any class above applies AND a different interpretation would produce
   a materially different answer:
   1. Run a light dict lookup on `warehouse.public.data_dictionary` to ground the options —
      use `kategori` or `sumber` filters; do NOT run any counting SQL yet.
   2. Form 2–3 concrete options from the lookup result; each option must include a label,
      the underlying code(s), and one-line meaning. Never ask a bare "apa yang dimaksud?".
   3. Set `Clarification Budget: 1` in the Conversation Ledger.
   4. In **gateway / headless mode** → call `request_clarification` with the grounded options.
      In **interactive mode** → call `ask_user` with the same options.
   5. STOP all tool calls for this turn. No further SQL or discovery.

   **When Budget = 0** (clarification already used, or direct execution from the start):
   - Pick the most defensible interpretation from context and dict evidence.
   - State the assumption explicitly in the answer ("Saya asumsikan X karena Y").
   - Continue to DISCOVER.

2. **Discover schema**
   - Call `list_source_context` to find generated schema docs and read relevant files
     (`columns.md`, `overview.md`, `relationships.md`).
   - Call `list_tables` when generated context is absent or needs verification.
   - Call `describe_table` for the most likely fact tables before writing joins or aggregations.
   - Do not query a column until schema or context confirms it exists.
   - Prefer fully-qualified names: `warehouse.public.<table>`.

3. **Query**
   - Write SQL based on what you learned from context and schema.
   - Use `execute_sql(sql="SELECT ...")` — `sql` is the canonical argument.
   - DuckDB syntax: `column ILIKE '%term%'` (not function-style).
   - For nullable/blank text dimensions: `COALESCE(NULLIF(TRIM(CAST(col AS VARCHAR)), ''), 'Unknown')`.
   - Break complex queries into steps: core data first, then code resolution as a follow-up JOIN or query.
   - If a column contains coded values in the result, always resolve them via
     `warehouse.public.data_dictionary` before presenting.
   - SQL pairs in `seeknal/sql_pairs/` are verified reference examples. Consult them
     when you need to verify a query pattern for a known business question, but
     write your own SQL first based on what you understand.

4. **Recover**
   - If a table is missing, call `list_tables` and retry.
   - If a column is missing, call `describe_table` and retry.
   - If a query fails, read the error, fix the SQL, retry up to 3 times.
   - Never give up with "kendala teknis" — a SQL error is a fixable problem.

5. **Answer**
   - Lead with actual numbers from the query result.
   - Resolve all codes to human-readable labels before showing the answer.
   - Explain filters, date range, and any caveats.
   - Suggest 1–3 follow-up questions or analyses.
   - Stop after ~15 tool calls. Answer with caveats if directionally clear.

## Multi-turn behavior

Carry forward discovered table names and query results across turns. When the user
asks "now by region" or "per tahun", reuse the prior table and run only the
additional SQL needed. Do not re-discover what is already known.
