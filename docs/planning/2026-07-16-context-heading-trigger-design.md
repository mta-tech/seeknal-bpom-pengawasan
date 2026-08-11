# Context & Skill Trigger Optimization - 2026-07-16

## Problem

Agent needs clear signals to choose which context file to read and which skill to load. Original headings and descriptions were too vague or too specific.

## Solution

### Context Files

Changed first-line headings to descriptive format:

```
#HEADING TEXT IN ALL CAPS#
```

Headings describe WHAT the file contains, not WHEN to read it. Agent decides based on understanding content, not keyword matching.

### Skill Files

Changed YAML frontmatter description to be general and descriptive:

```yaml
description: "Skill type for capability — what it does. How it works."
```

Descriptions explain WHAT the skill IS, not trigger conditions. System chooses based on understanding capability.

## Changes Made

### Context Files (19 files)

| Variant | Files Changed |
|---|---|
| A (v5-predikat-trim) | predikat.md, filter_code_reference.md, data_architecture.md, forecast_guide.md, forecast_recipes.md |
| C (after-refactor-v2) | Same 5 files (identical content) |
| Baseline | 9 files: business_glossary, code_resolution, code_translation_protocol, data_architecture, data_quality_rules, intent_mapping, query_recipes, forecast_guide, forecast_recipes |

### Skill Files (12 files)

| Skill | Variant | New Description |
|---|---|---|
| bpom-analyst | A, B | "Analytical skill for factual data questions — counting, historical trends, breakdowns, rankings, comparisons, and lists. Queries registration data with verified SQL." |
| bpom-analyst | C | "Analytical skill for factual data questions — counting, historical trends, breakdowns, rankings, comparisons, and lists. Uses structured gates with SQL budget control." |
| bpom-analyst | Baseline | "Orchestrator skill for factual data questions — counting, historical trends, breakdowns, rankings, comparisons, and lists. Runs full pipeline from context load to evidence audit." |
| bpom-forecaster | All | "Forecasting skill for predicting future registration trends. Computes projections deterministically from historical data with quality labels." |
| detect-anomaly | All | "Anomaly detection skill for identifying unusual patterns in registration time series. Detects outliers and explains data irregularities." |
| evidence-auditor | Baseline | "Verification skill for auditing SQL evidence before answering. Checks scope, filters, consistency, and fabrication. Returns PASS or FIX with specific issues." |
| database-analyst | Baseline | "Generic database analysis skill for read-only connected sources. Discovers schema, queries data, and answers with evidence." |
| business-question-answering | Baseline | "Strategic business analysis skill for questions about opportunities, priorities, and recommendations. Translates business concepts into actionable insights." |

## Key Design Principles

1. **Descriptive, not prescriptive** — describe WHAT, not WHEN
2. **General, not specific** — no listing of entity names or data types
3. **No technical details** — no internal mechanisms or tool names
4. **No trigger keywords** — system decides based on understanding
5. **Consistent format** — same approach for context and skill files

## Version Bumps

| Skill | Old Version | New Version |
|---|---|---|
| bpom-analyst (A/B) | 4.0.0 | 4.0.1 |
| bpom-analyst (C) | 4.0.0 | 4.0.1 |
| bpom-analyst (Baseline) | 2.0.0 | 2.0.1 |
| bpom-forecaster | 6.0.0 | 6.0.1 |
| detect-anomaly | 1.0.0 | 1.0.1 |
| evidence-auditor | 1.0.0 | 1.0.0 (unchanged) |
| database-analyst | 1.1.0 | 1.1.0 (unchanged) |
| business-question-answering | 1.0.0 | 1.0.0 (unchanged) |
