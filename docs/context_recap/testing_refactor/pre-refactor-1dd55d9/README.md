# Pre-Refactor Baseline — 1dd55d9 (18 Jun 2026)

Snapshot file reasoning dari commit `1dd55d97f233110353458bbc275dd1b46f1cf88f`
(merge PR #7 "[feat] Introduce bpom-forecaster skill", 18 Jun 2026).

## Tujuan snapshot
Baseline **sebelum refactor** — ditangkap SEBELUM:
- `4733c77` "[ref] Simplify agent context (net -1600 lines)"
- `f8d34b0` "[ref] Operationalize runtime resolution engines (Fase 1)"

Mewakili **era deklaratif/cheat-sheet**: context masih menyimpan kode domain
inline (AMDK, Garam, granularity risiko, test accounts) dan bpom-analyst masih
berupa orchestrator monolith 465 baris.

## Sumber (di 1dd55d9) → struktur di sini
- `context/` (9 file) → `context/`
- `seeknal/skills/` (5 skill) → `skills/` (prefix `seeknal/` dikupas)
- `SEEKNAL_ASK.md` (327 baris) → `SEEKNAL_ASK.md`

## Inventaris
- context: business_glossary, code_resolution, code_translation_protocol,
  data_architecture, data_quality_rules, forecast_guide, forecast_recipes,
  intent_mapping, query_recipes
- skills: bpom-analyst, bpom-forecaster, business-question-answering,
  database-analyst, evidence-auditor

## Perbedaan kunci vs HEAD (Fase 1)
- `context/source_discovery_protocol.md` BELUM ADA di sini (lahir di Fase 1).
- `code_translation_protocol.md` = versi "Two-Way Source-Aware" deklaratif
  (kode AMDK/Garam/risiko di-hardcode), BUKAN Four-Pass Resolver prosedural.
- `bpom-analyst/SKILL.md` = 465 baris monolith vs ~130 baris sekarang.
- `SEEKNAL_ASK.md` = 327 baris vs 458+ baris setelah ekspansi Fase 1.

## Hubungan dengan snapshot lain
- `../v2-230626/` — baseline 23 Jun (lebih baru dari sini, masih pre-refactor),
  hanya mencakup `context/` + `skills/` (tanpa `SEEKNAL_ASK.md`).
- Folder ini = baseline **lebih awal + lebih lengkap** (mencakup `SEEKNAL_ASK.md`).

## Cara regenerasi
```bash
git archive 1dd55d97f233110353458bbc275dd1b46f1cf88f -- context SEEKNAL_ASK.md | tar -xC .
git archive 1dd55d97f233110353458bbc275dd1b46f1cf88f -- seeknal/skills | tar -x --strip-components=1 -C .
```
