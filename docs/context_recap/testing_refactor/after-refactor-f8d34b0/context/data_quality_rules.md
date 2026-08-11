# Data Quality Rules

This file stores structural correctness rules.
It must not become a catalog of business-code answers.

Resolve business codes at runtime through:

- `context/code_translation_protocol.md`
- `context/source_discovery_protocol.md`

## 1. Universal exclusions

### Bad data years

Exclude artifact years from date-based work:

```sql
EXTRACT(YEAR FROM tanggal) NOT IN (1900, 1970)
```

or use bounded date ranges that naturally exclude those artifacts.

### Test accounts

Always exclude known internal/test accounts from production-facing answers.
These exclusions are structural hygiene and may stay hardcoded here.

## 2. Date filtering

Use date ranges, not `EXTRACT`, for year scoping.

Correct:

```sql
WHERE tanggal >= '{Y}-01-01' AND tanggal < '{Y_plus_1}-01-01'
```

Avoid:

```sql
WHERE EXTRACT(YEAR FROM tanggal) = {Y}
```

## 3. Event-first filter discipline

Do not choose status, application-type, or lifecycle filters from memory.

First lock the business event class.
The items below are examples, not an exhaustive list:

- issued registration / license identity,
- application / submission lifecycle,
- commitment / compliance lifecycle,
- amendment / variation / status transition,
- or another explicit operational event found in the data.

Then resolve the exact runtime filters from dictionary or discovery.

Rules:

- different event classes do not share the same filter stack,
- even if two questions sound similar in natural language, they may refer to different operational events,
- commitment-style questions must first decide whether the user asks about an issued identity with a state attached, or a lifecycle event that reached that state,
- If that difference changes the answer materially, clarify before execution.

## 4. Date column discipline

Choose the date column by event, not by habit.

Examples:

- issued registration / license identity -> issuance date column
- application / submission -> payment or application lifecycle date column
- other lifecycle events -> the date column that actually records that lifecycle event

Do not switch date columns just because another column is easier to query.

## 5. Coverage-aware column choice

When more than one column could represent the same concept, choose by usable coverage.

Rules:

- check NULL / blank / placeholder dominance before grouping,
- do not use a low-coverage column as the headline dimension,
- if coverage is still weak, answer with the limitation visible.

## 6. Missing time scope

Do not silently choose a year, all-time, or rolling period when the user did not specify one
and those options would materially change the answer.

Clarify first in that case.

If the active topic already established the time scope explicitly, it may be reused.

## 7. ERBA cast discipline

ERBA often stores operational columns as text.
Use native PostgreSQL casts and guard bad values explicitly.

Examples:

```sql
tanggal::timestamp
tanggal_bayar::timestamp
trader_id::bigint
```

Do not use `TRY_CAST`, `TRY_CONVERT`, or `SAFE_CAST`.

## 8. status_komitmen normalization

`status_komitmen` may mix text forms such as integer-like and float-like values.
Normalize before comparing.

Example:

```sql
ROUND(status_komitmen::numeric)::int::text = '5'
```

This is a structural storage rule; the business meaning of the code is still resolved at runtime.
