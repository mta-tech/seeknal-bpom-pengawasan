# 10 — Katalog Kualitas Data + Bug di Context/Skill Existing

Dua bagian: (A) isu kualitas data intrinsik, (B) **bug di context/skill existing** yang bisa sebabkan jawaban salah.

---

## Bagian A — Isu Kualitas Data Intrinsik (13 isu terverifikasi)

| # | Isu | Angka | Sebab / Sifat | Dampak |
|---|---|---|---|---|
| 1 | **String `'Null'` ≠ SQL NULL** (verdict) | 64.391+2.832+55.889 | artefak ETL | `IS NULL`→0 baris; pakai `= 'Null'` |
| 2 | `akhir` hanya 3 komoditi | 64.391 baris (35%) | desain ETL | compliance all-komoditi salah |
| 3 | **PRODUK PANGAN stop status 4** | 33.777 (100%) | proses bisnis | backlog tersembunyi |
| 4 | **ROKOK cliff Jan 2025** | 1.665→18/bln | kebijakan | trend putus |
| 5 | pendaftar corrupt | 23.455 self-concat + 5.773 address leak | ETL self-concat | over-count 8,8% |
| 6 | lokasi_iklan 2-field + embed | 49.101 dua-bagian + 998 >1000 char | struktur tersembunyi | butuh parse |
| 7 | nomor_surat 7 pola | 49.050 sentinel (27%) | format campuran | filter dulu |
| 8 | **`direktur_pusat` biner** | 187.556 nol | flag, bukan durasi | avg/median salah |
| 9 | tanggal_proses NULL | 304.697 (16,8%) | pekat di status 0 & 4 | path mining tak reliable |
| 10 | casing nama_balai/komoditi | log=Title, main=UPPER | ETL | UPPER() wajib saat join |
| 11 | 64.982 id ghost | 7.343 di 2023+ | arsip-after-report | join dari main |
| 12 | self-approve 95,9% | institusional | governance | SoD lemah |
| 13 | dimension schema rusak | 4/5 tabel | star-schema gagal | jangan dipakai |

### Detail isu #1 — String 'Null' (paling kritis)

Lihat `09_verdict_rules_reversal.md` untuk aturan lengkap. Ringkas: `WHERE ... IS NULL` di kolom verdict = **0 baris**. Harus `= 'Null'` / `<> 'Null'`.

### Detail isu #5 — pendaftar corrupt

Tiga pola sistematis:
- **Self-concat** (23.455 baris): `PT KONIMEX` → `PT KONIMEXPT KONIMEX`. Deteksi: `LEFT(pendaftar, len/2) = RIGHT(pendaftar, len/2)`.
- **Multi-space**: `KONIMEX   INDONESIA` (spasi ganda/triple).
- **Address leakage** (5.773 baris): nama + alamat tumpah.

Normalisasi kasar: `regexp_replace(upper(pendaftar), '[^A-Z0-9]', '', 'g')`. Hasil: 6.584 mentah → 6.001 normal (8,8% inflasi).

### Detail isu #8 — `direktur_pusat` biner

Lihat `04_tabel_timeline_durasi.md`. Hanya {0, 1, NULL}. **Bukan durasi hari.** Avg/median "durasi direktur→pusat" dari kolom ini = keliru total.

### Detail isu #11 — id ghost

64.982 id di log/timeline tak di main. **7.343 di 2023+** (bukan murni historis). Status: draft-only (4.879) / ditolak (1.187+773). Catatan log ghost 2023+ normal (bukan deletion marker) → hipotesis: mekanisme retensi aktif vs audit.

---

## Bagian B — ⚠️ BUG DI CONTEXT/SKILL EXISTING (wajib dikoreksi)

Saat membaca ulang `context/` (3 file) + `seeknal/skills/` (4 file), ditemukan **15+ kesalahan penulisan** yang bisa sebabkan jawaban salah atau mode kegagalan. Bagian ini didokumentasikan tapi **belum dikoreksi** (sesuai instruksi: hanya buat docs/temuan_database dulu).

### Bug Tier 1 — FAKTUAL SALAH (menghasilkan angka salah)

#### Bug B1: `IS NULL` / `IS NOT NULL` pada verdict — SYSTEMIC (4 file)

| File | Baris | Salah | Seharusnya |
|---|---|---|---|
| `context/predikat.md` | §3-DEFAULT | "filter `IS NOT NULL`" untuk "sudah dinilai" | `<> 'Null'` |
| `context/filter_code_reference.md` | L89 | "NULL: 64.379" (ambigu) | string 'Null' 64.391 |
| `context/filter_code_reference.md` | L101 | `WHERE kesimpulan_penilaian_akhir IS NOT NULL` closure "sudah dinilai" | `<> 'Null'` |
| `context/filter_code_reference.md` | L177 | `WHERE kesimpulan_penilaian_akhir IS NULL` pivot "belum_dinilai" | `= 'Null'` |
| `seeknal/skills/bpom-pengawasan-analyst/SKILL.md` | L74 | `COUNT(*) FILTER (WHERE kesimpulan_penilaian_akhir IS NULL) AS belum_dinilai` | `= 'Null'` |

**Dampak**: Untuk pertanyaan "hasil pengawasan", agen mengikuti SKILL L74 → query `IS NULL` → 0 baris → lapor "0 belum dinilai, 100% sudah dinilai". Kebalikan dari kenyataan (48,8% belum dinilai di 2026).

#### Bug B2: "22 target unmatched" — SALAH (6 tempat)

| File | Baris |
|---|---|
| `context/data_architecture.md` | L30, L63 |
| `context/predikat.md` | L158 |
| `context/filter_code_reference.md` | L159 |
| `seeknal/skills/bpom-pengawasan-target/SKILL.md` | L17, L150 |

**Realitas**: dengan `UPPER()` di kedua sisi, **0 unmatched**. Klaim ini menyebabkan agen mengecualikan 154 baris target yang seharusnya match.

#### Bug B3: `direktur_pusat` dideskripsikan sebagai durasi (3 file)

| File | Baris | Salah |
|---|---|---|
| `context/data_architecture.md` | L87 | "direktur ke pusat (median 0, max 1)" |
| `seeknal/skills/bpom-pengawasan-timeline/SKILL.md` | L17 | "direktur_pusat: median 0, max 1 — JANGAN DIARTIKAN sangat cepat" |
| `seeknal/skills/bpom-pengawasan-timeline/SKILL.md` | L28-42 | Trap 2 masih framed sebagai duration |

**Realitas**: flag biner {0,1}, BUKAN durasi. Agen report "median 0 hari direktur→pusat" = menyesatkan.

#### Bug B4: `akhir` sebagai default verdict — BERBAHAYA

`context/predikat.md` §3-DEFAULT menyuruh pakai `kesimpulan_penilaian_akhir` untuk "lulus vs gagal".

**Realitas**: `akhir` hanya terisi 3 komoditi (ROKOK/OBAT/KOSMETIKA). 4 lain (PANGAN/OT/SUPLEMEN/KUASI = 63.417 baris) 100% 'Null'. Agen diam-diam drop 34% data.

#### Bug B5: `jenis_pembuat_iklan` "82% kosong, hindari" — menyesatkan

`context/predikat.md` §5-WARNING + `context/filter_code_reference.md` §5.

**Realitas**: 100% terisi untuk PANGAN, 0% lain. Analisis pembuat-iklan-pangan keliru didiskualifikasi.

### Bug Tier 2 — GAP LEVEL ANALISIS (penyebab mode kegagalan "tidak temukan tabel")

#### Gap B6: Tidak ada SMOKE TEST di Gate

`SEEKNAL_ASK.md` Gate 0-5 tidak punya langkah verifikasi koneksi. Agen baru tahu koneksi bermasalah di tengah eksekusi → thrashing. **Solusi**: lihat `00_connection_contract_dan_smoke_test.md`.

#### Gap B7: Connection contract vogue

`SEEKNAL_ASK.md` L9-13: "Connection is supplied by the runtime environment." Tidak menyebut database name (`pengawasan`), schema (`public`), atau anchor verifikasi. Agen tak punya reference.

#### Gap B8: Tidak ada question→table router

Untuk "hasil pengawasan", agen harus rakit sendiri dari 3 file context. Tidak ada peta langsung. Agen yang load parsial kehilangan jejak. **Solusi**: router di `00`.

#### Gap B9: Metode schema discovery tidak dispesifikkan

Context tidak bilang: pakai `pg_catalog.pg_class` (always visible), BUKAN `information_schema.tables` (privilege-aware → 0 baris kalau role tak di-grant). Agen yang fallback ke information_schema → salah simpul "tidak ada tabel".

#### Gap B10: Skill hanya handle happy path

Semua 4 skill langsung `FROM mv_pengawasan` tanpa diagnose "what if error". Stop rule "probe 0 baris 2x → stop" tidak mendiagnosa WHY.

### Bug Tier 3 — DATA BASI (snapshot 2026-08-10, live 2026-08-12)

Semua angka di 3 context + contoh SQL off ±2 hari. Contoh:
- `predikat.md` §1: 183.953 → realitas **183.968**
- `predikat.md` §1: 172.165 → **172.180**
- `predikat.md` §1: 9.738 → **9.742**
- `predikat.md` §3: akhir 'Null' 64.379 → **64.391**
- verdict counts di `filter_code_reference.md` §3 semua off sedikit.

### Bug Tier 4 — TEMUAN PENTING YANG SAMA SEKALI TIDAK ADA DI CONTEXT

| Temuan (dari deepdive ini) | Dampak jika tak ada |
|---|---|
| Hukum `akhir = COALESCE(pusat, balai)` 100% | Agen tak tahu aturan derivasi |
| PANGAN stop status 4 (0% selesai) | "Pangan selesai?" dijawab salah |
| ROKOK cliff Jan 2025 | Trend rokok tanpa konteks breakpoint |
| agg basis `tgl_end` (bukan tgl_start) | Trend dari agg bias temporal |
| Self-approve 95,9% institusional | Governance blind spot |
| lokasi_iklan struktur 2-field `"A""B"` | Parsing lokasi kehilangan setengah data |
| NIE prefix multi-komoditi (bukan 1:1) | Taksonomi produk salah |
| `akhir` hanya 3 komoditi (Cluster A/B/C) | Compliance all-komoditi salah |
| 7.343 id ghost 2023+ (bukan murni historis) | Salah teori retensi |
| Reversal asimetris per direktorat | Bias direktorat tak terlihat |

---

## Rangkuman: bagaimana bug saling mengunci

Kegagalan IBA ("0 data, tidak ada tabel operasional") dan jawaban salah ("100% sudah dinilai") **bukan satu penyebab tunggal**. Ini hasil kombinasi:

1. **Bug B1** (`IS NULL` verdict) → query verdict `IS NULL` mengembalikan 0 → angka "belum dinilai" jadi 0.
2. **Gap B6/B9** (tidak ada smoke test + discovery vogue) → saat query pertama gagal/error, agen tidak punya prosedur → fallback ke schema discovery yang salah metode → "tidak ada tabel".
3. **Gap B7/B8** (connection vogue + tidak ada router) → agen tak punya anchor concrente.

**Solusi komprehensif**: file `00_connection_contract_dan_smoke_test.md` (sudah ditulis) menutup Gap B6-B9. Koreksi Bug B1-B5 (di context/skill) — ditunda sampai instruksi lanjutan.

## Bukti SQL
Lihat `13_sql_audit_trail.md` §10 untuk verifikasi setiap bug.
