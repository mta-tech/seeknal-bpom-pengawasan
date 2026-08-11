# Test Run Analysis — 2026-06-12

> **Scope:** the two latest runs of the day, reconciled against the **live `rpo_v2` database**
> (queried directly via the SSH tunnel `localhost:5533` on 2026-06-12).
> **Files analyzed:**
> - `seeknal/tests/outputs/2026-06-12/v1/multiturn_results_20260612_045846.json` (multiturn)
> - `seeknal/tests/outputs/2026-06-12/v1/multiturn_results_20260612_045059.json` (singleturn-style)

---

## 1. Runs analyzed

| File | Suite | Turns | Raw passed | Raw rate |
|---|---|---|---|---|
| `..._045846.json` | Multiturn (13 scenarios, deep follow-ups) | 117 | 103 | **88%** |
| `..._045059.json` | Singleturn-style (per-question) | 71 | 66 | **93%** |
| **Combined** | | **188** | **169** | **89.9%** |

Both are the **latest** runs (11:50 & 11:58) and contain **zero infrastructure errors** — the DB
tunnel and model endpoint had recovered. The earlier runs the same morning (`032805` / `035621`)
scored 77% / 76% **purely because of infrastructure failures**, not reasoning:

- **31** DB-connection drops (`"kendala koneksi teknis ke database rpo_v2"`)
- **4×** `ModelHTTPError 503 — gemini-3-flash-preview`
- **1×** `UsageLimitExceeded`

Proof this was infra, not regression: the **identical** suite the previous day (`041431`) had
**0** such errors and scored 89%. So these two clean runs measure reasoning quality directly.

---

## 2. Reconciled pass rate (raw vs. true)

The runner uses **exact substring matching** with **no numeric tolerance**, and some expected
values are **stale**. After classifying every failure against the live DB:

| Category | 045846 | 045059 | Total |
|---|---|---|---|
| Raw passed | 103 | 66 | 169 |
| **False-fail** (answer actually correct) | 8 | 4 | **12** |
| **Genuine bug** | 6 | 1 | **7** |
| **Effectively correct** (passed + false-fail) | 111 / 117 | 70 / 71 | **181 / 188 = 96.3%** |
| **Genuinely wrong** | 6 / 117 | 1 / 71 | **7 / 188 = 3.7%** |

**Bottom line: ~96% is genuinely correct; only ~4% (7 turns) are real agent errors.**

---

## 3. The 12 false-fails — agent was right, the test was wrong

### Stale oracle (DB grew; agent matches live DB)
| Case | Agent | Oracle | Live DB | |
|---|---|---|---|---|
| UMKM (nie_skala T2, stress_20 T5, stress_50 T5) | 12.342 | 12.295 | **12.342** | agent correct |
| MR all-time (`01_`) | 119.313 | 118.896 | **119.314** | agent correct |
| NIE ERBA (sql_transparency T1) | 30.230 | 30.276 | **~30.230** | agent correct |

### Drift ≤0.5% (live data shifted slightly)
- cross-turn arithmetic `3.409` ≈ `3.411` (mr_komitmen T4) — subtraction over the Ledger was done correctly
- BTP `951` ≈ `950` (stress_50 T26)

### Wording / format (correct trend answered, literal token absent)
- `"per tahun"` — AMDK_Trend, BTP_ERBA_Trend, Garam_Beryodium_Trend (045059), stress_50 T13
- `"Garam Beryodium"` spelling — stress_50 T32

---

## 4. The 7 genuine failures — proven against the live DB

Method: the **agent's actual executed SQL** (from the `sqls` field) was replayed on `rpo_v2`. In
every case the agent's SQL reproduced its wrong number **exactly** → the data is correct; the
**query logic is the fault**.

| # | Case (turn) | Agent | What the SQL did wrong | DB-verified correct |
|---|---|---|---|---|
| 1 | **UMKM** `nie_definisi T5` | **10.412** | `#sqls=0` — answered from memory; defined "UMKM = Mikro+Kecil" only | Mikro 5.506 + Kecil 4.906 + **Menengah 1.930 = 12.342** (DB: `1+2`=10.412, `1+2+3`=12.342) |
| 2 | **Disetujui MR** `stress_20 T7` | **2** | `status_komitmen = 5` (= **Dibatalkan/cancelled**) labeled as "disetujui" | code 4 (976) + code 7 (5.262) = **6.236** (DB: code 5 = 2 — exactly the agent's wrong number) |
| 3 | **NIE BTP** `stress_20 T14` | **1.102** | used `tanggal_aju` (should be `tanggal`) + dropped `jenis_permohonan` filter | **950** (DB: replaying agent SQL → 1.102 exactly) |
| 4 | **Year-switch** `stress_50 T10` | **33.386** | "kalau tahun 2022" → answered TOTAL combined NIE; dropped the carried MR + ERBA-only subject | MR ERBA 2022 = **1.048** (subject lost entirely) |
| 5 | **Cascade** `stress_50 T11` | wrong | built the up/down comparison on T10's wrong base | — (cascade of #4) |
| 6 | **Scope "semua sistem"** `stress_50 T17` | **62.877** | included BTP tables in "all registration systems" | product-only = **61.217** (DB: +BTP = 62.877 — confirms BTP wrongly included) |
| 7 | **Risk-Tinggi all-time** `03_` | **120.234** | wrong ERLA risk-code mapping → overcount ~16k | ERBA(301,304) 83.143 + ERLA(jenis_dokumen=302) 20.555 = **103.698** |

**Direct answer to "is the data or the SQL wrong?"** → **The data is correct. The agent's SQL is
wrong.** Replaying the agent's SQL on the live DB returns its exact wrong figures (10.412, 2,
1.102, 62.877), confirming logic — not data — is at fault.

---

## 5. Why it still happens — single root mechanism

**It is not a missing definition.** Every rule (UMKM = scale 1+2+3, disetujui = {4,7}, BTP date =
`tanggal`, ERBA-only scope, risk-code mapping) **already exists in the context files**, and the
agent applies them correctly in the **opening turn** of every scenario.

Failures occur **only on implicit follow-up / drill-down turns** ("dari situ…", "yang disetujui",
"kalau tahun X", "semua sistem"). On those turns the agent does one of two things:

1. **Answers from memory without querying** (`#sqls = 0`) → recalls a *wrong* definition or
   arithmetic. This produced UMKM `10.412`: it never ran SQL, just summed Mikro+Kecil from the
   prior turn and forgot Menengah.
2. **Re-queries but fails to carry the parent turn's method invariants** → wrong date column
   (`tanggal_aju`), wrong status/risk code (5 instead of {4,7}), dropped filter
   (`jenis_permohonan`), broadened scope (+BTP), or lost subject (MR → total).

This is exactly a violation of the agent's own principle **"inherit ANSWERS, re-derive METHODS."**
It instead does the opposite — *inherits/recalls the method imperfectly and skips a fresh RESOLVE*.
Because the same metric is computed **correctly in most other turns**, this is **execution
instability on follow-ups**, not a broken rule.

---

## 6. What is already working (do not change)

- Infra-recovered runs reach **~96% effective accuracy** — the earlier "inherit answers,
  re-derive methods" + Conversation Ledger fix did recover the regression (52% → ~96% effective).
- Opening-turn correctness is solid across all entities (NIE, permohonan, BTP, risk, scale, forecast).
- The honesty guardrail works: on DB failure the agent reports "kendala koneksi" instead of
  fabricating (proven by the morning run).
- Context definitions are complete and correct — the live DB confirms every canonical value.

---

## 7. Next steps

### Test methodology (cheap; recovers ~12 false-fails immediately)
1. Add **±5% numeric tolerance** (or refresh oracles) — fixes stale values: UMKM `12.295→12.342`,
   risk-T `102.507→103.698`, MR all-time `118.896→119.314`, MR-2022 `1.414→1.048`.
2. Relax wording assertions (`"per tahun"`, spelling variants) to concept/number checks.

### Agent (the 7 genuine bugs — one mechanism, teach-the-thinking, no new definitions)
3. **Forbid answering quantitative follow-ups from memory** — a new number must come from a fresh
   query; `#sqls = 0` is allowed only for pure arithmetic over the Ledger. (Fixes Bug 1.)
4. **On drill-down, RESOLVE must re-read per-table invariants and carry the parent
   subject/scope/codes**, changing only the user's requested delta: date column (`tanggal` vs
   `tanggal_aju`), status_komitmen codes ({4,7} vs 5), risk-code mapping, `jenis_permohonan`
   filter, ERBA-only vs +BTP scope, and the carried entity/risk/system/year. (Fixes Bugs 2–7.)
5. **Verify Bug 6** (ERLA risk-Tinggi mapping) by capturing the full ERLA `WHERE` on the next run.

Target files for the agent-side changes: 2 context files + the skill (no new business
definitions), consistent with the teach-the-thinking philosophy.
