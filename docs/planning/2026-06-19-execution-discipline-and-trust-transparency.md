# seeknal-bpom-neo: Execution Discipline & Trust-Through-Transparency

**Date:** 2026-06-19
**Reference audits:**
- `docs/audit_context/uat_audit_report_15jun2026.md` — the canonical target spec (RC-1…RC-6, additions AF-1…AF-6, hypotheses H6–H8, recommendations R1–R13, and the §10 output-format spec). This is the **acuan**.
- `docs/audit_context/audit_concurrency_production_18jun2026.md` — the SQL-execution evidence (RC-A…RC-E) from the 18 June concurrency-production runs.

**Principle (unchanged, non-negotiable):** we do **not** hardcode answers. Every change below is a *reasoning policy* — teaching the agent *when* to do *what*, *why*, *with which source*, and *how* — so it generalizes to unseen phrasings. Putting every question into context is brittle; teaching the way of thinking makes the system know *kapan harus melakukan apa, untuk apa, pakai apa, bagaimana caranya*.

**Flow (unchanged):** `SEEKNAL_ASK.md` (orchestrator) → loads `context/*.md` on demand → invokes `seeknal/skills/*`; docs live in `docs/`. The system behaves as an agent that maps → chooses → executes to answer data questions against `rpo_v2`.

---

## 1. What this rework is (and is not)

The 17–18 June changes (`dictionary-grounded-code-translation`, `dimension-reasoning`, `llm-forecaster`) corrected **facts** (RC-2, RC-3, RC-4, canonical "total NIE", coverage-aware columns) and added forecasting. The 18 June evidence shows the next bottleneck is **not more facts** — it is:

1. one **fact that did not close** (cross-system risk scope — RC-1 still returns 98.231 for MT),
2. **uncontrolled execution** (simple questions fan out into 10+ SQLs; unfamiliar concepts loop to empty answers),
3. a **REFLECT step that audits but does not block**,
4. and **no transparency contract** so the same question is answered differently each session.

This rework is therefore about **discipline + transparency**, plus repairing the single open fact. It deliberately leaves the working machinery alone.

---

## 2. Current-state map (analyzed before planning)

| Layer / File | What it does today | Status |
|---|---|---|
| `SEEKNAL_ASK.md` | Decision OS: gate → Semantic Commitment → State Comparison → route (FORECAST→forecaster, else analyst); §2 behavioral contracts; §4 canonical defs + segment codes; §5 info hierarchy; §6 guardrails | **Mostly keep.** §2 ALL-TIME-UNION default competes with risk-isolation (see F1); §5 "dictionary mandatory for every coded term" lacks proportionality (A1) |
| `context/business_glossary.md` | Concept reference; risk structural facts at `:87–93`, `:253–262` | **Fix:** `:258` "use ERBA-only for risk analysis" contradicts `:90` "ERLA contributes when combined" → F1 |
| `context/code_translation_protocol.md` | Two-way, sumber-aware dictionary lookup; ambiguity loop resolves equivalence by **COUNT-test** (`§3`) | **Fix:** cross-system risk equivalence is *definitional*, must not be decided by a data probe → F1 |
| `context/code_resolution.md` | Dictionary JOIN mechanics (AKRONIM, region `/100`, fallbacks) | Keep |
| `context/data_quality_rules.md` | Mandatory filters; **RC-2 jenis_permohonan conditional (`:61`)**; **RC-4 commitment Case A/B (`:77`)**; coverage-aware columns (`:127`); ERBA casts; status_komitmen normalization; date-column rules | **Keep** (RC-2/RC-4 already correct). Add verb-semantics for "disetujui/diterbitkan" → F2 |
| `context/intent_mapping.md` | Schema-linking: decomposition, Step-0 normalize, segment resolution, ENTITY/DIMENSION registries, risk/skala/daerah/SLA/komitmen | **Keep + extend.** No entries for klaim / peruntukan / expiry / company-ranking → A2 |
| `context/query_recipes.md` | Adaptive R1–R13; **`:10` already teaches ONE query `GROUP BY year` + separate global total / `ROLLUP`** | **Keep + leverage** — this is the engine for the A4 matrix |
| `context/forecast_*.md` + `bpom-forecaster` | 6-phase forecast pipeline | **Keep** (FORECAST 2→8/12; works) |
| `seeknal/skills/bpom-analyst/SKILL.md` | PHASE 0→CAPTURE→RESOLVE→PLAN→EXECUTE→REFLECT→GENERATE; binding gate; Synthesis Patterns A–G; soft "~12 tool-call" stop (`PHASE 4`) | **Enhance:** add Authoritative-Path/proportionality (A1), completion guarantee (A3), matrix output (A4) |
| `seeknal/skills/evidence-auditor/SKILL.md` | Audit checklist A–E with PASS/FIX/HONEST-FAIL verdicts | **Enhance:** it *checks* "ERLA has 3 levels" but does not **block** a collapsed answer → E1 |
| Follow-up machinery (State Comparison Engine, inherit-ANSWERS/re-derive-METHODS, Conversation Ledger) | Multi-turn handling | **DO NOT TOUCH** (works; user-confirmed) |
| Harness `scripts/test_multiturn_v3.py` | Exact-substring scoring; no tolerance; `assert_not_contains` unread | **Enhance (measurement only):** separate substantive/presentation/empty → E2 |

---

## 2.1 Source-of-truth precedence (must be explicit before implementation)

One reason the system drifted is that multiple files can currently answer the same question from
different angles. This rework must lock the precedence order so future edits cannot reintroduce
contradictions.

| Priority | File / Layer | Authority |
|---|---|---|
| P1 | `SEEKNAL_ASK.md` | Global routing, lane selection, canonical defaults, answer-contract selection |
| P2 | `context/data_quality_rules.md` | Mandatory filters, date-column identity, status logic, Case A/B commitment branching |
| P3 | `context/code_translation_protocol.md` | Runtime code meaning, inbound/outbound dictionary procedure, `sumber` discipline |
| P4 | `context/business_glossary.md` | Business concepts that are **not** resolved from dictionary (ontology, metric meaning, segment/business semantics) |
| P5 | `context/intent_mapping.md` | Parsing user wording into entity/operation/dimension/condition and choosing query shape |
| P6 | `context/query_recipes.md` | Query frameworks once intent + rules are already resolved |
| P7 | `seeknal/skills/*` | Execution workflow, enforcement, answer generation, and blocking behavior |

**Rule:** if two files disagree, the higher-precedence file wins; the lower-precedence file must be
rewritten to point upward instead of restating a conflicting rule.

---

## 3. KEEP — working well, do not change

- **Follow-up / multi-turn** (State Comparison Engine, inherit-answers/re-derive-methods, Conversation Ledger). Explicitly out of scope.
- **RC-2** jenis_permohonan-by-intent (`data_quality_rules.md:61`) and **RC-4** commitment Case A/B (`:77`).
- **ERBA TEXT casts**, `status_komitmen` ROUND-normalization, NULL-tanggal guard, date-column identity (NIE→`tanggal`, permohonan→`tanggal_bayar`).
- **Coverage-aware column choice** (`data_quality_rules.md:127`).
- **`query_recipes.md:10`** one-query breakdown + separate global total / `ROLLUP` — reuse it, don't rewrite it.
- **Forecaster** skill and routing.
- **Honesty guardrails**: no fabrication, no test-data-as-source, report failures plainly.
- **Non-data conversation classes**: `SMALL_TALK`, `META`, `OUT_OF_SCOPE`, and communication alignment behavior remain unchanged.
- **Support skills not on the main runtime path** (`database-analyst`, `business-question-answering`) are not expanded in this rework unless a rule is explicitly migrated into `bpom-analyst`.

---

## 4. FIX — broken / contradictory (correctness)

### F1 — Cross-system risk scope: one deterministic ontology, out of the COUNT-test path  *(closes RC-1 / RC-A; audit R1, R8)*
**Problem (18 June evidence):** UAT-MT-2 → `ERBA 302 UNION ERLA jenis_dokumen 303 (MT+MR)` = **98.231** (should be 11.919, ERBA-only); UAT-MR-1 → ERBA-only `303` = **41.516** (should be **119.374** = ERBA 303 + ERLA 301). Opposite treatment of ERLA, because three instructions disagree and a fourth (`code_translation_protocol §3`) tells the agent to *probe magnitudes* to decide a *definitional* question.

**Teach (not hardcode):** a single **Cross-System Risk Equivalence** reasoning block, stated once, applied deterministically:
- ERBA carries 4 levels (`kategori_dokumen`); ERLA carries 3 (`jenis_dokumen`) and **cannot isolate Menengah Tinggi**.
- Decision rule by *isolatability*, not by data magnitude:
  - **Menengah Tinggi** → **ERBA-only**; state "ERLA cannot isolate MT" (never UNION ERLA medium into an MT count).
  - **Menengah Rendah / Low** → **ERBA `303` + ERLA `301`** (equivalent), combined; state the lossy mapping.
  - **Tinggi** → ERBA + ERLA `302`; **Tinggi Notifikasi** → ERBA-only.
- Remove the contradictory line `business_glossary.md:258` ("use ERBA-only for risk analysis"); replace with a pointer to this block.
- `code_translation_protocol.md`: keep COUNT-test for *true* ambiguity (unknown code, typo), but **exclude the risk-level equivalence from it** — equivalence is ontology, resolved from this block.

This is ontology (like "UMKM = skala 1+2+3"), reusable for any phrasing — not a per-question answer.

### F2 — Verb semantics: "disetujui / diterbitkan / diproses / diajukan"  *(closes RC-B)*
**Problem:** UAT-JP-MAYOR-2025 counted *submitted* (`tanggal_bayar`) when the user said *disetujui* → 8.153 vs 6.636.
**Teach:** in `intent_mapping.md` (verb register) + `data_quality_rules.md`, map the lifecycle verb to (entity, date column, status):
- *diterbitkan / terbit / disetujui (as an issued NIE)* → NIE entity, `tanggal`, valid-NIE status.
- *diajukan / masuk* → permohonan, `tanggal_bayar`, no status filter.
- a `jenis_permohonan` (mayor/minor/baru) is a **scope filter**, independent of the lifecycle verb.

---

## 5. ADD — missing capabilities (control · coverage · transparency)

### A1 — Authoritative-Path & proportional execution  *(audit R7; AF-1, AF-6; closes RC-D)*
**Problem:** UAT-AMDK-1 (a one-query scalar) ran **10 SQLs** — STATUS looked up 5× and discovery run for the already-known `jenis_pangan='1401'`.
**Teach** (in `SEEKNAL_ASK.md §5` + `bpom-analyst` PHASE 2–4):
- **Resolve once, reuse:** each `data_dictionary` `kategori` is looked up **at most once per turn**; record the binding and reuse it.
- **Skip what's already authoritative:** if a code is fixed in `SEEKNAL_ASK.md §4` / glossary (AMDK, Garam, AMDK status list), use it directly — no discovery probe.
- **Dictionary is for translation/disambiguation, not for applying known mandatory filters** (a plain NIE count does not need to "translate" STATUS).
- **Authoritative path:** when the question resolves to one entity + one metric + one time column + one system scope + ≤1 coded filter → `1 binding (if needed) + 1 final query + ≤1 verification`. Branch only if the first result is structurally suspicious.
- Make the "~12 tool-call" stop rule **binding**, not advisory.

### A2 — Direct-field concept guides  *(audit R9; AF-4; closes RC-C)*
**Problem:** KLAIM-1/2/3 looped 24 tool-calls of `ILIKE` guessing → empty.
**Teach** concise reasoning guides in `intent_mapping.md` + `business_glossary.md` for the under-taught concepts — **klaim** (`klaim` / `klaim_label`), **peruntukan**, **expiry / kadaluarsa** (`tanggal_exp`), **company ranking** (`m_trader.*` canonicalization). Each guide states: canonical metric · primary column · dictionary lookup needed? · default scope · common pitfalls. General reasoning, not per-question SQL.

### A3 — Completion guarantee (never empty)  *(audit R11; AF-2)*
**Teach** (in `bpom-analyst` GENERATE): if ≥1 authoritative query succeeded and no blocking ambiguity remains, the agent **must** emit an answer. If a concept could not be resolved within the probe budget, answer **best-effort with a stated limitation** — never return an empty string. (Pair with E2 so genuine orchestrator no-run drops are tracked separately.)

### A4 — Output contract: transparent matrix from ONE query  *(audit R12, R13, §10; addresses H8/RC-5 determinism)*
**Teach** a stable presentation contract in `bpom-analyst` GENERATE + `SEEKNAL_ASK.md`:
- A COUNT is presented as a matrix: **rows = years** (or months); **columns = system × the code dimension relevant to *this* question** (status for plain counts, **risk for risk questions**, jenis_permohonan for application-type questions — *parameterized, not always status*); a **Total** row/column; `-` for absent system/period; a short *Keterangan* (code definitions) and *Filter* block.
- **Critical coupling (see §7):** the matrix is **displayed from a single grouped query** (reuse `query_recipes.md:10` `GROUP BY system, <code>, date_trunc('year')` / `ROLLUP`). It is a *presentation* of one result set, **never** gathered by one query per cell.
- **Proportionality:** a tightly-scoped scalar (e.g. "AMDK 2023") gets a compact shape (scalar + small breakdown), not a full multi-year matrix. Shape is keyed to question scope; *same class of question → same shape* (kills session-to-session variance).

### A5 — Context-load and token-discipline rules  *(supports A1; prevents context inflation)*
**Problem:** query inflation is only half the issue; the current workflow also re-reads too much
context too often, which increases reasoning noise and delays commitment.

**Teach** in `SEEKNAL_ASK.md` + `bpom-analyst`:
- **Phase 0 base load stays minimal**: only files needed to define global runtime invariants are
  loaded unconditionally.
- Additional context files are **conditional by need**:
  - `intent_mapping.md` when parsing or dimension decomposition is needed,
  - `query_recipes.md` only once intent + filters are already resolved,
  - `data_architecture.md` only when table/join topology is still unresolved,
  - `business_glossary.md` only for ontology/segment/metric meaning,
  - `code_translation_protocol.md` only for coded terms actually present this turn.
- Re-reading for re-derive-methods remains valid, but it must target the **smallest authoritative
  file**, not reload the whole context set reflexively.

### A6 — Intra-turn binding/cache policy  *(supports A1 and determinism)*
The current planning says "resolve once, reuse" but does not define what may be reused. This
rework must make it explicit:
- A dictionary lookup result for the same `(kategori, sumber, normalized_term)` may be reused
  within the same turn.
- A segment discovery result may be reused within the same turn only after it is promoted to the
  turn's **authoritative binding**.
- A quick verification count may be reused within the same REFLECT round, but not carried as a
  business fact into the next turn.
- Cross-turn reuse still applies **only to answers**, never to bindings or methods.

---

## 6. ENHANCE — strengthen existing

### E1 — REFLECT: from checklist to blocking gate  *(audit R8; AF-5)*
`evidence-auditor/SKILL.md` currently *checks* but ships anyway. Add explicit **BLOCK** conditions — the agent must NOT collapse into one number, and must instead answer per-system with the stated limitation (or re-resolve), when:
- a risk level is not isolatable across systems (MT in ERLA),
- commitment Case A vs B is unresolved,
- segment scope is broad-vs-strict ambiguous,
- per-year rows materially contradict the grand-total logic.
Verdict set becomes PASS / FIX / **BLOCK-AND-SCOPE** / HONEST-FAIL.

### E2 — Harness: separate failure classes  *(audit R10; H8 — measurement only, not agent)*
In `scripts/test_multiturn_v3.py`: classify each failure as **substantive / presentation / empty**; add numeric tolerance + Indonesian thousands normalization; wire the currently-dead `assert_not_contains`; report infra/no-run separately. This lets us tell whether a change improved reasoning vs hurt presentation — without touching the agent.

### E3 — Limited-answer contract  *(supports E1 and A3)*
`LIMITED_ANSWER` / `BLOCK-AND-SCOPE` must have a stable final form so implementation does not
improvise. The answer contract is:
- state the exact part that is answerable,
- state the exact part that is not safely collapsible,
- give separated per-system or per-scope figures when available,
- explicitly name the blocking ambiguity,
- do **not** emit one synthetic grand total if that total would mislead.

This keeps the answer useful while preserving epistemic honesty.

---

## 7. Design note — reconciling Transparency (R13) with Economy (R7)

These two asks appear to conflict (maximal detail vs minimal queries). They reconcile under **one rule**: **transparency is a property of how we *display* a single query, never of how many queries we run.**
- The full matrix comes from **one** `GROUP BY system, <relevant_code>, date_trunc('year')` (+ `ROLLUP` for totals) — already sanctioned by `query_recipes.md:10`.
- **Forbidden:** one query per cell / per code / per year (the exact RC-D inflation).
- Status/risk definitions for the *Keterangan* come from the **one** deduped dictionary lookup (A1), not per-row probes.
- The "Consistency" leg of the Trust Equation is also a **determinism lever**: a fixed shape per question-class directly attacks RC-5 (non-determinism) and the harness false-fails (H8).

If A4 ships without A1, transparency re-imports inflation — so **A1 and A4 must ship together**.

---

## 7.1 Output contracts beyond COUNT

The audit-grade matrix is only for COUNT-like outputs. The plan must also stabilize the answer
shape for the other operation families so determinism improves system-wide:

| Operation | Contract |
|---|---|
| `LIST` | compact table of row-level records with explicit scope and limit note; no matrix |
| `TOP` | ranked table, grouping basis stated explicitly, total population note if truncated |
| `COMPARE` | side-by-side table plus one-line conclusion naming the winning side and basis |
| `TREND` | period rows + total/summary line + short directional interpretation |
| `INVESTIGATE` | observation → decomposition evidence → bounded hypothesis; never policy speculation |
| `AGE / SLA` | bucket summary first, oldest-item detail only when explicitly requested |
| `EXPLAIN_EVIDENCE` | no new SQL; arithmetic or restatement over ledgered facts, with operands shown |

**Rule:** each operation family gets one canonical display shape. Equivalent questions should not
change format session-to-session.

## 7.2 Output size bounds

Transparency must not turn every answer into an unreadable dump. Add explicit limits:
- default matrix period span = user scope; if all-time covers many years, show all years only when
  the user asked for trend/distribution, otherwise compact with a note that detailed yearly rows
  are available.
- ranking/list defaults remain top-10 unless user asks otherwise.
- `Keterangan` and `Filter` blocks must be concise and deduplicated.
- when the truthful breakdown is very wide, prefer a summarized matrix plus a short note over
  uncontrolled table growth.

This is a presentation policy, not a reasoning shortcut.

---

## 8. Anti-hardcode position

Every item is a *procedure or ontology*, not an answer table:
- F1 risk equivalence = ontology (which level maps across systems), like UMKM = scale 1+2+3 — applies to any phrasing.
- A1/A3 = execution policy (how many probes, when to stop, must finalize).
- A2 = concept reasoning (canonical metric/column/scope), not memorized counts.
- A4/E1 = presentation + gating policy.
No per-question SQL is stored; the dictionary remains the runtime source of code meanings (the 17 June protocol stays).

---

## 8.1 File-level change map

To avoid implementer guesswork, the intended edit shape is:

| File | Action type | Purpose |
|---|---|---|
| `SEEKNAL_ASK.md` | revise | lane selection, canonical defaults, answer-contract selection, context-load proportionality |
| `context/business_glossary.md` | revise | risk ontology fix, direct-field guides, remove/replace conflicting statements |
| `context/data_quality_rules.md` | extend | verb semantics, reinforce filter precedence, keep RC-2/RC-4 intact |
| `context/intent_mapping.md` | extend | direct-field concepts, operation-family output intent, parsing additions |
| `context/code_translation_protocol.md` | revise | remove risk-equivalence from COUNT-test path; keep source-aware dictionary procedure |
| `context/query_recipes.md` | extend lightly | grouped-query support for transparent output shapes, not new hardcoded scenario pairs |
| `seeknal/skills/bpom-analyst/SKILL.md` | revise | authoritative path, context-load discipline, completion guarantee, output contracts |
| `seeknal/skills/evidence-auditor/SKILL.md` | revise | blocking verdicts and limited-answer enforcement |
| `scripts/test_multiturn_v3.py` | revise | measurement/reporting only, not runtime reasoning |

No change is planned for:
- `bpom-forecaster` logic,
- follow-up ledger/state-comparison behavior,
- `code_resolution.md` mechanics unless a referenced contradiction forces wording cleanup.

## 8.2 Planning-document governance

This plan becomes the active implementation reference for the June 19 rework. Earlier planning
docs remain historical context, but where they conflict with this document, this document wins.
The implementation pass should annotate or cross-reference earlier planning docs rather than trying
to satisfy contradictory instructions from multiple dates.

---

## 9. What we deliberately do NOT change

Follow-up/multi-turn machinery · the two-way dictionary protocol (only narrowing risk-equivalence out of COUNT-test) · ERBA casts & normalization · RC-2/RC-4 rules · coverage-aware columns · forecaster · honesty guardrails · the 7-phase skeleton (we tune its weight, not its shape).

---

## 10. Expected impact (mapped to evidence)

| Item | Target |
|---|---|
| F1 | UAT-MT-2 → ~11.919 (not 98.231); UAT-MR-1 → ~119.374 (not 41.516); MT/MR stable across sessions |
| F2 | UAT-JP-MAYOR-2025 → ~6.636 |
| A1 | UAT-AMDK-1 SQL 10 → ≤3; avg SQL/case back below the 4.95 baseline |
| A2 + A3 | KLAIM 0/3 → answered or honest-limitation (never empty); empty-answer count down |
| A4 | same question → same matrix shape (determinism); every number user-verifiable |
| E1 | no collapsed cross-system risk numbers shipped as if exact |
| E2 | regression reports distinguish reasoning vs presentation vs runtime |

## 10.1 Acceptance metrics (make success measurable)

Target thresholds for the first implementation pass:
- **Direct-lane execution budget:** median SQL/query count for simple scalar cases ≤ 3.
- **Empty-answer rate:** 0 for cases where at least one authoritative query succeeded.
- **Determinism:** repeated fresh-session runs of the same high-frequency question produce the same
  scope, same number, and same answer contract.
- **Risk/commitment correctness:** UAT-MT, UAT-MR, MR dibatalkan, and total NIE 2025 all move into
  the substantive-pass bucket.
- **Harness reporting:** every failed case is labeled `substantive`, `presentation`, or `empty`;
  uncategorized failures are not allowed.

---

## 11. Sequencing (phased, highest-leverage first)

- **Phase 1 — Correctness:** F1 (risk equivalence) + E1 (blocking gate). Biggest substantive-failure reduction; pure teaching-consistency.
- **Phase 2 — Control:** A1 (authoritative path / dedup / proportionality) + A3 (completion). Cuts SQL inflation and empty answers.
- **Phase 3 — Transparency + coverage:** A4 (matrix, built on A1) + A2 (direct-field guides) + F2 (verb semantics).
- **Phase 4 — Measurement & verify:** E2 (harness classes) + live-DB verification (§12).

## 11.1 Dependency order (implementation-safe)

- `2.1 precedence` must be applied before context rewrites, otherwise contradictions can be
  reintroduced while editing.
- **F1 must land before E1**, because the blocking gate needs the final ontology to enforce.
- **A1 must land before A4**, because transparent output without authoritative-path control will
  increase SQL inflation.
- **A3 depends on E1**: the system should only guarantee completion after it knows when to block
  rather than fabricate.
- **A2 should land before broad output-contract rollout** so under-taught concepts do not inherit
  generic but wrong shapes.
- **E2 is last**; it should measure the final runtime behavior, not drive it.

---

## 12. Verification (run when the DB tunnel is active)

1. Re-run UAT subsets that exercise each fix: `--scenario UAT-MT`, `UAT-MR`, `UAT-TREN-RISK`, `UAT-AMDK`, `UAT-JP`, `KLAIM`.
2. Confirm against live `rpo_v2`: ERBA `kategori_dokumen='302'` ≈ 11.919; ERBA `303` + ERLA `301` ≈ 119.374; ERLA `jenis_dokumen='303'` ≈ 84k (proves it is MT+MR, not MT).
3. Measure execution: SQL/case and tool-calls/case before vs after on matched `scenario_id`s (the script in `audit_concurrency_production_18jun2026.md` Appendix A).
4. Determinism check: ask the same "total NIE 2025" / MT / MR question across 3 fresh sessions → identical scope, number, and matrix shape.
```bash
uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/singleturn --scenario UAT-MT
uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/singleturn --scenario KLAIM
```

## 13. Documentation end-state after implementation

Once the rework ships, documentation should be left in a clean, non-contradictory state:
- this planning doc remains the historical design record for the June 19 rework,
- updated runtime truth lives in `SEEKNAL_ASK.md`, `context/*.md`, and `seeknal/skills/*`,
- earlier superseded reasoning in prior planning docs should be referenced as historical, not as
  live behavioral instructions,
- the audit doc remains the evidence base; it should not become the runtime rule source.

The system should have one clear story:
`audit findings` → `planning decision` → `runtime contract`.
