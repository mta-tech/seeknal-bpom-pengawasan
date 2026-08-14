# Temuan Database Pengawasan — Data Understanding Lengkap

Dokumentasi ini adalah hasil **deepdive data understanding** terhadap database `pengawasan` (schema `public`) sistem pengawasan iklan BPOM. Setiap angka berasal dari query langsung ke database, bukan asumsi.

## Snapshot verifikasi

| Item | Nilai |
|---|---|
| Snapshot tanggal | **`sync = 2026-08-12 23:23:43`** (main), `2026-08-12 23:24:49` (ketidaksesuaian) |
| Sifat data | ETL mirror harian dari sistem RPO — **bukan** database operasional real-time |
| Policy | Live SQL tetap otoritatif. ETL refresh setiap hari → angka dapat bergeser ±sedikit tiap hari. Dokumen ini merekam snapshot 2026-08-12 |

## Ringkasan eksekutif (10 temuan paling penting)

1. **`akhir` dikunci komoditi** — kolom `kesimpulan_penilaian_akhir` hanya terisi untuk 3 komoditi (ROKOK, OBAT, KOSMETIKA). Empat komoditi lain (PRODUK PANGAN, OBAT TRADISIONAL, SUPLEMEN KESEHATAN, OBAT KUASI) 100% bernilai string `'Null'`. Tingkat kepatuhan tidak boleh dihitung dari `akhir` tanpa memisahkan komoditi.
2. **String `'Null'` ≠ SQL NULL** — semua kolom verdict memakai string 4-karakter `'Null'`, bukan SQL NULL. `WHERE ... IS NULL` mengembalikan **0 baris**. Harus `= 'Null'` atau `<> 'Null'`.
3. **Hukum derivasi verdict 100% valid**: `IF komoditi IN (ROKOK,OBAT,KOSMETIKA) THEN akhir = COALESCE(pusat, balai)`. Saat `akhir` terisi, selalu sama dengan `pusat` jika pusat terisi (91.819 baris), atau sama dengan `balai` jika pusat 'Null' (27.773 baris). **0 anomali** dari 183.968 baris.
4. **PRODUK PANGAN workflow terpotong** — 100% event PANGAN berhenti di status 4 (`pusat - MT Pembuatan SPK`), tidak pernah mencapai direktur atau status 999 (selesai). Backlog 33.777 event yang menggantung.
5. **ROKOK cliff Januari 2025** — dari 1.665 event/Desember 2024 menjadi 18 event/Januari 2025 (drop 98.9% dalam satu bulan). Breakpoint kebijakan, bukan tren menurun.
6. **`direktur_pusat` adalah flag biner {0,1}**, BUKAN durasi hari. 187.556 baris bernilai 0, 2.244 bernilai 1, 47.121 NULL. Siapa pun yang menghitung avg/median "durasi direktur→pusat" dari kolom ini akan keliru.
7. **Self-approve 95.9% institusional** — di 172.180 event yang punya catatan draft dan spv_1, 165.184 di-supervisi oleh **orang yang sama** yang membuat draft-nya. Kontrol pemisahan tugas di balai praktis tidak ada.
8. **`agg` basis tanggal = `tgl_end`** — kubus pre-aggregated diagregasi per tanggal SELESAI pengawasan, BUKAN tanggal mulai. Cocok 100% per bulan dengan main jika dipasangkan via `tgl_end`. Trend dari agg akan bias kalau dianalisis via `tgl_start`.
9. **Multi-product hanya OBAT & KOSMETIKA** — 1 event bisa memuat banyak produk (max 40) HANYA untuk OBAT (sweep apotek) dan KOSMETIKA. Lima komoditi lain 100% 1 event = 1 produk. Grain pengawasan tidak setara antar komoditi.
10. **64.982 id hantu di log/timeline** — ada 64.982 id di `mv_pengawasan_log`/`mv_pengawasan_timeline` yang tidak ada di `mv_pengawasan`. 7.343 di antaranya bertahun 2023+ (status draft/ditolak). Hipotesis: mekanisme retensi aktif vs audit — main hanya memuat event aktif, log/timeline menyimpan riwayat lengkap termasuk yang sudah diarsipkan setelah dilaporkan.

## Struktur dokumentasi

| File | Isi |
|---|---|
| `00_connection_contract_dan_smoke_test.md` | Aturan koneksi, smoke test wajib, question→table router, metode schema discovery andal. **Mencegah kegagalan mode "tidak menemukan tabel"** |
| `01_arsitektur_dan_grain.md` | Sifat ETL mirror, schema public vs dimension, ERD, grain hierarchy, lensa interpretasi |
| `02_tabel_mv_pengawasan.md` | Profil 16 kolom tabel utama, semua unique value, hukum verdict, struktur `lokasi_iklan` 2-field |
| `03_tabel_log_workflow.md` | Log transisi status, dictionary `status_code × label × trx_steps`, process mining, self-approve |
| `04_tabel_timeline_durasi.md` | Timeline milestone + durasi, `direktur_pusat`=flag, backlog PANGAN, status 8/9 anomali |
| `05_tabel_agg_kubus.md` | Kubus pre-agg, basis `tgl_end`, periode paralel, `last_updated` |
| `06_tabel_ketidaksesuaian.md` | 6 klasifikasi non-conformity, 100% PRODUK PANGAN, multi-klasifikasi per event |
| `07_tabel_coverage_target.md` | `coverage_balai` 88×514, `target_balai` 2024-saja, struktur regulasi embedded |
| `08_komoditi_master_axis.md` | **Capstone**: matriks 7 komoditi × semua dimensi, 3 cluster perilaku |
| `09_verdict_rules_reversal.md` | Hukum COALESCE, reversal asimetris per komoditi, hierarki severity |
| `10_data_quality_catalog.md` | Katalog 13+ isu kualitas data dengan angka + sebab + dampak |
| `11_sinapsis_prediksi.md` | Tabel "connecting the dots" — prediksi silang antar-kolom |
| `12_honest_gaps.md` | Hal-hal yang TIDAK bisa dijawab database ini (butuh sumber RPO/domain) |
| `13_sql_audit_trail.md` | Semua query reproducible sebagai bukti setiap klaim |
| `14_pola_pertanyaan_user_dan_vocabulary.md` | Analisis 340 pertanyaan real user KAI: statistik topik, vocabulary mapping user→kolom, 10 template pertanyaan berulang |
| `15_ekspektasi_informasi_dan_boundary.md` | Matriks ekspektasi user vs ketersediaan data, boundary sistem (neo/pemeriksaan/pengujian/eksternal), template honest response |
| `16_sql_pairs_user_pengawasan.md` | 20 pasangan pertanyaan user → SQL valid → ekspektasi jawaban (khusus DB `pengawasan`) |

## Cara membaca

- **Analyst baru**: mulai dari `00` (koneksi) → `01` (arsitektur) → `08` (capstone komoditi) → baru tabel detail.
- **Yang ingin koreksi context/skill**: lihat `10_data_quality_catalog.md` §"Bug di context/skill existing".
- **Yang butuh bukti SQL**: buka `13_sql_audit_trail.md`, setiap klaim punya query.
- **Yang ingin tahu batas database**: baca `12_honest_gaps.md` sebelum bertanya hal yang tak bisa dijawab.
- **Yang ingin paham pertanyaan user production**: baca `14_pola_pertanyaan_user_dan_vocabulary.md` (vocabulary) → `15_ekspektasi_informasi_dan_boundary.md` (ekspektasi vs ketersediaan) → `16_sql_pairs_user_pengawasan.md` (SQL siap pakai).

## Catatan kejujuran

- Semua angka bersifat **snapshot 2026-08-12**. ETL refresh harian → angka akan bergeser.
- 6 hal **tidak dapat dijawab** dari database ini sendiri (lihat `12_honest_gaps.md`) — butuh akses ke sumber RPO atau konfirmasi domain expert BPOM.
- Dokumentasi ini bersifat **observatif murni** — semua aturan (hukum COALESCE, cluster komoditi, dst) disimpulkan dari pola data, bukan dari spesifikasi sistem.
