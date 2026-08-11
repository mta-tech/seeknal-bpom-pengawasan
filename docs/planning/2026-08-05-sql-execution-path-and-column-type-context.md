# seeknal-bpom-neo: Jalur Eksekusi SQL & Peta Tipe Kolom — Pembagian Peran Context vs Engine

**Document type:** Audit Findings + Context Change Plan
**Project:** seeknal-bpom-neo (BPOM RPO Analytics Agent)
**Status:** Implemented 2026-08-05 — lihat §9 untuk catatan pelaksanaan
**Terbatas pada varian:** `after-forecast-chart-enhance` · `after-forecast-chart-enhance-diffuse` (varian lain di `after-chart-030826/` sengaja tidak disentuh sebagai pembanding)
**Date:** 2026-08-05
**Scope berkas (usulan):** `context/data_architecture.md` · `context/predikat.md` (rujukan silang saja) · `skills/bpom-analyst/SKILL.md`
**Spec engine pendamping:** `iba-deploy-runbook/specs/2026-08-05-spec-sqlr-seeknal-pg-query-routing.md`
**Melanjutkan:** `docs/planning/2026-08-04-context-mapping-fidelity-and-coverage-closure.md`
**Bukti:** batch `seeknal/tests/outputs/2026-08-05/v1-after-chart/` (`20260805_014839`, `20260805_022446`) · ±20 query verifikasi langsung ke `rpo_v2`

---

## 1. Ringkasan Eksekutif

Batch 2026-08-05 menghasilkan **12 timeout dari 48 run**. Penelusuran menunjukkan penyebabnya
bukan penalaran agent dan bukan harness test, melainkan **jalur eksekusi SQL**: satu query yang
diselesaikan Postgres dalam ~1 detik memakan 35–48 detik lewat DuckDB `postgres_scanner`.

Dokumen ini menetapkan **pembagian peran yang tegas**, karena salah menaruh perbaikan justru
berisiko membuat sistem lebih buruk:

| Persoalan | Diperbaiki di | Alasan |
|---|---|---|
| **Ke mana query dieksekusi** (performa) | **Engine** (spec SQLR) | Keputusan deterministik. Tidak boleh bergantung pada kepatuhan LLM per-panggilan. |
| **Kolom mana bertipe apa** (kebenaran) | **Context** (dokumen ini) | Pengetahuan domain yang stabil. Persis jenis fakta yang terbukti dipatuhi 90–100% bila diserahkan sebagai tabel. |

**Yang TIDAK dilakukan di context, beserta alasannya (§3)**: mengajari agent membungkus query
dengan `postgres_query(...)`. Secara teknis terbukti bekerja (35,93 s → 2,28 s, lolos validator
keamanan seeknal), tetapi ditolak karena menaruh keputusan performa deterministik di komponen
probabilistik.

---

## 2. Temuan yang mendasari

### 2.1 Waktu turn habis di dalam tool, bukan di LLM

Pembedahan satu turn nyata `UAT-LC-EXP-RISIKO-1` (varian `after-forecast-chart-enhance`):

| | Turn 1 | Turn 2 |
|---|---|---|
| Wall clock | 109,0 s | 77,4 s |
| **Di dalam tool call** | **79,5 s (73%)** | **67,2 s (87%)** |
| LLM + harness | 29,5 s (27%) | 10,2 s (13%) |
| `execute_sql` | 6× = 74,9 s (rata² 12,5 s) | 2× = 34,3 s (rata² 17,1 s) |

Instrumentasi internal seeknal mencatat query tunggal **33.806 ms** dan **32.916 ms**.

### 2.2 Hipotesis "hasil tool terlalu besar" — terbantah

Sempat diduga penyebabnya adalah menangkap hasil tool berisi ribuan baris JSON. Diuji atas
**773 tool call** dari kedua batch:

| Metrik | Nilai |
|---|---|
| Median hasil tool | **239 karakter** |
| Hasil terbesar (seluruh run) | 16 KB — dan itu `read_project_file`, bukan SQL |
| Hasil `execute_sql` terbesar | **2,4 KB** |
| Total seluruh hasil `execute_sql`, 2 batch | 65 KB |

Agent menulis query agregasi, jadi yang kembali 4–20 baris. Biaya penangkapannya nol. **Yang mahal
bukan hasilnya besar, melainkan query-nya lama menghitung.**

### 2.3 Akar: agregasi tidak didorong ke sumber

Pengukuran SQL identik, hasil diverifikasi identik:

| Jalur | Waktu |
|---|---|
| `psql` langsung | 1,13 s |
| DuckDB `postgres_scanner` (jalur agent) | 48,51 s |
| DuckDB tanpa cast (pushdown-friendly) | 1,32 s |
| `postgres_query()` passthrough | 0,97 s |

Penting: membuat SQL pushdown-friendly **tidak selalu menolong**. Pada query `UAT-LC-AKTIF-1`
versi tanpa cast justru **lebih lambat** (44,78 s → 51,60 s), karena `COUNT(DISTINCT nomor)` tetap
dihitung DuckDB secara lokal sehingga kolom tetap wajib menyeberang. Ini menutup opsi
"ajari agent menulis SQL tanpa cast" sebagai strategi performa.

### 2.4 Tipe kolom: penyebab 75% kegagalan pemindahan eksekusi

332 SQL unik yang benar-benar ditulis agent diuji parse+plan di PostgreSQL: **312 (94,0%) jalan apa
adanya**. Dari 20 yang gagal, **15 (75%) berakar pada tipe kolom**, bukan dialek:

| Penyebab | Jumlah |
|---|---|
| `operator does not exist: text = integer` | 10 |
| `UNION types text and timestamp cannot be matched` | 3 |
| `UNION types text and bigint cannot be matched` | 2 |
| dialek murni (ORDER BY, syntax) | 4 |
| `date_trunc(unknown, text)` | 1 |

Ini menjadikan peta tipe kolom bukan sekadar kenyamanan — ia prasyarat agar perbaikan engine
mencapai cakupan penuh.

---

## 3. Keputusan: kenapa routing TIDAK ditaruh di context

Opsi termurah secara permukaan adalah menulis aturan: *"bungkus query analitik dengan
`postgres_query('warehouse', $q$...$q$)`"*. Sudah diuji — lolos `validate_sql_for_agent` dan
bekerja lewat REPL asli (35,93 s → 2,28 s, hasil identik). Tetap ditolak, karena empat alasan:

**(1) Matematika kepatuhan.** Kepatuhan aturan deklaratif di proyek ini terukur ~90%. Satu turn
berisi 6–25 query, dan **satu query lolos saja sudah membakar ~40 detik** dari budget 400:

| Query per turn | Peluang semua patuh (@90%) |
|---|---|
| 5 | 59% |
| 10 | 35% |
| 20 | 12% |

**(2) Bukti dari audit kita sendiri.** `docs/audit_context/2026-07-29-uat-compact-execution/01-compact-V.md`
mendokumentasikan aturan yang **dibaca lalu dilanggar**: §16 (`UAT-MD-1`) — `predikat §12-C` ada
byte-identik di kedua varian, trace menunjukkan agent membacanya, lalu tetap menjumlah partisi
bulanan dan salah; §10 (`UAT-KOMITMEN-VARIASI-1`) — §5 dibaca lalu Case A/B tertukar. Laporan itu
menyimpulkan sendiri: *"variabilitas ketaatan LLM, bukan context yang kekurangan aturan."*

**(3) Bertentangan dengan prinsip context yang sudah kita tetapkan.** Aturan context harus
**general dan topic-level**, bukan resep prosedural yang terikat satu mekanisme engine. Instruksi
`postgres_query` akan usang begitu router engine aktif, dan berpotensi menabraknya.

**(4) Beban sintaksis.** Nesting quoting `$q$...$q$` di dalam SQL yang di-generate adalah sumber
salah tulis; kegagalannya memicu retry yang justru membakar waktu lagi.

> **Prinsip yang diambil:** context memuat **apa yang benar tentang data**; engine memutuskan
> **bagaimana dan di mana query dijalankan**. Menukar keduanya membuat sistem lebih rapuh.

---

## 4. Perubahan context yang diusulkan

Mengikuti prinsip yang terbukti di `2026-08-04-context-mapping-fidelity-and-coverage-closure.md` §1:
**serahkan jawabannya, jangan perintahkan penurunannya** (kepatuhan 90–100% bila daftar lengkap
diberikan, vs ~20% bila hanya aturan naratif). Maka isi perubahan adalah **tabel**, bukan imbauan.

### 4.1 Peta tipe kolom ERBA vs ERLA → `context/data_architecture.md`

**Fakta pokok yang harus dinyatakan lebih dulu:**

> `t_produk_3_erba` menyimpan **seluruh** kolom sebagai `text`, termasuk tanggal dan id numerik.
> `t_produk_3_rilis_erla` memakai tipe asli (`timestamp`, `bigint`, `double precision`, `boolean`).
> **37 kolom bertipe berbeda antara kedua tabel.**

**Tabel asimetri lengkap (diverifikasi ke `information_schema` 2026-08-05):**

| Kolom | ERBA | ERLA |
|---|---|---|
| `tanggal`, `tanggal_aju`, `tanggal_bayar`, `tanggal_berkas`, `tanggal_diambil`, `tanggal_exp`, `tanggal_exp_hprspb`, `tanggal_hprspb`, `tanggal_lbl`, `last_proses` | `text` | `timestamp` |
| `trader_id`, `pabrik_id`, `produsen_id`, `user_id`, `perbaiki_label`, `single_md`, `td_label`, `td_pengajuan`, `td_penolakan`, `ttd` | `text` | `bigint` |
| `biaya`, `jumlah_bayar`, `nilaif0`, `pmr`, `takaran_saji` | `text` | `double precision` |
| `english`, `hardcopy`, `makanan`, `pending`, `webreg`, `webreg_pgsql` | `text` | `boolean` |
| `status_komitmen`, `sub_kemasan_id`, `kode_kbli`, `ecolabel`, `sni_sukarela`, `jenis_penolakan_komitmen` | `text` | **tidak ada kolomnya** |

**Konsekuensi yang harus dinyatakan eksplisit (ini yang mencegah bug):**

1. Perbandingan tanggal di ERBA **wajib** cast: `NULLIF(tanggal_exp,'')::timestamp`. Di ERLA
   **jangan** di-cast — kolomnya sudah `timestamp`.
2. `trader_id` ERBA butuh `::bigint` untuk perbandingan numerik; ERLA tidak
   (`trader_id <> 3384` langsung).
3. `UNION`/`UNION ALL` antara ERBA dan ERLA **wajib menyamakan tipe di kedua sisi** untuk kolom
   mana pun dari tabel di atas. Ini penyebab 5 kegagalan SQL nyata pada batch 2026-08-05.
4. Enam kolom terakhir hanya ada di ERBA — pertanyaan yang menyentuhnya bersifat **ERBA-only**,
   dan jawabannya wajib menyatakan batasan itu, bukan diam-diam melaporkannya sebagai gabungan.

### 4.2 Fakta format data (memungkinkan SQL yang lebih sederhana dan aman)

Diverifikasi atas seluruh baris, bukan sampel:

| Kolom (ERBA) | Baris kosong | Baris non-ISO |
|---|---|---|
| `tanggal` | 0 | 0 |
| `tanggal_exp` | 0 | 0 |
| `tanggal_bayar` | 0 | 0 |
| `tanggal_aju` | 0 | 0 |
| `tanggal_berkas` | 0 | 0 |
| `trader_id` (non-numerik) | 0 | 0 |

Rentang: `erba.tanggal` `1970-01-01` → `2026-08-04`; `erba.tanggal_exp` `1970-01-01` → `2031-08-04`;
`erla.tanggal_exp` `1900-01-01` → `2031-04-17`.

**Implikasi yang boleh dinyatakan:** karena formatnya ISO `YYYY-MM-DD HH:MM:SS` tanpa kekecualian,
urutan leksikografis = urutan kronologis. Ini menjadikan `tanggal_exp >= '2027-01-01'` setara
dengan versi cast, **dan** menjelaskan kenapa `SUBSTR(tanggal,1,4)` untuk mengambil tahun aman.

> **Catatan penting agar tidak disalahpahami:** fakta ini ditulis sebagai **karakteristik data**,
> bukan sebagai perintah optimasi. Jangan menulis aturan "hindari cast supaya cepat" — sudah
> terbukti tidak konsisten (§2.3) dan performa bukan urusan context.

### 4.3 Rujukan silang, bukan duplikasi

`context/predikat.md` dan `context/filter_code_reference.md` **tidak diubah isinya**. Cukup satu
rujukan dari bagian entity/SQL di `predikat.md` ke peta tipe di `data_architecture.md`, supaya
tidak lahir dua sumber kebenaran yang bisa menyimpang — persoalan "deskripsi kembar" yang sudah
pernah kita alami.

`skills/bpom-analyst/SKILL.md` cukup ditambah satu pointer ke peta tipe pada bagian penulisan SQL.
**Jangan** menyalin tabelnya ke skill.

---

## 5. Risiko perubahan context & mitigasi

Fokus arahan: **jangan sampai perubahan membuat aplikasi lebih buruk.**

| Risiko | Mitigasi |
|---|---|
| Context bertambah panjang → menggeser perhatian dari aturan yang sudah bekerja | Tambahan terkonsentrasi di satu berkas (`data_architecture.md`), berupa tabel padat. Ukur panjang sebelum/sesudah; bandingkan jumlah `read_project_file` per turn di trace. |
| Agent jadi menambah cast di ERLA (over-correction) | Tabel menyatakan **kedua** sisi secara eksplisit, bukan hanya "ERBA itu text". Tambahkan contoh benar/salah untuk ERLA. |
| Dua sumber kebenaran (predikat vs data_architecture) | Rujukan silang satu arah; tabel hanya hidup di satu berkas (§4.3). |
| Fakta tipe berubah bila skema BPOM berubah | Cantumkan tanggal verifikasi + query `information_schema` yang dipakai, agar bisa diperiksa ulang. |
| Perbaikan context dikira menyelesaikan timeout | Dinyatakan eksplisit di §1 dan §3: performa diselesaikan spec SQLR, bukan dokumen ini. |

---

## 6. Verifikasi

Perubahan context ini **tidak boleh diklaim berhasil** berdasarkan pembacaan; wajib dibuktikan
dengan eksekusi nyata (sesuai standar yang sudah kita tetapkan).

- [ ] Jalankan `UAT-v2-compact-V` dan `-VII` pada varian ber-context baru vs varian lama
      (`--variants-path docs/context_recap/after-chart-030826 --workers 1 --timeout 400`)
- [ ] Hitung dari trace: jumlah `describe_table` per turn **turun** (indikator agent berhenti
      menebak tipe kolom)
- [ ] Hitung dari `turns[].sqls`: jumlah SQL yang gagal karena ketidakcocokan tipe pada `UNION`
      **turun menuju 0**
- [ ] Uji ulang kompatibilitas dialek atas korpus SQL baru: target naik dari 94,0% menuju ≥98%
- [ ] Skenario yang sebelumnya PASS **tetap** PASS, dan **angkanya tidak berubah** (bandingkan
      teks jawaban, bukan hanya status)
- [ ] Tidak ada SQL baru yang menambahkan cast pada kolom ERLA yang sudah bertipe benar

---

## 7. Urutan pelaksanaan

1. **Spec SQLR Phase 0–2 lebih dulu** (harness kesetaraan + router + fallback, gate masih OFF).
   Ini menyelesaikan timeout, sehingga pengukuran kualitas context berikutnya tidak lagi tercemar
   run yang mati di tengah jalan.
2. **Perubahan context §4** setelah timeout mereda — barulah efeknya terhadap kualitas jawaban
   bisa diukur jujur.
3. **SQLR Phase 4** (view ternormalisasi) terakhir; ia mengurangi kebutuhan agent menulis cast
   manual, sehingga sebagian isi §4.1 bisa disederhanakan kemudian.

Urutan ini penting: mengubah context saat 25% run masih timeout akan menghasilkan pengukuran yang
tidak bisa ditafsirkan.

---

## 8. Catatan terpisah: harness test & tool eksternal

Dua hal muncul dari investigasi yang sama, di luar cakupan context maupun spec SQLR:

1. **`upload_to_s3` memakan 32,9 detik** untuk satu panggilan ketika stack storage tidak
   terjangkau, dan ia dipanggil di hampir semua skenario. Ini penyumbang timeout kedua setelah
   SQL. Perlu fail-fast + timeout pendek.
2. **`scripts/test_variant_compare.py`** — mekanisme penangkapan tool call yang ditambahkan
   (lanjutan di §9.3)
   2026-08-05 memakai `event_stream_handler` pada `agent.run_sync`, yang **mengubah panggilan
   model dari `generateContent` menjadi `streamGenerateContent`**. Efeknya terhadap durasi belum
   konklusif (median 8,33 s vs 10,43 s, n=3, rentang tumpang tindih) tetapi ia confound yang
   mencemari perbandingan lintas-run. Perbaikannya sudah diverifikasi: bungkus
   `AbstractToolset.call_tool` pada instance toolset — menangkap call + result tanpa menyentuh
   mode request model. Harus diterapkan sebelum batch pembanding berikutnya dijalankan.

---

## 9. Catatan Pelaksanaan (2026-08-05)

### 9.1 Yang diubah

**Engine** (repo `seeknal`, detail di spec SQLR §8): router `_try_pg_route` + gate
`sql_routing.pg_passthrough`, plus perbaikan satu bug pre-existing di `detect_pg_only_namespace`
yang membuat routing **tidak pernah** aktif untuk SQL terkualifikasi realistis.

**Context** — hanya pada dua varian yang diminta, berkas `context/data_architecture.md` saja:

| Varian | Perubahan |
|---|---|
| `after-forecast-chart-enhance` | 4 baris tabel asimetri tipe + aturan UNION + fakta kebersihan data — ringkas, sesuai gaya varian ini |
| `after-forecast-chart-enhance-diffuse` | isi sama, ditulis lebih menjelaskan sesuai gaya varian ini |

Keduanya juga mendapat blok `sql_routing.pg_passthrough: true` di `seeknal_agent.yml`.

`predikat.md`, `filter_code_reference.md`, dan berkas skill **tidak disentuh** — sesuai §4.3, tabel
tipe hanya hidup di satu tempat agar tidak lahir dua sumber kebenaran. Varian lain di
`after-chart-030826/` (`after-forecast-anomaly-refactor`, `-v2`) sengaja dibiarkan sebagai pembanding.

### 9.2 Hasil

Dua skenario yang **sebelumnya TIMEOUT** kini lulus di kedua varian:

| Skenario | Sebelum | Sesudah |
|---|---|---|
| `UAT-LC-EXP-RISIKO-1` | TIMEOUT (enhance) | **PASS** kedua varian |
| `UAT-LC-AKTIF-1` | TIMEOUT **kedua** varian | **PASS** kedua varian (diffuse 83,1 s dari budget 400 s) |

Query tunggal terukur 33,38 s → **0,69 s** dengan baris hasil identik. Cakupan routing atas 332 SQL
nyata: **84,9%**; sisanya jatuh ke jalur DuckDB lama dan tetap menjawab benar.

### 9.3 Yang belum dikerjakan

1. **Verifikasi §6 belum lengkap.** Yang sudah dibuktikan: skenario yang tadinya timeout kini PASS.
   Yang **belum**: batch penuh compact-V + compact-VII untuk memastikan skenario yang sebelumnya
   PASS tidak berubah angkanya, dan hitungan `describe_table` per turn belum dibandingkan.
   Ini harus dijalankan sebelum perubahan context dianggap tuntas.
2. **Confound harness belum diperbaiki** — `test_variant_compare.py` masih memakai
   `event_stream_handler`, jadi panggilan model masih `streamGenerateContent`. Perbandingan batch
   berikutnya sebaiknya menunggu ini dibereskan agar bersih.
3. **Jalur PG belum punya timeout** setara `sql_timeout_seconds` (spec SQLR §8.5) — risiko terbuka.
