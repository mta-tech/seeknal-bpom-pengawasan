# Intent Mapping — Question → Query Structure

**How to read a question.** Not what to filter — filters, counts, and scope defaults live in
`context/predikat.md`. Not what a code means — that is `data_dictionary`.

---

## Step 0 — Normalize first (mandatory)

Fix typos and informal wording **before** mapping anything. Do not ask for clarification on an
obvious typo, and **never inject raw user words into SQL**.

---

## Question Decomposition — read the structure before the words

| Component | Identifies | Determines |
|---|---|---|
| **Subject** | the entity being asked about | granularity of `GROUP BY` and of one output row |
| **Predicate** | what is wanted about the subject | metric column + aggregation |
| **Modifier** | conditions restricting scope | `WHERE` clause |
| **Scope dimensions** | extra axes the result must cover | extra `GROUP BY` columns |

### Examples

| Question | Subject | Shape |
|---|---|---|
| "Berapa NIE risiko tinggi?" | NIE | scalar |
| "Tren NIE per daerah dan tahun" | NIE over time | `GROUP BY tahun, daerah` (dependent) |
| "Produk apa yang paling banyak dibatalkan?" | produk → **kategori** | `GROUP BY` category, `ORDER BY COUNT DESC` |
| "Daerah mana UMKM terbanyak?" | daerah | `GROUP BY` region, `ORDER BY COUNT DESC` |
| "Distribusi NIE per risiko, skala, tren 10 tahun" | NIE | **3 separate queries** + synthesis (independent) |

### The subject noun controls granularity

This generalizes to questions not listed anywhere:

| Subject form | One output row is | `GROUP BY` |
|---|---|---|
| "berapa" / scalar | a single number | none |
| "tren" / "per tahun" | one year | `date_trunc('year', tanggal)` |
| "daerah mana" / "wilayah apa" | one region | region column (see §Daerah) |
| "produk apa" / "kategori apa" | one product **category** | resolvable category code (see §Kategori) |
| "perusahaan mana" | one company | `trader_id` / `nama_trader` |
| "skala apa" | one industry scale | `skala_industri_id` / `skala_industri` |
| "risiko apa" | one risk level | `kategori_dokumen` (ERBA) |

**"Produk apa yang paling X" is a RANKING, not a LIST.**
- **LIST / SEARCH** — "cari produk", "tampilkan produk" → individual rows, use `nama`.
- **RANKING** — "produk apa yang paling banyak X" → **category aggregation**.

These are different operations. In a ranking context, "produk apa" means *which category ranks
highest*.

### Dependent vs Independent dimensions

- **DEPENDENT** — the user wants the dimensions **crossed**.
  Signals: "tren **per** X", "X **dan** Y" in one phrase, "berdasarkan X per tahun".
  → **One** query, multi-column `GROUP BY`.
- **INDEPENDENT** — the user wants each dimension **separately**.
  Signals: "berdasarkan risiko, skala, **dan** tren" (listed as distinct aspects).
  → **N** queries, one per dimension, synthesized in the answer.

Separate queries are also required when one dimension is **ERBA-only** (risiko, komitmen) while
another spans both systems.

---

## OPERATION → SQL pattern

| Operation | Trigger words | Pattern |
|---|---|---|
| COUNT | jumlah, berapa, total | `COUNT(DISTINCT <metric>)` — see `predikat.md` §1 |
| TREND | tren, per tahun, perkembangan | `GROUP BY <time> ORDER BY <time>` |
| BREAKDOWN | per, berdasarkan, menurut | `GROUP BY <dimension>` |
| TOP | terbanyak, top, paling | `ORDER BY <metric> DESC LIMIT N` |
| COMPARE | dibanding, vs, lebih besar | `CASE WHEN`, or two queries then reconcile |
| LIST | daftar, cari, tunjukkan | `SELECT detail … LIMIT 10` |
| INVESTIGATE | kenapa, mengapa, penyebab, alasan kenaikan/penurunan | trend → find the inflection point → decompose → name the top contributor → **state it as a hypothesis**, not a proven cause |
| AGE / SLA | sudah berapa lama, lama tertahan, belum selesai, SLA, menunggak, > N hari | see §SLA below |
| FORECAST | prediksi, proyeksi, bulan/tahun depan, outlook, akan ada berapa | → route to `bpom-forecaster`. Horizon: "hingga X" = now → end of X (all intermediate periods); unstated → 3 months, say so. **ERBA only** — never forecast ERLA. |

If a question mixes **past trend + future projection**: analyst handles the historical base,
forecaster the projection, then present one unified timeline.

---

## Dimension notes — where the column choice is not obvious

### Daerah / wilayah — choose by semantics **and** coverage

| User phrase | Column | Meaning | Coverage |
|---|---|---|---|
| "daerah" / "kab/kota" / "provinsi" (unqualified) | JOIN `m_trader_rba.kotakab_id` / `provinsi_id` | **company** location | **high (≈100%)** — **default** |
| "daerah/lokasi **pabrik**", "tempat produksi" | `daerah_pabrik` (product table) | factory location | **low** — many unresolved |
| "daerah **produsen**" | `daerah_produsen` | producer / makloon location | sparse |

- **Unqualified "daerah" → company kab/kota** via the `m_trader` join. It is the most complete and
  what users normally mean.
- Use `daerah_pabrik` **only** when the user explicitly says pabrik/produksi — then **say it is
  factory location** (it differs from company location for a sizeable share) **and report the
  coverage gap**.
- Region codes need conversion and may be legacy codes → `code_resolution.md`. Keep the raw code when
  unresolved. **Never silently switch to a different dimension because it happens to have data.**

### Kategori pangan — as a breakdown / ranking dimension

For "kategori terbanyak" / "Top N kategori" / "per kategori", group by the **resolvable code**, not
the free-text name.

`nama_kategori` is **mostly empty** → grouping by it makes "Tanpa Kategori" dominate, which is
wrong. Use `kategori_pangan` resolved to a broad category via AKRONIM
(`'KP ' || LEFT(kategori_pangan, 2)`, near-full coverage — `code_resolution.md`). State that the
granularity is a broad category when finer detail is not reliable.

`nama_kategori ILIKE` remains correct for **searching** a named segment
(`business_glossary.md` §Product Segment Codes) — just never as a grouping key.

### Durasi / SLA / aging

- Entity = **PERMOHONAN**, not NIE. Aging measures the application lifecycle, not the issued licence.
- Age = `CURRENT_DATE - tanggal_bayar::date` (ERBA needs the cast; ERLA is native).
- **Only meaningful for in-process applications** — exclude anything with a final outcome. Discover
  the "still open" status codes from the dictionary; **do not hardcode them**.
- Never confuse age with `tanggal` (the NIE issue date).

### Risiko · komitmen · skala · segmen produk

These carry rules that decide the number, not just the column:

- **Risiko** — different column *and* different codes per system → `business_glossary.md`.
- **Komitmen** — two counting cases (A vs B) and a number-format trap → **`predikat.md` §7–§8**.
- **Skala / UMKM** — NULL means Importir; UMKM = 1+2+3 → **`predikat.md` §10**.
- **Segmen produk** (AMDK, garam, roti, …) — the only codes **not** in the dictionary →
  `business_glossary.md` §Product Segment Codes. If the discovery probe returns more than one
  plausible code family, **ask the user**; never pick silently.

---

## Implicit references (multi-turn)

- "tahun yang sama" → the year from the previous turn.
- "dari situ" / "yang tadi" / "itu" → the dataset or scope from the previous turn's result.
- "selisihnya" → compute from **the two most recent relevant numbers** — check which pair is meant
  (e.g. combined − ERBA, not ERBA − ERLA).
- "kalau [dimensi/tahun/produk] lain?" → change **only** that component; preserve entity, system,
  and scope.

Inherit **answers**, re-derive **methods** (`SEEKNAL_ASK.md` §1.3).
