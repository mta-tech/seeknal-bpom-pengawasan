# 11 — Sinapsis: Prediksi Silang Antar-Kolom (Connecting the Dots)

> File ini adalah **peta prediksi**: jika kamu tahu nilai satu kolom, kamu bisa memprediksi nilai/perilaku kolom lain. Setiap baris adalah "jembatan knowledge" yang terverifikasi dari data.

## Tabel sinapsis utama

| Jika tahu… | Maka prediksi… | Karena |
|---|---|---|
| `komoditi` ∈ {ROKOK, OBAT, KOSMETIKA} | `kesimpulan_penilaian_akhir` terisi (bukan 'Null') | ETL sinkron `akhir` hanya untuk 3 komoditi Cluster A |
| `komoditi` = PRODUK PANGAN | `akhir`='Null', `jenis_pembuat_iklan` terisi, ada ketidaksesuaian | Flow pangan terminal di pusat, verdict di balai |
| `komoditi` = OBAT KUASI | `kesimpulan_penilaian_balai`='Null' | Verdict eksklusif di pusat (Cluster C kontrarian) |
| `komoditi` = ROKOK | `nie` kosong (100%), `media_iklan`=MEDIA_LUARRUANG (91%), `akhir` terisi, 100% selesai, 1 event=1 produk | Regulasi rokok khusus |
| `komoditi` ∈ {OBAT, KOSMETIKA} | 1 event bisa banyak produk (multi-produk) | Sweep monitoring (apotek display) |
| `komoditi` ∈ {PANGAN, OT, SUPLEMEN, KUASI} | 1 event = 1 produk pasti | Per-instance monitoring |
| `media_iklan` = ELEKTRONIK | `lokasi_iklan` = URL platform atau `"platform""url"` | Struktur 2-field lokasi |
| `media_iklan` = MEDIA_LUARRUANG | `lokasi_iklan` = alamat jalan | ROKOK dominan |
| `media_iklan` = MEDIA_LAIN + `lokasi_iklan` seperti `"SCTV""SCTV"` | Ini iklan TV | Pola entri TV concat stasiun |
| `balai` MK & `pusat` TMK | `akhir` = TMK (reversal) | Pusat otoritas final |
| `balai` TMK & `pusat` MK | `akhir` = MK (reversal) | Pusat otoritas final |
| `status_code` = 0 atau 4 | `tanggal_proses` mungkin NULL | Tahap draft/pusat jarang catat waktu |
| `id` di log tapi tak di main | Event 2023+ = draft-only/ditolak (diarsip setelah dilaporkan) | Retensi aktif vs audit |
| `id` pra-2023 di log | Tidak akan ada di main | Main dibatasi ≥2023 |
| `prefix NIE` (NA/MD/SD…) | Komoditi (indikatif, BUKAN deterministik) | Prefix multi-komoditi |
| `direktur_pusat` = NULL | `tanggal_kirim_direktur` = NULL, `kabalai_direktur` = NULL | Event belum sampai direktur |
| `trx_steps` ∈ {draft, spv_1} | 95,9% orangnya SAMA | Self-approve institusional |
| `komoditi` = ROKOK & tahun 2025+ | Volume event drop 98,9% | Breakpoint kebijakan Jan 2025 |

## Cluster perilaku (3 cluster verdict)

```
Cluster A (akhir terisi):    ROKOK · OBAT · KOSMETIKA
                              → compliance dari `akhir` = COALESCE(pusat, balai)

Cluster B (akhir='Null',     PRODUK PANGAN · OBAT TRADISIONAL · SUPLEMEN
        balai terisi):        → compliance dari `balai` (pangan) atau `pusat` (OT/SUPLEMEN)

Cluster C (akhir='Null',     OBAT KUASI (kontrarian)
        balai='Null'):         → compliance dari `pusat` saja
```

## Matrix prediksi komoditi × media × struktur

| Komoditi | media dominan | lokasi_iklan bentuk | NIE | jenis_pembuat |
|---|---|---|---|---|
| KOSMETIKA | ELEKTRONIK 82% | URL platform / `"platform""url"` | NA-prefix dominan | kosong |
| ROKOK | LUARRUANG 91% | alamat jalan | kosong (by design) | kosong |
| PRODUK PANGAN | ELEKTRONIK 60% | `"Indomaret""Kembang Seri"` / URL | MD/ML-prefix | **TERISI 100%** |
| OBAT | ELEKTRONIK 48% | `"Apotek""Jl..."` / URL | DT/DB/DK-prefix | kosong |
| OT | ELEKTRONIK 77% | URL / `"Toko""Jl..."` | TR/HT-prefix | kosong |
| SUPLEMEN | ELEKTRONIK 74% | URL platform | SD/SI/SL-prefix | kosong |
| OBAT KUASI | ELEKTRONIK 81% | URL platform | QD/QL-prefix | kosong |

## Prediksi workflow completion

| Komoditi | % selesai (999) | terminal di mana | verdict sah di kolom |
|---|---|---|---|
| ROKOK | 100% | selesai | akhir |
| OBAT KUASI | 99,8% | selesai | pusat |
| OT | 99,8% | selesai | pusat/balai |
| SUPLEMEN | 99,8% | selesai | pusat/balai |
| OBAT | 97,8% | selesai / status 4 (2,2%) | akhir |
| KOSMETIKA | 79,7% | selesai / status 4 (3,2%) | akhir |
| **PRODUK PANGAN** | **0%** | **status 4 (terminal)** | **balai** |

## Prediksi konsentrasi pemutus

| Komoditi | pemutus utama | key-person risk |
|---|---|---|
| ROKOK | Daryani (~95%) | tinggi |
| KOSMETIKA | Sulistyowati + Tita | dua orang |
| OBAT | Rina + Franciska | dua orang |
| OT + KUASI + SUPLEMEN | **Lia Amalia (1 org)** | **sangat tinggi** |

## Aturan inferensi turunan

Dari sinapsis di atas, beberapa aturan formal bisa diturunkan untuk validasi data:

1. **Invariant `akhir`**: `IF komoditi NOT IN (ROKOK,OBAT,KOSMETIKA) THEN kesimpulan_penilaian_akhir = 'Null'` (100% valid, 0 counter-example).
2. **Invariant `akhir` Cluster A**: `IF komoditi IN (ROKOK,OBAT,KOSMETIKA) AND akhir <> 'Null' THEN akhir = COALESCE(pusat, balai)` (100% valid).
3. **Invariant `ROKOK`**: `IF komoditi = 'ROKOK' THEN nie IN ('','--','-') AND media_iklan IN ('MEDIA_LUARRUANG','MEDIA_LAIN')` (100% valid).
4. **Invariant `OBAT KUASI`**: `IF komoditi = 'OBAT KUASI' THEN kesimpulan_penilaian_balai = 'Null'` (100% valid).
5. **Invariant `direktur_pusat`**: `IF direktur_pusat IS NULL THEN tanggal_kirim_direktur IS NULL AND kabalai_direktur IS NULL` (100% valid).

Aturan-aturan ini bisa dipakai sebagai **assertion test** untuk mendeteksi data quality drift antar snapshot ETL.

## Cara pakai sinapsis ini

- **Validasi query**: sebelum jalankan query kompleks, cek apakah filter konsisten dengan sinapsis (mis. jangan filter `komoditi='ROKOK' AND nie<>'--'` — akan 0 baris).
- **Forecast anomali**: jika trend ROKOK tiba-tiba naik 2025+, cek apakah ada perubahan kebijakan (sinapsis bilang cliff Jan 2025).
- **Data entry check**: jika satu baris melanggar invariant (mis. PANGAN dengan `akhir`='MK'), itu data anomaly — flag untuk review.
- **Query optimization**: banyak query bisa disederhanakan dengan memakai sinapsis (mis. tak perlu `COALESCE(pusat,balai)` untuk PANGAN — langsung pakai `balai`).
