#!/usr/bin/env python3
"""Periksa manifes halaman context terhadap database domain ini.

Tiga pemeriksaan:
  1. tiap tabel & kolom di manifes ADA di database;
  2. tiap literal nilai ADA PERSIS di data, termasuk spasi dan kapitalisasinya;
  3. tiap kolom berkode di database MUNCUL di manifes salah satu halaman,
     atau terdaftar di ABAIKAN sebagai sengaja tidak diajarkan.

Menyertakan KONTROL NEGATIF: nama karangan harus dilaporkan tidak ditemukan.
Tanpa kontrol itu lulus, hasil pemeriksaan tidak boleh dipercaya.

Pakai:  WAREHOUSE_URL=postgresql://... python3 periksa_manifes.py [context_dir]
Keluar dengan kode 1 bila ada pelanggaran.
"""
import os
import re
import sys

try:
    import psycopg2
except ImportError:
    sys.exit('psycopg2 belum terpasang')

DSN = os.environ.get('WAREHOUSE_URL')
if not DSN:
    sys.exit('WAREHOUSE_URL belum diset — ambil dari .env, jangan tulis kredensial di berkas ini')

CTX = sys.argv[1] if len(sys.argv) > 1 else 'context'

# kolom yang sengaja TIDAK diajarkan: id internal, indeks array, stempel baris
ABAIKAN = {
    'sync', 'last_updated', 'id', 'id_balai', 'id_kabupaten', 'id_steps', 'idx', 'rn',
    'created_at', 'updated_at', 'posisi_dalam_array', 'criteria_index',
}

cn = psycopg2.connect(DSN)
cn.set_session(readonly=True, autocommit=True)
cu = cn.cursor()

cu.execute("""select table_name, column_name from information_schema.columns
              where table_schema='public'""")
rows = cu.fetchall()
TABEL = {t for t, _ in rows}
KOLOM = {c for _, c in rows}

# kolom berkode: kardinalitas terkendali -> layak diajarkan
cu.execute("""select s.tablename, s.attname from pg_stats s
              join information_schema.columns k on k.table_schema='public'
                   and k.table_name=s.tablename and k.column_name=s.attname
              where s.schemaname='public'
                and k.data_type in ('text','character varying')
                and s.n_distinct between 2 and 200""")
BERKODE = {(t, c) for t, c in cu.fetchall() if c not in ABAIKAN}


cu.execute("""select table_name, column_name from information_schema.columns
              where table_schema='public' and data_type in ('text','character varying')""")
TEKSKOL = [(t, c) for t, c in cu.fetchall() if c not in ABAIKAN]


def ada_persis(nilai):
    for t, c in TEKSKOL:
        cu.execute(f'select 1 from "{t}" where "{c}" = %s limit 1', (nilai,))
        if cu.fetchone():
            return True
    return False


manifes = {}
for fn in sorted(os.listdir(CTX)):
    if not fn.endswith('.md'):
        continue
    teks = open(os.path.join(CTX, fn), encoding='utf-8').read()
    m = re.search(r'<!-- MANIFES\s*(.*?)-->', teks, re.S)
    if not m:
        continue
    blok = {}
    for baris in m.group(1).strip().split('\n'):
        if ':' not in baris:
            continue
        k, v = baris.split(':', 1)
        v = v.strip()
        blok[k.strip()] = [] if v == '-' else [x.strip() for x in v.split(',') if x.strip()]
    manifes[fn] = blok

langgar = []

# --- 1 & 2
terdaftar = set()
for fn, blok in manifes.items():
    for t in blok.get('tabel', []):
        if t not in TABEL:
            langgar.append(f'[1] {fn}: tabel `{t}` tidak ada di database')
    for c in blok.get('kolom', []):
        if c not in KOLOM:
            langgar.append(f'[1] {fn}: kolom `{c}` tidak ada di database')
        terdaftar.add(c)
    for v in blok.get('nilai', []):
        if not ada_persis(v):
            langgar.append(f'[2] {fn}: nilai {v!r} tidak ada persis di data')

# --- 3
for t, c in sorted(BERKODE):
    if c not in terdaftar:
        langgar.append(f'[3] kolom berkode `{t}`.`{c}` tidak muncul di manifes halaman mana pun')

# --- kontrol negatif
kontrol = []
if 'kolom_karangan_xyz' in KOLOM:
    kontrol.append('nama kolom karangan justru ditemukan — alat rusak')
if ada_persis('NILAI KARANGAN YANG TIDAK MUNGKIN ADA XYZ'):
    kontrol.append('nilai karangan justru ditemukan — alat rusak')

print(f'Halaman bermanifes : {len(manifes)}')
print(f'Kolom berkode      : {len(BERKODE)}')
print(f'Kontrol negatif    : {"LULUS" if not kontrol else "GAGAL — " + "; ".join(kontrol)}')
print()
if kontrol:
    print('Pemeriksaan dibatalkan: kontrol negatif gagal, hasil tidak bisa dipercaya.')
    sys.exit(2)
if langgar:
    print(f'PELANGGARAN: {len(langgar)}')
    for x in langgar:
        print('  ' + x)
    sys.exit(1)
print('Tidak ada pelanggaran.')
cn.close()
