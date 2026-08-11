# UAT — 9 pertanyaan uji terhadap skill pengawasan

Snapshot: `sync = 2026-08-10 22:53:15` · Database: `pengawasan` · 9 questions / 7 unique

Setiap jawaban mengikuti Gates 0–5 (SEEKNAL_ASK.md). SQL dieksekusi langsung, angka terverifikasi.

---

## Q1 — "Berapa jumlah pemeriksaan untuk yang memiliki durasi lebih dari 3 hari?"

**Gate 0**: kata "pemeriksaan" tidak ada di domain → honest redirect. Domain skill = `pengawasan`. Asumsi: user maksud **pengawasan dengan durasi pipeline > 3 hari**. Load `bpom-pengawasan-timeline`.

**Gate 1**: durasi yang mana? Ada 3 kolom (`mulai_kabalai`, `kabalai_direktur`, `direktur_pusat`). Asumsi tampilkan semua, user pilih.

**Jawaban** (dari `mv_pengawasan_timeline`, distinct `id_pengawasan`):

| Stage pipeline | Pengawasan dengan durasi > 3 hari |
|---|---|
| `mulai_kabalai` (start → kabalai) | **166.069** dari 236.856 (70%) |
| `kabalai_direktur` (kabalai → direktur) | **177.237** (75%) |
| `direktur_pusat` (direktur → pusat) | **0** (kolom ini mayoritas 0 — data belum terisi, bukan benar-benar cepat) |

**Honest note**: "pemeriksaan" tidak ada di skill ini. Kalau yang dimaksud pemeriksaan fisik lab, domain itu belum terkoneksi.

---

## Q2 — "Berapa total jumlah pengawasan untuk komoditi KOSMETIKA per media"

**Gate 0**: data factual → `bpom-pengawasan-analyst` + `visualize-chart`.
**Gate 1**: entity = "pengawasan" — bisa baris/event/surat. Tampilkan keduanya.

**Jawaban** (dari `mv_pengawasan`, filter `komoditi='KOSMETIKA'`):

| media_iklan | baris produk | event unik |
|---|---|---|
| ELEKTRONIK | 39.861 | 35.768 |
| CETAK | 4.235 | 3.384 |
| MEDIA_LUARRUANG | 4.229 | 3.410 |
| **Total** | **48.325** | **42.562** |

---

## Q3 & Q4 (duplikat) — "Perbandingan pengawasan produk makanan vs obat-obatan, Juli 2025"

**Gate 1 (blocking)**: "obat-obatan" ambiguous. Dua reading:
- (a) `OBAT` saja
- (b) family farmasi (`OBAT` ∪ `OBAT TRADISIONAL (OT)` ∪ `OBAT KUASI` ∪ `SUPLEMEN KESEHATAN`)

Skill **harus meminta klarifikasi**. Asumsi (a) untuk demo:

| komoditi | baris | event unik |
|---|---|---|
| PRODUK PANGAN | 1.122 | 1.122 |
| OBAT (saja) | 852 | 694 |

**Versi family (b)** untuk perbandingan: PRODUK PANGAN 1.122 baris vs family farmasi 1.610 baris.

---

## Q5 & Q6 (duplikat) — "Total pengawasan KOSMETIKA di media elektronik"

**Gate 0–2**: langsung, semua anchor ada di `filter_code_reference.md` §1 & §4.

**Jawaban**:

| entity | angka |
|---|---|
| baris produk | **39.861** |
| event unik | 35.768 |
| surat unik | 2.255 |

---

## Q7 — "Total pengawasan komoditi KOSMETIKA"

**Jawaban**:

| entity | angka |
|---|---|
| baris produk | **48.325** |
| event unik | 42.562 |
| surat unik | 2.515 |

---

## Q8 — "Tren jumlah hasil uji TMS 2023–2025"

**Gate 1 (blocking)**: **"TMS" tidak ada di data**. Verified: `WHERE kesimpulan_* ILIKE '%TMS%'` = 0 baris. Yang ada hanya `MK` / `TMK`.

Skill **harus meminta klarifikasi**: apakah maksudnya `TMK` (Tidak Memenuhi Keputusan)?

**Jika user konfirmasi TMK**, tren dari `kesimpulan_penilaian_akhir`:

| tahun | TMK | MK | belum dinilai |
|---|---|---|---|
| 2023 | 16.774 | 13.226 | 0 |
| 2024 | 21.932 | 24.748 | 0 |
| 2025 | 7.519 | 19.919 | 0 |

**Honest note**: 2025 data sampai snapshot (Agustus 2026 ada, tapi pertanyaan sampai 2025). Tahun 2025 mungkin tidak lengkap di snapshot tertentu — perlu verify.

---

## Q9 — "Trend pengawasan iklan OBAT 2024–2025 by verifikasi pusat"

**Gate 1**: "obat" → `OBAT` saja atau family? Asumsi `OBAT` saja.
**Gate 2**: kolom = `kesimpulan_penilaian_pusat` (sesuai "verifikasi pusat").

**Jawaban** (order by tahun, lalu count):

| tahun | kesimpulan_penilaian_pusat | baris |
|---|---|---|
| 2024 | NULL (belum dinilai pusat) | 7.472 |
| 2024 | TMK | 864 |
| 2024 | MK | 741 |
| 2025 | NULL | 7.910 |
| 2025 | TMK | 814 |
| 2025 | MK | 729 |

**Honest note**: ~80% baris OBAT tidak punya verdict pusat (NULL). Severity grade (`TMK KRITIKAL/MAYOR/MINOR`) bisa di-split kalau user minta.

---

## Ringkasan pola yang terjawab oleh skill

| Pola pertanyaan | Skill yang load | Status |
|---|---|---|
| Durasi/SLA pipeline | `bpom-pengawasan-timeline` | ✓ terjawab + honesty trap `direktur_pusat` |
| Breakdown by komoditi × dimensi | `bpom-pengawasan-analyst` | ✓ terjawab |
| Klarifikasi istilah informal ("obat-obatan", "pemeriksaan") | Gate 1 `bpom-pengawasan-analyst` | ✓ trigger `request_clarification` |
| Kode tidak dikenal ("TMS") | Gate 2 path P5 NOT COVERED | ✓ honest "tidak ada, perlu klarifikasi" |
| Trend multi-tahun by verdict | `bpom-pengawasan-analyst` + `visualize-chart` | ✓ terjawab |
| Partial-year disclosure | Gate 5 CHECK list | ✓ applied |

## Pola yang belum teruji di 9 pertanyaan ini

- `bpom-pengawasan-target` (target vs realisasi) — tidak ada pertanyaan target di list
- Ketidaksesuaian klasifikasi (6 kategori) — tidak ada pertanyaan
- `COUNT(DISTINCT pendaftar)` dengan cleansing — tidak ada pertanyaan

Untuk coverage penuh, perlu tambah ≥1 pertanyaan per skill yang belum teruji.
