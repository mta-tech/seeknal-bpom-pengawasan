# seeknal-bpom-neo Ask Context — v2 (enhancement)

> **Status:** NEW file. Enhancement version of `SEEKNAL_ASK.md` (original file remains
> as reference). v2 = v1 + structured workflow discipline (capture→plan→execute→reflect→
> generate), mandatory filter checklist, default scope resolution, multi-turn state contract,
> anti-hallucination honesty rules, and typo tolerance. Activate by pointing the agent
> to this file when ready (without removing v1).

This project connects to a BPOM read-only PostgreSQL database (`rpo_v2`) of product
registration data for processed foods and food additives (BTP). Users are BPOM analysts,
and they **frequently write informally or with typos** (e.g. "jumlh", "brp", "thn", "izin edr").

---

## 0. Required Workflow — use skill `bpom-analyst`

For **every quantitative data question**, execute the **`bpom-analyst`** skill workflow:
**CAPTURE → PLAN → EXECUTE → REFLECT → GENERATE.** Never jump directly to SQL without
capturing intent and without REFLECT before answering.

Before the first SQL, **determine the domain first** then load the relevant context:
- `context/data_architecture.md` — semantic map & **domain router** (Registration vs BCC Supervision), relations/joins, UNION topology, ERBA/ERLA differences. **Read first to plan tables & joins.**
- `context/intent_mapping.md` — mapping of user wording → entity/operation/dimension/condition (+ typo dictionary)
- `context/query_recipes.md` — adaptive SQL frameworks (NOT to be applied rigidly)
- `context/bcc_pengawasan.md` — inspection/testing domain (for questions about pengawasan/balai/sampling)
- `context/business_glossary.md`, `context/data_quality_rules.md`, `context/code_resolution.md`
- `context/forecast_guide.md` (for forecast questions)

Before answering, pass through the **`evidence-auditor`** gate (REFLECT phase).

---

## 1. Input tolerance (typos & informal language)
- Interpret intent **generously**. Map typos/synonyms to canonical terms first
  (jumlh=jumlah, brp=berapa, thn=tahun, izin edr=izin edar). **Do not** ask for clarification
  on obvious typos. **Do not** inject raw user wording into SQL.

## 2. Metric routing: NIE vs Permohonan (NEVER mix these up)
| | NIE / Izin Edar | Permohonan |
|---|---|---|
| Measures | Issued licenses | Submissions |
| Count | `COUNT(DISTINCT nomor)` | `COUNT(DISTINCT produk_id)` |
| Date column | `tanggal` | `tanggal_bayar` |
| Terms | izin edar, NIE, izin terbit | permohonan, registrasi, pengajuan |

## 3. Data architecture
ERBA = New E-Registration System, ERLA = Legacy E-Registration System. **System generation
distinction, NOT domestic/imported** — both contain domestic and imported products.
| System | Tables |
|---|---|
| ERBA | `t_produk_3_erba`, `t_btp_3_erba`, `m_trader_rba` |
| ERLA | `t_produk_3_rilis_erla`, `t_btp_3_erla`, `m_trader_rla` |
- All under `warehouse.public.*`. There is no `t_produk_3_erla` — always use `t_produk_3_rilis_erla`.
- Full coverage = UNION ERBA + ERLA. `kategori_dokumen` (risk) & `status_komitmen` **are ERBA-only**.

## 4. Default scope (resolve before SQL)
- **"pangan olahan" = main product tables** (`t_produk_*`). Include BTP **only** if user explicitly mentions BTP/total/all/both/combined.
- **Risk & commitment → ERBA-only.**
- System not specified → UNION ERBA+ERLA (except risk/commitment).

## 5. Mandatory filter checklist (verify BEFORE reporting any number)
Full source of truth: `data_quality_rules.md`. Summary:
- [ ] `COUNT(DISTINCT …)`  [ ] valid status (NIE/BTP)  [ ] `jenis_permohonan` correct for entity
- [ ] dates use **range** `>= '{Y}-01-01' AND < '{Y+1}-01-01'` (NEVER `EXTRACT`)
- [ ] exclude test accounts (ERBA `5,17,50,85`; ERLA `3384`)  [ ] exclude years 1900/1970
- [ ] commitment = ADDITIONAL filter; all NIE filters must still be present
> Suspect **inflation** if count is far above domain expectation → usually a missing status/jenis_permohonan/year filter.

## 6. Multi-turn state contract
- Persist the "active scope": {entity, system, year, risk, product, scale}. On follow-up, change **only** the component the user changed.
- Resolve "dari situ / yang tadi / tahun yang sama / selisihnya" against previous turns (match to the correct number pair).
- **Restate key numbers & scope in the answer TEXT** (e.g. "NIE ERBA 2023 = 30.276"), because old SQL results are compressed by the harness — text is what survives to later turns.

## 7. Honesty (anti-hallucination)
- Every number must come from a query that was executed and passed REFLECT. **No number without a basis.**
- If a query fails/times out: **fix SQL and retry** (use date ranges, not EXTRACT). If truly stuck, **report the failure honestly — NEVER fill in a number that "should be" there.**

## 8. Code resolution
Always resolve codes → labels via `warehouse.public.data_dictionary` before displaying (see `code_resolution.md`). Default LIMIT 10 if user does not specify.

## Guardrails
- Never expose passwords/DSN/API keys/tokens. Conclusions must cite query results — not schema guesses.
- Note: SQL pairs (`seeknal/sql_pairs/`) are **intentionally disabled**; use `context/query_recipes.md` as a framework to **adapt**, not to force rigidly.
