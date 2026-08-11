# seeknal-bpom-neo: Runtime Change Log and Journaling Requirements

**Document type:** Implementation note  
**Date:** 2026-06-25  
**Status:** Applied to active runtime files  
**Scope:** `SEEKNAL_ASK.md` · `context/*.md` · `seeknal/skills/*` · deploy sync behavior

---

## 1. Purpose

This document records the practical runtime changes already applied after the 2026-06-24 planning set.

It exists for two reasons:

1. to document which planning principles were actually implemented,
2. to define the next journaling/state requirements so the agent can stay dynamic without losing reasoning discipline.

This is not a new architecture. It is an implementation delta note for the active architecture.

---

## 2. Principles Reinforced by the Changes

### 2.1 Database-first, not context-first

For factual answers, context is now framed as reasoning guidance only.
Answers must come from database evidence or validated ledger facts that originally came from database evidence.

### 2.2 Clarify-first when scope is materially missing

If year, period, or source scope is missing and different choices would materially change the answer, the agent must clarify before counting.

The system must not silently default to:

- all-time,
- a single year,
- or combined ERBA+ERLA

when that choice changes the answer meaningfully.

### 2.3 Discovery over hardcoded mapping

A new runtime discovery layer was introduced so the agent can:

- try dictionary lookup first,
- probe real data when dictionary coverage is broad or absent,
- compare ERBA and ERLA before combining,
- and only then bind filters or ask a clarification question.

### 2.4 Examples are illustrative, not exhaustive

Several files previously risked teaching the model that `NIE`, `permohonan`, or a few named cases were the whole problem space.

That wording has been revised.

The runtime should now treat those labels as examples of:

- event classes,
- source-path classes,
- recipe families,
- and reasoning categories

rather than a fixed catalog of valid user questions.

### 2.5 User-language output

The system must answer in the user's language.

Rules:

- if the user asks in Indonesian, answer in Indonesian,
- if the user asks in English, answer in English,
- internal English context files do not control output language,
- domain terms and proper nouns from the data may stay unchanged where appropriate.

### 2.6 Anti-hallucination boundary

The system must not invent factual information.

For factual turns, information must come only from:

- executed database evidence,
- or validated ledger facts that originally came from executed database evidence.

Project docs, tests, memory, and context text are not factual answer sources.

---

## 3. Changes Applied

### 3.1 New file added

`context/source_discovery_protocol.md`

Purpose:

- teach runtime discovery,
- teach cross-system verification,
- teach escalation from dictionary -> probe -> compare -> clarify,
- block false confidence when the dictionary is not enough.

### 3.2 Orchestrator updated

`SEEKNAL_ASK.md`

Applied changes:

- added stronger database-first language,
- added discovery protocol into source precedence,
- strengthened clarification rules for missing time/source scope,
- added explicit ban on letting context replace factual evidence.

### 3.3 Core context files simplified

Updated:

- `context/data_architecture.md`
- `context/data_quality_rules.md`
- `context/code_resolution.md`
- `context/query_recipes.md`
- `context/code_translation_protocol.md`

Applied direction:

- remove answer-like or over-specific wording,
- keep structural and procedural rules,
- move from fixed examples to general classes,
- keep runtime resolution as the authority for business-code meaning.

### 3.4 Skill behavior updated

Updated:

- `seeknal/skills/bpom-analyst/SKILL.md`
- `seeknal/skills/evidence-auditor/SKILL.md`
- `seeknal/skills/database-analyst/SKILL.md`
- `seeknal/skills/business-question-answering/SKILL.md`

Applied direction:

- add explicit `DISCOVER` phase,
- block counting SQL before material ambiguity is resolved,
- block false equivalence across ERBA/ERLA,
- block silent defaulting of time/source scope,
- make concept labels clearly illustrative, not exhaustive.

### 3.5 Runtime config tightened

Updated:

- `seeknal_agent.yml`

Applied direction:

- `ask_user.enabled: true`
- `ask_user.auto_select: false`
- `request_clarification.enabled: true`

This keeps clarification active while avoiding silent auto-selection in real runs.

### 3.6 Deploy config synchronized

The same reasoning files were synced into:

`iba-deploy-runbook/configs/seeknal-project`

Only deploy-specific differences should remain there:

- DSN/env wiring
- deploy comments
- operational runtime configuration

Reasoning content should stay aligned with `seeknal-bpom-neo`.

---

## 4. Journaling Requirement

The next weak point is not only context quality.
It is state quality.

The agent needs a clearer journal of what was already established in the conversation so it can:

- avoid repeated clarification,
- avoid follow-up drift,
- answer provenance questions without recomputing,
- and know when a new user turn is still the same topic or already a new topic.

### 4.1 Journal purpose

The journal is not a transcript copy.
It is a compact runtime state record.

It should store only what the next turn needs for safe reasoning.

### 4.2 Minimum journal fields

Every completed analytical turn should leave a structured record containing:

```text
Topic ID
Turn classification
Semantic Commitment Block
Locked business event
Locked time scope
Locked source scope
Confirmed user bindings
Source Discovery Record summary
Binding Table summary
Executed query references
Validated facts
Active limitations
Provenance references
Clarification state
Clarification budget remaining
```

### 4.3 Journal rules

- Store validated answers, not raw chain-of-thought.
- Store the final bound interpretation, not every abandoned hypothesis.
- Store provenance pointers to executed SQL, not only prose summaries.
- Store user-confirmed scope explicitly so follow-up turns can reuse it safely.
- Do not store prior method choices as reusable truth unless they were explicitly confirmed as scope.

### 4.4 Journal use cases

The journal must support these runtime behaviors:

1. **Follow-up on the same topic**
   Reuse confirmed scope and facts, but re-derive the new method.

2. **Provenance turn**
   Show where the answer came from without new SQL when evidence already exists.

3. **Clarification continuation**
   Resume exactly from the pending ambiguity instead of restarting full reasoning.

4. **Topic boundary detection**
   Detect when the new turn has changed entity, event, source path, or time scope enough to count as a new question.

### 4.5 Journal anti-patterns

Do not let the journal become:

- a cache of reusable SQL methods,
- a giant transcript summary,
- a memory of guessed interpretations,
- or a replacement for runtime discovery.

The journal exists to stabilize state, not to hardcode the next answer.

---

## 5. Next Recommended Work

The highest-value next steps are:

1. formalize the runtime journal schema in code,
2. persist provenance references per executed answer,
3. persist clarification state and budget explicitly,
4. ensure follow-up classification reads the journal first,
5. keep deploy/runtime reasoning files synchronized from one canonical source.

---

## 6. Governance Note

If future changes alter:

- clarification policy,
- source discovery behavior,
- or journaling fields,

update this document together with the active planning set.

Do not let implementation drift silently away from planning again.
