# BPOM Agent Enhancement Proposal
## From Query-Centric Reasoning to Information-Centric Reasoning

**Date:** 2026-06-04  
**Project:** seeknal-bpom-neo  
**Scope:** Context, Skills, SEEKNAL_ASK.md, Multi-turn Reasoning, Discovery Strategy, Evaluation Framework

---

# Executive Summary

Current BPOM agent performance is already strong in many areas:

- Understands most business terminology.
- Can generate valid SQL for common analytical questions.
- Can apply domain-specific filters.
- Can perform multi-step reasoning.
- Can answer many quantitative questions correctly.

However, recent test results and production observations reveal a different class of problems.

The largest gaps are no longer SQL generation problems.

The largest gaps are:

1. Scope continuity failures.
2. Evidence continuity failures.
3. Over-reasoning on simple interactions.
4. Missing information resolution strategy.
5. Excessive ReAct execution for simple questions.
6. Inconsistent totals vs breakdowns.
7. Evaluation framework false failures.
8. Lack of distinction between discoverable and non-discoverable knowledge.

The recommendation is **not** to add more query recipes.

Instead, the recommendation is to evolve the agent into an:

> Information-Centric Analytical Agent

that understands:

- what information is needed,
- where that information should come from,
- when discovery is required,
- when discovery should be skipped,
- when previous evidence should be reused,
- and when no deep reasoning is needed at all.

---

# Current State

## Existing Workflow

Current BPOM workflow:

```text
CAPTURE
↓
PLAN
↓
EXECUTE
↓
REFLECT
↓
GENERATE
```

This workflow is effective for:

- single-turn analytical questions
- known business entities
- straightforward SQL generation

However it assumes every user message requires deep reasoning.

This assumption creates several failure modes.

---

# Problem Area 1
## Excessive Reasoning for Non-Analytical Messages

### Current Behavior

Examples:

```text
Hi
Hello
Thanks
Okay
Continue
```

Agent may still:

- enter CAPTURE
- load context
- create plans
- evaluate intent
- trigger unnecessary reasoning

---

### Impact

- Increased latency
- Unnecessary token usage
- Poor conversational experience
- Resource waste

---

### Root Cause

No conversation routing layer exists before analytical reasoning begins.

Every message is treated as a potential data question.

---

### Recommended Solution

Introduce:

```text
Conversation Gate
```

before all reasoning.

---

### Expected Workflow

```text
USER INPUT
↓
CONVERSATION GATE
```

Classify:

```text
SMALL_TALK
META_DISCUSSION
FOLLOW_UP
DATA_QUESTION
```

Only DATA_QUESTION proceeds to SQL-related reasoning.

---

# Problem Area 2
## Scope Drift Across Follow-Up Questions

### Example

Turn 1

```text
How many high-risk self-manufactured large-industry NIEs in 2024?
```

Answer:

```text
7,705
```

Turn 2

```text
How about per year?
```

Expected:

```text
Same scope
+
GROUP BY year
```

Actual behavior:

Agent often resets scope entirely.

---

### Impact

User perceives:

```text
7705
↓
42061
↓
312021
```

as contradictory answers.

---

### Root Cause

Agent treats follow-up questions as new questions.

No active scope preservation exists.

---

### Recommended Solution

Introduce:

```text
STATE LAYER
```

---

### Expected Behavior

Agent stores:

```json
{
  "entity": "NIE",
  "year": 2024,
  "risk": "high",
  "production": "self-manufactured",
  "industry_scale": "large",
  "system": "ERBA"
}
```

Follow-up questions modify only the requested dimension.

---

# Problem Area 3
## Evidence Continuity Failure

### Current Behavior

Agent answers:

```text
7705
```

Later user asks:

```text
Why is it different?
Where does that number come from?
```

Agent re-runs new queries.

---

### Impact

Different answers appear.

User loses trust.

---

### Root Cause

Agent does not persist evidence objects.

Only final text survives.

---

### Recommended Solution

Store evidence metadata.

Example:

```json
{
  "metric": "NIE",
  "value": 7705,
  "filters": {
    "risk": "high",
    "industry": "large",
    "production": "self"
  }
}
```

---

### Expected Result

Agent can explain:

- source query
- filters
- scope
- origin of numbers

without recomputing.

---

# Problem Area 4
## Missing Information Resolution Layer

### Current Behavior

Agent often jumps directly from:

```text
Question
↓
SQL
```

---

### Impact

Agent may:

- use incorrect columns
- use text search when classification exists
- miss available dictionary mappings

---

### Root Cause

No structured process exists for determining:

```text
What information is needed first?
```

---

### Recommended Solution

Add:

```text
RESOLVE
```

phase.

---

### New Workflow

```text
CAPTURE
↓
STATE
↓
RESOLVE
↓
PLAN
↓
EXECUTE
↓
REFLECT
↓
GENERATE
```

---

# Problem Area 5
## No Information Resolution Hierarchy

### Current Behavior

Agent may immediately search actual data.

Example:

```text
AMDK
↓
ILIKE '%air minum%'
```

---

### Risk

Discovery may fail.

Naming conventions may vary.

Business concepts become unstable.

---

### Recommended Resolution Hierarchy

```text
1. Business Ontology
2. Data Dictionary
3. Schema Discovery
4. Actual Data Discovery
5. User Clarification
```

---

### Principle

Never use data discovery as the first strategy.

Use it only when higher-confidence sources fail.

---

# Problem Area 6
## Recipe Explosion Risk

### Current Behavior

New failures encourage creation of:

```text
R12
R13
R14
R15
...
```

---

### Impact

Maintenance becomes impossible.

Agent becomes example-driven rather than reasoning-driven.

---

### Root Cause

Recipes attempt to solve intent variability.

---

### Recommended Solution

Replace query recipes with query shapes.

---

### Query Shapes

```text
COUNT
TREND
BREAKDOWN
TREND + BREAKDOWN
COMPARE
TOP-N
LIST
```

---

### Example

Instead of:

```text
Recipe:
Trend by region by year
```

Use:

```text
TREND
+
REGION DIMENSION
```

Query compiler assembles final query.

---

# Problem Area 7
## Missing Baseline Filter Injection

### Current Behavior

Agent sometimes remembers:

```text
status_komitmen
```

but forgets:

```text
status
jenis_permohonan
test account exclusions
```

---

### Impact

Inflated results.

Incorrect counts.

---

### Root Cause

Mandatory filters are described narratively.

Not enforced structurally.

---

### Recommended Solution

Baseline Filter Injection.

---

### Rule

For NIE:

Always inject:

```text
status filter
jenis_permohonan filter
test account exclusion
date range
```

before applying additional filters.

Additional filters never replace baseline filters.

---

# Problem Area 8
## Inconsistent Totals vs Breakdowns

### Example

Agent reports:

```text
Total = 119,115
```

but yearly breakdown sums to:

```text
103,085
```

---

### Impact

Contradictory reporting.

Loss of trust.

---

### Root Cause

Totals and breakdowns come from different query scopes.

---

### Recommended Solution

Add consistency validation.

---

### Rule

If:

```text
Total
AND
Breakdown
```

are both reported:

```text
SUM(Breakdown)
≈
Reported Total
```

must hold.

Otherwise REFLECT fails.

---

# Problem Area 9
## Discovery Cost Explosion

### Current Behavior

Discovery can become expensive.

Potential flow:

```text
dictionary
schema
sample data
more data
retry
```

---

### Impact

Timeouts.

Slow responses.

Tool call inflation.

---

### Recommended Solution

Discovery Budget.

---

### Rule

Maximum:

```text
1 dictionary lookup
1 schema lookup
1 data discovery query
```

before planning.

If still unresolved:

- ask user
- report ambiguity

---

# Problem Area 10
## Evaluation False Failures

### Examples

CB-1

```text
Risiko Menengah Rendah
vs
risiko Menengah Rendah
```

CB-6

```text
per tahun
vs
pertahun
```

CB-8

```text
wilayah
vs
daerah
```

---

### Root Cause

Assertions are lexical.

Not semantic.

---

### Recommended Solution

Evaluation should verify:

- semantic meaning
- numerical correctness
- scope correctness

before string matching.

---

# Proposed Future Workflow

```text
USER INPUT
↓
CONVERSATION GATE
↓
STATE
↓
CAPTURE
↓
RESOLVE
↓
PLAN
↓
EXECUTE
↓
REFLECT
↓
GENERATE
```

---

# Expected Benefits

## Faster

- fewer unnecessary tool calls
- reduced context loading

---

## More Accurate

- better scope preservation
- stronger filter enforcement
- consistent totals and breakdowns

---

## More Scalable

- less dependence on query recipes
- less hardcoded business logic
- more reusable reasoning patterns

---

## Better Multi-Turn Performance

- scope continuity
- evidence continuity
- follow-up awareness

---

## Better User Experience

Agent understands:

```text
Hi
```

does not require SQL.

Agent understands:

```text
Why is this number different?
```

requires evidence explanation rather than new queries.

Agent understands:

```text
How about by year?
```

means modify previous scope rather than restart reasoning.

---

# Strategic Direction

The next evolution of BPOM Agent should not be:

```text
More Query Recipes
```

and should not be:

```text
More Hardcoded Business Rules
```

The next evolution should be:

```text
Information-Centric Reasoning
```

supported by:

- Conversation Gate
- State Layer
- Information Resolution Layer
- Query Shape Compiler
- Baseline Filter Injection
- Evidence Continuity
- Consistency Validation
- Discovery Budget
- Semantic Evaluation