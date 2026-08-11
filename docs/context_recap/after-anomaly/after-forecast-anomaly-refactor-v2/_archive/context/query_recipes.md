# Query Recipes — SQL Shapes

**These are shapes, not answers.** Every filter, cast, count method, and scope default comes from
**`context/predikat.md`** — read it before writing SQL. Nothing here restates a rule; the
placeholders below mean *"apply what `predikat.md` says"*.

Tables are `warehouse.public.<table>` (`warehouse` = the attached PostgreSQL source).

There is one shape per **operation class**. Adapt the shape to the question; do not look for a
recipe that matches the question verbatim — one will not exist.

---

## S1 — Scalar count

> "Berapa NIE pangan olahan tahun 2023?"

```sql
SELECT COUNT(DISTINCT nomor) AS jumlah_nie
FROM warehouse.public.t_produk_3_erba
WHERE <mandatory filters: predikat.md §4>
  AND <valid NIE status: predikat.md §5>
  AND <date range on `tanggal`: predikat.md §2-§3>
```

Permohonan → `COUNT(DISTINCT produk_id)` on `tanggal_bayar`, **no status filter** (`predikat.md` §1, §5).

---

## S2 — Cross-system (UNION ERBA + ERLA)

> "Berapa NIE AMDK sepanjang waktu?"

Filter **inside** each side (each system has its own status list, casts, and exclusions), then
aggregate **once** over the union.

```sql
SELECT COUNT(DISTINCT nomor) AS jumlah_nie
FROM (
  SELECT nomor
  FROM warehouse.public.t_produk_3_erba
  WHERE <ERBA filters + ERBA segment code>

  UNION ALL

  SELECT nomor
  FROM warehouse.public.t_produk_3_rilis_erla
  WHERE <ERLA filters + ERLA segment code>
) u
```

Canonical UNION template with casts → `predikat.md` §9.
`nomor` does not overlap between systems, so `UNION ALL` + `COUNT DISTINCT` is exact.
Risk and commitment need a **separate `WHERE` per side** — codes are not equivalent across systems.

---

## S3 — Time series (trend)

> "Tren NIE per tahun."

**One** query with `GROUP BY` — not one query per year.

```sql
SELECT date_trunc('year', tanggal) AS tahun,
       COUNT(DISTINCT nomor)       AS jumlah_nie
FROM warehouse.public.t_produk_3_erba
WHERE <filters>
  AND tanggal >= '2000-01-01' AND tanggal < '2030-01-01'
GROUP BY 1 ORDER BY 1
```

> ⚠️ **The grand total is NOT the sum of the yearly rows.** A `nomor` recurring across years would
> be counted twice. Compute the total as a **separate global `COUNT(DISTINCT nomor)`** over the
> same filtered set (standalone aggregate, subquery, or `GROUP BY ROLLUP`) — `predikat.md` §1.

---

## S4 — Breakdown / ranking by a dimension

> "NIE per tingkat risiko." · "10 daerah dengan NIE terbanyak."

`GROUP BY` the dimension, `LEFT JOIN` the dictionary for the label, never show a raw code.

```sql
SELECT COALESCE(dd.deskripsi, '<fallback>') AS label,
       COUNT(DISTINCT p.nomor)              AS jumlah_nie
FROM warehouse.public.t_produk_3_erba p
LEFT JOIN warehouse.public.data_dictionary dd
  ON dd.kategori = '<kategori>'
  AND dd.sumber IN ('<SYSTEM>', 'ERBA dan ERLA', 'ERLA dan ERBA')
  AND dd.kode = <conversion of p.<column>>          -- code_resolution.md
WHERE <filters>
GROUP BY 1 ORDER BY 2 DESC LIMIT 10
```

- The `sumber` filter is **mandatory** — omitting it fans out multi-source categories.
- Code conversions (region `ROUND(/100,2)`, `kategori_pangan` → AKRONIM, **ERLA `status`
  zero-padding**) → `code_resolution.md`.
- Trader joins are **always `LEFT JOIN`**, and companies are counted from the product table's
  `trader_id` (`predikat.md` §11).
- If the result is dominated by NULL / "Tanpa Kategori" → stop and switch column
  (`data_quality_rules.md` §Coverage).

---

## S5 — Multi-query synthesis

> "NIE berdasarkan risiko, skala, dan trennya."

These are **independent** dimensions — one query each, then synthesize in the answer.
Do **not** force them into a single `GROUP BY`.

Separate queries are also required when one dimension is **ERBA-only** (risiko, komitmen) while
another spans both systems.

Dependent dimensions ("per risiko **dan** per tahun") are the opposite case → **one** query with a
multi-column `GROUP BY`.

---

## Adaptation notes

1. **Never copy a shape without re-deriving its filters from `predikat.md` this turn.** The shape
   tells you the SQL structure; `predikat.md` tells you what is correct.
2. **Prefer one round-trip.** One `GROUP BY` query beats N per-year queries — lighter on the
   connection and immune to the double-counting trap in S3.
3. **Use ranges, never `EXTRACT`** for date scoping (`predikat.md` §2) — `EXTRACT` forces a full
   table transfer and times out.
4. **A BTP table is structurally a product table.** Same columns, same count rules; only the table
   name changes.
