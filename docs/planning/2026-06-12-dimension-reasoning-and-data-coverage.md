# seeknal-bpom-neo: Dimension Reasoning & Data-Coverage Awareness

**Document type:** Implementation Plan (teach-the-thinking enhancement)
**Project:** seeknal-bpom-neo (BPOM RPO Analytics Agent)
**Status:** Implemented (§1–§9). Round 2 (§10) added after runs `082208` / `084127`.
**Date:** 2026-06-12
**Scope:** `SEEKNAL_ASK.md` · `seeknal/skills/bpom-analyst/SKILL.md` · `context/intent_mapping.md` · `context/data_quality_rules.md` · `context/business_glossary.md` · `context/query_recipes.md` · `context/code_resolution.md`
**Amends:** `docs/planning/2026-06-11-follow-up-inheritance-refinement.md`

---

## 1. Background

After the follow-up inheritance fix (11 June), the agent recovered to ~96% effective accuracy on
multiturn runs. Two classes of problems remain, surfaced by the WhatsApp staging report
(`docs/audit_context/test_results_10_juni_2026.md`) and the 12 June runs:

1. **"Simple questions" answered at the wrong altitude** — e.g. "permohonan bulan Mei" answered
   in *year* context instead of *month*; "Top 10 kategori pangan" dominated by "Tanpa Kategori";
   "tren BTP per skala" not produced; region questions weak.
2. **Follow-up execution bugs** still appear intermittently (UMKM drops Menengah, "disetujui" uses
   the wrong code, etc.) — see §6.

This plan was built from **direct verification against the live `rpo_v2` database** (2026-06-12),
not assumptions. It stays faithful to the project philosophy: **teach the agent how to reason —
do not hardcode answers into context.** One genuine ontology hardcode is documented in §5.

### 1.1 What the database actually shows

| Finding | Evidence (live `rpo_v2`) |
|---|---|
| `nama_kategori` is sparse | **59% empty/NULL** in ERBA — unusable as a grouping key |
| `kategori_pangan` is complete & resolvable | **100%** resolvable via AKRONIM `'KP ' \|\| LEFT(kategori_pangan,2)` |
| Factory region is sparse | `daerah_pabrik` resolvable for only **37%** of ERBA NIE (28% literally `'NULL'`) |
| Company region is complete | `m_trader_rba.kotakab_id` / `provinsi_id` populated **100%** (via JOIN) |
| Factory ≠ company location | `daerah_pabrik` differs from `daerah_trader` in **33%** of rows |
| Month granularity works | Permohonan ERBA *May*: 2023=1,700 · 2024=4,087 · 2025=5,174 · 2026=5,087 |
| Domestik/Impor proxy exists | `negara_pabrik`: ID=176,163 (domestic), CN/MY/KR/IT/US = import |
| BTP can be sliced by scale | `t_btp_3_erba` → `m_trader_rba` join: **100%** joinable |
| Commitment is ERBA-only | `t_produk_3_rilis_erla` has **no** `status_komitmen` column |
| ERBA/ERLA risk codes collide | code `301` = "Tinggi" (ERBA) but "Low Risk" (ERLA) — opposite meaning |

---

## 2. Hypotheses (root causes)

**H1 — Coverage-blind column choice (the central one).** The agent selects a column by *name
match* rather than *data coverage*. It groups by `nama_kategori` (59% empty) and `daerah_pabrik`
(37% resolvable) instead of the complete, resolvable alternatives. This single behavior explains
the category, region, and "Tanpa Kategori" failures at once.

**H2 — Missing period granularity.** `intent_mapping.md` teaches only *year* and *all-time* time
shapes. There is no rule for *month* / sub-year ranges, so the agent collapses "bulan Mei" to a
year.

**H3 — Missing dimension knowledge.** `intent_mapping.md` has no **region** dimension entry, no
**domestik/impor** concept, and does not state that **scale applies to BTP** (via the trader join).
The data supports all three; the agent was simply never taught them.

**H4 — Orchestrator rules permit the follow-up bug.** `SEEKNAL_ASK.md` §6 says *"prior-turn recall
via message history is legitimate"*, which directly licenses answering a **new** number from memory
— exactly the UMKM `10,412` bug (the agent re-defined UMKM = Mikro+Kecil from memory, ran no query).
This contradicts the §0.5 principle "re-derive METHODS".

**H5 — Cross-system code collision (needs a hardcode).** ERBA `kategori_dokumen` and ERLA
`jenis_dokumen` reuse the same codes with **opposite** meaning. This is the root of the
risiko-tinggi all-time overcount and cannot be derived — it must be an explicit mapping.

---

## 3. Approach — teach the reasoning, keep it general

The fix is to add **general reasoning rules**, not per-question answers. The centerpiece is one
transferable principle that resolves H1 and auto-covers unseen dimensions:

> **Coverage-aware column choice:** before grouping or ranking by a dimension, prefer the column
> (or resolvable code) for that concept with the **best data coverage**. If a result is dominated
> by NULL / "Tanpa Kategori" / "unidentified", stop and switch to a more complete column for the
> same concept. If coverage is still low, **state the limitation honestly** — never present
> "Tanpa Kategori" as the answer, and never silently switch to a different subject.

Everything else is a small, targeted teaching addition layered on the existing
orchestrator → context → skill architecture.

---

## 4. Changes per file

### 4.1 `SEEKNAL_ASK.md` (orchestrator) — 4 adjustments

| # | Section | Change | Why |
|---|---|---|---|
| 1 | §6 Guardrail #1 | Tighten "prior-turn recall is legitimate" → only a **validated answer already in the Conversation Ledger** (number tied to the exact scope) may be reused. A **new** number (different scope/filter/dimension, incl. "dari situ yang UMKM") **requires a fresh query**; never recompute from a remembered breakdown. `#sqls=0` is allowed only for arithmetic over numbers literally in the Ledger. | Removes the rule that licenses the UMKM recall bug (H4) |
| 2 | §0.5 `EXPLAIN_EVIDENCE` | Add a discriminating test: a derived total (e.g. UMKM from scale) is `EXPLAIN_EVIDENCE` **only if every component is already a validated number in the Ledger**; if any component is missing → it is `MODIFY_SCOPE` (must RESOLVE + query). | Stops "compute from memory" masquerading as explanation (H4) |
| 3 | §4 Product Segment | Note: for category **grouping/ranking**, use the resolvable `kategori_pangan` → AKRONIM code (100%); `nama_kategori` is for specific-segment **search** only, not as an aggregation key. | Fixes "Top 10 kategori" (H1) |
| 4 | §2 Behavioral Contracts | Add a **month** granularity row (in sync with §4.3 below), so sub-year granularity is locked from session start. | Fixes month altitude (H2) |
| 5 | §0.5 Output Shape | Add the **count-breakdown rule**: a COUNT with no year (or a named month) outputs a per-year (or month-per-year) breakdown **with the total at the end**, never a bare total. | Per-time detail for "berapa X" (user decision) |

> Everything else in `SEEKNAL_ASK.md` (Conversation Gate, Intent Extraction, Schema State,
> Information Need hierarchy, SQL-transparency & anti-topic-drift guardrails, Communication
> Alignment) is **adequate and unchanged**.

### 4.2 `seeknal/skills/bpom-analyst/SKILL.md` (execution engine)

- **RESOLVE — coverage check:** before grouping/ranking by a dimension, assess column coverage;
  pick the most complete column for the concept; report low coverage honestly. (H1 centerpiece)
- **RESOLVE — carry parent invariants on drill-down:** on a follow-up, re-read the per-table
  invariants and carry the parent turn's subject/scope/codes, changing only the requested delta —
  date column (`tanggal` vs `tanggal_aju`), status_komitmen codes ({4,7} vs 5), risk codes,
  `jenis_permohonan` filter, ERBA-only vs +BTP scope, carried entity/risk/system/year.
  (Execution bugs §6)
- **No new number from memory:** mirror of the §6.1 orchestrator rule at the execution layer.
- **GENERATE — count-breakdown shape:** render a COUNT answer as the per-year (or month-per-year)
  table first, with the **grand total on the last line**; never emit a lone total for an all-time
  or month-without-year count.

### 4.3 `context/intent_mapping.md` (dimension registry — most additions here)

- **Month / sub-year row** in the time-dimension rules: "bulan X / per bulan / tren bulanan" →
  `date_trunc('month', col)`; single month → `EXTRACT(MONTH FROM col)=M` or a month range.
  Granularity = the **smallest** time unit the user names.
- **F3 rule (user decision):** month **without** a year → do not ask, do not assume one year →
  break the month down **per year** (one row for that month in each year that has data — the set of
  years comes from the data, not a fixed start). Date column follows the entity (NIE=`tanggal`,
  permohonan=`tanggal_bayar`); mandatory filters stay.
- **Count breakdown rule (user decision) — never lead with a bare total:** a COUNT question
  ("berapa NIE risiko tinggi pangan olahan", "berapa permohonan UMKM", …) is **not** answered with
  just the total. Always show the **time breakdown first, then the grand total at the end**:
  - no year stated → **one row per year that has data** + grand total;
  - month stated, no year → **one row per year that has data for that month** + grand total;
  - a single explicit year → that year's figure (do **not** force a month split unless the user names a month).
  This makes "berapa X" informative (shows the distribution/trend) instead of a lone scalar.
  The SQL already groups by year for all-time; this rule governs the **output shape** in GENERATE.
- **Derive the range from the data — never assume a fixed start/end year.** The set of years
  shown comes from the actual data (e.g. the date column's span), not a hardcoded value like
  "2012" or "the current year". The agent first determines the **latest available year** from the
  data/schema state, then:
  - relative periods resolve against that latest year — **"N tahun terakhir"** = the last N years
    up to the latest available year; **"1 tahun terakhir" / "terbaru"** = the latest available year;
  - all-time = every year present, earliest-with-data through latest-with-data.
  Teach the *process* (find latest year → derive the window), not specific years. This already
  exists for relative periods in `intent_mapping.md` ("resolve against MAX(year), not 2023") —
  extend the same thinking to the count-breakdown output.
- **Region dimension (new entry):** column choice by semantics + coverage —
  - default "daerah" / "kab/kota" → **`m_trader_rba.kotakab_id` / `provinsi_id`** (100%, company location)
  - explicit "pabrik / lokasi produksi" → `daerah_pabrik` (37%; must state it is factory ≠ company, 33% differ, and report coverage)
  - unresolved code → "legacy Kemendagri code" (already in `code_resolution.md`); keep raw code.
- **Category ranking rule:** group/rank by `kategori_pangan` → AKRONIM (100%), not `nama_kategori`.
- **Scale applies to BTP:** scale always comes from the `m_trader` join (via `trader_id`),
  available for **all** entities including BTP (100% joinable).
- **Risk collision (hardcode, §5):** reinforce/correct the ERBA-vs-ERLA risk-code table.

### 4.4 `context/data_quality_rules.md`

- Add the **coverage-aware column choice** meta-principle (H1) as a data-quality rule, with the
  concrete coverage facts (`nama_kategori` 59% empty; `daerah_pabrik` 37%).

### 4.5 `context/business_glossary.md`

- Add **Domestik / Impor**: derived from `negara_pabrik` (or `negara_produsen`) — `'ID'` = domestic,
  else import. There is **no** dedicated domestic/import column; ERBA/ERLA are *systems*, not origin.
  State the basis when answering. (Commitment = ERBA-only is already documented.)

### 4.6 `context/query_recipes.md`

- Add a **sub-year / month** time form to the conventions (alongside single-year and all-time),
  with the `date_trunc('month', col)` and month-range patterns.

### 4.7 `context/code_resolution.md`

- Already teaches region conversion (`ROUND(/100,2)`), the legacy-code explanation, and
  `kategori_pangan` → AKRONIM. **Minor** reinforcement only; no structural change.

---

## 5. The one legitimate hardcode — ERBA/ERLA risk-code collision

The database proves the same code means opposite things across systems:

| Code | ERBA `kategori_dokumen` | ERLA `jenis_dokumen` |
|---|---|---|
| 301 | **Tinggi** (High) | **Pangan Low Risk** |
| 302 | Menengah Tinggi | **Pangan High Risk** |
| 303 | Menengah Rendah | Pangan Medium Risk |
| 304 | Tinggi Notifikasi | — |

This cannot be derived and **must** be an explicit cross-system mapping (the project owner approved
hardcoding genuine ontology collisions). A table already exists in `intent_mapping.md`; the action
is to **verify/correct the ERLA middle level** (DB: 303 = Medium Risk) and document that ERLA has
3 risk levels vs ERBA's 4 (a lossy mapping). This is the **only** hardcode; all other items are
general reasoning rules.

---

## 6. Relationship to the remaining follow-up execution bugs

These were proven against the DB on 2026-06-12 (replaying the agent's own SQL reproduced each wrong
number exactly). They are **execution** failures on drill-down turns, not missing definitions:

| Bug | Symptom | Fixed by |
|---|---|---|
| UMKM drops Menengah | `10,412` (Mikro+Kecil), `#sqls=0` | §4.1 #1–2 + §4.2 (no number from memory) |
| "Disetujui" uses code 5 | `2` (code 5 = cancelled), labeled approved | §4.2 carry-codes on drill-down |
| BTP wrong column | `tanggal_aju` + dropped `jenis_permohonan` → `1,102` | §4.2 carry-invariants |
| Year-switch subject loss | "kalau 2022" → total combined, lost MR+ERBA | §4.2 carry subject/scope |
| Scope "semua sistem" | included BTP → `62,877` vs `61,217` | §4.3 default-scope reinforcement |
| Risk-Tinggi all-time | `120,234` vs `103,698` | §5 risk-code mapping |

---

## 7. What we deliberately do NOT change

- **status_komitmen / UMKM / disetujui / BTP definitions** — already correct in context (the bugs
  are execution, not definition).
- **Test-suite artifacts** — stale oracles, substring matching, no numeric tolerance. These belong
  in `scripts/test_multiturn_v3.py` + the YAML files, **not** in agent files. Chasing exact stale
  numbers by changing the agent would be wrong.
- **Infrastructure** — DB-tunnel drops and model-endpoint 503s are environmental, outside the agent.
- The core Decision OS layer, Conversation Ledger, and "inherit answers, re-derive methods"
  principle — kept as-is.

---

## 8. Expected impact

> Expectations describe **behavior and shape only** — no specific totals (numbers drift; quoting
> them would become de-facto hardcoding).

| Area | Before | After (expected behavior) |
|---|---|---|
| "permohonan bulan Mei" | answered as a year | that month broken down per year (only years with data), total at the end |
| "Top 10 kategori pangan" | "Tanpa Kategori" dominates | resolvable broad categories ranked by count |
| "daerah mana paling banyak NIE" | sparse (factory location) | company kab/kota dimension (full coverage), ranked |
| "tren BTP per skala industri" | not produced | per-year × scale, via the trader join |
| "produk impor per daerah" | "no such column" | derived from `negara_pabrik` (non-`ID` = import), basis stated |
| "berapa NIE risiko tinggi" (all-time) | bare, overcounted total | per-year rows (range derived from the data) + grand total on the last line, using the correct ERLA risk code |
| UMKM follow-up | drops a component (answered from memory) | re-queried with the full definition (scale 1+2+3) |

Net expectation: the "simple question" class becomes consistent, the 6 follow-up execution bugs
close, and the system stays **general** — it learns *when to do what, with which column, and how* —
rather than memorizing answers.

---

## 9. Verification (run when the DB tunnel is active)

```bash
cd seeknal-bpom-neo
uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/multiturn
```

Targeted manual checks — judge **shape and behavior**, not a fixed number (totals drift):
- "jumlah permohonan bulan Mei" → that month broken down per year (only years with data), total last.
- "Top 10 kategori pangan" → resolvable categories ranked by count; no "Tanpa Kategori" dominance.
- "daerah mana paling banyak NIE" → company kab/kota dimension, full coverage, ranked.
- "tren izin edar BTP per skala industri 5 tahun terakhir" → year × scale; the 5-year window is
  derived from the **latest available year in the data**, not a fixed year.
- "berapa NIE risiko tinggi pangan olahan" (all-time) → per-year rows (range derived from the data)
  with the grand total on the last line. The grand total must be a **global `COUNT(DISTINCT nomor)`**
  that **matches an independent fresh DB query** — it will be **less than the arithmetic sum of the
  per-year rows** when a `nomor` spans multiple years (see §10.2); never sum the rows. ERLA risk uses
  the correct collided code (§5), so no overcount.
- Follow-up: "NIE MR ERBA 2023" → "dari situ yang UMKM?" → a **fresh query** is issued (`#sqls>0`),
  using the full UMKM definition (scale 1+2+3), not a number recomputed from memory.

> Note: some test oracles are stale vs the live DB because the data keeps growing. Refresh oracles
> against a fresh query or apply ±5% tolerance when judging — separately from the agent changes above.

---

## 10. Round 2 — adjustments after runs `082208` & `084127`

Both runs **predate** the §1–§9 edits, so most failures (disetujui=5, dropped `jenis_permohonan`,
`#sqls=0` recall, BTP `user_id`, ±BTP scope, ERLA risk collision) are expected to be already
covered — confirm by **re-running** before adding anything for them. Inspecting the **actual SQL**
of the failing turns (replayed on the live DB) surfaced **three gaps §1–§9 did NOT cover**. All
three are general reasoning rules, not hardcoded answers.

### 10.1 Ban `TRY_CAST` — ERBA casts must be native PostgreSQL
`stress_20 T14` produced `TRY_CAST(tanggal AS TIMESTAMP)` → **syntax error in PostgreSQL** (TRY_CAST
is DuckDB/Spark, not PostgreSQL), so the query never runs. The agent occasionally reaches for a
non-PostgreSQL dialect.
- **Fix:** ERBA TEXT columns are cast **only** with `::timestamp` / `::bigint` (or
  `NULLIF(col,'')::timestamp` for empty-string safety). PostgreSQL has **no** `TRY_CAST` /
  `TRY_CONVERT` / `SAFE_CAST` — never emit them.
- **Files:** `context/data_quality_rules.md` (§ERBA cast), `SEEKNAL_ASK.md` §3.

### 10.2 Grand total = global `COUNT(DISTINCT)`, never the sum of per-year rows
Side-effect of the new count-breakdown rule (§4.3): the agent built a per-year table and **summed
the rows** for the total. A single `nomor` (izin edar) appears in multiple years (renewals/variations),
so the row-sum double-counts. **DB-verified:** MR all-time row-sum = **141,682** vs global
`COUNT(DISTINCT nomor)` = **119,314** (the agent answered ~141,680). Same effect inflated Risiko
Tinggi (~110k vs ~104k).
- **Fix:** per-year rows use `COUNT(DISTINCT …)` per year, but the **grand total is computed
  separately as a global `COUNT(DISTINCT nomor)`** over the whole set (a standalone aggregate, a
  subquery, or `GROUP BY ROLLUP`). Never derive the total by adding the year rows. Applies to NIE
  (`nomor`) and permohonan (`produk_id`).
- **Files:** `context/intent_mapping.md` (count-breakdown rule), `seeknal/skills/bpom-analyst/SKILL.md`
  PHASE 6 Pattern E, `context/query_recipes.md`.

### 10.3 No year stated → ALL-TIME for EVERY operation (not just trends)
`CAP-3` ("5 daerah dengan izin edar terbanyak", no year) → the agent defaulted to **ERBA 2023**.
The "no year → all-time" rule existed but was only honored for COUNT/trend, not for TOP/ranking, and
the agent additionally tilted to ERBA-only ("recent data").
- **Fix (hard rule at the decision layer):** if the user does not explicitly state a year/range,
  Time Scope = **ALL-TIME** (UNION ERBA+ERLA, `GROUP BY year`). The agent may **never** inject a year
  (2023/2024/current) or restrict to ERBA-only as a "recency" default — this binds for **COUNT, TOP,
  BREAKDOWN, COMPARE**, not just `tren`. Derive the year window from the data.
- **Files:** `SEEKNAL_ASK.md` §0.5 (Time Scope lock) + §2 Behavioral Contracts.

### 10.4 Verified NOT needing new rules (already covered by §1–§9)
disetujui = {4,7} (not 5), mandatory `jenis_permohonan` on NIE follow-ups, no new number from memory
(`#sqls=0`), BTP `trader_id` (not `user_id`), "semua sistem" = product-only, ERLA risk codes. The
SQL of these failing turns was wrong **from the start** (incomplete filter / wrong code / wrong
column) — the data was never wrong — and §1–§9 already address each. **Re-run to confirm; do not
re-edit pre-emptively.**

### 10.5 Diagnosis recap — "is the SQL or the data wrong?"
Across both runs: **the database data is always correct.** Each wrong answer traces to one of:
(a) SQL wrong from the start (missing filter, wrong code, wrong column, non-PG dialect),
(b) no SQL run at all (`#sqls=0`, answered from memory), or
(c) SQL correct + data correct + **stale test oracle** (not an agent fault).
There was **no case** of "correct SQL returning wrong data".
