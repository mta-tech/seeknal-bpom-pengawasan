# Seeknal Ask — project guidance (Dev VM / BPOM NeonDB sample)

> This file is loaded into the agent's context for every session in this
> project. It carries **project-specific** conventions and is NOT part of
> seeknal core. (SEEK5 Phase 4 — the permissive clarification nudge lives
> here, not in hardcoded prompts.)

## Clarification (SEEK5 `request_clarification`)

A `request_clarification` tool is available in this (headless/worker)
environment. Use it when the user's question is **genuinely ambiguous** and
the different interpretations would produce materially different answers.

This database (BPOM regulatory data) has several concept types where a single
word maps to multiple valid interpretations. When the user's question leaves
one of these unresolved, **call `request_clarification`** with 2-3 concrete
options (mark the most likely one `recommended`) **before** running data SQL.

### Ambiguity types that require clarification

**1. Data system / source** — ERBA and ERLA are two separate registration
systems with non-overlapping data. When the user asks about NIE, produk, or
registrations without stating which system, the query scope is fundamentally
different. Ask which system (ERBA, ERLA, atau gabungan keduanya).

**2. Object / product scope** — When the user names a product category broadly
(e.g., "susu", "formula bayi", "AMDK", "minuman"), the term may match multiple
sub-categories, jenis_pangan codes, or segments that yield different results.
Ask which sub-category or scope is intended before running SQL.

**3. Status / filter dimension** — Words like "aktif", "terdaftar", "berlaku",
or "bulan ini" may refer to different dimensions: NIE status, permohonan that
were processed, komitmen, or a time filter on a specific date column. Ask
which dimension the user means.

### When NOT to ask
- The question is specific enough — the user named the exact code, scope,
  status, or period.
- The ambiguity is only cosmetic (typo, informal phrasing, clearly resolvable
  from context) — proceed with the most reasonable interpretation and state
  the assumption explicitly.
- You already clarified the same concept earlier in this conversation — reuse
  that answer; do not re-ask.
- Only one interpretation produces non-empty data — confirm via COUNT-test,
  then state the basis.

### How it works
After you call `request_clarification`, **the turn ends**. The user's answer
arrives as the **next message**; bind it and proceed directly to the query —
do not re-ask the same question.

### Multi-slot form — ask all unclear aspects at once
One `request_clarification` call supports **1–3 slots**. Each slot is one
question with its own set of answer options.

- **When more than one aspect is unclear** (e.g., system AND product scope),
  put each as a separate slot in **one call** — do not defer slot 2 to the
  next turn.
- **Options per slot**: 2–4 options. A free-text "fill in your own" field is
  added automatically by the UI — do not add one yourself.
- **Recommended**: mark one option `recommended: true` per slot.
- **Rule**: 2 ambiguous aspects → 2 slots, 1 call. 3 aspects → 3 slots, 1 call.