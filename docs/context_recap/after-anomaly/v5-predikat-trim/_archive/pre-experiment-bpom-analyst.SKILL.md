---
name: bpom-analyst
description: "Thin-trigger for BPOM analytical questions. CAPTURE → ROUTE → EXECUTE → REFLECT → PRESENT. Routes kode lookup to data_dictionary, predicates to predikat.md, SQL shapes to query_recipes.md. Use for every quantitative BPOM question (NIE, permohonan, risiko, skala/UMKM, komitmen, produk spesifik, gabungan sistem)."
tags: [bpom, text-to-sql, orchestration, reflection, analyst]
version: "3.0.0"
---

# BPOM Analyst — Thin-Trigger

**Workflow:** CAPTURE → ROUTE → EXECUTE → REFLECT → PRESENT

This skill directs the **thinking flow** for BPOM data questions. Same shape as `bpom-forecaster`
and `detect-anomaly`: the skill decides WHEN and HOW; literal code values, predicate rules, and
SQL fragments are looked up — never recalled.

---

## CAPTURE — understand the question

Begin from the Decision Layer output (`SEEKNAL_ASK.md` §1). Branch on State Comparison:
- `EXPLAIN_EVIDENCE` → skip to PRESENT (no new query).
- `MODIFY_SCOPE` / `EXTEND_SCOPE` → reuse prior **answers** only; **re-derive the method** via ROUTE.
- `NEW_QUESTION` → full workflow from scratch.

Apply `intent_mapping.md`: Subject→Granularity, Dependent vs Independent dimensions, normalize typos.

**SYSTEM-SCOPE GATE (first, before any SQL).** No system named (ERBA / ERLA / gabungan) and entity
is NIE / permohonan / produk / BTP → **clarify now, write no SQL** (`predikat.md` §7.1).
Risiko / komitmen → ERBA-only by definition; proceed and say so.

Emit the Semantic Commitment Block before SQL:
```
Intent:  Entity | Operation | Dimensions (DEPENDENT/INDEPENDENT) | Time Scope | Output Shape
Scope:   entity=… · system=… · year=… (or ALL-TIME) · BTP=yes/no
SCE:     NEW_QUESTION | MODIFY_SCOPE | EXTEND_SCOPE | EXPLAIN_EVIDENCE
```

---

## ROUTE — bind every concept to its authority (before SQL)

**Step 0 — check the verified maps first, for ANY coded concept (not just product segments):**
`context/verified_bindings.md` (concept → proven column+code) and
`context/filter_code_reference.md` (pipeline stages, risk taxonomies, entity choice, known
decoys). A hit there is the binding — skip free probing. Several concepts have a lexically
tempting wrong column (`klaim` vs `klasifikasi_id`; `klasifikasi_id='309'` vs `pemrosesan`)
that free probing reliably falls into.

Every concept in the question binds to one of three authoritative sources
(`code_translation_protocol.md` §4 is the full hierarchy):

| Type | Authority | When |
|---|---|---|
| **A — Kode Berkamus** | `data_dictionary` (via `code_translation_protocol.md` §2) | Default for any code value not covered by Step 0. Includes `JENIS_PANGAN`. |
| **B — Segmen Produk fallback** | `nama_kategori` discovery (`code_translation_protocol.md` §4.2) | Only when Type A returns 0 rows **and no entry in Step 0's maps**. **Must use `ask_user` if ambiguous — never silently pick.** |
| **C — Predikat** | `context/predikat.md` | Counting method, scope defaults, filters, Case A/B, etc. |

Record bindings in the binding table (`code_translation_protocol.md` §5) before SQL.

**RESOLVE gate:** no SQL until every coded term is bound (Step 0 or Type A) and `predikat.md`
consulted (Type C). If probing surfaces more than one plausible column or code family for one
concept, that is Type-B ambiguity — ask the user.

For **SQL shape** (count/trend/breakdown/UNION/multi-query) → `context/query_recipes.md` (5 canonical).
For **table topology / JOIN** → `context/data_architecture.md` (LEFT JOIN mandatory, orphan `trader_id`).

---

## EXECUTE — controlled

- Write SQL using recipe + bindings + predikat fragments.
- ~6 tool calls max per turn — if not converging, stop and explain what's missing.
- ERBA casts mandatory (TEXT → `::timestamp` / `::bigint`).
- UNION: separate WHERE per side (codes differ across systems).
- On error: re-check ROUTE — most errors come from a skipped binding/predikat step, not syntax.

---

## REFLECT — audit before answering

Run `evidence-auditor/SKILL.md` as the verification gate. Critical blocks:

- **`COUNT(DISTINCT …)` — BLOCK if `COUNT(*)`** on `t_produk_3_*` / `t_btp_3_*` (versioned tables; `COUNT(*)` over-counts +25% ERBA, +57% ERLA).
- Scope match (entity / time column / year scope / system / BTP scope) against the Semantic
  Commitment Block.
- Filters **match the population** (`predikat.md` §3–§5): issued-NIE status filter only when
  counting issued NIE — never stacked onto a population defined by another workflow state;
  jenis_permohonan conditional; test accounts; status_komitmen normalization if applicable.
- Case A/B komitmen correct for the intent.
- Consistency with prior turns (NIE ERBA 2023 must be the same number in every turn).

Verdict: **PASS** → proceed to PRESENT. **FIX: <reason>** → return to ROUTE/EXECUTE (max 3 rounds).
**HONEST-FAIL** → state the limitation; do not fabricate.

---

## PRESENT — answer the user

Output shape: see `SEEKNAL_ASK.md` §6 (`RINGKAS` / `ANALITIS` / `AUDIT_GRADE`). Honesty: §7.

Formatting rules:
- Bullets use `-`, never `*`. Tables stand alone (blank line before/after, not duplicated as bullets).
- Every number traces to a query that passed REFLECT (this turn or prior turn in conversation).
- Failed/empty/timed-out query → report the failure. Never synthesize from memory/benchmark.
- Test data (`seeknal/tests/`, `read_ask_test`/`run_ask_test`/`list_ask_tests`) is NOT a source.
- Output language follows the user's latest language.
- Resolve coded values to labels via `code_translation_protocol.md` §2.2 before presenting.
- If user asks to see the SQL, show the actual SELECT as a ```sql block. Never include credentials.

---

## CSV export (FC2d — once per turn, agent-decided)

Any answer showing analytical/tabular data → call `upload_to_s3` **exactly once** with the SQL
behind the final answer. Narrative-only answers → skip.

`execute_sql` results are **not auto-uploaded** — you decide which query the answer is about
(usually the last one, after exploratory/profiling queries). Export after REFLECT passes.

```python
upload_to_s3(filename="registrations-2026.csv",  # descriptive name; system refines automatically
             sql=<the SQL behind the final answer>)
```

**Pick the right SQL:**
- The complete aggregate/breakdown (drop `LIMIT`/top-N so export isn't truncated).
- Not row-level detail unless the user explicitly asked.
- For multi-query answers (e.g. ERBA+ERLA union), export the single SQL reproducing the whole
  combined result.
- Skip if purely explanatory (`EXPLAIN_EVIDENCE`) or no meaningful table.

Never paste the raw download URL in the answer — the frontend renders a Download button
automatically.

---

## Anomaly awareness

Handled by `detect-anomaly/SKILL.md` (sibling). If presenting a `run_forecast` result with an
`## Anomali` block (auto-attached on LEMAH/TOLAK backtest), include it. If the user asks about
anomalies directly, route to `detect-anomaly`. Always state flagged periods were **not removed**.
