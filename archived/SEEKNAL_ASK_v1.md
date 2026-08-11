# seeknal-bpom-neo Ask Context

This project connects to a BPOM (Badan Pengawas Obat dan Makanan) read-only
PostgreSQL database (`rpo_v2`) containing product registration data for processed
foods and food additives (BTP). Users are BPOM analysts.

## Context discovery

Two tools exist for different context types. Use both in every session:

| Tool | Accesses | Use when |
|---|---|---|
| `list_context_files` → `read_project_file` | `context/` — hand-written business knowledge | Need business definitions, data quality rules, code resolution, domain concepts |
| `list_source_context` → `read_source_context` | `.seeknal/context/sources/` — generated DB schema docs | Need table structure, column types, row counts, profiling |

**At the start of every BPOM data question**, call `list_context_files` and load
the files relevant to the question before writing any SQL. These files live at
project root `context/` — `list_context_files` will find them there. Key files:

- `context/business_glossary.md` — what NIE, permohonan, BTP, AMDK, Garam Beryodium mean
- `context/data_quality_rules.md` — mandatory filters, exclusions, date column rules
- `context/code_resolution.md` — how to resolve coded columns to human-readable labels
- `context/forecast_guide.md` — how to use the `forecast_permohonan` table

Do NOT use `list_source_context` as a substitute for business knowledge — it only
contains database schema, not business meaning.

## Critical routing: NIE vs Permohonan

These are DIFFERENT metrics. Never confuse them.

| | NIE / Izin Edar | Permohonan |
|---|---|---|
| Measures | Issued licenses | Applications submitted |
| Count column | `COUNT(DISTINCT nomor)` | `COUNT(DISTINCT produk_id)` |
| Date column | `tanggal` | `tanggal_bayar` |
| User terms | "izin edar", "NIE", "izin terbit" | "permohonan", "registrasi", "pengajuan" |

## Data architecture

ERBA = E-Registrasi Baru (new system). ERLA = E-Registrasi Lama (legacy system).
Both cover all product types — this is a system-generation distinction, not geographic.

| System | Tables |
|---|---|
| ERBA (E-Registrasi Baru) | `t_produk_3_erba`, `t_btp_3_erba`, `m_trader_rba` |
| ERLA (E-Registrasi Lama) | `t_produk_3_rilis_erla`, `t_btp_3_erla`, `m_trader_rla` |
| Reference | `data_dictionary`, `forecast_permohonan` |

- All tables are in `warehouse.public.*`
- No `t_produk_3_erla` table — use `t_produk_3_rilis_erla`
- For full coverage, UNION ERBA and ERLA tables
- ERLA valid statuses include `'0099'` (not in ERBA)
- ERLA NIE filter includes `'304'` in jenis_permohonan (not in ERBA)
- `kategori_dokumen` and `status_komitmen` exist only in ERBA

## Query behavior (non-negotiable)

- **Always execute SQL and show actual data.** Never describe what you would query.
- **Never say "kendala teknis"** or "masalah eksekusi". Fix the SQL and retry.
- **Resolve all coded columns** before presenting results. See `context/code_resolution.md`.
- **Default limit**: top 10 results unless user specifies otherwise.
- **Show SQL** if the user asks for it.
- **Fix errors**: if a query fails, read the error, fix it, retry up to 3 times.

## SQL pairs

`seeknal/sql_pairs/*.yml` contains verified queries for common questions. They are
reference examples — consult them when you are uncertain about the correct approach
for a known query pattern. Do not treat them as mandatory first steps.

## Guardrails

- Never save passwords, DSNs, API keys, or tokens.
- Conclusions must cite actual query results — never answer from schema guesses.
- One-off filters stay in the chat; save only reusable business logic via `write_project_file`.
