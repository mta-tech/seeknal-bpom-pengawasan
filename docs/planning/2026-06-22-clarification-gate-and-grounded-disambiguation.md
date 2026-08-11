# seeknal-bpom-neo: Clarification Gate & Grounded Disambiguation

**Date:** 2026-06-22
**Reference audits:**
- `docs/audit_context/uat_audit_report_15jun2026.md`
- `docs/audit_context/uat_system_failure_analysis_19jun2026.md`
- `docs/audit_context/uat_test_results_analysis_19jun2026.md`
- `docs/planning/2026-06-19-execution-discipline-and-trust-transparency.md`

**Principle (unchanged, non-negotiable):** we do **not** hardcode answers or question-specific SQL.
The system must be taught a **general reasoning method**: when to clarify, what to clarify, which
authoritative source to consult, how to choose a path, when to stop exploring, and how to state
assumptions honestly. The goal is an agent that generalizes to unseen phrasing, larger schemas, and
future tables without turning the context into a static catalog.

**Flow (unchanged at the top level):** `SEEKNAL_ASK.md` (orchestrator) → loads `context/*.md` on
demand → invokes `seeknal/skills/*`; docs live in `docs/`. What changes in this rework is the
**decision discipline before final SQL**, not the architectural shell.

---

## 1. Why this rework is needed

The current UAT gap is no longer explained by missing facts alone. The audits already show that the
system often reaches the database, executes syntactically valid SQL, and still fails because it
**commits to the wrong interpretation before query construction**.

The next bottleneck is therefore:

1. **ambiguity is recognized conceptually but not enforced operationally**,
2. **gateway/UAT execution does not support a real clarification step**,
3. **the agent is still rewarded for guessing instead of blocking on material ambiguity**,
4. **dictionary use is present but not yet elevated into a clarification protocol**,
5. **real-user phrasing is shorter, looser, and more ambiguity-prone than internal test phrasing**.

This rework is about installing a **Clarification Gate** and a **Grounded Disambiguation Policy**
so the system knows when it must stop, ask, bind, and only then write SQL.

---

## 2. Current-state diagnosis

### 2.1 What the system already has

| Layer / File | What it already does | Status |
|---|---|---|
| `SEEKNAL_ASK.md` | Defines `CLARIFICATION`, Semantic Commitment, State Comparison, Conversation Ledger, and the "inherit ANSWERS, re-derive METHODS" principle | **Keep.** Strong conceptual base already exists |
| `context/code_translation_protocol.md` | Teaches source-aware dictionary resolution and `sumber` discipline | **Keep + sharpen.** Good translation base, but not yet a clarification policy |
| `context/business_glossary.md` | Holds business ontology and concept explanations | **Keep + clean.** Must avoid drifting into question-specific examples |
| `context/intent_mapping.md` | Normalizes user phrasing into entity / operation / dimension / scope | **Keep + extend.** Needs explicit ambiguity triggers |
| `context/data_quality_rules.md` | Encodes filter logic, date-column rules, commitment branching, and ERBA cast discipline | **Keep.** Already carries important correctness rules |
| `seeknal/skills/bpom-analyst/SKILL.md` | Runs CAPTURE → RESOLVE → PLAN → EXECUTE → REFLECT → GENERATE | **Enhance.** Needs a mandatory ambiguity decision gate |
| `seeknal/skills/evidence-auditor/SKILL.md` | Audits evidence and result integrity | **Enhance.** Must detect unresolved ambiguity, not only SQL/result coherence |

### 2.2 What the system does not really have yet

The system has the **language** of clarification, but not yet the **runtime contract** for
clarification in UAT/gateway mode.

Observed reality:

1. `SEEKNAL_ASK.md` already allows a `CLARIFICATION` turn.
2. The conversation model already tracks `Pending: <unresolved clarification, or none>`.
3. The follow-up planning docs already assume clarification can exist as part of the ledger.
4. But the runtime agent in gateway/headless mode does **not** expose an interactive `ask_user`
   step before final SQL.

So the design currently says:

```
ambiguity exists
→ clarification is a valid concept
→ the agent should remember pending clarification
```

But the runtime behavior in UAT effectively becomes:

```
ambiguity exists
→ agent cannot truly stop and ask in-channel
→ agent guesses
→ SQL is built for the guessed interpretation
```

This mismatch is one of the missing root causes behind the UAT failure profile.

---

## 3. The current flow vs the required flow

### 3.1 Current flow

```
User Question
    ↓
[1] CAPTURE
    ↓
[2] RESOLVE from context/dictionary
    ↓
[3] PLAN SQL path
    ↓
[4] EXECUTE
    ↓
[5] REFLECT
    ↓
[6] GENERATE answer
```

This flow works when the question is already precise enough to bind a single interpretation.

### 3.2 The missing decision step

The system currently lacks an explicit **"must I clarify before final SQL?"** gate between
CAPTURE and RESOLVE/PLAN.

That missing step matters because many UAT questions are not wrong, but **under-specified**.
Examples of under-specification:

- the user names a business event but not its lifecycle interpretation,
- the user names a concept whose code differs across ERBA and ERLA,
- the user names a category that may be direct-field, coded, or discovery-based,
- the user asks a short natural question whose target entity is not fully locked.

### 3.3 Required flow

```
User Question
    ↓
[1] CAPTURE
    ↓
[2] AMBIGUITY CHECK
      - Is the target entity clear?
      - Is the business event clear?
      - Is the source path clear?
      - Is the code family / exact state distinction clear?
      - Is the concept direct-field vs coded vs discovery clear?
    ↓
[3A] If clear → RESOLVE → PLAN → EXECUTE → REFLECT → GENERATE
    ↓
[3B] If materially ambiguous → CLARIFY → bind answerable interpretation → then continue
```

This is the core enhancement. The system should not be taught more memorized answers; it should be
taught **when clarity is insufficient for safe execution**.

---

## 4. Root-cause extension: what was still under-mentioned

The existing audits already diagnose business-semantic failure well. The following aspects need to
be added more explicitly so the rework targets the real failure mode.

### 4.1 Design/runtime contradiction

The current documentation already assumes clarification can happen. The runtime used by UAT does
not yet operationalize that assumption in a first-class way. This means:

- the design rewards careful disambiguation,
- the runtime often rewards premature commitment.

This contradiction should be treated as a formal root cause, not a footnote.

### 4.2 Ambiguity is not yet classified as a first-class failure source

Today the audit classes focus on:

- code mapping,
- status family,
- source-path selection,
- direct-field mishandling,
- commitment confusion,
- over-exploration.

Those are still correct. But many of them are **downstream effects** of a deeper condition:
**the system failed to recognize that the question needed clarification before binding**.

### 4.3 UAT is a language-style stress test, not only a business-rule test

Internal tests mostly validate:

- correct query templates,
- known mappings,
- canonical wording,
- explicit scope.

UAT additionally tests whether the system can handle:

- shorthand phrasing,
- implicit scope,
- business colloquialisms,
- omitted qualifiers,
- natural follow-up expectations.

This means UAT is not merely "harder data logic". It is also a **human-language ambiguity test**.

### 4.4 Dictionary grounding is available but underused as a clarification source

The database already contains enough structured meaning to ground a clarification:

- `STATUS`
- `STATUS_KOMITMEN`
- `KEMASAN_ID`
- `JENIS_DOKUMEN`
- `KATEGORI_DOKUMEN`
- geographic dictionaries
- source-partitioned category tables

So the right path is not to manually enumerate every user phrase in context. The right path is to
teach the agent to:

1. detect the ambiguity class,
2. inspect the relevant dictionary/schema source,
3. produce a constrained natural-language clarification,
4. proceed only after the ambiguity is resolved or explicitly scoped.

---

## 5. Clarification policy: what must change

### 5.1 Clarification mode

**Policy choice:** for **material ambiguity**, the system should use **block-first clarification**.

Material ambiguity means the ambiguity would change one or more of:

- the counted entity,
- the source path,
- the lifecycle definition,
- the code family,
- the meaning of the final number.

If the ambiguity is only cosmetic or a clear typo, the system should continue without asking.

### 5.2 Clarification style

The clarification must be **grounded choice**, not a free-floating generic question.

That means the follow-up should be:

- natural in wording,
- constrained in options,
- anchored to dictionary/schema/data or prior conversation state,
- explicit about the assumption boundary if the system must proceed.

**Good pattern:**
> "By `disetujui`, do you mean approved application status, or approved commitment status?"

**Good pattern:**
> "For `kemasan plastik`, should I count ERBA only, ERLA only, or combine both systems using each system's own packaging codes?"

**Bad pattern:**
> "Can you clarify what you mean?"

The bad pattern delegates the reasoning burden back to the user. The required behavior is the
opposite: the agent should present the plausible, grounded interpretations.

### 5.3 Clarification threshold

The system should **not** ask follow-up questions for every turn.

It should proceed directly when:

- the entity is already locked,
- the concept resolves to one authoritative field/path,
- the lifecycle meaning is canonical in context,
- the source path is already determined,
- the coded filter can be bound safely without ambiguity.

This preserves speed and avoids conversational friction for already-clear questions.

---

## 6. Ambiguity taxonomy the agent must learn

The system should explicitly learn the following ambiguity classes and treat them as a decision
layer, not as ad hoc intuition.

### 6.1 Entity ambiguity

Example:
- "disetujui" could refer to a **permohonan** lifecycle or an **NIE** result.

**Required response:** clarify only if the entity materially changes the counting logic.

### 6.2 Business-event ambiguity

Example:
- "aktif"
- "terbit"
- "dibatalkan"
- "dalam proses"

These are not merely words; they select lifecycle semantics.

**Required response:** bind the event meaning before SQL.

### 6.3 Source-path ambiguity

Example:
- the same concept exists in ERBA and ERLA with different granularity or coding.

**Required response:** determine whether the answer is:

- ERBA-only,
- ERLA-only,
- safely combinable,
- only partially combinable with a visible limitation.

### 6.4 Exact-state vs family-state ambiguity

Example:
- "disetujui" may mean exact status `4` only, or a broader approved family including
  "disetujui dengan catatan".

**Required response:** do not collapse exact and family semantics unless the user clearly asked for
the broader grouping.

### 6.5 Direct-field vs coded vs discovery ambiguity

Example:
- expiry questions should usually resolve to `tanggal_exp`,
- some segment questions require dictionary binding,
- some product-group questions require segment discovery.

**Required response:** classify the concept type first; do not over-explore if a direct field
already exists.

### 6.6 Conversation-scope ambiguity

Example:
- a short follow-up such as "yang aktif berapa?" can depend on the prior entity, prior year,
  prior system, and prior segment.

**Required response:** use the ledger first; ask only if the prior scope does not uniquely resolve
the turn.

---

## 7. File-level change map

This section makes the implementation target explicit so the rework stays consistent with the
existing architecture.

### 7.1 `SEEKNAL_ASK.md`

**Current role:**
- conversation gate,
- Decision OS,
- semantic commitment,
- state comparison,
- behavioral contracts.

**What should change:**
- add a formal **Ambiguity Check** stage after Semantic Commitment,
- define **material ambiguity** vs non-material ambiguity,
- define `DIRECT_EXECUTION` vs `CLARIFY_FIRST` routing,
- define the answer contract when clarification is not possible in-channel,
- make the `Pending` clarification state operational, not just conceptual.

**Why this file:**
This is the orchestrator. If clarification is only described lower in the stack, the system will
stay inconsistent.

### 7.2 `context/intent_mapping.md`

**Current role:**
- parse user phrasing into system intent.

**What should change:**
- add ambiguity triggers by concept class,
- add explicit examples of event words that require semantic locking,
- add concept-type classification guidance:
  - direct field,
  - coded concept,
  - discovery concept,
  - master-data identity,
  - lifecycle family,
  - cross-system concept.

**Why this file:**
This is where the system learns how natural language maps into execution shape.

### 7.3 `context/code_translation_protocol.md`

**Current role:**
- source-aware code resolution.

**What should change:**
- frame dictionary lookup as both a **translation tool** and a **clarification source**,
- teach how to build grounded candidate options from dictionary results,
- preserve the principle that code binding is source-aware and never blindly reused across systems.

**Why this file:**
The data dictionary is the strongest non-hardcoded substrate for grounded follow-up generation.

### 7.4 `context/business_glossary.md`

**Current role:**
- business ontology and concept explanation.

**What should change:**
- remove wording that reads like memorized question-answer shortcuts,
- keep ontology-level concepts only,
- strengthen concept definitions that help disambiguate business language,
- ensure cross-system concepts are described as reasoning rules, not frozen examples.

**Why this file:**
This file must stay conceptual. If it drifts into scenario-specific hints, the system becomes
brittle and non-general.

### 7.5 `context/data_quality_rules.md`

**Current role:**
- mandatory filters and correctness rules.

**What should change:**
- reinforce where status/lifecycle meaning depends on exact user wording,
- distinguish exact state, family state, and business-event interpretation where needed,
- clarify that some filters only become legal after the event semantics are locked.

**Why this file:**
Many UAT failures happen because filters are technically valid but semantically premature.

### 7.6 `seeknal/skills/bpom-analyst/SKILL.md`

**Current role:**
- execution workflow and phase discipline.

**What should change:**
- add a required **Clarification Gate** in CAPTURE/RESOLVE,
- define when the skill must stop and ask,
- define when it may proceed with a stated assumption,
- define how grounded options are formed,
- define a stop rule so ambiguity does not degrade into exploratory SQL loops.

**Why this file:**
This is the operational layer. The behavior has to be enforceable here, not only descriptive.

### 7.7 `seeknal/skills/evidence-auditor/SKILL.md`

**Current role:**
- check whether the produced answer is supported by evidence.

**What should change:**
- add unresolved-ambiguity detection as a blocking condition,
- reject answers whose SQL is coherent but whose interpretation was never safely bound,
- allow scoped or limited answers when a safe combined answer is not possible.

**Why this file:**
REFLECT should not approve a polished answer that rests on an unresolved semantic fork.

---

## 8. What should stay unchanged

To avoid regression, the following parts should remain stable unless a contradiction is found:

- follow-up inheritance principle: **inherit ANSWERS, re-derive METHODS**
- Conversation Ledger as the cross-turn state model
- source-aware dictionary resolution
- RC-2 / RC-4 correctness already encoded in `data_quality_rules.md`
- ERBA cast discipline and date-column rules
- non-hardcoded philosophy
- honesty and limitation disclosure
- forecaster routing and forecasting logic

This rework is about **installing a better decision gate**, not replacing the whole system.

---

## 9. What is being fixed vs enhanced vs updated

### 9.1 Fixed

- the missing explicit decision step before final SQL,
- the gap between conceptual clarification and runtime execution discipline,
- the tendency to commit to a single interpretation without first testing whether the question is
  sufficiently bound.

### 9.2 Enhanced

- grounded dictionary use,
- ambiguity detection,
- natural-language clarification quality,
- source-aware option generation,
- limitation handling when full collapse is unsafe.

### 9.3 Updated

- orchestrator flow in `SEEKNAL_ASK.md`,
- intent parsing rules,
- code-resolution framing,
- ontology wording in the glossary,
- analyst-skill execution discipline,
- evidence-auditor blocking logic.

---

## 10. Target behavior after the rework

The intended runtime behavior becomes:

1. read the user question,
2. normalize obvious typo/noise,
3. lock Semantic Commitment,
4. run Ambiguity Check,
5. if the question is clear, proceed directly and efficiently,
6. if the question is materially ambiguous, generate a grounded clarification,
7. bind the interpretation,
8. execute the minimal authoritative SQL path,
9. reflect on both SQL correctness **and interpretation validity**,
10. answer with either:
   - a final answer,
   - a limited but honest scoped answer,
   - or a clarification request where the channel allows it.

This is the behavior of an agentic analytical system. It is not taught by stuffing more example
questions into context; it is taught by installing the decision policy that governs when to ask,
when to resolve, when to scope, and when to stop.

---

## 11. Anti-hardcode guardrail

This rework must be rejected if it turns into:

- enumerating user questions one by one,
- storing question-specific answer templates,
- memorizing per-scenario SQL,
- adding glossary content that only helps a fixed test set,
- forcing one combined answer where the schema itself does not support it cleanly.

This rework is successful only if it teaches the agent:

- how to inspect,
- how to classify,
- how to clarify,
- how to bind,
- how to execute proportionally,
- how to state limitations truthfully.

That is the only path that scales from 6 tables to 100 tables without turning the system into a
fragile prompt catalog.
