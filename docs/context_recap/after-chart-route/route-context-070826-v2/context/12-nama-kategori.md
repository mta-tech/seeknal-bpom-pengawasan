Nama kategori — probe teks bebas untuk segmen: kopi instan, sirup berperisa, mi instan, red wine, serbuk

Keterisian `nama_kategori` **berbeda jauh antar sistem** — periksa dulu (`00-menghitung.md` §5),
lalu **probe kedua sistem**. Sisi yang katalognya lebih lengkap sering bukan yang diduga; jangan
memperlakukannya sebagai kolom satu sistem.

## Prosedur tiga langkah

```sql
-- 1. TEMUKAN nilai persisnya (sekali, berlingkup, pakai LIMIT)
SELECT nama_kategori, COUNT(*) FROM t_produk_3_erba
WHERE nama_kategori ILIKE '%<istilah>%' GROUP BY 1 ORDER BY 2 DESC LIMIT 20;
-- ulangi pada t_produk_3_rilis_erla

-- 2. PUTUSKAN lebarnya dari pertanyaan (lihat "menutup set" di bawah)

-- 3. HITUNG dengan kecocokan persis
WHERE nama_kategori = '<nilai persis>'          -- atau IN ('<a>','<b>') bila konsepnya majemuk
```

**Jangan menghitung lewat ILIKE.** Pola menjaring nilai tetangga yang tidak ditanya, dan
selisihnya tidak terlihat di hasil — query tetap jalan dan angkanya tetap masuk akal.

## Nilai yang sudah terverifikasi persis

| Konsep | Nilai `nama_kategori` |
|---|---|
| Kopi instan | `'Kopi Instan'` (juga ada `'Kopi Instan Dekafein'`) |
| Sirup berperisa | `'Sirup Berperisa'` — ada tetangga `'Sirup Encer Berperisa'`, populasinya bisa lebih besar |
| Mi instan | `'Mi Instan'` (juga `'Mi Instan Lainnya'`) |
| Anggur merah | `'Still Grape Wine Merah / Anggur Merah (Red Wine)'` — panjang, ada garis miring & kurung |
| Minuman serbuk berperisa | `'Minuman Serbuk Berperisa (Tidak Berkarbonat)'` |

## Menutup set — bagian yang paling sering meleset

Satu ILIKE biasanya cocok ke beberapa nilai, dan **nilai-nilai itu tidak setara**:

- **Terlalu sempit.** "Kopi" mencakup Kopi Bubuk, Kopi Instan, Minuman Kopi, Biji Kopi, Kopi Celup,
  Minuman Serbuk Kopi. Menjawab "berapa produk kopi" dengan baris Kopi Instan saja adalah versi
  teks-bebas dari mengambil satu kode dari sebuah set.
- **Terlalu lebar.** Kategori bersaudara yang namanya hanya beda satu kata bisa lebih besar
  daripada yang diminta — melebarkan pola bisa membalik urutan besaran. Pola juga menjaring nama
  yang hanya memuat kata itu sebagai bagian ("Bumbu Penguat Rasa dan Garam" bukan garam).
- **Ejaan bervariasi dalam kolom yang sama** (mis. varian *i/y* pada istilah serapan) — dua nilai
  untuk satu gagasan; pola yang berlabuh pada satu ejaan kehilangan yang lain. Baca daftar hasil
  probe, jangan berasumsi ejaannya seragam.

Lebarnya ditentukan **pertanyaan**, bukan kemiripan string. **Sebutkan nilai-nilai yang dipakai**
di jawaban supaya lingkupnya terlihat. Benar-benar ambigu → tanya (Gate 1), jangan menebak.

## Bila nol baris

Jangan mempermutasi kata kunci. Nol dari satu sistem bisa berarti namespace/katalog berbeda —
periksa sistem satunya. Nol dari keduanya setelah probe yang wajar → jawab "tidak ditemukan"
dengan jujur.

Untuk jawaban sensitif atas suatu segmen (pencabutan, pembatalan), periksa sekilas `nama`/`merk`
baris yang cocok dan laporkan baris yang tidak termasuk segmen itu.

## Rute

- Nilai persis sudah ketemu dan memetakan bersih ke kode → **KEMBALI** `11-kode-segmen.md`,
  hitung dengan kodenya (lebih murah, bisa dipakai ulang).
- **KEMBALI** ke `10-segmen-produk.md` untuk aturan lintas dimensi (segmen × negara, segmen × kemasan).
