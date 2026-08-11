# Varian A — MINIMAL

**Hipotesis (H1):** model flash bingung karena VOLUME & kepadatan context (file 15-20KB, korpus
~120KB). Dengan korpus kecil terstruktur, jawaban lebih akurat & konvergen antar-run.

**Desain:** context/ hanya 3 file inti — `predikat.md` (aturan hitung/filter), 
`filter_code_reference.md` (peta kode), `data_architecture.md` (trim ~3.5KB) — plus 2 file
forecast. SEEKNAL_ASK ~3KB. Skill analyst tipis 5-langkah. Sisanya diarsip di `_archive/`
(tidak terlihat `list_context_files`).

**Harness (sama di A/B/C, beda dari baseline):** kompaksi deterministik ON, `request_limit: 30`,
prompt generik seeknal OFF. Lihat `docs/planning/2026-07-15-three-hypothesis-experiment.md`.
