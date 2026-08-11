# After Forecast + Anomaly Refactor — e0ffafd (13 Jul 2026)

Snapshot file reasoning dari kondisi **working tree apa adanya** per 13 Jul 2026,
bertepatan dengan HEAD `e0ffafd` ("docs: sync skills/context with actual CSV
auto-upload + forecast behavior") pada branch `feat/forecast-context`.

## Tujuan snapshot

Baseline **setelah eksperimen forecast ETS seasonal engine + anomaly detection
(FC2c/FC2a/FC2d)** ditambahkan di atas baseline after-refactor Fase 1
(`f8d34b0`). Mewakili era:

- Fase 1 procedural tetap utuh (Four-Pass Resolver, blocking contract, dst).
- Skill baru lahir: `detect-anomaly` (thin-trigger ke engine, sama polanya
  dengan `bpom-forecaster`).
- `bpom-forecaster` di-trim jadi thin-trigger + lock AutoETS (FC2c) — komputasi
  forecast pindah ke engine (iba-forecast), skill cuma menentukan KAPAN dan
  menyusun SQL.
- Context forecast di-refresh: `forecast_guide.md` (period inference +
  stock vs flow), `forecast_recipes.md` (resep FC2a/FC2c).
- `bpom-analyst/SKILL.md` menyerap workflow CSV export satu-kali (FC2d) sebagai
  bagian dari answering workflow, menggantikan hook `csv_upload_reminder` yang
  di-retire (auto-upload setiap execute_sql dianggap terlalu agresif).

Komit-komit kunci sejak baseline Fase 1:
- `8f79a9e` "[ref, forecast-context] Refactor bpom-forecaster to thin-trigger
  + lock AutoETS (FC2c)"
- `287f5f5` "[ref, forecast-context] r4 skill: period inference + stock vs flow
  + block execute_python"
- `e0ffafd` "docs: sync skills/context with actual CSV auto-upload + forecast
  behavior"

## Sumber (working tree) → struktur di sini

| Source (`seeknal-bpom-neo/`) | Dest (folder ini) | Catatan |
|------------------------------|-------------------|---------|
| `SEEKNAL_ASK.md` (8675 B, v8 orchestrator) | `SEEKNAL_ASK.md` | copy |
| `seeknal_agent.yml` (2342 B) | `seeknal_agent.yml` | copy, dengan `forecast/anomaly/upload_to_s3` enabled |
| `context/` (9 file) | `context/` | copy |
| `seeknal/skills/` (6 skill) | `skills/` (prefix `seeknal/` dikupas) | copy |
| (root) `.env` | `.env` → `../../../../.env` | symlink |
| (root) `.seeknal` | `.seeknal` → `../../../../.seeknal` | symlink |
| — | `seeknal/skills` → `../skills` | alias konvensional seeknal |

## Inventaris

### Context (9 file)
business_glossary, code_resolution, code_translation_protocol,
data_architecture, data_quality_rules, forecast_guide, forecast_recipes,
intent_mapping, query_recipes.

> Catatan: `source_discovery_protocol.md` **belum ada** di snapshot ini (hanya
> ada di `iba-deploy-runbook/configs/seeknal-project/context/`). Bisa disalin
> terpisah kalau diperlukan untuk paritas dengan deployment.

### Skills (6)
- `bpom-analyst` — orchestrator + workflow CSV export satu-kali (FC2d).
- `bpom-forecaster` — thin-trigger forecast (FC2c), lock AutoETS.
- `business-question-answering` — routing kategori pertanyaan.
- `database-analyst` — executor SQL + discovery stage.
- `detect-anomaly` — **BARU** di snapshot ini. Thin-trigger ke engine anomaly
  (iba-forecast `/anomaly`), pola identik dengan bpom-forecaster.
- `evidence-auditor` — audit hasil + citation.

### seeknal_agent.yml
- `prompt.workflow: true` + clarification gate (cek data/subject/event/time scope).
- `forecast.enabled: true` (`max_horizon: 12`).
- `anomaly.enabled: true`.
- `upload_to_s3.enabled: true`.
- `hooks.csv_upload_reminder` **retired** (sekarang keputusan agent, bukan hook).
- `dsn_env: WAREHOUSE_URL` (konvensi lokal bpom-neo; deployment pakai
  `IBA_DATABASE_DSN`).

## Catatan WIP (penting)

Snapshot ini menangkap **working tree apa adanya**, BUKAN murni HEAD `e0ffafd`.
File-file berikut berbeda dari HEAD karena modifikasi belum ter-commit:

```
 M SEEKNAL_ASK.md
 M context/forecast_guide.md
 M context/forecast_recipes.md
 M seeknal/skills/bpom-analyst/SKILL.md
 M seeknal/skills/bpom-forecaster/SKILL.md
 M seeknal_agent.yml
?? seeknal/skills/detect-anomaly/   (skill baru, belum di-git add)
```

Untuk baseline murni ter-commit, kembalikan file-file di atas ke versi HEAD
`e0ffafd` sebelum membandingkan, atau ambil via
`git show e0ffafd:<path>` / `git stash` sebelum snapshot.

## Perbedaan kunci vs baseline sebelumnya (after-refactor-f8d34b0)

| Aspek | f8d34b0 (Fase 1) | e0ffafd (snapshot ini) |
|-------|------------------|------------------------|
| Jumlah skill | 5 | 6 (tambah `detect-anomaly`) |
| `bpom-forecaster` | orchestrator forecast penuh | thin-trigger, lock AutoETS (FC2c) |
| Forecast compute | di-skill | di engine (iba-forecast), skill cuma trigger |
| Anomaly detection | tidak ada | enabled, route ke engine |
| `forecast_guide.md` | versi awal | + period inference + stock vs flow |
| CSV export | hook `csv_upload_reminder` (auto per query) | keputusan agent satu-kali (FC2d) |
| `SEEKNAL_ASK.md` | 279 baris (Fase 1) | v8 orchestrator, 8675 B |

## Hubungan dengan snapshot lain

- `../pre-refactor-1dd55d9-notsystemprompt/` — baseline awal (era deklaratif,
  18 Jun). Untuk A/B "sebelum vs sesudah seluruh refactor".
- `../after-refactor-f8d34b0-notsystemprompt/` — baseline Fase 1 (25 Jun).
  Untuk A/B "Fase 1 vs forecast+anomaly era".

Folder non-`notsystemprompt` lama (`after-refactor-f8d34b0`, `pre-refactor-1dd55d9`,
`pre-refactor-ask-notsystemprompt`, `before-rollback-2026-07-02`) sudah di-prune
saat snapshot ini dibuat — varian `notsystemprompt` dianggap kanonik.

## Cara regenerasi (dari working tree bpom-neo)

```bash
SRC=seeknal-bpom-neo
DEST=docs/context_recap/testing_refactor/after-forecast-anomaly-refactor-notsystemprompt

mkdir -p "$DEST"/{context,skills,seeknal}
cp "$SRC"/SEEKNAL_ASK.md "$SRC"/seeknal_agent.yml "$DEST"/
cp "$SRC"/context/*.md "$DEST"/context/
cp -r "$SRC"/seeknal/skills/* "$DEST"/skills/

# symlinks konvensional
ln -sf ../../../../.env      "$DEST/.env"
ln -sf ../../../../.seeknal  "$DEST/.seeknal"
ln -sf ../skills             "$DEST/seeknal/skills"

# bersihkan artifact Windows ADS (kalau ada)
find "$DEST" -name '*:Zone.Identifier*' -delete
```
