# Code Translation Protocol — Two-Way, Source-Aware Resolution

> **This file holds PROCEDURE, never answers.** It teaches the agent *how to look a code
> up* and *how to handle ambiguity* — it does NOT store what any code means. Code meanings
> live only in the live `warehouse.public.data_dictionary` table and are resolved at runtime.
> Any other context file that lists code→meaning is wrong by construction; resolve here instead.

The governing principle:

> **A code is born from the dictionary and dies as a definition through the dictionary.**
> Never decide what a code means — look it up, every time, per system, in both directions.

---

## 0. Why this exists

`data_dictionary` (≈1,141 rows) is the authoritative meaning of every coded column value. It has
a **`sumber`** column that distinguishes the two registration systems:

| `sumber` value | Applies to |
|---|---|
| `ERBA` | ERBA only |
| `ERLA` | ERLA only |
| `ERBA dan ERLA` / `ERLA dan ERBA` | both systems (shared meaning) |

The same numeric code can mean different things in ERBA vs ERLA (e.g. `STATUS` code `9999`
exists in **both**; `KEMASAN_ID` and `STATUS` carry separate ERBA and ERLA rows). **A lookup or
JOIN that ignores `sumber` produces a fan-out** (one product row joins to two dictionary rows →
`COUNT(DISTINCT)` distortion) **or an ambiguous label.** Always filter by `sumber`.

ERBA and ERLA also classify risk under **different category names** (not the same code reused):

| Concept | ERBA | ERLA |
|---|---|---|
| Risk level column | `kategori_dokumen` | `jenis_dokumen` |
| `data_dictionary` kategori | `KATEGORI_DOKUMEN` (sumber `ERBA`) | `JENIS_DOKUMEN` (sumber `ERLA dan ERBA`) |
| Levels | 4 (Tinggi / Menengah Tinggi / Menengah Rendah / Tinggi Notifikasi) | 3 (Low / High / **Medium** Risk) |

> ERLA has **no separate Menengah Tinggi** — its `JENIS_DOKUMEN` Medium-Risk code spans both MT and
> MR. Never assume ERLA `303` equals ERBA `302`; that equivalence is false and must be tested, not
> assumed (see §3).

---

## 1. Column → kategori pointer (where to look — NOT what it means)

| Column | `kategori` | Notes |
|---|---|---|
| `kategori_dokumen` (ERBA risk) | `KATEGORI_DOKUMEN` | sumber `ERBA`; present "Risiko " prefix at output |
| `jenis_dokumen` (ERLA risk) | `JENIS_DOKUMEN` | sumber `ERLA dan ERBA`; 3 levels only |
| `status` | `STATUS` | **multi-source** — MUST filter `sumber` |
| `status_komitmen` | `STATUS_KOMITMEN` | ERBA only; key `ROUND(status_komitmen::numeric)::int::text` |
| `status_produk` | `STATUS_PRODUK` | ERBA |
| `status_usaha` | `STATUS_USAHA` | ERBA |
| `jenis_permohonan` | `JENIS_PERMOHONAN` | `ERBA dan ERLA` |
| `jenis_dokumen` (document type, not risk, ERBA) | `JENIS_DOKUMEN` | only ERLA's carries risk; in ERBA it is document type |
| `jenis_btp`, `jenis_produk_btp` | `JENIS_BTP`, `JENIS_PRODUK_BTP` | |
| `bentuk_sediaan` | `BENTUK_SEDIAAN` | |
| `kemasan_id`, `sub_kemasan_id` | `KEMASAN_ID`, `SUB_KEMASAN_ID` | `KEMASAN_ID` **multi-source** |
| `klasifikasi_id` | `KLASIFIKASI_ID` | (deprecated for filtering — see glossary) |
| `kode_kbli` | `KODE_KBLI` | |
| `peruntukan` | `PERUNTUKAN` | |
| `skala_industri_id` / `skala_industri` | `SKALA_INDUSTRI dan SKALA_INDUSTRI_ID` | NULL/empty → "Importir" |
| `negara_pabrik`, `negara_produsen` | `NEGARA_PABRIK dan NEGARA_PRODUSEN` | |
| `daerah_*`, `provinsi_id`, `kotakab_id` | `DAERAH_TRADER, DAERAH_PABRIK, DAERAH_PRODUSEN, PROVINSI_ID, KOTAKAB_ID` | needs `ROUND(/100,2)` conversion (see `code_resolution.md`) |
| `kategori_pangan` (broad category) | `AKRONIM` | key `'KP ' || LEFT(kategori_pangan,2)` |
| `jenis_penolakan_komitmen` | `JENIS_PENOLAKAN_KOMITMEN` | ERBA; "why cancelled" reason |

To discover categories not listed: `SELECT DISTINCT kategori, sumber FROM warehouse.public.data_dictionary ORDER BY kategori`.

---

## 2. The canonical pattern — one query, two directions

### 2.1 Inbound — user word → code (during RESOLVE, before any SQL)

```sql
SELECT sumber, kode, deskripsi
FROM warehouse.public.data_dictionary
WHERE kategori = '<KATEGORI>'
  AND sumber IN ('<SYSTEM>', 'ERBA dan ERLA', 'ERLA dan ERBA')   -- <SYSTEM> = ERBA | ERLA
  AND deskripsi ILIKE '%<user phrase>%';
```

Resolve **per system separately** when building a UNION (ERBA side with `sumber` ERBA…, ERLA side
with `sumber` ERLA…). Bind the returned `kode` into the WHERE clause. Record the binding (see §5).

### 2.2 Outbound — code → definition (during GENERATE)

```sql
LEFT JOIN warehouse.public.data_dictionary dd
  ON dd.kategori = '<KATEGORI>'
  AND dd.sumber IN ('<SYSTEM>', 'ERBA dan ERLA', 'ERLA dan ERBA')   -- prevents fan-out
  AND dd.kode = <coded_column>::text
-- status_komitmen: dd.kode = ROUND(status_komitmen::numeric)::int::text
-- present COALESCE(dd.deskripsi, <coded_column>) — NEVER show a raw code in the answer
```

---

## 3. Ambiguity loop — re-map until grounded

After running §2.1, branch on the result:

- **Exactly 1 strong match** → bind `term → kode` → proceed.
- **0 rows** → identify why before broadening:

  **Path A — likely typo or informal phrasing** (the word phonetically resembles a dict entry):
  → Broaden with multi-pattern ILIKE: `deskripsi ILIKE '%men%' AND deskripsi ILIKE '%tinggi%'`.
  `pg_trgm` is NOT installed — the agent does the fuzzy match, not the DB.

  **Path B — semantic family concept** (the word is a valid business term but describes a GROUP
  of states, not a single code — e.g. "selesai", "sudah diputuskan", "berhasil", "tidak jalan",
  "sudah final", "sudah ada hasilnya"):
  → Do NOT broaden with ILIKE — this is not a typo.
  → Run: `SELECT kode, deskripsi FROM data_dictionary WHERE kategori = '<KATEGORI>' ORDER BY kode`
    to enumerate every code in the column's category.
  → Identify which codes semantically qualify (those whose deskripsi could fall under the
    user's grouping concept — e.g. for "selesai" in STATUS_KOMITMEN: kode 4, 5, 7 all qualify
    as "terminal/final" states).
  → If multiple codes qualify → treat identically to the **>1 rows** case below.
  → If only 1 code qualifies → bind that code → proceed as "Exactly 1 strong match".

  **Telling Path A from Path B:** if multi-pattern ILIKE still yields 0 rows AND the user's word
  is a natural-language concept (not a garbled version of a known dict label) → Path B.
- **>1 rows, or the two systems diverge** → this is real ambiguity. Do **not** guess:
  1. enumerate candidate bindings;
  2. **test each candidate against data** with a quick `COUNT(DISTINCT …)` when the ambiguity is
     about which code/label pair best matches the same concept;
  3. judge by magnitude/plausibility and discard candidates whose data behavior is clearly
     incompatible with the locked intent;
  4. if the ambiguity is actually **ontology-level** (for example two systems encode different
     granularity, or one system cannot isolate the same level as the other), do **not** force a
     numeric equivalence from a COUNT test. Escalate back to business semantics /
     `business_glossary.md` and keep the limitation visible;
  5. if the gap between candidates is material (>20% difference in likely result), use the
     **Ambiguity Gate (SEEKNAL_ASK.md §0.7)** — emit a grounded clarification question with
     options derived from the dictionary results; never silently pick; never fabricate.
     If the context prevents clarification this turn, pick the data-supported binding and
     state the basis + limitation explicitly in the answer.

### 3.1 Dictionary lookup as clarification grounding

When an inbound lookup returns >1 candidate and the gap between interpretations is material
(>20% difference in estimated count), do not pick unilaterally. Instead:

1. Format the candidates as grounded options using live dictionary data:
   ```
   Option A: [term] → kode=[X] (sumber=[S], deskripsi=[D])
   Option B: [term] → kode=[Y] (sumber=[S], deskripsi=[D])
   ```
2. Emit a natural-language clarification question using these options as the body.
3. Set `Pending: CLARIFICATION | class=EXACT_VS_FAMILY | term=<term> | options=[A, B]` in the
   Conversation Ledger.
4. Stop. Do not proceed to PLAN until the user responds.

---

## 4. Source hierarchy — translation is not dictionary-only

Resolve meaning from the most authoritative source that applies:

1. **`data_dictionary`** (sumber-aware) — for coded column values (§2).
2. **Probe the related table** — for meanings absent from the dictionary:
   - product segments (AMDK, Garam, susu, …) → discover via `nama_kategori` / confirm via
     `jenis_pangan` in `t_produk_3_erba` / `t_produk_3_rilis_erla` (codes differ per system),
     and choose the code by **coverage** (parent category over a single sub-code);
   - company identity → `m_trader_rba` / `m_trader_rla`.
   ```sql
   SELECT DISTINCT jenis_pangan, nama_kategori, COUNT(*) AS cnt
   FROM warehouse.public.<table>
   WHERE nama_kategori ILIKE '%<keyword>%'
   GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10;
   ```
3. **Business semantics** (`business_glossary.md`) — for concepts that are not codes
   (NIE = `COUNT(DISTINCT nomor)`, "pangan olahan" scope, final-vs-transient commitment concept,
   or when different systems do not expose the same ontology).

Translation is only for coded values. If a concept is already a direct field or a master-data
attribute, move back to schema/architecture resolution instead of forcing dictionary logic onto it.

A segment code is never hardcoded as truth — it is discovered and coverage-tested.

---

## 5. Binding record (feeds the SKILL.md RESOLVE gate)

Before writing SQL, every coded term must have a row:

```
term            | kategori          | sumber | kode(s)        | source query
"menengah tinggi"| KATEGORI_DOKUMEN | ERBA   | 302            | dict lookup §2.1
"dibatalkan"     | STATUS_KOMITMEN  | ERBA   | 5              | dict lookup §2.1
```

No SQL may be written until every coded term is bound from the dictionary (not from memory).
On a follow-up turn the binding is **re-derived** (re-queried) — it is a method, never inherited.
The lookup *result* may be cached within a session (reference data is immutable mid-conversation);
the *business decision* (which filter to apply) is still re-derived each turn.
