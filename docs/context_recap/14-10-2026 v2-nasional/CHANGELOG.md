# CHANGELOG — `14-10-2026 v2-nasional` (pengawasan nasional)

**Tanggal:** 14 Oktober 2026
**Turunan:** `13-10-2026 v1-nasional` (draft) — dipromosikan + diadaptasi
**Verifikasi:** live `staging` via `pengawasan_reader` · diff live≡snapshot kosong

## Dasar perubahan

`v1-nasional` disusun dari template regional dan **belum pernah diterapkan**; ia masih membawa sisa aturan regional yang faktual salah untuk akun nasional (`pengawasan_reader`, semua balai):

1. **"view" di ±20 titik** (context + skills) — akun nasional memakai `fact_pengawasan`, bukan view balai. Semua diarahkan ulang ke fakta.
2. **Skills analyst**: "Riwayat approval/log/timeline tidak ada di akun ini" — **salah** (terbukti ter-grant: `fact_pengawasan_approval` ±1,87 jt baris; `fact_pengawasan_narasi` ±211 rb baris). Diganti: riwayat tahapan tersedia; durasi antar-tahap via `lag(created_at)`.
3. **Skills forecaster & detect-anomaly**: "view hanya satu balai" — salah untuk nasional. Diganti: fakta memuat semua balai (termasuk PUSAT); pertanyaan per-balai wajib filter `balai_id`; baris DEMO sudah dibersihkan di sumber.
4. **`95-batas-domain.md`**: baris `balai_id` "view sudah satu balai — tidak perlu" → "pertanyaan per-balai/lintas balai: filter wajib". Contoh kalimat NOT COVERED diganti ke kasus yang benar untuk nasional (naskah/materi iklan).
5. **`30-vonis.md` / `60` / `70`**: "ditolak" kini diajarkan sebagai dua jalur (keluarga `TMK*` pada kolom vonis, atau `trx_steps LIKE 'ditolak_%'` di approval); durasi & riwayat tahapan dinyatakan tersedia.
6. **`SEEKNAL_ASK.md` scope**: klaim "semua `fact_*` (termasuk riwayat approval), log/timeline" tidak tersedia — dikoreksi menjadi hanya `target_balai`, `coverage_balai`, objek domain lain.
7. **Nama tool klarifikasi**: `request_clarification` → **`ask_clarification`** (skills + ASK).

## Isi baru (dari draft, tetap)

- `context/35-sisi-pusat.md`, `70-atribusi-kasus.md`, `97-glossary-istilah-user.md`, `forecast_guide.md` — 4 halaman yang belum ada di live sebelumnya.

## Yang sengaja TIDAK berubah

- Arsitektur akun (`fact_pengawasan` + approval + narasi; 15 bridge; 15 dim tanpa `dim_master_data`).
- Kontrak tool forecast/anomaly/chart/S3.

## Belum dikerjakan (sesi lanjutan)

- UAT smoke end-to-end via agent hidup (angka acuan nasional).
- Batch testcase NPPZA.
