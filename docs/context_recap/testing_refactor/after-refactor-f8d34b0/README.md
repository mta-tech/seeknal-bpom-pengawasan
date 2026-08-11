# After-Refactor Baseline — f8d34b0 (25 Jun 2026)

Snapshot file reasoning dari kondisi **sekarang** (working tree per 25 Jun 2026),
bertepatan dengan HEAD `f8d34b033bfe96af97e2b54ba44624588105a204`
("[ref] Operationalize runtime resolution engines (Fase 1)").

## Tujuan snapshot
Baseline **setelah refactor** — pasangan dari `../pre-refactor-1dd55d9/`.
Mewakili **era prosedural/Fase 1**: context sudah dibersihkan dari hardcode domain,
mekanisme resolusi dipusatkan ke protokol, skill di-trim jadi workflow+blocking contract.

Refactor yang sudah terjadi sejak pre-refactor baseline:
- `4733c77` "[ref] Simplify agent context (net -1600 lines)"
- `f8d34b0` "[ref] Operationalize runtime resolution engines (Fase 1)"

## Sumber (working tree) → struktur di sini
- `context/` (10 file) → `context/`
- `seeknal/skills/` (5 skill) → `skills/` (prefix `seeknal/` dikupas)
- `SEEKNAL_ASK.md` (279 baris) → `SEEKNAL_ASK.md`

## Inventaris
- context: business_glossary, code_resolution, code_translation_protocol,
  data_architecture, data_quality_rules, forecast_guide, forecast_recipes,
  intent_mapping, query_recipes, **source_discovery_protocol** (baru di Fase 1)
- skills: bpom-analyst (~130 baris, trim), bpom-forecaster,
  business-question-answering, database-analyst, evidence-auditor

## Perbedaan kunci vs pre-refactor (1dd55d9)
- `context/source_discovery_protocol.md` **BARU ADA** (lahir di Fase 1) — protokol
  Stage A→D discovery→clarify.
- `code_translation_protocol.md` = Four-Pass Resolver prosedural + Binding Matrix
  (BUKAN versi "Two-Way Source-Aware" deklaratif lagi). Anti-Hardcode Rule di §11.
- `bpom-analyst/SKILL.md` ~130 baris (workflow+blocking contract) vs 465 baris monolith.
- `SEEKNAL_ASK.md` 279 baris dengan Clarification Gate §2, Sufficiency Check,
  Conversation Ledger terstruktur.

## Catatan WIP (penting)
Snapshot ini menangkap **working tree apa adanya**. Satu file berbeda dari HEAD
`f8d34b0` karena modifikasi belum ter-commit:
- `skills/database-analyst/SKILL.md` — mengandung WIP (perubahan uncommitted).

Semua file lain identik dengan HEAD `f8d34b0`. Untuk baseline murni ter-commit,
kembalikan file ini ke versi HEAD sebelum membandingkan, atau gunakan
`git show f8d34b0:seeknal/skills/database-analyst/SKILL.md`.

## Hubungan dengan snapshot lain
- `../pre-refactor-1dd55d9/` — baseline 18 Jun (pendahulu, era deklaratif).
- `../v2-230626/` — baseline 23 Jun (tengah, antara pre dan post refactor).
- Folder ini = baseline **terbaru pasca-refactor**.

## Cara regenerasi (dari working tree)
```bash
cp -r context docs/context_recap/after-refactor-f8d34b0/
cp -r seeknal/skills docs/context_recap/after-refactor-f8d34b0/  # lalu rename skills
cp SEEKNAL_ASK.md docs/context_recap/after-refactor-f8d34b0/
```
