# Data Architecture

This file teaches structural topology, not business answers.

## 1. Domain boundaries

- Registration-style questions often live in ERBA/ERLA product and BTP tables.
- Forecast-style questions use `forecast_permohonan`.
- Supervision / inspection / sampling data is not connected here.

If the asked domain is not present in the connected database, say so clearly.

## 2. Core topology

Logical relations are known semantically, not enforced by foreign keys.

```text
ERBA product/BTP facts  -> trader master ERBA
ERLA product/BTP facts  -> trader master ERLA
fact coded columns      -> data_dictionary
```

Primary identities:

- `nomor` = issued registration / NIE identity
- `produk_id` = application identity
- `trader_id` = company identity

Use `LEFT JOIN` to trader masters.
Do not assume referential completeness.

## 3. System split

There are two parallel systems:

- `ERBA` = newer operational world
- `ERLA` = older operational world

They are related in business domain but not guaranteed equivalent in:

- code meaning,
- column naming,
- date coverage,
- concept granularity.

Treat cross-system equivalence as a runtime hypothesis.

## 4. Structural asymmetry that matters

These are stable architecture facts:

- ERBA often stores operational values as text and may need explicit casts.
- ERLA and ERBA may use different column names for similar business ideas.
- Some concepts exist in only one system.
- Combined answers usually require explicit `UNION` logic.
- Product tables and BTP tables are separate business paths and should not be mixed unless the user asks for a combined total.

Do not turn these asymmetries into hardcoded business mappings.
Use them as planning warnings, then verify with runtime discovery.

## 5. Join intent

Common planning rules:

- join product/BTP facts to trader master only when trader attributes are needed,
- count the business identity from the fact table, not from the joined master side,
- resolve coded values through `data_dictionary`,
- verify exact columns with schema introspection before final SQL.

## 6. Source selection rule

Choose tables by business event first.
The list below is illustrative, not exhaustive:

- issued registration / license identity,
- application / submission,
- additive/BTP-specific flow,
- forecast,
- or another event family discovered from the schema and business context.

Choose system scope second:

- ERBA only,
- ERLA only,
- combined.

If system scope is not stated and would materially change the answer, clarify before execution.
