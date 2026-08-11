# seeknal-bpom-neo: Dictionary-Grounded Code Translation (Two-Way Resolution Gate)

**Document type:** Implementation Plan (teach-the-thinking enhancement)
**Project:** seeknal-bpom-neo (BPOM RPO Analytics Agent)
**Status:** Implemented — Phase 1 (2026-06-17) + Phase 2 analytical extension (2026-06-17). Pending live-tunnel regression (§11).
**Date:** 2026-06-17
**Scope:** `context/code_translation_protocol.md` (NEW) · `context/code_resolution.md` · `context/business_glossary.md` · `context/intent_mapping.md` · `context/data_quality_rules.md` · `context/query_recipes.md` · `context/data_architecture.md` · `seeknal/skills/bpom-analyst/SKILL.md` · `seeknal/skills/evidence-auditor/SKILL.md` · `SEEKNAL_ASK.md`
**Phase 2 additions:** `context/intent_mapping.md` (INVESTIGATE + AGE operations; Durasi/SLA dimension) · `context/query_recipes.md` (R12 aging; R13 root-cause decomposition) · `seeknal/skills/bpom-analyst/SKILL.md` (Synthesis Pattern F root-cause; Synthesis Pattern G SLA/aging)
**Amends / supersedes:** `docs/planning/2026-06-12-dimension-reasoning-and-data-coverage.md` §5 — replaces the *hardcoded* ERBA/ERLA risk-collision table with a *runtime dictionary lookup* (the anti-hardcode evolution of the same problem).
**Evidence base:** `docs/audit_context/uat_audit_report_15jun2026.md` + direct verification against live `rpo_v2` (2026-06-17).

---

## 1. Background

The UAT of 15 June 2026 (57 questions across 14 conversations) showed the agent producing wrong
numbers on **static historical data** (2023/2024) that, by definition, cannot move. A wrong number
on unchanging data proves the generated SQL is structurally wrong — not that data drifted. The full
audit is in `docs/audit_context/uat_audit_report_15jun2026.md`.

The 12 June plan already intended to correct the ERBA/ERLA risk collision (§5 of that doc), yet the
UAT shows the collision still mis-fires (Risiko Menengah Tinggi all-time = 95,736 vs a true ~11,923).
Investigating *why a documented fix did not hold* surfaced the real, deeper root cause:

> **The meaning of every code is cached as a finished answer inside the context files**
> (`business_glossary.md`, `intent_mapping.md`, `code_resolution.md`, `query_recipes.md`).
> These caches are (a) wrong, (b) incomplete, and (c) mutually contradictory. Because the context
> already "answers", the agent skips the `data_dictionary` lookup that `SKILL.md` already prescribes.
> The agent therefore translates codes **from memory, not from the source.**

This plan stays faithful to the project philosophy — **teach the agent how to think, never hardcode
answers** — and pushes it one level further: the agent must **never decide what a code means; it must
look the meaning up**, every time, in the authoritative source, in both directions (word→code when
building filters, code→definition when answering).

### 1.1 What the database actually shows (live `rpo_v2`, 2026-06-17)

| Finding | Evidence |
|---|---|
| `data_dictionary` is rich, not tiny | **1,141 rows** (the "9 rows" seen before was a stale `pg_stat` estimate) |
| The dictionary has a **`sumber`** column | values: `ERBA`, `ERLA`, `ERBA dan ERLA`, `ERLA dan ERBA` — this is the ERBA/ERLA disambiguator |
| Risk uses **different category names**, not the same one | ERBA risk = `KATEGORI_DOKUMEN` (sumber `ERBA`); ERLA risk = `JENIS_DOKUMEN` (sumber `ERLA dan ERBA`) |
| ERLA has **3 risk levels**, not 4 | `JENIS_DOKUMEN`: 301=Pangan Low Risk, 302=Pangan High Risk, **303=Pangan Medium Risk** (spans MT+MR), 000=Belum Dikategorikan |
| ERBA has **4 risk levels** | `KATEGORI_DOKUMEN`: 301=Tinggi, 302=Menengah Tinggi, 303=Menengah Rendah, 304=Tinggi Notifikasi |
| Same code, different meaning across systems | `STATUS`: ERBA `0999`=Perizinan Berusaha Terbit; ERLA `999`=NIE Sudah Selesai, `9`=Dicabut/Dibatalkan; **`9999` exists in BOTH** = "Sudah Diubah" |
| Multi-source categories exist | `STATUS` and `KEMASAN_ID` each have separate ERBA **and** ERLA rows |
| Dictionary is more complete than the cache | `STATUS_KOMITMEN` includes **"Draft Pemenuhan Komitmen"** (~29,167 rows) — absent from `business_glossary.md` |
| Commitment cancellation is large | `STATUS_KOMITMEN='5'` (Komitmen Dibatalkan) = **5,199** distinct nomor; system answered 254 |
| Segment codes are **not** in the dictionary | AMDK / Garam Beryodium have no dictionary category — meaning must be probed from product tables |
| `pg_trgm` is **not installed** | fuzzy/typo matching must be done by the agent (normalize + multi-pattern `ILIKE`), not a DB similarity function |

---

## 2. Hypotheses (root causes)

**H1 — Cached code meanings defeat the lookup (the central one).** `SKILL.md` PHASE 2 already says
"look up the code in `data_dictionary`", but the context files ship a finished answer for each code.
The agent reads the cache, gains false certainty, and never queries the source. The cache has drifted
from the source, so the answer is wrong. *Fixing the cache is not the fix — removing the cache is.*

**H2 — `sumber`-blind resolution.** The lookup/JOIN pattern in `code_resolution.md` filters by
`kategori` only, never by `sumber`. For multi-source categories (`STATUS`, `KEMASAN_ID`) and shared
codes (`9999`), this causes a **fan-out** (one product row joins to two dictionary rows →
`COUNT(DISTINCT)` distortion) or an ambiguous label. The agent has no rule that translation is
per-system.

**H3 — Cross-system equivalence assumed, not tested.** The cached tables assert "ERLA 303 = ERBA MT".
The DB says ERLA 303 = *all* medium risk (~7× the ERBA MT magnitude). No mechanism forces the agent
to test an equivalence claim against data, so the false equivalence propagates (RC-1: 95,736 vs
11,923).

**H4 — Filter scope baked as unconditional rule.** `data_quality_rules.md` declares
`jenis_permohonan IN ('301','305')` and "commitment queries still require all NIE filters" as
absolute. The agent applies them even when the question asks for *all active NIE* (RC-2) or for
*cancelled applications regardless of NIE* (RC-4: 254 vs 5,199). This is a definition problem, not a
code-lookup problem — addressed by the light semantic-definition element (WI-6).

**H5 — Segment codes hardcoded instead of discovered.** Garam Beryodium is pinned to a 12-digit
sub-code (`120101000001`, 189 rows) instead of the parent category (`jenis_pangan='1204'`, 198 rows).
The meaning lives in the product table, not the dictionary, and must be discovered + coverage-tested
(RC-3).

---

## 3. Approach — teach the resolution, keep it general

One transferable principle, applied in both directions, replaces every cached code table:

> **A code is born from the dictionary and dies as a definition through the dictionary.**
> No code meaning is stored as an answer in any context file. Context files store only the
> **procedure** for looking it up and the **procedure** for handling ambiguity — never the result.
> Resolution is **per-system** (`sumber`-aware); cross-system equivalence is **tested against data**,
> never assumed. When the meaning is not in the dictionary, **probe the related table**; when neither
> resolves cleanly, **pick the data-supported interpretation and state the assumption** (the
> "ask the user" channel is intentionally not built yet — see §8).

This is the anti-hardcode position taken to its logical end: the 12 June plan accepted one
"legitimate hardcode" (the risk-collision table). This plan removes even that — the collision is
discoverable by querying `data_dictionary` with `sumber`, so it should be *taught as a lookup*, not
frozen as a table.

### 3.1 The canonical pattern (one query, two directions)

**Inbound — word → code (during RESOLVE, before any SQL):**
```sql
SELECT sumber, kode, deskripsi
FROM warehouse.public.data_dictionary
WHERE kategori = '<KATEGORI>'
  AND sumber IN ('<SYSTEM>', 'ERBA dan ERLA', 'ERLA dan ERBA')   -- <SYSTEM> = ERBA | ERLA
  AND deskripsi ILIKE '%<user phrase>%';
-- 0 rows  → typo path: broaden by syllable patterns ('%men%' AND '%tinggi%'), or check another kategori
-- 1 row   → bind: term → kode → becomes a filter
-- >1 rows → ambiguity: COUNT-test each candidate, pick the data-supported one, STATE the basis
```

**Outbound — code → definition (during GENERATE):**
```sql
LEFT JOIN warehouse.public.data_dictionary dd
  ON dd.kategori = '<KATEGORI>'
  AND dd.sumber IN ('<SYSTEM>', 'ERBA dan ERLA', 'ERLA dan ERBA')   -- prevents fan-out
  AND dd.kode = <coded_column>::text
-- status_komitmen: dd.kode = ROUND(status_komitmen::numeric)::int::text
-- present COALESCE(dd.deskripsi, <column>) — NEVER show a raw code
```

### 3.2 Source hierarchy (translation is not dictionary-only)

1. **`data_dictionary`** (sumber-aware) — for coded values.
2. **Probe the related table** — for meanings absent from the dictionary: product segments via
   `nama_kategori` / `jenis_pangan` (`t_produk_*`), company names via `m_trader_*`. Per the project
   owner's direction: *open the related table to obtain the correct meaning.*
3. **Business semantics** (`business_glossary.md`) — for metrics/concepts that are not codes
   (NIE = `COUNT(DISTINCT nomor)`, "pangan olahan" scope, etc.).

---

## 4. Changes per file

### 4.1 `context/code_translation_protocol.md` (NEW — the single source of resolution procedure)
- The two-way canonical pattern (§3.1), `sumber`-aware.
- Column → `kategori` pointer table (moved from `code_resolution.md` §"Column → kategori mapping" —
  this is a *where to look* pointer, not a *what it means* answer).
- The ambiguity loop: 0 / 1 / >1 rows; the magnitude hypothesis test for cross-system equivalence
  (e.g. ERLA `JENIS_DOKUMEN`=303 vs ERBA `KATEGORI_DOKUMEN`=302 differ ~7× → not equivalent → surface
  that ERLA cannot isolate MT from MR).
- The source hierarchy (§3.2) and the typo strategy (multi-pattern `ILIKE`; `pg_trgm` unavailable).
- Explicit non-goals: this file resolves **codes**; metric/segment meaning is delegated to the
  glossary / discovery probe.

### 4.2 `context/code_resolution.md`
- Correct the false claim that `kategori_dokumen` (ERBA) and `jenis_dokumen` (ERLA) carry the same
  labels — they do not (ERBA: Tinggi/Menengah Tinggi/Menengah Rendah; ERLA: Low/High/Medium Risk).
- Add the mandatory `sumber` predicate to the lookup and JOIN patterns.
- Keep only genuine **transformation** procedures (region `ROUND(/100,2)`, AKRONIM `'KP '||LEFT(,2)`,
  legacy-Kemendagri explanation). Point all code→meaning resolution to the new protocol (§4.1).

### 4.3 `context/business_glossary.md`
- **Remove** the risk-code tables (ERBA & ERLA) and the `STATUS_KOMITMEN` code table as *sources of
  meaning*; replace with a pointer: "coded values are resolved at runtime via
  `code_translation_protocol.md`; do not read meaning from a static table here."
- **Keep** non-code knowledge: NIE vs permohonan definitions, ERBA vs ERLA generational distinction,
  the *concept* of final-vs-transient commitment states (without listing codes), Column Purpose Guide,
  Makloon, origin (negara_pabrik), deprecated columns.
- Fix RC-3: Garam Beryodium ERBA → `jenis_pangan = '1204'` (parent, ~198 in 2023); note
  `kategori_pangan='120101000001'` is a single sub-type only.

### 4.4 `context/intent_mapping.md`
- Remove the risk-code table (currently §Risk, lines ~211–225) and the Status-Komitmen code table
  as *meaning*; replace with a pointer to the protocol. Keep the schema-linking layer
  (Subject→granularity, dependent/independent dimensions, time rules) — that is reasoning, not a code
  cache.
- Fix Garam in the segment table → `jenis_pangan='1204'`.
- **(Phase 2 addition — Gap 1/2 closure)** Add two new OPERATION entries to the OPERATION → SQL
  pattern table:
  - `INVESTIGATE` — triggered by "kenapa/mengapa/penyebab"; maps to trend + decomposition query
    sequence (see Synthesis Pattern F in §4.7).
  - `AGE / SLA` — triggered by "sudah berapa lama/lama tertahan/durasi/menunggak/> N hari"; maps
    to `CURRENT_DATE - tanggal_bayar` age calculation (see R12 in §4.6).
- **(Phase 2 addition — Gap 2 closure)** Add **Durasi / SLA / Aging** subsection to the DIMENSION
  registry: entity = PERMOHONAN; age column = `tanggal_bayar`; only meaningful for in-process rows;
  see R12 for template.

### 4.5 `context/data_quality_rules.md`
- Split the `jenis_permohonan` rule into a **conditional** (see WI-6 / §4.9): apply `IN ('301','305')`
  only for "newly issued NIE" intents; omit it for "all active NIE / total registered" intents.
- Split the commitment rule into two cases (RC-4): (A) "NIE that also has commitment status X" keeps
  the NIE filters; (B) "applications whose commitment was cancelled" drops the NIE status filter —
  most cancellations precede NIE issuance.

### 4.6 `context/query_recipes.md`
- R3/R11 (risk CASE), R6 (commitment), R10 (segment) must **not** embed literal codes as truth.
  Convert to placeholders fed by the resolution step: `kategori_dokumen IN ({resolved codes})`.
- R6: provide two variants matching the two commitment cases (§4.5).
- R10: Garam → `jenis_pangan='1204'`; reinforce "discover segment codes by probe, do not hardcode".
- **(Phase 2 addition — Gap 2 closure) R12 — Application age / SLA:** canonical template for
  `CURRENT_DATE - tanggal_bayar::date` on in-process applications; age-bucket aggregation; ERBA
  cast note; applies to both a detail-level (oldest N applications) and a summary-level (bucket counts).
- **(Phase 2 addition — Gap 1 closure) R13 — Root cause decomposition:** two-step template:
  (1) trend query to confirm inflection year; (2) decomposition by `jenis_permohonan` and top
  traders at the inflection year; guides the agent to name the top contributor as a data-supported
  hypothesis, not a conclusion.

### 4.7 `seeknal/skills/bpom-analyst/SKILL.md`
- **PHASE 2 RESOLVE — hard gate:** add a **Translation Binding Table** that must be filled before any
  SQL: `term → kategori → sumber → resolved code(s) → source query`. Add a `Bindings:` line to the
  RESOLVED CONSTRUCTS block. *No SQL may be written until every coded term is bound from the
  dictionary (not from recall).*
- **PHASE 5 REFLECT:** replace the checklist item "(commitment) all NIE filters still present" (the
  rule that enforces RC-4) with the two-case discrimination (§4.5). Add a re-evaluation step: if a
  result's magnitude is far from domain expectation, return to RESOLVE and re-translate.
- **PHASE 6 GENERATE:** make the outbound dictionary JOIN mandatory for every coded column; the answer
  presents definitions, never raw codes.
- **(Phase 2 addition — Gap 1 closure) Synthesis Pattern F — Investigative / Root Cause:** four-step
  procedure for "kenapa/mengapa/penyebab" questions: (1) confirm inflection point from trend;
  (2) run decomposition query by most informative dimension (R13); (3) name top contributor with
  absolute and % share; (4) state as data-supported hypothesis, never a concluded cause. If no single
  contributor dominates, state that explicitly. Never fabricate policy/regulatory reasons.
- **(Phase 2 addition — Gap 2 closure) Synthesis Pattern G — SLA / Aging:** triggered by
  "sudah berapa lama/lama tertahan/> N hari"; entity = PERMOHONAN; template from R12; present as
  age-bucket summary table first, then oldest-N detail on request; always state the reference date
  used for age calculation.

### 4.8 `seeknal/skills/evidence-auditor/SKILL.md`
- Update checklist B/E: risk resolution must be `sumber`-aware; commitment audit follows the two-case
  rule; add "every coded column in the output is dictionary-resolved (no raw codes, no fan-out)".

### 4.9 `SEEKNAL_ASK.md` (orchestrator)
- §5 Information Need Resolution: raise **Level 2 (Dictionary)** to mandatory for every coded term —
  not a step that a cache can skip.
- §6 Guardrails: add **"No cached code meanings"** — code meaning is valid only from the live
  dictionary (two-way), `sumber`-aware; raw codes must never appear in answers.
- §4 Product Segment Codes: fix Garam → `jenis_pangan='1204'`.
- **(WI-6, light semantic layer)** Add a short **Canonical Definitions** note: "total izin edar / NIE"
  without qualifier = ERBA+ERLA product tables, **no** BTP unless requested, **no** `jenis_permohonan`
  filter (that is "NIE baru" only); distinguish "NIE baru" vs "NIE aktif". This cures the
  non-determinism (RC-5) at the definition layer.

---

## 5. Anti-hardcode position — why this supersedes the 12 June §5 hardcode

The 12 June plan documented one approved hardcode: the ERBA/ERLA risk-collision table. The live DB
shows that collision is fully described in `data_dictionary` once `sumber` is honored:

| kategori | sumber | kode | deskripsi |
|---|---|---|---|
| KATEGORI_DOKUMEN | ERBA | 301 / 302 / 303 / 304 | Tinggi / Menengah Tinggi / Menengah Rendah / Tinggi Notifikasi |
| JENIS_DOKUMEN | ERLA dan ERBA | 301 / 302 / 303 | Pangan Low Risk / Pangan High Risk / Pangan Medium Risk |

Because the collision is *discoverable*, freezing it in a table is unnecessary and — as the UAT
proved — fragile (the frozen table drifted and re-introduced the very overcount it was meant to
prevent). Teaching the lookup is strictly more robust and removes the last hardcode. **Net result:
zero hardcoded code meanings anywhere in the system.**

---

## 6. Follow-up / conversation handling (relationship to existing machinery)

The State Comparison Engine and Conversation Ledger (`SEEKNAL_ASK.md` §0.5) already classify a
follow-up as NEW_QUESTION / MODIFY_SCOPE / EXTEND_SCOPE / EXPLAIN_EVIDENCE and apply "inherit
ANSWERS, re-derive METHODS". This plan slots into that contract cleanly:

- A **translation binding is a METHOD** → it is re-derived every turn (the dictionary is re-queried),
  so a wrong binding in turn N cannot leak into turn N+1.
- Only **validated answers + scope** carry forward via the Ledger.
- Topic continuation vs topic switch is the SCE's job; because the clarification channel is not built,
  a genuinely ambiguous switch is resolved by the data-supported interpretation **with the assumption
  stated** (§8).
- **Optimization (allowed):** the *result* of a dictionary lookup is immutable within a session and
  may be cached per session; the *business decision* (which filter to apply) is still re-derived. This
  distinguishes caching reference data (fine) from inheriting a method (forbidden).

No changes to the SCE/Ledger mechanics are required — only the §4.9 guardrail addition.

---

## 7. Scalability — proportional now, designed for scale

The DB currently has **8 tables**. The design intent is to scale toward 1000+ tables **without
over-engineering today**: prepare via *interfaces/procedures*, not *infrastructure*. The rule of
thumb: with few tables the context may hold a map; at scale the context must hold *how to discover*
the map. Writing WI-1…WI-9 as **procedures** (how to ask the DB about itself) — not static maps —
keeps the door open.

| Layer | Status in seeknal today | Action |
|---|---|---|
| L7 Observability | archive stores Q/A/SQL | (deferred) add per-turn binding + lookup trace |
| L6 Conversation State (follow-up) | **strong** (SCE + Ledger) | tighten Ledger scope precision; binding = method |
| L5 Verification | partial (manual REFLECT) | (deferred) formalize dry-run / sanity / self-correct |
| L4 Planning | partial | (deferred) FK-graph join-path planner |
| L3 Semantic / Metrics | **gap (critical)** | **light** canonical-definitions now (WI-6); full engine later |
| L2 Resolution | exists but `sumber`-blind | **this release** — sumber-aware + source hierarchy |
| L1 Catalog / Discovery | **gap (scale)** | (deferred) `information_schema` introspection + semantic index |

**Deliberately deferred (interfaces not locked):** L1 schema discovery (relevant past ~50 tables),
L4 join-path planner, L5 formal verification, the clarification channel (G4), the eval-harness CI
(G6), resolution observability (G7). Safe to defer **only because** WI-1…WI-9 are written as
procedures, so L1/L4 later *extend* rather than *replace*.

---

## 8. Ambiguity policy (decided)

The "ask the user" clarification channel is **not built** in the current system. Until it is
(deferred to a later phase), ambiguity that data cannot adjudicate is resolved by:
1. choosing the interpretation **best supported by the data**, then
2. **stating the basis and the limitation explicitly** in the answer
   (e.g. *"ERLA cannot separate Menengah Tinggi from Menengah Rendah; this figure is combined
   medium risk"*).

The system never silently guesses, and never fabricates a number.

---

## 9. What we deliberately do NOT change

- **The Decision OS, SCE, Conversation Ledger, "inherit answers / re-derive methods"** — sound; kept.
- **The 7-phase workflow** — the reasoning frame is correct; we tighten two gates, not the frame.
- **Metric correctness already in context** (NIE/permohonan count + date columns, UMKM = 1+2+3,
  status_komitmen ROUND normalization) — correct; untouched except where RC-2/RC-4 require the
  conditional split.
- **Test-suite oracles** — refreshing stale oracles is separate from agent changes; do not chase
  stale numbers by editing the agent.
- **Infrastructure** (tunnel drops, model 503s) — environmental, out of scope.

---

## 10. Expected impact

> Expectations describe **behavior and the audit's static-data acceptance numbers** only. Numbers on
> moving data (current-year, all-time live counts) will drift; quoting those as targets would itself
> become a hardcode.

| Case (static unless noted) | Before | After (expected) | Mechanism |
|---|---|---|---|
| NIE Menengah Tinggi, all-time | 95,736 | **~11,919** (ERBA), with ERLA limitation stated | H1+H2+H3, §4.1–4.3 |
| Komitmen Dibatalkan | 254 | **~5,199** | H4, §4.5/4.7 |
| Garam Beryodium 2023 | 189 | **~198** | H5, §4.3/4.6 |
| Produk MD 2025 (all active) | 30,760 | **~36,706** | H4, §4.5/4.9 |
| "Total NIE 2025" across sessions | 3 different answers | **one answer**, deterministic (~53,535) | WI-6, §4.9 |
| Coded columns in any answer | raw codes / wrong labels | dictionary definitions, `sumber`-correct, no fan-out | §4.7/4.8 |
| Already-correct cases | BTP 2023=950; AMDK 2023≈1,843; susu Mei 2026=0 | unchanged (no regression) | regression guard §11 |
| "Kenapa perubahan mayor naik?" | bare trend table or no answer | trend → inflection point named → top contributor named → stated as data hypothesis | Synthesis Pattern F, R13, §4.4/4.7 |
| "Permohonan mana yang tertahan > 30 hari?" | not handled / wrong entity | PERMOHONAN age bucket table + oldest-N list | Synthesis Pattern G, R12, §4.4/4.6/4.7 |

Net: code translation gains a single source of truth (the live dictionary, two-way, `sumber`-aware);
the proven failures become structurally impossible; the system extends its analytical reach from
**retrieval + aggregation** to **root-cause decomposition** and **SLA / aging analysis**; the system
stays **general** — it learns *when to look up what, in which source, for which system, and how to
handle ambiguity* — rather than memorizing answers.

---

## 11. Verification (run when the DB tunnel is active)

```bash
cd seeknal-bpom-neo

# Phase 1 (RC regression + singleturn UAT):
uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/singleturn --filter UAT

# Phase 2 (multiturn follow-up):
uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/multiturn
```

Acceptance — judge against the static-data numbers in §10 (these do not drift):

**RC regression (Phase 1 release):**
- MT all-time ≈ 11,919 (not 95,736); Komitmen Dibatalkan ≈ 5,199 (not 254);
  Garam 2023 ≈ 198 (not 189); Produk MD 2025 ≈ 36,706 (not 30,760).
- Determinism (RC-5): ask "total izin edar 2025" in three fresh sessions → identical number (≈ 53,535).
- Two-way translation: outbound shows "Komitmen Dibatalkan" not code `5`; inbound "menengh tnggi" resolves via multi-pattern ILIKE.
- `sumber` safety: `STATUS` code `9999` returns one label, no fan-out.
- No regression: BTP 2023=950; AMDK 2023 (combined) ≈ 1,843; susu sekolah Mei 2026=0.
- Cross-file audit: `grep` the `context/` tree → no code→meaning tables remain.

**Phase 2 additions (Gap 1 / Gap 2 — manual test until UAT cases are added):**
- Ask "Kenapa perubahan mayor meningkat drastis tahun 2025?" → response must:
  (a) show a per-year breakdown of permohonan by `jenis_permohonan`;
  (b) name the dominant contributor (e.g. Perubahan Mayor count delta);
  (c) label it "hipotesis berbasis data" — NOT assert a policy cause.
- Ask "Ada permohonan yang sudah menunggu lebih dari 90 hari?" → response must:
  (a) use `tanggal_bayar` (not `tanggal`) as the age base;
  (b) show an age-bucket table;
  (c) state the reference date used for calculation.
- Neither question should return a "cannot answer" — both now have a defined procedure.

> Note: some test oracles are stale vs the live DB because data keeps growing. Refresh oracles against
> a fresh query (or apply a tolerance) when judging — separately from the agent changes above.
