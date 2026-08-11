# Audit Report — Concurrency-Production SQL Execution & Reasoning (18 June 2026)

**Baseline (before context change):** `seeknal/tests/outputs/2026-06-18/concurrency-production/concurrency_20260618_053248.json` (238 cases, mode `parallel`, 05:32 UTC)
**After context change (combined 238):** `concurrency_20260618_105642.json` + `_111702.json` + `_112026.json` + `_114952.json` (101+54+38+45 = 238 cases, mode `multi-user-distributed`, 10:56–11:49 UTC)
**Pedoman / oracle source:** `seeknal/tests/v1/singleturn/{UAT,CB,NIE,ETC}/*.yml`
**System under test:** `SEEKNAL_ASK.md` (orchestrator) + `seeknal/skills/{bpom-analyst,bpom-forecaster,evidence-auditor}/SKILL.md` + `context/*.md`
**Underlying LLM:** `gemini-3-f`
**Audit date:** 19 June 2026
**Method:** direct parse of each JSON `per_request[].metrics` (`tool_calls`, `sqls[]`), matched by `scenario_id`. No database connection yet — pedoman numbers are taken as ground truth pending live verification (Section 11).

---

## 1. Executive Summary

The context/skill/orchestrator changes shipped 12–18 June 2026 made the agent **more ambitious in reasoning but not more controlled in execution.** The net effect on a like-for-like 238-case comparison is a small quality regression and a real efficiency regression, distributed very unevenly across domains.

| Metric | Baseline (053248) | After (combined 238) | Δ |
|---|---|---|---|
| Pass rate | 55.9 % (133/238) | **52.9 % (126/238)** | −3.0 pp |
| Avg tool calls / case | 9.69 | **10.45** | +7.8 % |
| Avg SQL executions / case | 4.95 | **5.62** | +13.5 % |

The regression is **not uniform** — the system became stronger where it was newly taught and more fragile where the task used to be simple:

| Domain | Baseline | After | Direction |
|---|---|---|---|
| FORECAST | 2/12 | **8/12** | ▲ big improvement (new skill) |
| UAT | 16/101 | 19/101 | ▲ slight |
| AMDK | 0/1 | 1/1 | ▲ |
| CB | 34/38 | **26/38** | ▼ −8 |
| NIE | 43/45 | **38/45** | ▼ −5 |
| KLAIM | 3/3 | **0/3** | ▼ −3 (now empty answers) |

**Core thesis of this audit:** the dominant failure cause is **not** infrastructure and **not** test-string mismatch. At the request level, the large majority of failures are **substantive** — the SQL the agent executed does not match what the question requires. The reasons trace back to **specific, sometimes contradictory, instructions** in the context files and orchestrator. This document shows the SQL step-by-step for representative failing questions and connects each failure to the exact instruction that produced it.

---

## 2. Scope, Method, and a Note on Measurement

- **Fair comparison.** Baseline `053248` runs the full 238-case suite; the four "after" files are distributed subsets that together cover the *same* 238 `scenario_id`s. We compare per-case averages and match by `scenario_id`, so case-mix is controlled.
- **What we measured.** `metrics.tool_calls` ≈ number of agent tool round-trips (proxy for LLM turns); `len(metrics.sqls)` = SQL executions per case; `metrics.sqls[]` = the actual SQL text executed, in order.
- **Harness caveat (acknowledged, but not the headline).** The runner (`scripts/test_multiturn_v3.py:270`) scores by case-insensitive substring containment with no numeric tolerance, and `assert_not_contains` is never read. This *does* cause some false failures (e.g. a correct trend table failing because it wrote "dari tahun ke tahun" instead of the asserted "per tahun"). **However**, at the **request** level the picture is dominated by genuine errors:

| After-238 failing requests (112 total) | Count |
|---|---|
| Substantive (wrong number in the answer) | **85** |
| String-only (correct but format/synonym) | 3 |
| Empty answer (no result produced) | 24 |

For the UAT subset specifically: 82 failures → ~76 substantive, ~0 string-only, 6 empty. **The hypothesis "answers are correct, only string matching is wrong" does not hold for UAT.** This is a reasoning problem.

---

## 3. Current Condition — What the Outputs Look Like

A representative "after" answer is well-formatted and confident, but built on the wrong SQL. Example (`UAT-MR-1`):

> "Berdasarkan data dari sistem **ERBA**, terdapat total **41.516** izin edar (NIE) pangan olahan dengan tingkat risiko Menengah Rendah. Berikut adalah rincian jumlah izin edar per tahun…"

The prose quality is high; the number is wrong (pedoman expects 119.374). This is the signature of the current condition: **fluent answers, unstable query construction.** The agent also now spends more effort per question (more dictionary probes, discovery queries, and a separate grand-total query), and in the hardest unfamiliar domains it explores until it produces **no answer at all** (KLAIM, Section 5.3).

---

## 4. How the System Works (Architecture & Intended Cognitive Flow)

1. **`SEEKNAL_ASK.md` — Decision Operating System.** Classifies every input (SMALL_TALK / META / OUT_OF_SCOPE / CLARIFICATION / DATA_QUESTION). For a DATA_QUESTION it fills a **Semantic Commitment Block** (Entity / Operation / Dimensions / Time Scope / Output Shape), runs a **State Comparison Engine** against the Conversation Ledger, then routes by OPERATION.
2. **Routing.** `OPERATION = FORECAST` → `bpom-forecaster` skill (6-phase SQL pipeline). Everything else → `bpom-analyst` skill.
3. **`bpom-analyst` pipeline:** `PHASE 0 (mandatory context load)` → `CAPTURE` → `RESOLVE` (dictionary "Translation Binding" gate) → `PLAN` → `EXECUTE` → `REFLECT` (+ `evidence-auditor`) → `GENERATE` (mandatory outbound dictionary JOIN).
4. **Context files** (`context/*.md`) are loaded on demand per the Information-Need hierarchy in `SEEKNAL_ASK.md §5`.

This architecture is sound. The failures below come from **what the agent is told to do inside RESOLVE/EXECUTE**, not from the routing skeleton.

---

## 5. Root Cause Analysis — SQL Execution Traced to Context / Skill / SEEKNAL_ASK

This is the heart of the audit. Each subsection gives the question, the pedoman expectation, the **actual SQL executed step by step**, what went wrong, and the **exact instruction** responsible.

### RC-A — Cross-system risk scope has no deterministic rule (largest UAT failure driver)

Two questions, executed minutes apart, treat ERLA in **opposite** ways. That inconsistency is the diagnosis.

**Case A1 — `UAT-MT-2` (over-includes ERLA).**
Prompt: *"ada berapa produk pangan olahan risiko menengah tinggi yang sudah punya izin edar?"*
Pedoman: **11.919 (ERBA-only).** YAML note: *"ERLA tidak dapat isolasi MT."* `assert_not_contains: 95.736`.
Agent answer: **98.231** (FAIL). Tool calls 7, SQL 3.

Step-by-step SQL the agent ran:
1. `SELECT sumber, kode, deskripsi FROM data_dictionary WHERE kategori='KATEGORI_DOKUMEN' …` — inbound lookup; correctly binds ERBA "Menengah Tinggi" → `302`.
2. (dictionary lookup for the ERLA side risk category)
3. The analytical query:
   ```sql
   WITH all_nie AS (
     SELECT 'ERBA' AS system, nomor
     FROM warehouse.public.t_produk_3_erba
     WHERE kategori_dokumen = '302'          -- Menengah Tinggi  (CORRECT, ~11.9k)
       AND status IN ('0999','0906','9999') AND trader_id::bigint NOT IN (5,17,50,85)
     UNION ALL
     SELECT 'ERLA' AS system, nomor
     FROM warehouse.public.t_produk_3_rilis_erla
     WHERE jenis_dokumen = '303'             -- "Pangan Medium Risk (MT + MR)"  (WRONG, ~87k)
       AND status IN ('0099','0999','0906','9999') …
   ) SELECT COUNT(DISTINCT nomor) FROM all_nie;
   ```
   The agent's own inline comment says `303 = MT + MR`, yet it still UNION-ed that bucket into a Menengah-**Tinggi**-only count. `11.9k + 87k ≈ 98.2k`.

**Case A2 — `UAT-MR-1` (under-includes ERLA).**
Prompt: *"Berapa jumlah izin edar pangan olahan dengan risiko menengah rendah?"*
Pedoman: **119.374 = ERBA `303` (41.425) + ERLA `301` "Pangan Low Risk = setara MR" (77.949).**
Agent answer: **41.516** (FAIL — ERBA only). Tool calls 7, SQL 3. Final query:
```sql
SELECT COUNT(DISTINCT nomor) FROM warehouse.public.t_produk_3_erba
WHERE kategori_dokumen = '303'               -- ERBA MR only; ERLA never joined
  AND status IN ('0999','0906','9999') AND trader_id::bigint NOT IN (5,17,50,85)
  AND tanggal >= '2000-01-01' AND tanggal < '2030-01-01';
```

**Why this happens — contradictory and under-specified instructions:**

| Instruction | What it pushes | Effect |
|---|---|---|
| `business_glossary.md:258` — *"Risk queries (MR/MT/T)… use **ERBA-only** for risk analysis"* | ERBA-only always | correct for MT, **wrong for MR** (caused A2) |
| `business_glossary.md:88–91` — *"ERLA cannot isolate Menengah Tinggi… if a combined figure is requested, ERLA contributes combined medium risk"* | sometimes combine | conflicts with `:258` |
| `code_translation_protocol.md:110–118` — *"test each candidate against data with a quick `COUNT(DISTINCT)` … ERLA Medium ≈ ERBA MT+MR combined"* | resolve equivalence by **data magnitude** | a **definitional** decision pushed onto a numeric probe → unstable |
| `SEEKNAL_ASK.md §2` — *"no year stated → ALL-TIME, UNION ERBA+ERLA"* | always union both | loud default that competes with the quiet MT-exclusion caveat |

The agent receives one rule that says "ERBA-only for risk," another that says "combine when requested," a third that says "decide the cross-system equivalence by running COUNT-tests," and a global default that says "always UNION." There is **no single deterministic policy** that says *for level X, the system scope is Y*. So the agent guesses — and guesses differently each time. **The cross-system risk equivalence is a business definition, but the system currently tries to derive it from query magnitudes at runtime.**

### RC-B — Metric definition drift (entity / date column / status / scope)

**Case — `UAT-JP-MAYOR-2025-1`.**
Prompt: *"berapa permohonan perubahan mayor yang **disetujui** tahun 2025?"*
Pedoman: **6.636** (`jenis_permohonan = '302'` ERBA 2025).
Agent answer: **8.153** (FAIL). Tool calls 10, SQL 6. Final analytical query:
```sql
WITH permohonan_2025 AS (
  SELECT date_trunc('month', tanggal_bayar::timestamp) AS bulan, produk_id
  FROM warehouse.public.t_produk_3_erba
  WHERE jenis_permohonan = '302'                       -- Perubahan Mayor  (binding OK)
    AND status IN ('0999','0906','9999')
    AND tanggal_bayar::timestamp >= '2025-01-01'       -- counted by SUBMISSION date
    AND tanggal_bayar::timestamp <  '2026-01-01'
    AND trader_id::bigint NOT IN (5,17,50,85)
) SELECT COUNT(DISTINCT produk_id) FROM permohonan_2025 GROUP BY ROLLUP(bulan);
```
The code binding (`302`) is right, but the word **"disetujui" (approved)** was not translated into approval semantics — the agent counted *submitted* applications by `tanggal_bayar` rather than *approved* ones. The verb→(entity, date column, status) mapping is incomplete. `SEEKNAL_ASK.md §2` pins `registrasi → tanggal_bayar` and `NIE → tanggal`, but there is no deterministic rule for "disetujui/diterbitkan/diproses" combined with a `jenis_permohonan`.

*(A milder instance: `UAT-BTP-TREN-1` gets 2023 = 950 exactly right but 2024 = 1.107 vs 1.089 and 2025 = 1.542 vs 1.523 — a +1–2 % drift from a subtle status/dedup difference, not a wrong direction.)*

### RC-C — Unfamiliar concept → unbounded discovery → **empty answer** (cause of KLAIM 3→0)

**Case — `KLAIM-1` (and `-2`, `-3` identical pattern).**
Prompt: *"Berapa banyak produk pangan olahan yang memiliki klaim kesehatan tahun 2024?"*
Pedoman: a count exists (e.g. KLAIM-2: klaim 2024 = 2.492). Assertion is *lenient* (only needs `"klaim"` + `"2024"`).
Agent result: **EMPTY answer.** Tool calls **24**, SQL **14**.

Step-by-step, the agent never converges — it probes the dictionary and the table repeatedly, then guesses with `ILIKE`:
1–6. repeated `data_dictionary` lookups (STATUS / claim categories)
7. `SELECT DISTINCT jenis_pangan, nama_kategori FROM t_produk_3_erba WHERE nama_kategori ILIKE '%klaim%' …`
…
14. `SELECT nama, merk, klaim_label FROM warehouse.public.t_produk_3_erba WHERE klaim_label ILIKE '%0002%' AND tanggal >= '2024-01-01' LIMIT 10`

`KLAIM-3` ends even more desperately: `SELECT count(*) … WHERE nama ILIKE '%kesehatan%' OR merk ILIKE '%kesehatan%' OR keterangan ILIKE '%kesehatan%'`. After 24 tool calls the agent **fails to finalize** and returns an empty string. The failure here is not a wrong number — it is **no number**.

**Why:** there is no teaching path for the `klaim` / `klaim_label` concept, so the discovery loop is unbounded; the stop-rule in `bpom-analyst/SKILL.md` PHASE 4 (*"if ~12 tool-calls have been made… proceed to REFLECT. Do not loop"*) is advisory and was exceeded (24); and there is **no mandatory fallback** ("if not resolved in N probes, answer best-effort + state the limitation — never return empty").

### RC-D — Over-querying simple questions (the SQL/tool inflation)

**Case — `UAT-AMDK-1`.** Prompt: *"Berapa jumlah NIE untuk produk AMDK pada tahun 2023?"* — a single-year scalar that needs **one** query. The agent ran **10 SQL / 7+ tool calls**:
1. `SELECT … FROM data_dictionary WHERE kategori='STATUS' …`
2. `SELECT … FROM data_dictionary WHERE kategori='STATUS' …`  ← repeat
3. `SELECT kode,deskripsi FROM data_dictionary WHERE kategori='STATUS' AND sumber=… ` ← repeat
4. `… kategori='STATUS' …` ← repeat
5. `SELECT status, COUNT(*) FROM t_produk_3_rilis_erla WHERE status IN (…)` — status probe
6. `… kategori='STATUS' …` ← **fifth** STATUS lookup
7. `SELECT jenis_pangan, nama_kategori, COUNT(*) FROM t_produk_3_erba WHERE nama_kategori ILIKE '%air minum%' …` — segment discovery, although **AMDK = `jenis_pangan='1401'` is already given in `SEEKNAL_ASK.md §4**
8. `… WHERE jenis_pangan='1401' …` — discovery confirm
9. `SELECT source, COUNT(DISTINCT nomor) … (ERBA UNION ERLA)` — per-source count
10. `SELECT COUNT(DISTINCT nomor) …` — separate grand total

Five identical STATUS lookups + discovery for an already-known code + a split count/total. **Why:** `SEEKNAL_ASK.md §5` (*"Dictionary — mandatory for every coded term"*) and `bpom-analyst/SKILL.md` PHASE 2 (*"No SQL may be written until every coded term is bound from the dictionary"*) are absolute, with **no within-turn dedup**, **no exception for already-authoritative codes**, and **no exception for codes used only as mandatory filters** (STATUS does not need translating to *count* NIE). The `2026-06-12` breakdown rule then adds the separate grand-total query.

### RC-E — No-answer drops (noted, not the focus)

16 requests returned `status_code 200` with `tool_calls = 0`, `sqls = 0`, and an empty answer. These are **finalize/generation drops at the orchestrator layer**, not SQL-reasoning errors. They should be investigated separately on the serving side; they are out of scope for the reasoning analysis here but inflate the "empty" bucket in Section 2.

---

## 6. What the Context Changes Introduced — and What They Caused

| Planning doc (commit) | What it changed | Intended benefit | Observed side-effect |
|---|---|---|---|
| `2026-06-12-dimension-reasoning-and-data-coverage.md` (`85deadc`) | Mandatory per-year breakdown **+ separate global grand-total**; "no year → ALL-TIME UNION ERBA+ERLA" for every operation; fresh query on follow-ups | Correct altitude (month/region/category), no double-count totals | **+SQL per case** (RC-D), and the loud ALL-TIME-UNION default now competes with risk-isolation caveats (RC-A) |
| `2026-06-17-dictionary-grounded-code-translation.md` (`240ec43`, `93712c9`, `7d64c0a`) | Mandatory **inbound dictionary lookup before any SQL** for every coded term; mandatory **outbound JOIN**; **COUNT-test** to resolve ambiguity; REFLECT→RESOLVE re-translate loop | Stop using cached/wrong code meanings; resolve from live dictionary | **+SQL/+tool per case** (RC-D); and the **root of RC-A** — a definitional equivalence (ERLA↔ERBA risk) is delegated to a data-magnitude probe, producing unstable scope decisions |
| `2026-06-18-llm-forecaster-skill.md` (`e555ab1`, `185fecf`) | New `bpom-forecaster` skill, 6-phase SQL pipeline; FORECAST routing in `SEEKNAL_ASK.md` | Real forward-looking answers, structured output | **FORECAST 2→8/12** (clear win); pipeline cost is scoped to forecast intent only |
| `2026-06-17-uat-singleturn-test-suite.md` (`2baf7b2`) | 101 DB-verified UAT cases | Standing regression guard | **Measurement only** — no agent behavior change; its exact-substring scoring slightly under-reports true accuracy |

The two retrospective-side docs (dimension-reasoning, dictionary-grounded) are the source of both the efficiency regression and the risk-scope instability. The forecaster doc is a genuine, contained improvement.

---

## 7. Why the System Behaves This Way (Hypotheses)

- **H1 — Loud defaults override quiet exceptions.** "ALL-TIME → UNION both systems" is stated as a hard behavioral contract up front; "ERLA cannot isolate MT" lives deeper in a context file as a structural note. Under attention pressure the loud rule wins (RC-A, Case A1).
- **H2 — Definitional decisions are routed through data probes.** Asking the agent to "COUNT-test which code is equivalent" treats a *business definition* as an *empirical question*. Magnitude cannot tell you whether ERLA Low "counts as" MR — that is a policy choice — so the outcome is non-deterministic (RC-A).
- **H3 — Exploration is unbounded; the stop-rule is advisory.** With no hard probe budget and no mandatory fallback, an unfamiliar concept (klaim) sends the agent into a 24-call loop that ends in an empty answer (RC-C).
- **H4 — The mandatory gate has no proportionality.** "Look up every coded term, every time" with no dedup and no "already-known" exception turns a one-query task into ten (RC-D).
- **H5 — The teaching itself is internally inconsistent.** `business_glossary.md:258` and `:90` give opposite guidance on risk scope; the agent cannot be consistent when its sources are not.

---

## 8. How Many Fail, and of What Kind

- Combined after-238: **126 pass / 112 fail.** Of the 112: **85 substantive, 3 string-only, 24 empty** (16 of those empty are orchestrator no-run, RC-E).
- UAT-only: **19 pass / 82 fail** → **~76 substantive, ~0 string-only, 6 empty.**
- On the 95 matched non-empty cases, execution cost rose: tool calls 10.7 → 11.9, SQL 5.7 → 6.7.

The earlier hypothesis that failures are "mostly string-match noise" is **rejected for the UAT set**: these are genuine SQL-construction errors concentrated in RC-A and RC-B.

---

## 9. What Works Well

- **Forecaster** is a real win: FORECAST 2→8/12, with the structured 7-block output the suite expects.
- **Sumber-aware dictionary lookups** are happening (queries filter `sumber`), and **code bindings are often correct** (ERBA MT→302, Perubahan Mayor→302). The defect is *scope/aggregation*, not the inbound code lookup itself.
- **Honesty behaviors hold:** no fabricated numbers on failed queries; the agent reports ERBA/ERLA provenance in prose.
- Simple, well-specified cases remain correct (e.g. AMDK 2023 produced the right per-source structure even while over-querying).

---

## 10. Recommendations — Teach the Agent, Don't Hardcode

All recommendations are **reasoning policies** (general, reusable), not per-question answer tables.

- **R-A (RC-A, highest impact): one deterministic cross-system risk-scope policy.** Teach a single rule with its rationale: *a risk level that ERLA cannot isolate (Menengah Tinggi) → ERBA-only, and state the limitation; a risk level that has an ERLA equivalent (MR ↔ ERLA Low) → ERBA code + the equivalent ERLA code; always state the lossy-mapping caveat.* Remove the contradictory `business_glossary.md:258` line. Move this decision **out of the COUNT-test path** — equivalence is definitional, not empirical. (This generalises like "UMKM = scale 1+2+3"; it is ontology, not a hardcoded answer.)
- **R-B (RC-B): a verb→(entity, date column, status) resolution.** Teach how "disetujui / diterbitkan / diproses / diajukan" map onto entity, date column, and status filter, so approval-semantics questions stop being counted as raw submissions.
- **R-C (RC-C): bounded discovery + mandatory non-empty fallback.** Make the probe budget binding; when a concept cannot be resolved within it, the agent must answer best-effort **with a stated limitation** — never return empty. Add a minimal teaching path for `klaim_label`.
- **R-D (RC-D): proportional execution.** Look up a code only if it is not already authoritative (glossary §4) and is genuinely needed for translation/disambiguation (not merely as a known mandatory filter); **dedup each dictionary `kategori` to one lookup per turn**; collapse breakdown + grand-total into one `ROLLUP`.
- **R-E (RC-E): orchestrator-side investigation** of the `tool_calls=0` empty-answer drops.

---

## 11. Key Numbers to Verify Against the Live `rpo_v2` Database (Next Phase)

Before changing instructions, confirm these pedoman anchors with live queries (this is the "connect to DB" step deferred until now):

| Check | Pedoman | What the agent produced |
|---|---|---|
| MT all-time (ERBA `kategori_dokumen='302'`) | 11.919 | 98.231 (RC-A) |
| MR all-time (ERBA `303` + ERLA `301`) | 119.374 (41.425 + 77.949) | 41.516 (RC-A) |
| ERLA `jenis_dokumen='303'` magnitude (≈ MT+MR) | ~87k | (used wrongly for MT) |
| Perubahan Mayor 2025 (ERBA `jenis_permohonan='302'`) | 6.636 | 8.153 (RC-B) |
| BTP ERBA trend | 2023=950 / 2024=1.089 / 2025=1.523 | 950 / 1.107 / 1.542 (RC-B drift) |
| Klaim kesehatan 2024 | 2.492 | (empty — RC-C) |

---

## Appendix A — Reproducibility

Metrics and SQL traces were extracted directly from the JSON artefacts:
```python
import json, glob
for f in glob.glob("seeknal/tests/outputs/2026-06-18/concurrency-production/concurrency_*.json"):
    d = json.load(open(f))
    for r in d["per_request"]:
        m = r["metrics"]
        # r["scenario_id"], r["passed"], r["failures"], m["tool_calls"], m["sqls"]
```
Domain breakdown buckets by `scenario_id.split('-')[0]`. The four "after" files were unioned by `scenario_id` and confirmed to cover the same 238 scenarios as the baseline.

## Appendix B — Cross-References

- Orchestrator: `SEEKNAL_ASK.md` §2 (behavioral contracts), §4 (segment codes), §5 (information hierarchy), §6 (guardrails)
- Skill: `seeknal/skills/bpom-analyst/SKILL.md` PHASE 0/2/4/5/6
- Context: `business_glossary.md:88–91, :253–262`; `code_translation_protocol.md:31–41, :110–118`
- Planning: `docs/planning/2026-06-12-…`, `2026-06-17-dictionary-grounded-…`, `2026-06-18-llm-forecaster-…`
- Prior audits: `uat_audit_report_15jun2026.md` (RC-1 ERLA risk-scope first identified), `audit_multiturn_18jun2026.md` (warehouse-connection findings)
