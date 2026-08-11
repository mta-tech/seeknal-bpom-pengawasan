# seeknal-bpom-neo: Pre-Refactor NoSP Production Baseline

**Document type:** Implementation change-log + production baseline decision  
**Date:** 2026-06-26  
**Status:** Applied (PR #10 — `feat/pre-refactor-nosp-config`)  
**Scope:** `context/*.md` · `seeknal/skills/*` · `SEEKNAL_ASK.md` · `seeknal_agent.yml`  
**Reference audit:** `docs/audit_context/variant_compare_audit_26jun2026.md`  
**Snapshot source:** `docs/context_recap/testing_refactor/pre-refactor-1dd55d9-notsystemprompt/`

---

## 1. Purpose

This document records the production baseline decision made on 2026-06-26: the
seeknal-bpom-neo agent configuration was reverted to the **pre-refactor declarative
baseline** (commit `1dd55d9`) with the **notsystemprompt** (`noSP`) clarification
configuration.

The decision is based on the variant-compare audit conducted on the same date, which
tested 4 configurations across 66 unique scenarios (236 graded runs).

This is not a new architecture. It is a production baseline selection supported by
empirical test data, plus a gap analysis identifying what remains to be operationalized.

---

## 2. Audit Context

### 2.1 Test setup

| Parameter | Value |
|-----------|-------|
| Test date | 2026-06-26 |
| Test files | 5 variant-compare runs |
 Unique scenarios | 66 |
| Total graded runs | 236 (66 × 4 variants, minus 28 missing-variant slots) |
| Grading | Lenient re-grade (format/near-miss/no-assertion = pass) |

### 2.2 Variant results

| Variant | Overall | DIR pass | ASK pass | LLM calls/turn |
|---------|---------|----------|----------|----------------|
| pre-refactor (SP) | **68%** | **80%** | 57% | **4.9** |
| **pre-refactor (noSP)** ← selected | **64%** | 60% | **67%** | **5.5** |
| after-refactor (SP) | 64% | 69% | 61% | 10.0 |
| after-refactor (noSP) | 60% | 52% | 64% | 8.1 |

### 2.3 Important caveat

The after-refactor variant was tested with a **degraded 62-line `SEEKNAL_ASK.md`**
(stripped to clarification-only guidance), not the full 279-line v8 orchestrator that
exists at HEAD `f8d34b0`. The pre-refactor variant used its full 327-line declarative
orchestrator. This means the comparison was not fully apples-to-apples — the after-refactor
may perform better than measured if tested with its proper v8 orchestrator.

### 2.4 Failure breakdown (84 failures across 236 runs)

| Cause | Count | % of failures |
|-------|-------|---------------|
| Scope-mismatch (ERBA/ERLA/union/status) | 41 | 49% |
| Pure-value error (scope correct, number wrong) | 43 | 51% |

---

## 3. Decision Rationale

### 3.1 Why pre-refactor declarative context

The pre-refactor context files store BPOM domain codes **inline** — AMDK segment codes,
Garam codes, risk granularity, test-account exclusions, and status mappings are all
directly available in the context files. This provides:

- **direct lookup** for known domain concepts,
- **less LLM iteration** (fewer discovery SQL round-trips),
- **lower cost per turn** (5.5 vs 10.0 LLM calls).

The trade-off is that declarative context is harder to maintain as the domain grows and
may over-fit to currently known codes.

### 3.2 Why notsystemprompt (noSP)

The `noSP` configuration disables the seeknal framework's built-in default workflow prompt
and replaces it with a minimal custom prompt that directs the LLM to `SEEKNAL_ASK.md` as the
single source of truth. This gives:

- **full control** over the prompt chain (no hidden framework prompt),
- **explicit dependency** on `SEEKNAL_ASK.md` as orchestrator,
- **higher ASK accuracy** (67% vs 57% for SP) — the LLM reads the clarification gate
  more carefully when it is the primary instruction source.

### 3.3 Trade-off acknowledged

The `noSP` variant scores 4 percentage points lower than `SP` overall (64% vs 68%) and
significantly lower on DIR accuracy (60% vs 80%). The seeknal built-in workflow prompt
provides structural reasoning assistance that the custom minimal prompt does not replicate.

This trade-off was accepted because:
1. production requires explicit control over the prompt chain,
2. the 4% gap can be recovered by strengthening `SEEKNAL_ASK.md`,
3. the cost efficiency (5.5 vs 10.0 LLM calls) is valuable for production load.

---

## 4. Changes Applied

### 4.1 Summary

| Component | From (main `4dd27a1`) | To (pre-refactor snapshot) | Delta |
|-----------|----------------------|---------------------------|-------|
| `context/` (9 files) | Procedural v2 (~36 KB) | Declarative v1 (~128 KB) | Modified |
| `context/source_discovery_protocol.md` | Present (3.6 KB) | Not in pre-refactor | **Deleted** |
| `seeknal/skills/` (5 skills) | Trimmed (~130-line analyst) | Monolith (465-line analyst) | Modified |
| `SEEKNAL_ASK.md` | v8 (279 lines, procedural) | v4 + SEEK5 (394 lines, declarative) | Modified |
| `seeknal_agent.yml` | `prompt.workflow: false` + custom | Same + `auto_select: false` | Modified |

Total: **17 files changed**, +3,092 insertions, −1,391 deletions.

### 4.2 File-level detail

| File | Before (main) | After (this PR) | Lines |
|------|--------------|-----------------|-------|
| `context/business_glossary.md` | 3.4 KB (procedural) | 15.9 KB (declarative, inline codes) | +360% |
| `context/data_quality_rules.md` | 3.4 KB | 11.8 KB (inline status/test-account rules) | +250% |
| `context/intent_mapping.md` | 4.6 KB | 20.7 KB (entity registry + ambiguity triggers) | +350% |
| `context/query_recipes.md` | 1.7 KB | 15.6 KB (R1–R5 with examples) | +820% |
| `context/code_translation_protocol.md` | 5.4 KB (Four-Pass) | 7.9 KB (Two-Way Source-Aware) | +47% |
| `context/data_architecture.md` | 2.6 KB | 8.3 KB (topology + join logic) | +220% |
| `context/forecast_guide.md` | 3.1 KB | 16.0 KB | +420% |
| `context/forecast_recipes.md` | 6.7 KB | 17.9 KB | +170% |
| `context/code_resolution.md` | 2.1 KB | 5.9 KB | +180% |
| `context/source_discovery_protocol.md` | 3.6 KB | **deleted** | — |
| `seeknal/skills/bpom-analyst/SKILL.md` | ~130 lines | 465 lines (monolith) | +258% |
| `SEEKNAL_ASK.md` | 279 lines (v8) | 394 lines (v4 + SEEK5) | +41% |
| `seeknal_agent.yml` | `auto_select: true` | `auto_select: false` | production |

---

## 5. Component Detail

### 5.1 Context files (9 declarative)

The pre-refactor context uses a **declarative/cheat-sheet** style: domain codes, segment
mappings, and filter rules are stored inline rather than discovered at runtime.

Key characteristics:

- **`business_glossary.md`** (15.9 KB) — product segment codes (AMDK jenis_pangan=1401,
  Garam, BTP jenis_btp=47/48), canonical definitions, commitment concepts.
- **`data_quality_rules.md`** (11.8 KB) — mandatory filters: bad-year exclusion (1900/1970),
  test-account exclusion (trader_id IN 5,17,50,85), ERBA cast discipline, status families,
  Case A/B commitment branching.
- **`code_translation_protocol.md`** (7.9 KB) — Two-Way Source-Aware resolution (NOT the
  Four-Pass Resolver from the refactor). Codes are resolved via dictionary lookup with
  sumber-aware Path A/B branching.
- **`query_recipes.md`** (15.6 KB) — R1–R5 execution frameworks with hardcoded examples
  for issued-identity, submission, cross-system combined, breakdown/ranking, commitment.
- **`intent_mapping.md`** (20.7 KB) — ENTITY/OPERATION/DIMENSION registry, Step 0
  normalization, segment discovery, ambiguity triggers by concept class.

Notable absence: **`source_discovery_protocol.md`** does not exist in this baseline. The
procedural Stage A→D discovery protocol was introduced during the refactor (commit
`f8d34b0`). Without it, discovery is handled inline by `bpom-analyst/SKILL.md`.

### 5.2 Skills (5 monolith)

| Skill | Lines | Style |
|-------|-------|-------|
| `bpom-analyst` | 465 | Monolith — workflow phases + mechanics + examples inline |
| `bpom-forecaster` | 391 | Deterministic pipeline — eligibility, backtest, SN+MA3 |
| `evidence-auditor` | 105 | Audit checklist — granular verification steps |
| `database-analyst` | 84 | Generic read-only DB workflow with clarify gate |
| `business-question-answering` | 45 | Strategic question translation |

The `bpom-analyst` monolith (465 lines) combines what the refactor split into separate
mechanisms: workflow phases, blocking contracts, code resolution, and execution
discipline. This is more prescriptive but less maintainable.

### 5.3 SEEKNAL_ASK.md (v4 + SEEK5)

The orchestrator is **v4** (declarative) with the **SEEK5 clarification section** appended.

**v4 orchestrator (327 lines):**
- §0 Conversation Gate (turn classification)
- §1 Decision Frame (entity/operation/dimensions)
- §2 Semantic Commitment + State Comparison
- §3 Clarification (basic)
- §4 Conversation Ledger
- §5 Source Precedence
- §6 Output Contracts
- §7 Global Guardrails

**SEEK5 clarification addition (67 lines):**
- 3 ambiguity types requiring clarification:
  1. Data system / source (ERBA vs ERLA vs gabungan)
  2. Object / product scope (broad category → multiple sub-categories)
  3. Status / filter dimension (aktif, terdaftar, berlaku → multiple interpretations)
- When NOT to ask (4 exception rules)
- Multi-slot form (1–3 slots per `request_clarification` call)
- Turn-end behavior after clarification

### 5.4 seeknal_agent.yml (noSP + production)

```yaml
prompt:
  workflow: false              # disable seeknal built-in default workflow
  custom: |                    # minimal custom prompt
    You are a BPOM data analyst assistant.
    Your first step... read SEEKNAL_ASK.md...

agent:
  ask_user:
    enabled: true
    auto_select: false         # PRODUCTION: user must explicitly pick option
  request_clarification:
    enabled: true
```

Key production settings:
- `auto_select: false` — clarification options must be explicitly chosen by the user,
  not auto-picked (the `true` setting was for testing only).
- `prompt.workflow: false` — seeknal default workflow disabled, custom prompt active.
- `request_clarification.enabled: true` — headless clarification channel active.

---

## 6. Clarification Gate Status

### 6.1 The core problem

The variant-compare audit revealed that the system **does not ask back often enough**.
Of 94 direct-answer (DIR) turns, **51 were wrong (54%)** — many of these should have
triggered a clarification but did not.

This problem is **already diagnosed** in the planning documents:

> *"The system has the language of clarification, but not yet the runtime contract."*
> — `2026-06-22-clarification-gate-and-grounded-disambiguation.md` §2.2

> *"The ambiguity gate arrives too late — by line 151, the model is already in answer mode."*
> — `2026-06-24-context-simplification-and-followup-protocol.md` §1.1

### 6.2 What v4 + SEEK5 has

| Feature | Status |
|---------|--------|
| 3 ambiguity types (system, product, status) | Present |
| When-not-to-ask exceptions | Present |
| Multi-slot clarification form | Present |
| `request_clarification` tool wiring | Present |

### 6.3 What v4 + SEEK5 is missing (gap to active design)

| Feature (designed in planning) | In v4? | Impact |
|-------------------------------|--------|--------|
| 6 ambiguity classes (Entity, Event, Source, State, Concept, Scope) | Partial (3 of 6) | Entity/Event/Concept/Scope ambiguity undetected |
| Mandatory clarification gate before SQL | No | LLM proceeds to SQL without checking ambiguity |
| Clarification budget (default 0, max 2) | No | No counter to track/limit clarification rounds |
| Sufficiency check (`enough_to_execute: yes/no`) | No | LLM does not know when to stop and ask |
| Runtime blocking (block `execute_sql` when ambiguous) | No | No programmatic enforcement |
| Grounded options from dictionary lookup | Text only | No binding procedure to generate options from data |

### 6.4 Evidence from audit

From 236 graded runs:
- **ASK rate:** ~50% of questions trigger ask-back (the other ~50% go direct).
- **DIR failure rate:** 54% of direct answers are wrong.
- **ASK failure rate:** when the system does ask back and the harness picks a scope,
  the answer is correct ~62% of the time (but the raw `passed` flag said 100% — that
  was an artifact of the grader not enforcing assertions on `[AUTO]` turns).
- **Scope-mismatch dominance:** 27 of 41 scope-mismatches are ERBA→UNION (system
  broadens to union when GT expects single-system).

---

## 7. Known Trade-offs

| Aspect | Pre-refactor noSP (this baseline) | After-refactor (alternative) |
|--------|-----------------------------------|------------------------------|
| Context style | Declarative/hardcode (128 KB) | Procedural (36 KB) |
| Generalization | Risk of over-fitting to known codes | Protocol-based, more general |
| LLM cost per turn | 5.5 calls | 10.0 calls |
| DIR accuracy | 60% | 69% (with SP) |
| ASK accuracy | 67% | 61% |
| Clarification trigger rate | Higher (over-clarify tendency) | Lower (under-clarify) |
| Scalability to new domains | Hardcoded catalogs must grow | Discovery protocol handles unknowns |
| Maintenance | Edit inline codes per domain change | Edit protocol rules once |

---

## 8. Next Steps

### 8.1 Path A — Enhance v4 clarification gate (quick win)

Add clarification budget, mandatory gate text, and sufficiency check to `SEEKNAL_ASK.md`
v4 without changing the declarative context architecture.

- **Effort:** Low (edit `SEEKNAL_ASK.md` only)
- **Risk:** Still depends on LLM compliance — no programmatic enforcement
- **Targets:** Reduce DIR-fail rate from 54% toward 30%

### 8.2 Path B — Proper fair test of v8 (validation)

Create a branch with the full v8 `SEEKNAL_ASK.md` (279 lines, not the degraded 62-line
version) and re-run the variant-compare test. The v8 already has §2 Clarification Gate
with mandatory cases, budget, and sufficiency check.

- **Effort:** Medium (create branch + run test suite)
- **Risk:** Low — purely diagnostic
- **Value:** Determines if v8 actually performs better when tested fairly

### 8.3 Path C — Runtime enforcement (robust)

Add a programmatic gate in the skill/tooling layer that blocks `execute_sql` when
`pending clarification` is active. This is the design specified in
`04-clarification-and-ambiguity-policy.md` §9.

- **Effort:** High (code change in seeknal runtime)
- **Risk:** Medium — requires understanding seeknal framework internals
- **Value:** Eliminates the design-runtime contradiction permanently

### 8.4 Recommended sequence

1. **Path B first** — validate whether v8 is actually better (1-2 hours of testing).
2. **Path A if v4 is kept** — strengthen the clarification gate text (half-day edit).
3. **Path C for production** — build runtime enforcement regardless of which orchestrator
   version is selected (multi-day engineering effort).

---

## 9. References

| Reference | Path |
|-----------|------|
| Audit report | `docs/audit_context/variant_compare_audit_26jun2026.md` |
| Clarification policy (active design) | `docs/planning/04-clarification-and-ambiguity-policy.md` |
| Clarification gate analysis | `docs/planning/2026-06-22-clarification-gate-and-grounded-disambiguation.md` |
| Context simplification spec | `docs/planning/2026-06-24-context-simplification-and-followup-protocol.md` |
| Master plan | `docs/planning/2026-06-24-agent-runtime-refactor-master-plan.md` |
| Runtime change log | `docs/planning/2026-06-25-runtime-change-log-and-journaling-requirements.md` |
| PR #10 | `feat/pre-refactor-nosp-config` → `main` |
| Snapshot source | `docs/context_recap/testing_refactor/pre-refactor-1dd55d9-notsystemprompt/` |
| Commit template | `docs/commit_template.txt` |
