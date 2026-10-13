# Snapshot `14-10-2026 v2-nasional` — context & skill pengawasan nasional

**Tanggal potong:** 14 Oktober 2026
**Turunan:** `13-10-2026 v1-nasional` (draft, belum pernah aktif) + adaptasi wajib fakta nasional
**Sumber:** folder aktif (live) `seeknal-bpom-pengawasan` — akun `pengawasan_reader` (semua balai)

## Status

Potongan langsung dari folder aktif **setelah promosi + adaptasi** (PR promosi v1-nasional). Draft `v1-nasional` tidak pernah aktif — snapshot ini adalah **versi pertama yang diterapkan ke live**.

**Diverifikasi: live ≡ snapshot** — diff kosong untuk `context/`, `skills/`, `SEEKNAL_ASK.md`, dan `seeknal_agent.yml` (14 Okt 2026).

## Isi

```
14-10-2026 v2-nasional/
├── SEEKNAL_ASK.md        # orchestrator: scope auth nasional + PAGE MAP
├── seeknal_agent.yml     # harness: tool_call_limit 40, temperature 0.5, read_max_lines 200
├── context/              # 15 halaman (termasuk forecast_guide)
├── skills/               # 4 skill
└── seeknal/skills        # symlink -> ../skills
```

## Adaptasi vs `v1-nasional` (draft)

| Area | Perubahan |
|---|---|
| context (11 halaman) + skills | semua rujukan "view" → fakta nasional (`fact_pengawasan`) — akun nasional tidak memakai view balai |
| skills analyst | "riwayat approval/log/timeline tidak ada" → **salah**: riwayat tahapan tersedia di `fact_pengawasan_approval`; durasi antar-tahap dihitung via `lag(created_at)` |
| skills forecaster/detect-anomaly | "view hanya satu balai" → fakta memuat **semua balai**; pertanyaan per-balai wajib filter `balai_id` |
| `95-batas-domain.md` | baris `balai_id`: "tidak perlu" → **filter wajib** untuk pertanyaan per-balai; contoh kalimat diganti (naskah iklan) |
| `30-vonis.md` · `60` · `70` | "ditolak" = dua jalur (TMK* atau `trx_steps LIKE 'ditolak_%'`); durasi & riwayat tahapan tersedia |
| `SEEKNAL_ASK.md` | scope dikoreksi: `fact_pengawasan_approval`/`narasi` TERSEDIA (bukan "semua fact_* tidak tersedia") |
| skills + ASK | `request_clarification` → **`ask_clarification`** |

## Verifikasi

- Sweep frasa regional ("view", "satu balai", "tidak ada di akun ini") → **bersih**.
- Identitas live ≡ snapshot: diverifikasi 14 Okt 2026.
