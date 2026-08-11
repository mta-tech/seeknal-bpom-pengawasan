---
name: bpom-analyst
description: "Orchestrate BPOM RPO data questions end-to-end: capture intent, resolve constructs, plan, execute SQL, REFLECT/audit the evidence against business rules, then answer. Use for every quantitative BPOM question (NIE, permohonan, risiko, skala/UMKM, komitmen, produk spesifik, gabungan sistem)."
tags: [bpom, text-to-sql, orchestration, reflection, analyst]
version: "2.0.0"
---

# BPOM Analyst — Orchestrator

**Workflow:** PHASE 0 → CAPTURE → RESOLVE → PLAN → EXECUTE → REFLECT → GENERATE

This skill directs the **thinking flow** for BPOM data questions. Its goal is to answer
with **correctness, business accuracy, and honesty** — not just produce a number.

---

## PHASE 0 — MANDATORY CONTEXT LOAD (before anything else)

**This step is NOT optional.** Load these files unconditionally before CAPTURE:

```
read_project_file('context/business_glossary.md')
read_project_file('context/data_quality_rules.md')
read_project_file('context/code_translation_protocol.md')
```

These files contain: entity definitions, ERBA TEXT cast rules, mandatory NIE filters,
product segment codes for ERBA and ERLA, the **two-way sumber-aware code translation
protocol** (codes are resolved from the live dictionary, never recalled), and
`status_komitmen` float/integer normalization.

Proceeding without Phase 0 will produce wrong SQL. There are no exceptions.

---

## PHASE 1 — CAPTURE (understand the question)
1. **Begin from the Decision Layer output** (§0.5 SEEKNAL_ASK.md). The Semantic Commitment Block and State Comparison Engine classification are already available — use them as the starting point. Apply the **inherit ANSWERS, re-derive METHODS** principle (§0.5):
   - `EXPLAIN_EVIDENCE` (pure explanation / cross-turn arithmetic over ledgered answers) → skip directly to GENERATE; no new query.
   - `MODIFY_SCOPE` or `EXTEND_SCOPE` → **still run RESOLVE this turn.** Reuse prior **answers** (from the Conversation Ledger) only as inputs; re-derive the **method** (date column, count column, definitions, filters, casts) from scratch via the Information Need Resolution hierarchy. Then run only the delta/additional query. Never carry over a column/definition/filter choice just because it was used last turn.
   - `NEW_QUESTION` → full workflow from scratch.
2. **Normalize typos/informal language first** (see `intent_mapping.md` Step 0). Do not ask for clarification on obvious typos; do not inject raw user words into SQL.
3. **Determine DOMAIN first** via the router in `data_architecture.md` (Registrasi Pangan or Forecast). The **supervision domain (pemeriksaan/pengujian/inspection/balai) is NOT connected** — if asked, say so honestly and do NOT invent `star.*`/inspection tables.
4. Identify 4 components: **ENTITY** (NIE/permohonan/BTP/perusahaan/produk) · **OPERATION** (count/trend/breakdown/top/compare/list) · **DIMENSION** (time/risk/scale/commitment/segment) · **CONDITION** (year, system, product).
5. **Resolve implicit references** ("dari situ", "tahun yang sama", "selisihnya") against the scope/numbers from the previous turn. Change ONLY the component the user changed.
6. **Apply default scope**: "pangan olahan" = main product tables (BTP only if explicitly requested); risk & commitment = ERBA-only; system not specified = UNION ERBA+ERLA. **Time scope**: a stated year → that year; a stated range / "N tahun terakhir" → that range (+ `GROUP BY` year for trends); **NO year stated → ALL years (all-time)** via a wide bounded range (`>= '2000-01-01' AND < '2030-01-01'`), reported as total + per-year breakdown. Never silently assume a single year.
7. **Emit the Semantic Commitment Block before any SQL** — confirm and expand the Decision Layer output with full resolved detail:

   ```
   Intent:
     Entity:       [NIE | PERMOHONAN | BTP | PERUSAHAAN | PRODUK]
     Operation:    [COUNT | TREND | BREAKDOWN | TOP | COMPARE | LIST]
     Dimensions:   [list each — mark DEPENDENT or INDEPENDENT]
     Time Scope:   [stated year | stated range | ALL-TIME]
     Output Shape: [scalar | 1D-time | 1D-dim | 2D | multi-query synthesis]
   Scope: entity=… · system=… · year=… (or ALL-TIME) · BTP=yes/no
   SCE:   [NEW_QUESTION | MODIFY_SCOPE | EXTEND_SCOPE | EXPLAIN_EVIDENCE]
   ```

   The year is **BINARY**: stated → that year; not stated → ALL-TIME. There is **no "most
   complete / most recent year"** option. This block is what REFLECT/`evidence-auditor`
   checks against the prompt.
7. **Multi-Dimensional Decomposition** — apply after step 3 when the question involves more than one dimension or asks "which/what" about an entity:

   **Step A — Count the dimensions the user asks for simultaneously.**
   A dimension is anything requiring a separate GROUP BY column: time (tahun/bulan),
   location (daerah), risk (risiko), scale (skala), category (kategori pangan), etc.

   **Step B — Classify the relationship between dimensions:**
   - **DEPENDENT** dimensions: user wants a result that crosses both at once.
     Signals: "per X dan Y", "tren per X", "X berdasarkan Y per tahun"
     → One query with GROUP BY dim1, dim2 (multi-column GROUP BY)
     → One row in the result = one combination of (dim1, dim2)
   - **INDEPENDENT** dimensions: user wants each dimension reported separately.
     Signals: "berdasarkan risiko, skala, dan tren" (three separate aspects)
     → N queries, one per dimension → synthesize in GENERATE

   **Step C — Determine granularity from the question's SUBJECT noun.**
   The subject noun determines what one row of output represents:
   - "Berapa" / scalar → no GROUP BY name column needed
   - "Apa" / "Mana" in ranking context → GROUP BY the named entity's label column
   - "Produk apa yang paling X" → subject is produk as category → GROUP BY nama_kategori
   - For the full subject → GROUP BY mapping, see `intent_mapping.md` §Question Decomposition.

   **Step D — Determine if one query covers all dependent dimensions.**
   - YES if all dimensions share compatible filter logic and the same table source
   - NO if one dimension requires ERBA-only (risiko via kategori_dokumen) while another
     requires ERBA+ERLA combined (skala industri) → separate queries + GENERATE synthesis

## PHASE 2 — RESOLVE (identify and fill information gaps before SQL)

After CAPTURE, identify every piece of information still needed before SQL can be
written. For each gap, use the information taxonomy below. **Do not write SQL until
RESOLVED CONSTRUCTS are written.**

**RESOLVE runs every turn — including follow-ups.** Even on `MODIFY_SCOPE` / `EXTEND_SCOPE`,
the method (date column per entity, count column, definitions, filters, casts) is re-derived
here from the authority sources — it is **never inherited** from the previous turn. Only
validated **answers** carry over (via the Ledger), and only as inputs. This is what keeps a
wrong choice in one turn from drifting into the next.

**Re-derive means re-READ the source, not recall from memory.** In a long conversation the
turn-0 context load fades from attention; by turn 15+ the agent may "remember" a wrong method
(e.g. drift to `tanggal_aju` for permohonan). So for the method-defining facts of THIS turn —
the date column per entity (permohonan→`tanggal_bayar`, NIE→`tanggal`), mandatory filters, and
casts — re-open the relevant context file (`data_quality_rules.md`) rather than trusting recall.
A quick re-read is cheaper than a wrong answer.

**Provenance check for every business definition.** Any term that carries a definition — UMKM,
"pangan olahan" scope, "dibatalkan" / "disetujui" commitment codes, a product segment — must be
resolved from `business_glossary.md` (or `data_dictionary`), NOT from general/world assumption.
Before using a definition, ask: *did I get this from the glossary this turn, or am I assuming?*
If assuming → consult the glossary. (E.g. UMKM = skala 1+2+3 = Mikro+Kecil+**Menengah**, never
Mikro+Kecil only — confirm from glossary, do not default to the colloquial meaning.)

**A new number is always produced by a query — never recomputed from memory.** A follow-up that
asks for a different number ("dari situ, yang UMKM berapa?", "kalau yang disetujui?") requires a
fresh `execute_sql` this turn. Do NOT derive it by re-summing a breakdown you recall from a prior
turn — that is how components get dropped (e.g. UMKM losing Menengah). The only memory-only step
allowed is arithmetic over numbers that are **already validated answers in the Conversation
Ledger**, and only when every operand is present there; if any operand is missing, query.

**Coverage check before grouping/ranking a dimension.** When a question slices by a dimension
(kategori, daerah, skala, …), pick the column by **coverage, not name** (see
`data_quality_rules.md` §Coverage-aware column choice). If a breakdown comes back dominated by
NULL / `'NULL'` / "Tanpa Kategori" / "tidak teridentifikasi", stop and switch to a more complete
column or resolvable code for the same concept (category → `kategori_pangan`→AKRONIM, not
`nama_kategori`; unqualified daerah → trader `kotakab_id`, not `daerah_pabrik`). If coverage stays
low, report the gap honestly — never present "Tanpa Kategori" as the answer.

| What is needed | Where to get it |
|---|---|
| Concept / term definition (NIE, permohonan, ERBA, UMKM, commitment) | `context/business_glossary.md` (loaded in Phase 0) |
| Which table or column contains the data | `read_project_file('context/data_architecture.md')` |
| What a code value means (status, risiko, skala, daerah, negara) | `read_project_file('context/code_resolution.md')` then `execute_sql: SELECT kode, deskripsi FROM data_dictionary WHERE kategori = '...'` |
| Mandatory filter rules and ERBA cast pattern | `context/data_quality_rules.md` (loaded in Phase 0) |
| Product segment code (AMDK, susu, garam, etc.) | `business_glossary.md` §Product Segment Codes → if not listed: discovery query (see below) |
| SQL structure or query pattern | `read_project_file('context/query_recipes.md')` |
| Forecast / prediction data | `read_project_file('context/forecast_guide.md')` |
| Word → entity / operation / dimension mapping | `read_project_file('context/intent_mapping.md')` |

**Product segment discovery (for segments not in business_glossary.md):**
```sql
-- Step 1: find codes via nama_kategori
SELECT DISTINCT jenis_pangan, nama_kategori, COUNT(*) AS cnt
FROM warehouse.public.[table]
WHERE nama_kategori ILIKE '%<keyword>%'
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10

-- Step 2: confirm with name sample
SELECT DISTINCT nama FROM warehouse.public.[table] WHERE jenis_pangan = '<code>' LIMIT 5
```

**Column Purpose Check** — before selecting any column, classify its purpose:
- **WORKFLOW STATE** columns answer "What stage is this record in?" — use for filtering by stage, NOT for "why/reason" questions
- **REASON / DESCRIPTION** columns answer "Why did this happen?" — use for "alasan", "mengapa", "penyebab" questions
- **CLASSIFICATION** columns answer "What category/level is this?" — use for risk, scale, type grouping

The `status` column is a WORKFLOW STATE column. Status code values (0999, 9999, 0009)
are processing stages, NOT reasons. When user asks "what is the most common reason",
never report status codes as "uncategorized reasons" — they are irrelevant to the answer.
For which specific column serves which purpose → load `context/business_glossary.md` §Column Purpose Guide.

**Translation Binding gate (MANDATORY — code meanings come from the dictionary, never memory).**
For every coded term in the question (risk, status, commitment, jenis_permohonan, skala, negara,
…), resolve it **at runtime** via `context/code_translation_protocol.md` (inbound word→code,
**sumber-aware**) and write a binding row. **No SQL may be written until every coded term is bound
from the dictionary** — not recalled from a context table (those no longer hold code meanings).
On a follow-up turn the bindings are **re-derived** (re-queried), never inherited.

```
Bindings:
  term            | kategori          | sumber | kode(s) | source
  "menengah tinggi"| KATEGORI_DOKUMEN | ERBA   | 302     | dict lookup
  "dibatalkan"     | STATUS_KOMITMEN  | ERBA   | <final> | dict lookup
```

- 0 rows → typo path (multi-pattern ILIKE); >1 / cross-system divergence → COUNT-test candidates,
  pick the data-supported one, state the basis (protocol §3). Ambiguity is never silently guessed.
- Segment codes (AMDK, Garam) are not in the dictionary → discover via `nama_kategori` probe and
  pick the **parent** category by coverage (protocol §4) — do not hardcode a sub-code.

**RESOLVED CONSTRUCTS — write this block before PLAN:**
```
Table   : [which table(s) — both ERBA and ERLA if ALL-TIME or 2023+ scope]
Shape   : [scalar | 1D-time | 1D-dim | 2D: year×dim]
Segment : [jenis_pangan / kategori_pangan — prefer PARENT category; codes per system if relevant]
Cast    : [ERBA columns needing ::timestamp or ::bigint, or 'none' if ERLA-only]
Risk    : [ERBA: kategori_dokumen | ERLA: jenis_dokumen — resolved per system from the dictionary, NOT reused across systems]
Bindings: [every coded term → kode, from the Translation Binding gate above]
Dim     : [dimension column chosen + why by coverage — e.g. kategori_pangan→AKRONIM (not nama_kategori); kotakab_id (not daerah_pabrik)]
Time    : [single-year range | all-time per-year | month×year | N-years-back from latest data → output = per-period breakdown + grand total LAST, never a bare total]
Filters : [every mandatory filter listed explicitly; jenis_permohonan only if "NIE baru" (see data_quality_rules §jenis_permohonan); commitment Case A vs B (see §Commitment)]
```

Never write SQL before RESOLVED CONSTRUCTS (including Bindings) are complete.

---

## PHASE 3 — PLAN (design steps, do not improvise)

Write an explicit numbered plan (3–8 steps), may use `submit_plan`. Example step sequence:
1. Use RESOLVED CONSTRUCTS from PHASE 2 as the query blueprint.
2. Fetch the matching SQL framework from `query_recipes.md` (e.g. R1/R3/R6), then adapt to the question's scope.
3. Compose ONE final query (tables, filters, dimensions, casts all confirmed).
4. Execute the final query in PHASE 4 (EXECUTE).
5. Resolve result codes to labels via `data_dictionary` (see `code_resolution.md`).
6. Perform REFLECT/AUDIT in PHASE 5 before answering.

Recipe selection rules:
1. Pick the recipe whose scope matches; **adapt it**, don't force it.
2. If no recipe fits, build the query from `intent_mapping.md`.

## PHASE 4 — EXECUTE (controlled execution)
- Goal: **one final query** that answers the question — not unlimited exploration.
- Dates use **date ranges** (`>= '{Y}-01-01' AND < '{Y+1}-01-01'`), NEVER `EXTRACT` (timeout on SSH tunnel).
- **Stop rule:** if ~12 tool-calls have been made or results are sufficient, proceed to REFLECT. Do not loop.
- If a query errors/times out: read the error, fix the SQL, retry. **Do not** fall back to aggregate/forecast tables as a substitute for transactional numbers.
- If a query returns `Catalog "warehouse" does not exist`, re-run the SAME query once; if it still fails, report a transient connection error honestly — do NOT loop schema-discovery.

**Pre-submit checklist (check before running every query):**
- [ ] Every coded filter value comes from a **Binding** (dictionary lookup), not memory?
- [ ] Any `data_dictionary` lookup/JOIN filters **`sumber`** (per system) — to avoid fan-out on multi-source categories (`STATUS`, `KEMASAN_ID`) and shared codes (`9999`)?
- [ ] ERBA + ERLA UNION: ERBA side has `::timestamp` on `tanggal`/`tanggal_bayar` and `::bigint` on `trader_id`?
- [ ] Query filters `status_komitmen`: using `ROUND(status_komitmen::numeric)::int::text`, not a plain string `= '5'`?
- [ ] Risk filter resolved **per system** from the dictionary: ERBA `kategori_dokumen` (KATEGORI_DOKUMEN), ERLA `jenis_dokumen` (JENIS_DOKUMEN) — codes NOT reused across systems?
- [ ] `jenis_permohonan` applied only for "NIE baru" intent (omitted for "all active NIE")? Commitment query uses the correct Case A vs B (NIE status filter dropped for lifecycle counts)?
- [ ] ERBA `tanggal` NULL guard added for GROUP BY queries without date range? (`WHERE tanggal IS NOT NULL AND tanggal != ''`)

## PHASE 5 — REFLECT / AUDIT (MANDATORY before answering) ← core

**State Comparison Engine check — run first:**
Read the SCE classification from the Semantic Commitment Block:
- `EXPLAIN_EVIDENCE` → no new query was run; the answer is computed from ledgered facts.
  Skip the filter checklist, but verify the arithmetic/restatement is consistent with the
  Ledger. Proceed to GENERATE.
- `MODIFY_SCOPE` or `EXTEND_SCOPE` → **audit this turn's delta query in full** against the
  mandatory filter checklist below (steps 1–5), exactly as for a new query — the method was
  re-derived this turn and must be validated. Prior **answers** reused as inputs are trusted
  (they passed REFLECT when first computed) and are not re-queried, but any number produced by
  a query this turn is audited.
- `NEW_QUESTION` → full audit of all evidence gathered this turn (steps 1–5 below).

Before writing the answer, run the audit (full rubric in skill `evidence-auditor`; summary):
1. **List evidence**: write each number obtained + the originating query.
2. **Select authoritative**: one result whose scope **exactly** matches intent (entity, system, year, filters, BTP?).
3. **Mandatory filter checklist** (source: `data_quality_rules.md`): `COUNT(DISTINCT …)` ✓ valid status ✓ date range (not EXTRACT) ✓ exclude test accounts ✓ exclude 1900/1970 ✓ BTP scope correct ✓ codes dictionary-resolved & **sumber-aware** ✓ `jenis_permohonan` only for "NIE baru" intent (omitted for "all active NIE") ✓ commitment uses the correct **Case A vs B** (Case B = lifecycle "dibatalkan" → NIE status filter DROPPED; Case A = "NIE with commitment X" → filters kept).
4. **Sanity & re-evaluation**: result ≠ 0 without reason; `COUNT DISTINCT ≤ COUNT`; MR ≤ total MR ≤ total NIE; consistent with previous turns. Suspect **inflation** if far above domain expectation (missing status filter, or `sumber`-blind fan-out) and **under-count** if far below (wrong commitment case, or a sub-code instead of the parent segment). If the magnitude is implausible → **return to RESOLVE and re-translate** (re-check the bindings and the case), do not ship the number.
5. **Verdict**:
   - PASS → proceed to GENERATE.
   - FAIL/suspicious → fix (return to PLAN/EXECUTE), **max 3 rounds**.
   - Stuck / data truly unretrieval → **say so honestly. DO NOT fabricate numbers** and do not fill in "expected" values.

## PHASE 6 — GENERATE (answer to user)

**Communication Alignment — apply before writing any output:**
Context files are English working tools. Their language does NOT determine output language.
- Detect the language of the user's most recent question. Write the entire response in
  that language.
- Mirror the user's exact terminology: if they wrote "NIE" use "NIE"; if they wrote
  "izin edar" use "izin edar"; if they wrote "registrasi" use "registrasi".
- Keep unchanged regardless of response language: ERBA, ERLA, BPOM, NIE, BTP, AMDK,
  Garam Beryodium, Makloon, and all product names / category names / company names /
  region names as they appear in the database. These are proper nouns, not translated.

**Output Completeness Check — answer these before writing:**

1. "Does the output directly answer the question?"
   - User asked "which" / "what" → output must NAME the entity, not just count it
   - User asked "tren per X" → output must show X and time together in one result, not separately
   - User asked "prioritas" / "what to focus on" → output must name the priorities

2. "Are all requested dimensions represented?"
   Count the dimensions in the question. Verify each appears as a column or grouping in the output.

3. "For multi-query results — is there a synthesis?"
   If N queries were run for N independent dimensions, combine before presenting:

   **Synthesis Pattern A — Priority / Pengawasan questions:**
   After N result sets: identify entities appearing prominently in ≥ 2 results.
   These intersections are highest-priority findings → present them first.
   Example: entity X appears in top-5 by risiko AND top-3 by pembatalan → name it as priority.
   Then follow with per-dimension breakdown tables.

   **Synthesis Pattern B — Ranking questions ("X yang paling banyak Y"):**
   Output = ranked list: entity name, count, rank. Never summarize to a single total.
   Format: 1. Nama A — N occurrences · 2. Nama B — M occurrences

   **Synthesis Pattern C — Trend × Dimension ("tren X per Y"):**
   Output must show Y as rows with time as nested breakdown — not two separate tables.
   Y total + Y per-year trend is ONE result, presented together.

   **Synthesis Pattern D — Comparison ("X dibanding Y", "naik atau turun"):**
   Present both values side-by-side, compute difference, state direction.
   Format: "X: [value] · Y: [value] · Selisih: [delta] · arah: naik/turun N%"

   **Synthesis Pattern E — Count questions ("berapa X"), even without "tren":**
   Do NOT answer with a bare total. Show the **time breakdown first, grand total on the last line**:
   - no year stated → one row per year that has data, then the total;
   - a month named without a year → one row for that month in each year that has data, then the total;
   - a single explicit year → that year's figure (no month split unless a month is named).
   The set of years comes from the data (derive from the latest available year for "N tahun terakhir");
   never assume a fixed start year. Format as a `Tahun | Jumlah` table with a final **Total** row.
   **The Total row is a separate global `COUNT(DISTINCT nomor)`/`produk_id` over the whole set — NOT
   the sum of the per-year rows** (a `nomor` recurring across years would be double-counted; e.g. MR
   all-time row-sum 141.682 vs true distinct 119.314). Use a standalone aggregate / subquery / `ROLLUP`.

   **Synthesis Pattern F — Investigative / Root Cause ("kenapa / mengapa / penyebab"):**
   Trigger: user asks WHY something changed ("kenapa naik", "apa yang menyebabkan turun", "penyebab X",
   "alasan kenaikan"). This is NOT a standard COUNT or TREND — it requires decomposition reasoning.
   Do NOT answer with a bare trend table and leave interpretation to the user.

   Steps:
   1. **Confirm the inflection point.** Run or reuse the trend query. Identify the period where the
      change is sharpest (largest absolute or relative delta year-over-year).
   2. **Run a decomposition query** at the inflection period, splitting by the most informative
      dimension for the context (see R13 in `query_recipes.md`):
      - For permohonan surge → decompose by `jenis_permohonan` first, then top 5 traders.
      - For NIE shift by risk → decompose by `kategori_dokumen` (ERBA) per year.
      - For commitment anomaly → decompose by `status_komitmen` breakdown year-over-year.
   3. **Name the top contributor.** Identify the dimension-value that accounts for the largest share
      of the delta (absolute and %).
   4. **State the finding as a data-supported hypothesis, never a conclusion:**
      > "Kenaikan terbesar dikontribusikan oleh [X] sebesar [N] ([%] dari total delta). Faktor
      > non-data (kebijakan, regulasi, perubahan proses) tidak dapat dikonfirmasi dari data ini."
   5. **If no single contributor dominates** (delta is spread evenly across dimensions) → state that
      explicitly: "Kenaikan tersebar merata; tidak ada satu faktor dominan yang teridentifikasi
      dari data transaksi."
   6. **Never fabricate a policy or regulatory reason.** Only name what a query shows.

   **Synthesis Pattern G — SLA / Aging ("sudah berapa lama", "lama tertahan", "> N hari"):**
   Trigger: user asks about time-in-process for applications still in a non-final state.
   Entity = PERMOHONAN (not NIE). Age = `CURRENT_DATE - tanggal_bayar::date`.
   See R12 in `query_recipes.md` for the canonical template.
   Present as: (a) a summary table of age buckets (0–30 / 31–90 / 91–180 / >180 days) with counts,
   then (b) the oldest N applications by name/ID if the user asks to "see which ones".
   State the reference date used for the age calculation in the answer.
   Do NOT use `tanggal` (NIE issue date) for aging — that is the license date, not the wait start.

- Deliver **one reconciled number** + filter/scope explanation.
- **Update the Conversation Ledger** (§0.5 SEEKNAL_ASK.md) at the end of every data turn.
  Restate, in the TEXT, the active scope and each key number as a ledgered fact —
  `<number> = <scope> (from: <query>)` — because old SQL results are compressed by the harness;
  the ledger text is what survives for future-turn context and is what the State Comparison
  Engine reads next turn. For a breakdown, restate **every component value** and compute common
  aggregates proactively (e.g. UMKM = Mikro+Kecil+Menengah). The ledger records **answers and
  scope only — never the method** (do not log "I used column X").
- **Outbound translation is mandatory.** Resolve every coded column to its definition via the
  **sumber-aware** dictionary JOIN (`code_translation_protocol.md` §2.2 / `code_resolution.md`) —
  never display a raw code, and never JOIN without the `sumber` predicate (fan-out risk). The answer
  carries definitions (e.g. "Komitmen Dibatalkan"), not codes (e.g. `5`). For region codes with no
  `data_dictionary` match, explain they are legacy Kemendagri codes from ERLA — not "label not found".
- **Caveat hygiene:** do NOT narrate transient connection/tool errors you recovered from; add a caveat ONLY when it materially affects correctness/completeness. If the number was obtained, state it confidently.
- **Formatting:** use `-` for bullets (NEVER `*`); a table must stand alone with a blank line before/after, not adjacent to bullet/bold lines and not duplicated as bullets; prefer a TABLE for per-row numbers.
- **SQL transparency:** if the user asks to see the query ("tampilkan query", "query-nya apa", "show the SQL"), show the actual SELECT executed this turn as a fenced ```sql code block (readable/reusable), not a prose description. Never include credentials/DSN/host.

---

## Honesty principles (non-negotiable)
- Every number **must** trace to a real query result that passed REFLECT — executed in this turn, OR established by a query in an earlier turn of **this conversation** (carried in message history; that prior-turn recall is legitimate — see PHASE 5 restate-in-text). No number without a query basis.
- **Failed / empty / timed-out query = report the failure plainly.** Do NOT synthesize a table, ranking, trend, or "sample-year" number from memory, benchmark, or reference context. Keep **computed results** separate from **explanatory narrative** — never present a remembered figure as if it were computed. (A genuine prior-turn result for the same scope may be reused; a remembered/benchmark number may not.)
- **Keep the subject fixed.** If the requested entity/segment/dimension has no data (e.g. skala industri NULL for the asked segment), report that for the subject the user asked about — never silently switch to a different entity/segment that happens to have data.
- **Test data is NOT a data source.** Never answer from values in `seeknal/tests/` or via QA tools (`read_ask_test` / `run_ask_test` / `list_ask_tests`) — those are oracles for checking, not knowledge for answering.
- Better to answer "X with caveat Y" — or honestly "I could not retrieve this (reason)" — than a clean but wrong number.
