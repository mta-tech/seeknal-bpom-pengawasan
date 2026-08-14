# 12 — Honest Gaps: Apa yang TIDAK Bisa Dijawab Database Ini

> Dokumen ini mencatat batas pengetahuan yang bisa diperoleh dari database `pengawasan` sendirian. **Setiap gap di sini butuh sumber lain** (sistem RPO hulu, konfirmasi domain expert BPOM, atau dokumentasi sistem) untuk dijawab. Berhenti berpetualang dengan query kalau pertanyaan masuk kategori ini — jawab honest "tidak dapat dijawab dari database ini".

## Gap Tier 1 — TIDAK BISA dijawab dari DB ini (butuh sumber eksternal)

### Gap 1: Penyebab pasti ROKOK cliff Januari 2025

**Fenomena terverifikasi**: ROKOK drop dari 1.665 event/Desember 2024 menjadi 18/Januari 2025 (98,9% dalam satu bulan). Pola pasca-cliff ~18-30 event/bulan.

**Yang TIDAK ada di DB**: tidak ada kolom keterangan kebijakan, flag perubahan mandat, atau catatan regulatory change. Hanya terlihat breakpoint.

**Hipotesis (tak terverifikasi)**:
- BPOM berhenti monitoring rutin iklan rokok (alih mandat?)
- Perubahan regulasi rokok efektif 1 Jan 2025
- Sumber data RPO berubah scope

**Cara menjawab**: tanya domain expert BPOM / cek regulasi eksternal / cek dokumentasi sistem RPO. **Jangan fabrikasi alasan dari DB ini.**

---

### Gap 2: Mengapa `akhir` hanya disinkron untuk 3 komoditi

**Fenomena terverifikasi**: `kesimpulan_penilaian_akhir` hanya terisi untuk ROKOK, OBAT, KOSMETIKA (Cluster A). Empat komoditi lain 100% 'Null' meski workflow komplit (OT/SUPLEMEN/KUASI 99,8% selesai).

**Yang TIDAK ada di DB**: aturan ETL hulu tak terlihat. Tidak ada metadata "kolom ini di-sync dari tabel X untuk direktorat Y".

**Hipotesis**: 3 komoditi Cluster A dikelola direktorat yang pakai field `akhir`; 4 komoditi lain dicatat di `balai`/`pusat` saja di sistem sumber.

**Cara menjawab**: inspeksi pipeline ETL / skema RPO sumber. **Jangan asumsi aturan dari pola data saja.**

---

### Gap 3: Aturan arsip-after-report untuk 7.343 id ghost 2023+

**Fenomena terverifikasi**: 7.343 id di log/timeline bertahun 2023+ tidak ada di main. Status: draft-only (4.879), ditolak (1.187+773). Catatan log mereka NORMAL (bukan deletion marker): *"Telah masuk di rekapitulasi laporan"*, *"Mohon dilanjutkan"*, *"Entri Data oleh..."*.

**Yang TIDAK ada di DB**: tidak ada kolom `status_arsip`, `deleted_at`, atau flag retensi.

**Hipotesis terkuat**: main = event aktif, log/timeline = audit lengkap termasuk event draft/ditolak yang sudah diarsipkan setelah dilaporkan. Tapi **tak terkonfirmasi**.

**Cara menjawab**: tanya tim ETL / bandingkan langsung dengan RPO sumber. **Bukan ETL bug** (kemungkinan besar), tapi belum pasti apakah retensi sengaja atau kebocoran filter.

---

### Gap 4: Tafsir asli `direktur_pusat`

**Fenomena terverifikasi**: hanya {0, 1, NULL}. 0=187.556, 1=2.244, NULL=47.121. Berkorelasi 100% dengan `tanggal_kirim_pusat IS NOT NULL`.

**Yang TIDAK ada di DB**: dokumentasi makna kolom. Hanya inferensi.

**Hipotesis**: flag "sudah sampai pusat" (1) atau "belum" (0). NULL = belum sampai direktur.

**Cara menjawab**: dokumentasi sistem RPO. Sementara itu, **perlaku sebagai flag biner, bukan durasi**.

---

### Gap 5: Makna embedded record `lokasi_iklan` >1.000 karakter

**Fenomena terverifikasi**: 998 baris `lokasi_iklan` panjangnya >1.000 karakter, berisi rekaman multi-kolom terkombinasi (nomor urut, tanggal, media, produk, NIE, klaim, pendaftar, verdict) — terlihat seperti dump record lengkap.

**Yang TIDAK ada di DB**: dokumentasi struktur embedded ini. Tidak ada delimiter yang konsisten (mix tab, newline, kutip).

**Cara menjawab**: inspeksi satu-per-satu (sample 10-15 baris) untuk infer marker, ATAU tanya tim ETL dari mana field ini di-populate. **Untuk aggregate, exclude baris >1.000 char agar tidak men-skew distinct count.**

---

### Gap 6: Status 8 & 9 di timeline (3 baris aneh)

**Fenomena terverifikasi**: timeline punya `status=8` (1 baris) dan `status=9` (2 baris) yang TIDAK ada di dictionary log.

| id | tgl_start | status | mulai_kabalai | kabalai_direktur |
|---|---|---|---|---|
| 184603 | 2025-06-02 | 9 | 1 | 8 |
| 73307 | 2023-06-25 | 8 | 10 | 16 |
| 98994 | 2024-02-05 | 9 | 3 | 52 |

**Yang TIDAK ada di DB**: label untuk kode 8 & 9 di timeline. Event-nya normal (ada durasi), tapi status tak terdaftar.

**Hipotesis**: artefak ETL langka, atau kode internal yang tak ter-propagasi ke log. Bisa diabaikan tapi dilaporkan.

---

## Gap Tier 2 — BISA di-DB tapi belum dieksekusi lengkap (priority rendah)

Hal-hal yang masih bisa digali dari DB tapi belum sempurna:

### Gap 7: Per-balai self-approve concentration (deteksi kolusi lokal)

Sudah ada sampel 8 balai. Belum lengkap untuk 84 balai. Bisa query full untuk identifikasi balai dengan self-approve >95% (indikator kolusi).

### Gap 8: 2 event OBAT dengan >20 produk — error atau sweep apotek besar?

Sampel: id=122895 punya 14 baris dengan 1 NIE saja (14 produk sama NIE). Apakah ini data entry error atau memang 14 produk berbeda yang kebetulan NIE-nya tidak terisi? Perlu inspeksi.

### Gap 9: Pola `catatan` lengkap per `trx_steps`

Sudah diketahui kualitatif (ok/ACC/stamp/oleh:nama). Belum dikuantifikasi per step. Bisa jadi insight "apa yang ditulis auditor di tahap X".

### Gap 10: Nomor surat `OTHER` (1.389 baris) & `HAS_COMMA` (21 baris)

Sudah terkategori tapi belum di-inspeksi sample. Kemungkinan address leak atau format aneh.

### Gap 11: Full matriks NIE prefix × komoditi (semua prefix)

Sudah dapat 50+ prefix tapi belum lengkap. Ada prefix langka (`Ad`, `Am`, `De`, `Di`, `Ke`, `Ki`, `Kr`, `Lu`, `Mi`, `Pi`) yang belum di-klasifikasi.

---

## Gap Tier 3 — Batas desain database (bukan gap, tapi batas permanen)

### Tidak ada kolom ini di database (jangan fabrikasi)

- `provinsi` — hanya ada `kabupaten_kota` di `coverage_balai`
- `klaim` / `risk_grade` — tidak ada kolom risk
- `laboratory_result` — hasil lab tak ada di pengawasan (di database `pengujian` terpisah)
- `petugas` tabel — struktur org direkonstruksi dari `fullname` + `trx_steps` di log
- `budget` / `biaya` — tidak ada data finansial
- `foto` / `evidence_file` — tidak ada attachment

**Aturan**: kalau user nanya hal di atas, jawab honest "tidak ada di database pengawasan". Jangan fabrikasi kolom.

### Frasa user → honest response (dari 340 pertanyaan production KAI)

User production nyata-nyata menanyakan konsep yang tak tersedia. Gunakan template ini (lengkap di `15_ekspektasi_informasi_dan_boundary.md`):

| Frasa user | Frek KAI | Honest response singkat |
|---|---|---|
| **sarana produksi** | 21x | "Tidak tersedia di DB pengawasan. `pendaftar` = registrant/pemohon izin, BUKAN produsen. Data produsen ada di registrasi `neo` / Cek BPOM." |
| **produsen** | 13x | Idem di atas — `pendaftar` ≠ produsen |
| **jenis pangan** | 9x | "Ada di database registrasi `neo` (`t_produk_3_*`), bukan di pengawasan." |
| **kategori pangan** | 9x | Idem — domain neo |
| **provinsi** | 9x | "Hanya `kabupaten_kota` di `coverage_balai`. Tidak ada kolom provinsi." |
| **cek BPOM / cekb pom** | 5x | "Sistem eksternal, tidak terkoneksi ke DB pengawasan. NIE/nama_produk tersedia di main; sarana_produksi tidak." |
| **BKO (bahan kimia obat)** | 3x | "Kolom BKO tidak ada di DB pengawasan." |
| **SIAPik** | 1x | "Sistem eksternal." |
| **rule '9 bulan berikutnya'** | 5x | "Business rule organisasi, belum terdokumentasi di DB. DB hanya simpan tanggal milestone. Perlu klarifikasi basis tanggal deadline." |
| **UPT tidak melaporkan** | 12x | "Bisa dijawab via anti-join `coverage_balai` → `mv_pengawasan` (Pair 7 `16`), tapi butuh definisi periode 'tidak melaporkan'." |

**Aturan**: jangan coba-coba query tabel `sarpras`/`produk` yang tidak ada untuk frasa ini — langsung jawab honest.

### Tidak ada cross-database join

Database `pengawasan`, `pemeriksaan`, `penandaan`, `pengujian` ada di instance yang sama TAPI tidak ter-join di schema. Untuk analisis lintas-domain (mis. "produk yang diawasi DAN ditandai"), butuh orchestrator eksternal.

### Domain lain yang TIDAK dicakup

- **Registrasi pangan / NIE produk pangan olahan** → domain `seeknal-bpom-neo` (beda database, beda tabel `t_produk_3_*`)
- **Pemeriksaan/Pengujian/Sampling lab** → database `pengujian`/`pemeriksaan` terpisah, belum terkoneksi di skill pengawasan
- **Penandaan** → database `penandaan` terpisah

## Aturan kejujuran untuk agen

1. **Jawab honest "tidak tahu"** kalau pertanyaan masuk Gap Tier 1. Lebih baik daripada fabrikasi.
2. **Sebutkan sumber yang dibutuhkan** untuk menjawab (RPO, domain expert, dokumentasi sistem).
3. **Jangan ekstrapolasi** dari pola data ke kesimpulan kausal tanpa verifikasi eksternal.
4. **Dokumentasikan gap baru** yang ditemukan saat analisis ke file ini (append, jangan overwrite).

## Bukti SQL
Lihat `13_sql_audit_trail.md` §12 untuk query yang membuktikan tiap gap.
