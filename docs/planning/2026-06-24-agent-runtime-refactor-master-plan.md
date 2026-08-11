# seeknal-bpom-neo: Dynamic Agent Runtime Refactor Master Plan

**Document type:** Master implementation plan  
**Project:** seeknal-bpom-neo  
**Date:** 2026-06-24  
**Status:** Proposed  
**Scope:** `SEEKNAL_ASK.md` · `context/*.md` · `seeknal/skills/*` · runtime clarification path · `docs/planning/*`

---

## 1. Purpose

This plan defines the target refactor for the BPOM analytical agent as a **dynamic, decision-driven system** rather than a pattern-matching or answer-memorizing system.

The goal is not to teach the agent specific product answers, fixed code lists, or question templates. The goal is to teach the agent:

- how to decide what the user is actually asking,
- how to classify the type of concept being asked,
- how to choose the correct source path,
- when to stop and ask a clarification question,
- how to resolve codes from authoritative sources,
- how to retain conversation context without inheriting wrong reasoning,
- and how to explain provenance without recomputing the answer.

This plan also defines what must be removed, rewritten, preserved, archived, or newly introduced across the full system.

---

## 2. Target End State

The system should behave as a **dynamic analytical agent** with the following properties:

1. It does not answer from memorized domain examples.
2. It does not bind business meaning to a code unless the binding has been resolved from an authoritative source.
3. It does not execute SQL before the semantic interpretation is stable.
4. It does not inherit prior reasoning steps across turns.
5. It does inherit verified answers, scope, and explicit user-confirmed bindings when still relevant.
6. It does distinguish between:
   - a new question,
   - a scope modification,
   - an extension of the same analysis,
   - a provenance request,
   - and a clarification response.
7. It does treat ambiguity as a first-class runtime condition, not as an optional conversational nicety.

The system should be able to scale from the current small schema to much larger schemas by using a stable reasoning method rather than static catalogs.

---

## 3. Core Design Principles

### 3.1 Anti-Hardcode Principle

The system must not be improved by adding question-specific answers, fixed SQL for individual user phrasings, or a growing list of product-name shortcuts.

Allowed:

- teaching concept classes,
- teaching source selection method,
- teaching code resolution procedure,
- teaching ambiguity handling,
- teaching follow-up handling,
- teaching output and provenance discipline.

Not allowed as core design strategy:

- "if the user says X, always use code Y",
- "if the user says product Z, always route to this exact filter",
- embedding large business-answer catalogs into the orchestrator or context.

### 3.2 Method Over Memory

The agent should know **how to derive** the answer, not **what the answer usually is**.

### 3.3 Authoritative Source First

Every resolved meaning must come from the most authoritative available source for that concept type.

### 3.4 Clarify Before Compute

If materially different interpretations remain possible, clarification is mandatory before execution.

### 3.5 Inherit Answers, Re-derive Methods

Conversation continuity may reuse validated facts and explicit scope. It must never silently reuse prior column choices, filter logic, or code mappings.

### 3.6 Conditions, Not Product Names

The design must describe **data conditions and concept classes**, not rely on teaching named product examples as the primary operating method.

---

## 4. Architecture to Be Built

The refactored system should be organized into five clear layers.

### 4.1 Orchestrator Layer

Owned by `SEEKNAL_ASK.md`.

Responsibilities:

- classify the user turn,
- lock the semantic commitment,
- compare against conversation state,
- decide whether the turn is answerable directly, requires clarification, requires execution, or is provenance-only,
- select the correct skill path,
- enforce top-level answer contracts.

Non-responsibilities:

- storing domain code catalogs,
- explaining table structure,
- carrying detailed resolution instructions,
- storing segment definitions,
- storing example-heavy domain content.

### 4.2 Context Layer

Owned by `context/*.md`.

Responsibilities:

- store stable domain facts,
- store resolution procedures,
- store source-path rules,
- store data quality rules,
- store query templates only after scope is already locked.

Non-responsibilities:

- acting as an answer catalog,
- duplicating orchestration logic,
- mixing implementation history with active rules,
- teaching product-by-product shortcut behavior as the core method.

### 4.3 Skill Layer

Owned by `seeknal/skills/*`.

Responsibilities:

- execute the reasoning workflow,
- load only needed context,
- produce internal decision artifacts before SQL,
- block execution when prerequisites are missing,
- run SQL only after resolution is complete,
- audit evidence before answering.

### 4.4 Runtime Gate Layer

Owned by runtime ask/clarification wiring.

Responsibilities:

- suspend execution for clarification,
- resume after user answer,
- persist pending clarification state,
- prevent SQL execution while pending ambiguity remains,
- support provenance retrieval without new computation.

### 4.5 Documentation Governance Layer

Owned by `docs/planning` and related design docs.

Responsibilities:

- keep one active design source,
- archive historical planning,
- separate active architecture from implementation history,
- avoid instruction duplication across files.

---

## 5. What Must Be Preserved

The following system directions are fundamentally correct and must remain.

### 5.1 Preserve `SEEKNAL_ASK.md` as the single orchestrator entry point

It should remain the top-level controller for turn classification and conversation-level decision logic.

### 5.2 Preserve the anti-hardcode philosophy

The current strategic direction is correct and should become stricter, not weaker.

### 5.3 Preserve dictionary-grounded code resolution

`data_dictionary` must remain the authority for coded values where applicable.

### 5.4 Preserve the separation between ERBA and ERLA

The system must continue to treat them as distinct systems with distinct semantics when required.

### 5.5 Preserve the follow-up principle

The principle "inherit ANSWERS, re-derive METHODS" is correct and should become an architectural invariant.

### 5.6 Preserve forecasting as a separate capability

Forecasting should stay separate from the core analytical runtime path.

---

## 6. What Must Be Removed from Active Runtime Design

This section refers to removal from the **active operating path**, not necessarily deletion from repository history.

### 6.1 Remove knowledge-monolith behavior from `SEEKNAL_ASK.md`

The orchestrator must no longer contain:

- product segment code tables,
- domain-specific code lists,
- detailed schema notes,
- long behavioral lookup tables that duplicate `intent_mapping.md`,
- examples that act as disguised hardcoded shortcuts.

### 6.2 Remove answer-like examples from active context

Context files must stop teaching the model through large banks of question-shaped examples or named-product answer hints.

### 6.3 Remove duplicated rules across files

If a rule already belongs in one authoritative file, it must not appear as a competing active rule elsewhere.

### 6.4 Remove historical planning documents from the active planning path

Prior planning documents should not continue to function as parallel sources of truth for system design.

### 6.5 Remove contradictory legacy guidance from runtime influence

Any legacy guidance that encourages:

- shallow keyword routing,
- premature SQL execution,
- system mixing without source-aware resolution,
- or inherited method drift

must be retired from active use.

---

## 7. What Must Be Rewritten

### 7.1 `SEEKNAL_ASK.md` — major rewrite

This file should be rewritten into a **thin orchestrator**.

Its final structure should contain only:

- conversation gate,
- semantic commitment block,
- state comparison engine,
- conversation ledger contract,
- clarification gate policy,
- provenance gate,
- source precedence summary,
- output contract selector,
- global guardrails.

Everything else should move out.

### 7.2 `seeknal/skills/bpom-analyst/SKILL.md` — major rewrite

This file should be rewritten to make the execution contract explicit.

It should require internal artifacts before SQL:

- Event Lock
- Concept Type Table
- Binding Table
- Authoritative Source Path
- Execution Shape

The skill must be able to stop before SQL if any of the above is incomplete.

### 7.3 `seeknal/skills/evidence-auditor/SKILL.md` — moderate rewrite

The auditor must move from passive checklist behavior to active blocking behavior.

It must reject results when:

- event lock was not explicit,
- source path was not unique,
- ambiguity remained unresolved,
- direct-field concepts were over-explored,
- cross-system mappings were forced without equivalence.

### 7.4 `docs/planning/*` — major rewrite

The active planning set should be rewritten as a small final architecture set rather than an accretion of date-based amendment documents.

---

## 8. What Must Be Restructured

### 8.1 Restructure `context/` into clear categories

Active context should be grouped by role.

#### A. Stable domain facts

Examples:

- entity definitions,
- system distinctions,
- structural business semantics,
- metric meaning.

#### B. Resolution procedures

Examples:

- code translation protocol,
- source hierarchy,
- direct-field vs coded vs discovery decision rules,
- cross-system asymmetry handling.

#### C. Data quality and execution rules

Examples:

- cast rules,
- date column rules,
- mandatory filters,
- exclusion rules.

#### D. Query frameworks

Examples:

- adaptive recipe templates,
- aggregation shapes,
- canonical total-vs-breakdown patterns.

### 8.2 Restructure `docs/planning`

The active planning directory should become a clean final design set, for example:

- `01-agent-design-principles.md`
- `02-decision-model-and-conversation-state.md`
- `03-code-resolution-and-source-path-policy.md`
- `04-clarification-and-ambiguity-policy.md`
- `05-execution-discipline-and-transparency.md`
- `06-capability-extensions.md` (optional)

All historical date-stamped planning documents should be moved under an archive path.

### 8.3 Restructure capability-specific design out of core planning

Forecasting design should move into its own capability-specific documentation area.

---

## 9. What Must Be Added

### 9.1 Add a formal concept-type model

The system must explicitly classify user concepts into a finite set, such as:

- Business Event
- Coded Classification
- Direct Field
- Master-Data Attribute
- Segment Discovery Concept
- Cross-System Asymmetric Concept
- Conversation-Scope Reference

This classification must happen before SQL planning.

### 9.2 Add an explicit authoritative source-path protocol

For each concept, the agent must identify the source path it is using:

- dictionary resolution,
- direct field filtering,
- master-data join,
- discovery probe,
- business semantics rule,
- or mixed path with explicit justification.

### 9.3 Add ambiguity classes as first-class runtime objects

Ambiguity must be classified, not vaguely sensed.

Minimum ambiguity classes:

- Entity ambiguity
- Business-event ambiguity
- Source-path ambiguity
- Exact-state vs family-state ambiguity
- Direct-field vs discovery ambiguity
- Conversation-scope ambiguity

### 9.4 Add provenance as a distinct turn type

The system must support user requests such as:

- where did that number come from,
- show the SQL,
- what filter was used,
- how was this computed

without recomputing the answer.

### 9.5 Add explicit topic boundaries

Conversation state must distinguish:

- same topic,
- modified topic,
- extended topic,
- and new topic.

### 9.6 Add a clarification-runtime contract

The runtime must carry explicit pending clarification state and block execution until that state is resolved.

---

## 10. What Must Be Improved

### 10.1 Event Locking

The system must explicitly lock what event the user means before any filter logic is chosen.

This is necessary for terms like:

- active,
- issued,
- approved,
- cancelled,
- submitted,
- in process,
- expired,
- completed.

### 10.2 Concept-Type Discipline

The system must stop treating all unknowns the same way. Not every unknown term should trigger discovery, and not every descriptive phrase should trigger dictionary lookup.

### 10.3 Source-Path Discipline

The system must stop exploring many paths in parallel and then mixing results into one confident answer.

### 10.4 Follow-Up Discipline

Follow-up turns must:

- reuse facts where valid,
- re-derive method every time,
- retain scope only when the user clearly stays on the same topic,
- reset topic assumptions when a new topic starts.

### 10.5 Output Transparency

Every answer should be traceable to:

- a committed interpretation,
- a source path,
- bindings,
- filters,
- and actual executed evidence.

### 10.6 Proportional Execution

The number of executed SQL queries should be driven by unresolved information need, not by open-ended exploration.

---

## 11. What Should No Longer Be a Core Design Device

The following should no longer be central tools for agent improvement:

- product-name-specific examples,
- giant case libraries inside runtime docs,
- hardcoded segment tables as the main operating method,
- historical amendment notes inside active architecture files,
- repeated file-by-file duplication of the same rule.

Named products or product families may still appear in:

- audit documents,
- archived planning,
- evaluation corpora,
- or appendices.

They should not define the active architecture.

---

## 12. Handling of Existing Planning Documents

This plan recommends the following treatment of the existing planning set.

### 12.1 Move to archive after replacement

These documents should be archived once their surviving ideas are absorbed into the new active set:

- `2026-06-03-bpom-neo-context-skill-enhancement.md`
- `2026-06-04-From Query-Centric Reasoning to Information-Centric Reasoning.md`
- `2026-06-04-reasoning-framework-enhancement.md`
- `2026-06-11-follow-up-inheritance-refinement.md`
- `2026-06-12-dimension-reasoning-and-data-coverage.md`
- `2026-06-17-dictionary-grounded-code-translation.md`
- `2026-06-19-execution-discipline-and-trust-transparency.md`
- `2026-06-22-clarification-gate-and-grounded-disambiguation.md`
- `2026-06-24-context-simplification-and-followup-protocol.md`

These are valuable historical records, but should not remain competing active design sources.

### 12.2 Rewrite into active design sources

The active design should be rewritten into a compact architecture set based on the best ideas from the documents above.

### 12.3 Reclassify, not keep in core planning

These should move out of active core planning:

- `2026-06-17-uat-singleturn-test-suite.md`
- `2026-06-18-llm-forecaster-skill.md`

They are useful, but they are not part of the core runtime design.

---

## 13. File-by-File Refactor Intent

### 13.1 `SEEKNAL_ASK.md`

Action:

- Keep file
- Rewrite heavily
- Reduce size
- Remove duplicated domain material
- Keep only orchestration logic

### 13.2 `context/business_glossary.md`

Action:

- Keep file
- Simplify
- Remove answer-like examples
- Keep stable domain ontology
- Remove shortcut-teaching patterns

### 13.3 `context/intent_mapping.md`

Action:

- Keep file
- Strengthen concept typing
- Reduce question-template feel
- Emphasize decomposition and decision structure

### 13.4 `context/code_translation_protocol.md`

Action:

- Keep file
- Preserve as core procedure
- Tighten source-path role
- Make runtime usage mandatory where applicable

### 13.5 `context/data_quality_rules.md`

Action:

- Keep file
- Preserve correctness rules
- Make it strictly about quality and execution rules
- Avoid semantic drift into concept-resolution behavior

### 13.6 `context/data_architecture.md`

Action:

- Keep file
- Preserve topology and structural facts
- Prevent it from becoming a semantic shortcut source

### 13.7 `context/query_recipes.md`

Action:

- Keep file
- Preserve adaptive query templates
- Clarify that recipes are post-resolution execution frameworks only

### 13.8 `seeknal/skills/bpom-analyst/SKILL.md`

Action:

- Keep file
- Rewrite major sections
- Add hard pre-execution gates
- Reduce prose bloat
- Make blocking conditions explicit

### 13.9 `seeknal/skills/evidence-auditor/SKILL.md`

Action:

- Keep file
- Strengthen semantic audit gates
- Turn warnings into verdict logic where appropriate

### 13.10 Runtime ask/clarification path

Action:

- Keep and extend
- Use as operational foundation for clarification-first behavior
- Block execution until clarification resolves

---

## 14. Documentation End State

After refactor, the project should have:

### Active design docs

- small in number,
- clear in ownership,
- non-overlapping,
- method-driven,
- and free of historical accretion.

### Historical design docs

- preserved,
- archived,
- not removed from version control,
- not part of the active runtime design path.

### Runtime docs

- strictly aligned with the final orchestrator/context/skill contract.

---

## 15. Large-Scale Refactor Recommendation

This should be treated as a **major refactor**, not a sequence of isolated micro-fixes.

The system has already accumulated many correct ideas. The problem is that those ideas are currently:

- spread across too many documents,
- repeated in too many places,
- mixed with historical notes,
- and diluted by case-shaped examples.

The correct strategy is therefore:

1. consolidate the architecture,
2. shrink the orchestrator,
3. purify the context layer,
4. harden the skill gating,
5. operationalize clarification,
6. archive historical planning,
7. and keep the anti-hardcode principle as the non-negotiable center.

---

## 16. Final Recommendation

Do **not** delete the whole system and start over.

Do:

- preserve the correct architecture direction,
- remove knowledge-monolith behavior,
- rewrite the active planning/design set,
- simplify `SEEKNAL_ASK.md`,
- restructure `context`,
- harden `skills`,
- operationalize clarification and provenance,
- and retire date-layered planning documents from the active design path.

The final system should know **how to think about the data conditions** and **how to choose the right action**, without being trained through product-by-product answer memory.

