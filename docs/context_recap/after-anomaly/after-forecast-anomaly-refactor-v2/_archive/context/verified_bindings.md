# Verified Bindings — proven fishing spots

> **What this is:** concept → column+code bindings that have been VERIFIED against real data.
> These are *locations*, not answers — **this file never contains an answer number**, and every
> number in an answer must still come from a query you run yourself this turn.
>
> **Why it exists:** the same concept can live in a DIFFERENT column per system, and several
> columns can plausibly match one concept (see `data_architecture.md` §5a). This file records
> which pond was PROVEN right, so the choice is deterministic across sessions.
>
> **Admission rule:** entries are born only from the discovery procedure
> (`code_translation_protocol.md` §4) with a confirmed result, or manual verification.
> No proof → not admitted.
> **Lifecycle:** pure-code rows graduate to `data_dictionary` once its category is filled;
> **cross-column** bindings (concept → which column, per system) live here permanently.
> **Write-back:** a probe result confirmed by the user → add its entry here.
>
> **Counting entity:** every binding below was verified with `COUNT(DISTINCT nomor)` for
> registered-product (NIE) questions. Pair the binding with the entity rule in
> `filter_code_reference.md` §1 — the right column with the wrong counting entity still
> produces a wrong answer (often several-fold off).

```yaml
- concept: pangan bayi
  system: ERLA
  binding: "klasifikasi_id = '311'"
  do_not: "do not resolve via jenis_pangan for this concept in ERLA"

- concept: organik
  system: ERBA & ERLA
  binding: "pemrosesan = '301'"
  do_not: "klasifikasi_id '309' (Organik) exists but is NOT the verified pond for this concept"

- concept: pangan berklaim
  system: ERBA & ERLA
  binding: "klasifikasi_id = '305'"

- concept: pangan diet
  system: ERBA & ERLA
  binding: "klasifikasi_id = '310'"

- concept: peruntukan khusus
  system: ERBA & ERLA
  binding: "peruntukan = '0201'"

- concept: Single MD Induk
  system: ERBA & ERLA
  binding: "status_produk = '306'"
  note: "Single MD Anak = '307'"

- concept: makloon / berdasarkan kontrak
  system: ERBA & ERLA
  binding: "status_produk = '304'"

- concept: makanan (classification)
  system: ERBA & ERLA
  binding: "klasifikasi_id = '301'"

- concept: minuman (classification)
  system: ERBA & ERLA
  binding: "klasifikasi_id = '302'"
```
