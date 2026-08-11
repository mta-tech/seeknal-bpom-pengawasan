# seeknal-bpom-neo: Forecasting Simplification Note

**Document type:** Implementation note  
**Date:** 2026-06-25  
**Status:** Applied to active runtime files  
**Scope:** `context/forecast_guide.md` · `context/forecast_recipes.md` · `seeknal/skills/bpom-forecaster/SKILL.md`

---

## 1. Purpose

This note records the simplification applied to the forecasting path.

The objective was not to change the forecasting method.
The objective was to reduce context weight, remove excessive narration, and keep only the minimum rules needed for deterministic forecasting.

---

## 2. Why the Simplification Was Needed

The prior forecasting path was correct in principle but too heavy in practice.

Problems:

- too many narrative explanations,
- too many repeated rules across guide, recipes, and skill,
- overly rigid presentation instructions,
- too much attention spent on internal mechanics instead of runtime decisions.

This created unnecessary context load for a capability that should stay narrow and deterministic.

---

## 3. What Stayed the Same

These principles remain unchanged:

- forecasting is separate from ordinary analytical Q&A,
- forecasting is ERBA-focused,
- forecasting is SQL-first and deterministic,
- LLM must not invent forecast arithmetic,
- eligibility must be checked before forecasting,
- 24-month backtest remains the quality gate,
- output still follows the user's language.

---

## 4. What Was Simplified

### 4.1 `context/forecast_guide.md`

Simplified into a short rule file covering only:

- source scope,
- what may be forecast,
- refusal cases,
- eligibility gate,
- method summary,
- backtest gate,
- horizon policy,
- output rules.

Removed:

- long explanatory sections,
- large validated simulation tables,
- detailed vocabulary tables,
- long user-facing block contracts.

### 4.2 `context/forecast_recipes.md`

Reduced to the core SQL templates only:

- base filters,
- eligibility,
- monthly history,
- diagnostics,
- backtest,
- point forecast,
- interval.

Removed:

- long commentary around each query,
- extended interpretation text,
- extra formatting instructions embedded in the SQL reference.

### 4.3 `seeknal/skills/bpom-forecaster/SKILL.md`

Reduced to a short operational playbook:

`LOAD -> CAPTURE -> CHECK -> BACKTEST -> FORECAST -> PRESENT`

Removed:

- long phase-by-phase prose,
- rigid 7-block output contract,
- duplicated logic already covered in forecast context files,
- excessive internal presentation requirements.

---

## 5. Size Reduction

Approximate reduction after simplification:

- `forecast_guide.md`: 368 -> 139 lines
- `forecast_recipes.md`: 476 -> 230 lines
- `bpom-forecaster/SKILL.md`: 391 -> 115 lines

Total:

- before: 1,235 lines
- after: 484 lines

This materially reduces forecast-specific context load while preserving the forecasting method.

---

## 6. Design Direction After Simplification

Forecasting should now behave as:

- a narrow specialist path,
- deterministic and SQL-backed,
- simple to route,
- simple to read,
- simple to maintain.

The agent should spend its effort on:

- deciding whether a forecast is allowed,
- running the correct queries,
- and presenting a short practical result.

It should not spend its effort replaying long methodological narration unless the user explicitly asks for methodology details.

---

## 7. Governance Rule

If forecasting behavior changes in the future:

- keep the method deterministic,
- keep the files short,
- avoid rebuilding a large narrative forecasting manual inside active runtime files.

If detail is needed again, prefer:

- a separate historical/design note,
- or a methodology appendix loaded only when explicitly requested,

not a large always-loaded runtime instruction set.
